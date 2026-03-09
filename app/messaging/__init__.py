"""Messaging primitives for event-driven workflow components."""

from app.messaging.connection import RabbitMQConnectionManager
from app.messaging.publisher import EventPublisher
from app.messaging.consumer import EventConsumer
from app.messaging.events import (
    EventEnvelope,
    EventType,
    create_event_envelope,
    generate_event_id,
    generate_saga_id,
)

__all__ = [
    "RabbitMQConnectionManager",
    "EventPublisher",
    "EventConsumer",
    "EventEnvelope",
    "EventType",
    "create_event_envelope",
    "generate_event_id",
    "generate_saga_id",
]
