from __future__ import annotations

import json
from typing import Any, Dict

from aio_pika import DeliveryMode, Message

from app.messaging.connection import RabbitMQConnectionManager
from app.messaging.events import EventEnvelope


class EventPublisher:
    """Publishes events to the configured topic exchange."""

    def __init__(self, connection_manager: RabbitMQConnectionManager):
        self.connection_manager = connection_manager

    async def publish_event(self, routing_key: str, payload: Dict[str, Any]) -> None:
        if not routing_key:
            raise ValueError("routing_key must not be empty")

        envelope = EventEnvelope.model_validate(payload)
        body = json.dumps(envelope.model_dump(mode="json")).encode("utf-8")

        exchange = await self.connection_manager.get_exchange()
        await exchange.publish(
            Message(body=body, delivery_mode=DeliveryMode.PERSISTENT),
            routing_key=routing_key,
        )
