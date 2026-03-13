from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Final, List, Optional, cast

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.messaging.connection import RabbitMQConnectionManager
from app.messaging.consumer import EventConsumer
from app.messaging.events import (EventEnvelope, EventType,
                                  create_event_envelope)
from app.models.preferences import Preferences
from app.models.profile import Profile
from app.observability.metrics import incr, timed
from app.repositories.exercise import ExerciseRepository
from app.repositories.preferences import PreferencesRepository
from app.repositories.profile import ProfileRepository
from app.repositories.workout_request import WorkoutRequestRepository
from app.services.exercise_selector import ExerciseSelectorService
from app.services.outbox import OutboxService
from app.utils.fuzzy import get_top_candidate_by_repo

QUEUE_NAME: Final[str] = "exercise-pipeline"
ROUTING_KEY: Final[str] = "workout.draft.generated"
MIN_EXERCISE_COUNT: Final[int] = 3


def _safe_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return cast(Dict[str, Any], value)
    return {}


def _resolve_exercises(
    db: Session,
    *,
    draft: Dict[str, Any],
    profile: Profile,
    preferences: Preferences,
) -> List[Dict[str, Any]]:
    mapped = _map_exercise_candidates(
        db,
        draft=draft,
        profile=profile,
    )
    if len(mapped) >= MIN_EXERCISE_COUNT:
        return mapped

    selector = ExerciseSelectorService(db)
    fallback = selector.select_exercises_for_workout(
        fitness_goal=getattr(
            getattr(profile, "fitness_goal", None), "value", "general_fitness"
        ),
        fitness_level=getattr(
            getattr(profile, "fitness_level", None), "value", "beginner"
        ),
        available_equipment=cast(
            List[str], getattr(preferences, "available_equipment", []) or []
        ),
        target_muscle_groups=cast(
            List[str], getattr(preferences, "target_muscle_groups", []) or []
        ),
        workout_duration_minutes=cast(
            int, getattr(profile, "workout_duration_minutes", 45) or 45
        ),
        recently_used_exercises=[],
    )
    if len(fallback) > 0:
        incr("exercise_selector_fallback_count")
    return [_normalize_exercise_payload(ex, profile=profile) for ex in fallback]


def _default_prescription(profile: Profile) -> tuple[int, str, int]:
    fitness_level = str(
        getattr(getattr(profile, "fitness_level", None), "value", "beginner")
    ).lower()
    if fitness_level == "intermediate":
        return 4, "10-12", 45
    if fitness_level == "advanced":
        return 5, "12-15", 30
    return 3, "8-10", 60


def _normalize_exercise_payload(exercise: Dict[str, Any], *, profile: Profile) -> Dict[str, Any]:
    sets_default, reps_default, rest_default = _default_prescription(profile)
    sets_value = exercise.get("sets")
    reps_value = exercise.get("reps")
    rest_value = exercise.get("rest_seconds")
    try:
        sets = int(sets_value) if sets_value is not None else sets_default
    except Exception:
        sets = sets_default
    try:
        rest_seconds = int(rest_value) if rest_value is not None else rest_default
    except Exception:
        rest_seconds = rest_default

    return {
        "exercise_id": exercise.get("exercise_id"),
        "name": str(exercise.get("name") or exercise.get("exercise") or "").strip(),
        "target": exercise.get("target") or "General",
        "body_part": exercise.get("body_part") or "General",
        "secondary_muscles": exercise.get("secondary_muscles")
        if isinstance(exercise.get("secondary_muscles"), list)
        else [],
        "equipment": exercise.get("equipment"),
        "instructions": exercise.get("instructions")
        if isinstance(exercise.get("instructions"), list)
        else [],
        "gif_url": exercise.get("gif_url"),
        "sets": sets,
        "reps": str(reps_value) if reps_value else reps_default,
        "rest_seconds": rest_seconds,
        "mapping_source": exercise.get("mapping_source") or "selector_fallback",
    }


def _map_exercise_candidates(
    db: Session,
    *,
    draft: Dict[str, Any],
    profile: Profile,
) -> List[Dict[str, Any]]:
    exercise_repo = ExerciseRepository(db)
    candidates = cast(List[Dict[str, Any]], draft.get("exercise_candidates") or [])
    if not candidates:
        legacy = cast(List[Dict[str, Any]], draft.get("workout_exercises") or [])
        candidates = [{"name": ex.get("name") or ex.get("exercise")} for ex in legacy]

    # Fetch exercise names once for all candidates to avoid repeated DB queries
    exercise_names = exercise_repo.get_all_names()

    mapped: List[Dict[str, Any]] = []
    for candidate in candidates:
        raw_name = candidate.get("name") or candidate.get("exercise")
        name = str(raw_name).strip() if raw_name is not None else ""
        if not name:
            continue
        resolved = _find_exercise_by_name(exercise_repo, name, exercise_names=exercise_names)
        if resolved is None:
            continue
        mapped.append(
            _normalize_exercise_payload(
                {
                    "exercise_id": resolved["exercise_id"],
                    "name": resolved["name"],
                    "target": resolved["target"],
                    "body_part": resolved["body_part"],
                    "secondary_muscles": resolved["secondary_muscles"],
                    "equipment": resolved["equipment"],
                    "instructions": resolved["instructions"],
                    "gif_url": resolved["gif_url"],
                    "mapping_source": resolved["mapping_source"],
                },
                profile=profile,
            )
        )
    return mapped


def _find_exercise_by_name(
    exercise_repo: ExerciseRepository, name: str, exercise_names: List[tuple[int, str]]
) -> Optional[Dict[str, Any]]:
    exact = exercise_repo.get_by_name_exact(name)
    if exact is not None:
        incr("exercise_mapping_exact_count")
        return {
            "exercise_id": exact.id,
            "name": exact.name,
            "target": exact.target,
            "body_part": exact.body_part,
            "secondary_muscles": exact.secondary_muscles,
            "equipment": exact.equipment,
            "instructions": exact.instructions,
            "gif_url": exact.gif_url,
            "mapping_source": "db_exact",
        }

    fuzzy = get_top_candidate_by_repo(name, candidate_names=exercise_names,  score_cutoff=80.0, )
    if fuzzy is not None:
        resolved = exercise_repo.get_by_id(fuzzy.id)
        if resolved is not None:
            incr("exercise_mapping_fuzzy_count")
            return {
                "exercise_id": resolved.id,
                "name": resolved.name,
                "target": resolved.target,
                "body_part": resolved.body_part,
                "secondary_muscles": resolved.secondary_muscles,
                "equipment": resolved.equipment,
                "instructions": resolved.instructions,
                "gif_url": resolved.gif_url,
                "mapping_source": "db_fuzzy",
            }

    partial = exercise_repo.search_by_name(name, limit=1)
    if partial:
        resolved = partial[0]
        incr("exercise_mapping_partial_count")
        return {
            "exercise_id": resolved.id,
            "name": resolved.name,
            "target": resolved.target,
            "body_part": resolved.body_part,
            "secondary_muscles": resolved.secondary_muscles,
            "equipment": resolved.equipment,
            "instructions": resolved.instructions,
            "gif_url": resolved.gif_url,
            "mapping_source": "db_partial",
        }
    return None


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

            with db.begin_nested():
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
