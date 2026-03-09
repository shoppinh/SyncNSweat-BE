import asyncio

import pytest
from pydantic import ValidationError

from app.messaging.events import create_event_envelope, EventType
from app.messaging.publisher import EventPublisher


class FakeExchange:
    def __init__(self) -> None:
        self.publish_count = 0

    async def publish(self, message, routing_key):  # noqa: ANN001, ANN201
        self.publish_count += 1
        assert routing_key == "workout.requested"
        assert message.body


class FakeConnectionManager:
    def __init__(self) -> None:
        self.exchange = FakeExchange()

    async def get_exchange(self):  # noqa: ANN201
        return self.exchange


def test_publish_event_accepts_valid_envelope() -> None:
    publisher = EventPublisher(FakeConnectionManager())
    envelope = create_event_envelope(
        event_type=EventType.WORKOUT_PLAN_REQUESTED,
        source="api.workouts",
        payload={"request_id": "abc"},
    )

    asyncio.run(
        publisher.publish_event(
            routing_key="workout.requested",
            payload=envelope.model_dump(mode="json"),
        )
    )


def test_publish_event_rejects_invalid_payload_before_publish() -> None:
    manager = FakeConnectionManager()
    publisher = EventPublisher(manager)

    with pytest.raises(ValidationError):
        asyncio.run(
            publisher.publish_event(
                routing_key="workout.requested",
                payload={
                    "event_type": EventType.WORKOUT_PLAN_REQUESTED,
                    "saga_id": "s1",
                    "correlation_id": "c1",
                    "source": "api.workouts",
                    "version": 1,
                    "timestamp": "2026-03-04T10:00:00+00:00",
                    "payload": {},
                },
            )
        )

    assert manager.exchange.publish_count == 0
