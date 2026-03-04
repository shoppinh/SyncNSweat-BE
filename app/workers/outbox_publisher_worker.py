from __future__ import annotations

import asyncio
from typing import Final

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.messaging.connection import RabbitMQConnectionManager
from app.messaging.publisher import EventPublisher
from app.repositories.outbox_event import OutboxEventRepository

DEFAULT_BATCH_SIZE: Final[int] = 100
DEFAULT_RETRY_SECONDS: Final[int] = 30


async def publish_outbox_once(batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    manager = RabbitMQConnectionManager(
        amqp_url=settings.RABBITMQ_URL,
        exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
    )
    publisher = EventPublisher(manager)

    processed = 0
    db: Session = SessionLocal()
    repo = OutboxEventRepository(db)

    try:
        await manager.connect()
        pending_events = repo.get_pending(limit=batch_size)

        for event in pending_events:
            try:
                await publisher.publish_event(
                    getattr(event, "routing_key", ""), getattr(event, "payload", {})
                )
                repo.mark_published(event)
                db.commit()
                processed += 1
            except Exception as exc:  # noqa: BLE001
                repo.mark_failed(
                    event,
                    error_message=str(exc),
                    retry_after_seconds=DEFAULT_RETRY_SECONDS,
                )
                db.commit()
    finally:
        db.close()
        await manager.close()

    return processed


async def run_forever(poll_interval_seconds: int = 2) -> None:
    while True:
        await publish_outbox_once()
        await asyncio.sleep(poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_forever())
