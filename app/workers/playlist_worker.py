from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Final, cast

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.messaging.connection import RabbitMQConnectionManager
from app.messaging.consumer import EventConsumer
from app.messaging.events import EventEnvelope, EventType, create_event_envelope
from app.observability.metrics import incr, timed
from app.repositories.preferences import PreferencesRepository
from app.repositories.profile import ProfileRepository
from app.repositories.workout_request import WorkoutRequestRepository
from app.services.outbox import OutboxService
from app.services.playlist_selector import PlaylistSelectorService

QUEUE_NAME: Final[str] = "playlist-generation"
ROUTING_KEY: Final[str] = "workout.draft.generated"


def _safe_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return cast(Dict[str, Any], value)
    return {}


def _resolve_playlist(
    db: Session,
    *,
    profile_id: int,
) -> Dict[str, Any]:
    
    # TODO: The transaction has been closed after the Spotify access token is refreshed. 
    # Need to refactor the code to keep the transaction open until the playlist is generated, 
    # or implement a token refresh mechanism that can work outside of a transaction.
    profile_repo = ProfileRepository(db)
    preferences_repo = PreferencesRepository(db)

    profile = profile_repo.get_by_id(profile_id)
    preferences = preferences_repo.get_by_profile_id(profile_id)
    if profile is None or preferences is None:
        return {}

    try:
        selector = PlaylistSelectorService(db, profile, preferences)
        return selector.shuffle_top_and_recent_tracks(
            fitness_goal=getattr(getattr(profile, "fitness_goal", None), "value", "general_fitness"),
            duration_minutes=getattr(profile, "workout_duration_minutes", 45),
        )
    except Exception:
        return {}


def process_event(payload: Dict[str, Any]) -> None:
    
    envelope = EventEnvelope.model_validate(payload)
    incr("playlist_worker_received_count")

    request_id = int(envelope.payload["request_id"])
    profile_id = int(envelope.payload["profile_id"])

    db: Session = SessionLocal()
    request_repo = WorkoutRequestRepository(db)
    outbox_service = OutboxService(db)

    try:

        with db.begin():
            request = request_repo.get_by_id(request_id)
            if request is None:
                return

            with timed("playlist_generation_latency"):
                playlist = _resolve_playlist(db, profile_id=profile_id)
            next_event = create_event_envelope(
                event_type=EventType.PLAYLIST_READY,
                source="worker.playlist",
                payload={
                    "request_id": request_id,
                    "profile_id": profile_id,
                    "playlist": playlist,
                },
                saga_id=envelope.saga_id,
                correlation_id=envelope.correlation_id,
            )
            with db.begin_nested():
                request_repo.set_status(request, status="PARTIAL_READY")
                outbox_service.enqueue_event(
                    event_id=next_event.event_id,
                    routing_key="playlist.ready",
                    exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
                    payload=next_event.model_dump(mode="json"),
                )
        incr("playlist_worker_success_count")
    except Exception as exc:
        with db.begin():
            request = request_repo.get_by_id(request_id)
            if request is not None:
                request_repo.set_status(
                    request,
                    status="FAILED",
                    error_code="PLAYLIST_GENERATION_FAILED",
                    error_message=str(exc),
                )
        incr("playlist_worker_failure_count")
    finally:
        db.close()


async def _handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):
        body = json.loads(message.body.decode("utf-8"))
        process_event(_safe_json(body))


async def run_worker() -> None:
    manager = RabbitMQConnectionManager(
        amqp_url=settings.RABBITMQ_URL,
        exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
    )
    consumer = EventConsumer(manager)

    await consumer.consume(
        queue_name=QUEUE_NAME,
        routing_key=ROUTING_KEY,
        handler=_handle_message,
    )


if __name__ == "__main__":
    asyncio.run(run_worker())
