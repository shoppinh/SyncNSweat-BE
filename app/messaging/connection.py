from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aio_pika import ExchangeType, connect_robust
from aio_pika.abc import AbstractChannel, AbstractRobustConnection


@dataclass
class RabbitMQConnectionManager:
    """Manages RabbitMQ robust connection, channel, and exchange declaration."""

    amqp_url: str
    exchange_name: str
    exchange_type: ExchangeType = ExchangeType.TOPIC

    _connection: Optional[AbstractRobustConnection] = None
    _channel: Optional[AbstractChannel] = None

    async def connect(self) -> None:
        if self._connection and not self._connection.is_closed:
            return

        self._connection = await connect_robust(self.amqp_url)
        self._channel = await self._connection.channel()

    async def get_channel(self) -> AbstractChannel:
        if self._channel is None or self._channel.is_closed:
            await self.connect()

        if self._channel is None:
            raise RuntimeError("RabbitMQ channel is not available")

        return self._channel

    async def get_exchange(self):
        channel = await self.get_channel()
        return await channel.declare_exchange(
            self.exchange_name,
            type=self.exchange_type,
            durable=True,
        )

    async def close(self) -> None:
        if self._channel and not self._channel.is_closed:
            await self._channel.close()

        if self._connection and not self._connection.is_closed:
            await self._connection.close()

        self._channel = None
        self._connection = None
