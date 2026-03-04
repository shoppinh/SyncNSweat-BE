from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Dict
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class EventType(StrEnum):
    WORKOUT_PLAN_REQUESTED = "WorkoutPlanRequested"
    CONTEXT_PREPARED = "ContextPrepared"
    WORKOUT_DRAFT_GENERATED = "WorkoutDraftGenerated"
    WORKOUT_EXERCISES_READY = "WorkoutExercisesReady"
    PLAYLIST_READY = "PlaylistReady"
    WORKOUT_PLAN_COMPLETED = "WorkoutPlanCompleted"
    WORKOUT_PLAN_FAILED = "WorkoutPlanFailed"


class EventEnvelope(BaseModel):
    """Canonical event envelope for internal async messaging."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(..., min_length=1)
    event_type: EventType
    saga_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    version: int = Field(default=1, ge=1)
    timestamp: AwareDatetime
    payload: Dict[str, Any] = Field(default_factory=dict)


def _utc_timestamp() -> datetime:
    return datetime.now(timezone.utc)


def generate_event_id() -> str:
    return str(uuid4())


def generate_saga_id() -> str:
    return str(uuid4())


def create_event_envelope(
    *,
    event_type: EventType,
    source: str,
    payload: Dict[str, Any],
    saga_id: str | None = None,
    correlation_id: str | None = None,
    version: int = 1,
) -> EventEnvelope:
    """Create a validated event envelope with generated ids/timestamp."""

    resolved_saga_id = saga_id or generate_saga_id()
    resolved_correlation_id = correlation_id or resolved_saga_id

    return EventEnvelope(
        event_id=generate_event_id(),
        event_type=event_type,
        saga_id=resolved_saga_id,
        correlation_id=resolved_correlation_id,
        source=source,
        version=version,
        timestamp=_utc_timestamp(),
        payload=payload,
    )
