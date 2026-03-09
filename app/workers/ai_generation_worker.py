from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Final, List, cast

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.messaging.connection import RabbitMQConnectionManager
from app.messaging.consumer import EventConsumer
from app.messaging.events import EventEnvelope, EventType, create_event_envelope
from app.observability.metrics import incr, timed
from app.models.preferences import Preferences
from app.models.profile import Profile
from app.repositories.preferences import PreferencesRepository
from app.repositories.profile import ProfileRepository
from app.repositories.workout_request import WorkoutRequestRepository
from app.services.gemini import GeminiService
from app.services.outbox import OutboxService

QUEUE_NAME: Final[str] = "ai-generation"
ROUTING_KEY: Final[str] = "workout.context.ready"

logging.basicConfig(level=logging.INFO)
# logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


def _safe_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return cast(Dict[str, Any], value)
    return {}


async def _generate_draft(
    db: Session,
    *,
    profile: Profile,
    preferences: Preferences,
    context_payload: Dict[str, Any],
) -> Dict[str, Any]:
    # Keep AI invocation resilient; fall back to deterministic payload if provider errors.
    default_duration = int(getattr(profile, "workout_duration_minutes", 45) or 45)
    fallback_payload = {
        "focus": "General",
        "duration_minutes": default_duration,
        "exercise_candidates": [],
        "song_candidates": [],
        "source": "fallback_selector_seed",
    }
    try:
        gemini = GeminiService(db, profile, preferences)
        seed_exercises = [
            cast(str, w.get("focus"))
            for w in cast(
                List[Dict[str, Any]], context_payload.get("recent_workouts") or []
            )
            if w.get("focus")
        ]
        ai_response = await gemini.get_workout_draft_recommendations(
            seed_exercises=seed_exercises,
        )
        exercise_candidates = cast(
            List[Dict[str, Any]], ai_response.get("exercise_candidates") or []
        )
        song_candidates = cast(
            List[Dict[str, Any]], ai_response.get("song_candidates") or []
        )
        source = "ai" if exercise_candidates or song_candidates else "fallback_selector_seed"
        if source != "ai":
            incr("ai_draft_fallback_count")
        return {
            "focus": ai_response.get("focus") or "General",
            "duration_minutes": ai_response.get("duration_minutes") or default_duration,
            "exercise_candidates": exercise_candidates,
            "song_candidates": song_candidates,
            "source": source,
        }
    except Exception:
        incr("ai_draft_fallback_count")
        return fallback_payload


async def process_event(message_payload: Dict[str, Any]) -> None:
    logger.info("Received message for AI generation: %s", message_payload)
    envelope = EventEnvelope.model_validate(message_payload)
    incr("ai_worker_received_count")

    request_id = int(envelope.payload["request_id"])
    user_id = int(envelope.payload["user_id"])
    profile_id = int(envelope.payload["profile_id"])

    db: Session = SessionLocal()
    request_repo = WorkoutRequestRepository(db)
    profile_repo = ProfileRepository(db)
    preferences_repo = PreferencesRepository(db)
    outbox_service = OutboxService(db)

    try:
        with db.begin():
            request = request_repo.get_by_id(request_id)
            profile = profile_repo.get_by_id(profile_id)
            preferences = preferences_repo.get_by_profile_id(profile_id)

            if request is None or profile is None or preferences is None:
                with db.begin_nested():
                    if request is not None:
                        request_repo.set_status(
                            request,
                            status="FAILED",
                            error_code="AI_CONTEXT_MISSING",
                            error_message="Missing request/profile/preferences for AI generation",
                        )
                return

            with timed("ai_generation_latency"):
                draft_payload = await _generate_draft(
                    db,
                    profile=profile,
                    preferences=preferences,
                    context_payload=envelope.payload,
                )

            next_event = create_event_envelope(
                event_type=EventType.WORKOUT_DRAFT_GENERATED,
                source="worker.ai_generation",
                payload={
                    "request_id": request_id,
                    "user_id": user_id,
                    "profile_id": profile_id,
                    "draft": draft_payload,
                },
                saga_id=envelope.saga_id,
                correlation_id=envelope.correlation_id,
            )

            with db.begin_nested():
                request_repo.set_status(request, status="DRAFT_READY")
                outbox_service.enqueue_event(
                    event_id=next_event.event_id,
                    routing_key="workout.draft.generated",
                    exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
                    payload=next_event.model_dump(mode="json"),
                )
            incr("ai_worker_success_count")
    except Exception as exc:
        with db.begin():
            request = request_repo.get_by_id(request_id)
            if request is not None:
                request_repo.set_status(
                    request,
                    status="FAILED",
                    error_code="AI_GENERATION_FAILED",
                    error_message=str(exc),
                )
        logger.exception("AI generation failed for request_id=%s", request_id)
        logger.exception(exc)
        incr("ai_worker_failure_count")
    finally:
        db.close()



async def _handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):
        payload = json.loads(message.body.decode("utf-8"))
        await process_event(_safe_json(payload))


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
