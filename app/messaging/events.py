from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventEnvelope(BaseModel):
    """Canonical event envelope for internal async messaging."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    saga_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    version: int = Field(default=1, ge=1)
    timestamp: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


def _utc_iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_event_envelope(
    *,
    event_type: str,
    source: str,
    payload: Dict[str, Any],
    saga_id: str | None = None,
    correlation_id: str | None = None,
    version: int = 1,
) -> EventEnvelope:
    """Create a validated event envelope with generated ids/timestamp."""

    resolved_saga_id = saga_id or str(uuid4())
    resolved_correlation_id = correlation_id or resolved_saga_id

    return EventEnvelope(
        event_id=str(uuid4()),
        event_type=event_type,
        saga_id=resolved_saga_id,
        correlation_id=resolved_correlation_id,
        source=source,
        version=version,
        timestamp=_utc_iso_timestamp(),
        payload=payload,
    )
