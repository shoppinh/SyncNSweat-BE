from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Final, List, Optional, cast

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.messaging.connection import RabbitMQConnectionManager
from app.messaging.consumer import EventConsumer
from app.messaging.events import EventEnvelope, EventType, create_event_envelope
from app.observability.metrics import incr, timed
from app.repositories.exercise import ExerciseRepository
from app.repositories.outbox_event import OutboxEventRepository
from app.repositories.profile import ProfileRepository
from app.repositories.workflow_state import WorkflowStateRepository
from app.repositories.workout import WorkoutRepository
from app.repositories.workout_exercise import WorkoutExerciseRepository
from app.services.outbox import OutboxService

EXERCISE_QUEUE: Final[str] = "aggregation-exercises"
PLAYLIST_QUEUE: Final[str] = "aggregation-playlist"

logging.basicConfig(level=logging.INFO)
# logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

def _safe_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return cast(Dict[str, Any], value)
    return {}


def _extract_latest_payload(
    outbox_repo: OutboxEventRepository,
    saga_id: str,
    event_type: EventType,
) -> Dict[str, Any]:
    event = outbox_repo.get_latest_by_saga_and_event_type(
        saga_id=saga_id,
        event_type=event_type.value,
    )
    if event is None:
        return {}
    return _safe_json(event.payload).get("payload", {}) if isinstance(event.payload, dict) else {}


def _persist_finalized_workout(
    db: Session,
    *,
    request_id: int,
    profile_id: int,
    exercises_payload: Dict[str, Any],
    playlist_payload: Dict[str, Any],
) -> Optional[int]:
    profile_repo = ProfileRepository(db)
    workout_repo = WorkoutRepository(db)
    workout_exercise_repo = WorkoutExerciseRepository(db)
    exercise_repo = ExerciseRepository(db)

    profile = profile_repo.get_by_id(profile_id)
    if profile is None:
        return None

    playlist = _safe_json(playlist_payload.get("playlist"))
    exercises = cast(List[Dict[str, Any]], exercises_payload.get("exercises") or [])

    workout = workout_repo.create(
        {
            "user_id": cast(int, getattr(profile, "user_id", None)),
            "duration_minutes": getattr(profile, "workout_duration_minutes", 45),
            "focus": "General",
            "date": datetime.now(timezone.utc),
            "playlist_id": playlist.get("id") or playlist.get("playlist_id"),
            "playlist_name": playlist.get("name") or playlist.get("playlist_name"),
            "playlist_url": playlist.get("external_url") or playlist.get("playlist_url"),
        }
    )

    for idx, ex in enumerate(exercises):
        name = ex.get("name") or ex.get("exercise")
        if not name:
            continue

        exercise_obj = None
        search = exercise_repo.search_by_name(str(name), limit=1)
        if search:
            exercise_obj = search[0]
        else:
            exercise_obj = exercise_repo.create(
                {
                    "name": name,
                    "target": ex.get("target") or "General",
                    "body_part": ex.get("body_part") or "General",
                    "secondary_muscles": ex.get("secondary_muscles") if isinstance(ex.get("secondary_muscles"), list) else None,
                    "equipment": ex.get("equipment"),
                    "gif_url": ex.get("gif_url"),
                    "instructions": ex.get("instructions") if isinstance(ex.get("instructions"), list) else None,
                }
            )

        workout_exercise_repo.create_with_composite_key(
            workout_id=workout.id,
            exercise_id=exercise_obj.id,
            sets=int(ex.get("sets") or 1),
            reps=str(ex.get("reps") or "10-12"),
            order=idx + 1,
            rest_seconds=int(ex.get("rest_seconds") or 60),
        )

    return workout.id


def process_event(payload: Dict[str, Any], *, is_exercise_event: bool) -> None:
    envelope = EventEnvelope.model_validate(payload)
    incr("aggregation_worker_received_count")

    request_id = int(envelope.payload["request_id"])
    profile_id = int(envelope.payload["profile_id"])

    db: Session = SessionLocal()
    state_repo = WorkflowStateRepository(db)
    outbox_repo = OutboxEventRepository(db)
    both_ready = False

    try:
        with timed("aggregation_latency"):
            # Step 1: Update workflow state atomically. Capture readiness flag
            # before the transaction closes so we can act on it afterwards.
            # _persist_finalized_workout must NOT be called inside this block
            # because base.py's create() commits internally, which would close
            # this transaction and cause "Can't operate on closed transaction
            # inside context manager" on the subsequent db.refresh() call.
            with db.begin():
                state = state_repo.get_or_create(saga_id=envelope.saga_id, request_id=request_id)
                if is_exercise_event:
                    state.exercises_ready = True
                    state.exercises_event_id = envelope.event_id
                else:
                    state.playlist_ready = True
                    state.playlist_event_id = envelope.event_id

                db.add(state)
                both_ready = state.exercises_ready and state.playlist_ready

            # Step 2: If both sides are ready, persist the workout and enqueue
            # the completion event. Each repo.create() call commits on its own,
            # so this runs outside the explicit transaction above.
            if both_ready:
                exercises_payload = _extract_latest_payload(
                    outbox_repo,
                    envelope.saga_id,
                    EventType.WORKOUT_EXERCISES_READY,
                )
                playlist_payload = _extract_latest_payload(
                    outbox_repo,
                    envelope.saga_id,
                    EventType.PLAYLIST_READY,
                )

                workout_id = _persist_finalized_workout(
                    db,
                    request_id=request_id,
                    profile_id=profile_id,
                    exercises_payload=exercises_payload,
                    playlist_payload=playlist_payload,
                )

                completed = create_event_envelope(
                    event_type=EventType.WORKOUT_PLAN_COMPLETED,
                    source="worker.aggregation",
                    payload={
                        "request_id": request_id,
                        "profile_id": profile_id,
                        "workout_id": workout_id,
                    },
                    saga_id=envelope.saga_id,
                    correlation_id=envelope.correlation_id,
                )
                # enqueue_event does not commit by itself; use a separate
                # Session for outbox writes so we don't interfere with the
                # current session/transaction lifecycle on `db`.
                write_db = SessionLocal()
                write_outbox = OutboxService(write_db)
                try:
                    with write_db.begin():
                        write_outbox.enqueue_event(
                            event_id=completed.event_id,
                            routing_key="workout.completed",
                            exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
                            payload=completed.model_dump(mode="json"),
                        )
                finally:
                    write_db.close()
        incr("aggregation_worker_success_count")
    except Exception as exc:
        # Keep aggregation worker resilient. Notification phase handles terminal failure events.
        # Still has to enqueue an event indicating failure for the notification worker to pick up and update the request status accordingly.
        logger.exception(f"Error processing event in aggregation worker: {exc}")
        failed = create_event_envelope(
            event_type=EventType.WORKOUT_PLAN_FAILED,
            source="worker.aggregation",
            payload={
                "request_id": request_id,
                "profile_id": profile_id,            },
            saga_id=envelope.saga_id,
            correlation_id=envelope.correlation_id,
        )
        try:
            write_db = SessionLocal()
            write_outbox = OutboxService(write_db)
            try:
                with write_db.begin():
                    write_outbox.enqueue_event(
                        event_id=failed.event_id,
                        routing_key="workout.failed",
                        exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
                        payload=failed.model_dump(mode="json"),
                    )
            finally:
                write_db.close()
        except Exception:
            logger.exception("Failed to enqueue WORKOUT_PLAN_FAILED outbox event")
        incr("aggregation_worker_failure_count")
    finally:
        db.close()


async def _handle_exercise_message(message: AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):
        body = json.loads(message.body.decode("utf-8"))
        process_event(_safe_json(body), is_exercise_event=True)


async def _handle_playlist_message(message: AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):
        body = json.loads(message.body.decode("utf-8"))
        process_event(_safe_json(body), is_exercise_event=False)


async def run_worker() -> None:
    manager = RabbitMQConnectionManager(
        amqp_url=settings.RABBITMQ_URL,
        exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
    )
    consumer = EventConsumer(manager)

    await asyncio.gather(
        consumer.consume(
            queue_name=EXERCISE_QUEUE,
            routing_key="workout.exercises.ready",
            handler=_handle_exercise_message,
        ),
        consumer.consume(
            queue_name=PLAYLIST_QUEUE,
            routing_key="playlist.ready",
            handler=_handle_playlist_message,
        ),
    )


if __name__ == "__main__":
    asyncio.run(run_worker())
