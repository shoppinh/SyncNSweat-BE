from datetime import timezone

import pytest
from pydantic import ValidationError

from app.messaging.events import EventEnvelope, EventType, create_event_envelope


def test_create_event_envelope_defaults_and_metadata() -> None:
    envelope = create_event_envelope(
        event_type=EventType.WORKOUT_PLAN_REQUESTED,
        source="api.workouts",
        payload={"request_id": "abc"},
    )

    assert envelope.event_id
    assert envelope.saga_id
    assert envelope.correlation_id == envelope.saga_id
    assert envelope.version == 1
    assert envelope.timestamp.tzinfo == timezone.utc
    assert envelope.payload == {"request_id": "abc"}


def test_event_envelope_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(
            {
                "event_id": "e1",
                "event_type": EventType.WORKOUT_PLAN_REQUESTED,
                "saga_id": "s1",
                "correlation_id": "c1",
                "source": "api.workouts",
                "version": 1,
                "timestamp": "2026-03-04T10:00:00+00:00",
                "payload": {},
                "unknown": "nope",
            }
        )


def test_event_envelope_rejects_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(
            {
                "event_type": EventType.WORKOUT_PLAN_REQUESTED,
                "saga_id": "s1",
                "correlation_id": "c1",
                "source": "api.workouts",
                "version": 1,
                "timestamp": "2026-03-04T10:00:00+00:00",
                "payload": {},
            }
        )
