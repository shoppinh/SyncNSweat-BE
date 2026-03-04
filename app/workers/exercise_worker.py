from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Final, List, cast

from aio_pika import IncomingMessage
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
from app.services.exercise_selector import ExerciseSelectorService
from app.services.outbox import OutboxService

QUEUE_NAME: Final[str] = "exercise-pipeline"
ROUTING_KEY: Final[str] = "workout.draft.generated"


def _safe_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _resolve_exercises(
    db: Session,
    *,
    draft: Dict[str, Any],
    profile: Profile,
    preferences: Preferences,
) -> List[Dict[str, Any]]:
    existing = draft.get("workout_exercises") or []
    if isinstance(existing, list) and len(existing) > 0:
        return cast(List[Dict[str, Any]], existing)

    selector = ExerciseSelectorService(db)
    return selector.select_exercises_for_workout(
        fitness_goal=getattr(getattr(profile, "fitness_goal", None), "value", "general_fitness"),
        fitness_level=getattr(getattr(profile, "fitness_level", None), "value", "beginner"),
        available_equipment=cast(List[str], getattr(preferences, "available_equipment", []) or []),
        target_muscle_groups=cast(List[str], getattr(preferences, "target_muscle_groups", []) or []),
        workout_duration_minutes=cast(int, getattr(profile, "workout_duration_minutes", 45) or 45),
        recently_used_exercises=[],
    )


def process_event(payload: Dict[str, Any]) -> None:
    envelope = EventEnvelope.model_validate(payload)
    incr("exercise_worker_received_count")

    request_id = int(envelope.payload["request_id"])
    profile_id = int(envelope.payload["profile_id"])
    draft = _safe_json(envelope.payload.get("draft"))

    db: Session = SessionLocal()
    request_repo = WorkoutRequestRepository(db)
    profile_repo = ProfileRepository(db)
    preferences_repo = PreferencesRepository(db)
    outbox_service = OutboxService(db)

    try:
        request = request_repo.get_by_id(request_id)
        profile = profile_repo.get_by_id(profile_id)
        preferences = preferences_repo.get_by_profile_id(profile_id)

        if request is None or profile is None or preferences is None:
            with db.begin():
                if request is not None:
                    request_repo.set_status(
                        request,
                        status="FAILED",
                        error_code="EXERCISE_INPUT_MISSING",
                        error_message="Missing request/profile/preferences for exercise mapping",
                    )
            return

        with timed("exercise_mapping_latency"):
            exercises = _resolve_exercises(
                db,
                draft=draft,
                profile=profile,
                preferences=preferences,
            )

        next_event = create_event_envelope(
            event_type=EventType.WORKOUT_EXERCISES_READY,
            source="worker.exercise",
            payload={
                "request_id": request_id,
                "profile_id": profile_id,
                "exercises": exercises,
            },
            saga_id=envelope.saga_id,
            correlation_id=envelope.correlation_id,
        )

        with db.begin():
            request_repo.set_status(request, status="PARTIAL_READY")
            outbox_service.enqueue_event(
                event_id=next_event.event_id,
                routing_key="workout.exercises.ready",
                exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
                payload=next_event.model_dump(mode="json"),
            )
        incr("exercise_worker_success_count")
    except Exception as exc:
        with db.begin():
            request = request_repo.get_by_id(request_id)
            if request is not None:
                request_repo.set_status(
                    request,
                    status="FAILED",
                    error_code="EXERCISE_MAPPING_FAILED",
                    error_message=str(exc),
                )
        incr("exercise_worker_failure_count")
    finally:
        db.close()


async def _handle_message(message: IncomingMessage) -> None:
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
