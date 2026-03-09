from __future__ import annotations

import asyncio
import logging
from typing import Final

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.messaging.connection import RabbitMQConnectionManager
from app.messaging.publisher import EventPublisher
from app.observability.metrics import incr, timed
from app.repositories.outbox_event import OutboxEventRepository

DEFAULT_BATCH_SIZE: Final[int] = 100
DEFAULT_RETRY_SECONDS: Final[int] = 30


logger = logging.getLogger(__name__)


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
        if pending_events:
            # Persist claim and release row locks before external I/O.
            db.commit()

        incr("outbox_pending_batch_size", len(pending_events))

        for event in pending_events:
            try:
                with timed(
                    "outbox_publish_latency",
                    tags={"routing_key": getattr(event, "routing_key", "")},
                ):
                    await publisher.publish_event(
                        getattr(event, "routing_key", ""),
                        getattr(event, "payload", {}),
                    )

                repo.mark_published(event)
                db.commit()

                processed += 1
                incr("outbox_publish_success_count")

            except Exception as exc:
                db.rollback()
                repo.mark_failed(
                    event,
                    error_message=str(exc),
                    retry_after_seconds=DEFAULT_RETRY_SECONDS,
                )
                db.commit()

                incr("outbox_publish_failure_count")

    finally:
        db.close()
        await manager.close()

    return processed


async def run_forever(poll_interval_seconds: int = 2) -> None:
    while True:
        logger.info("Polling outbox for pending events...")
        await publish_outbox_once()
        await asyncio.sleep(poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_forever())
