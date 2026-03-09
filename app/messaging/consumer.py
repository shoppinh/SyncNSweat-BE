from __future__ import annotations

from typing import Awaitable, Callable

from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage

from app.messaging.connection import RabbitMQConnectionManager

MessageHandler = Callable[[AbstractIncomingMessage], Awaitable[None]]


class EventConsumer:
    """Minimal queue consumer helper for worker processes."""

    def __init__(self, connection_manager: RabbitMQConnectionManager):
        self.connection_manager = connection_manager

    async def consume(
        self,
        *,
        queue_name: str,
        routing_key: str,
        handler: MessageHandler,
    ) -> None:
        if not queue_name:
            raise ValueError("queue_name must not be empty")
        if not routing_key:
            raise ValueError("routing_key must not be empty")

        channel = await self.connection_manager.get_channel()
        exchange = await channel.declare_exchange(
            self.connection_manager.exchange_name,
            type=ExchangeType.TOPIC,
            durable=True,
        )
        queue = await channel.declare_queue(queue_name, durable=True)
        await queue.bind(exchange, routing_key=routing_key)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await handler(message)
