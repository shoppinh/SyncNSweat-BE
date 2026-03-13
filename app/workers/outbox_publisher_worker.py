from __future__ import annotations

import asyncio
import logging
from typing import Any, Final

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
        
        # Extract fields into plain dicts before commit to avoid expired ORM instances.
        # SQLAlchemy's default expire_on_commit=True will expire ORM instances after commit,
        # causing implicit DB reads on attribute access during the publish loop.
        # This can inadvertently open new transactions that stay open across async I/O.
        event_data: list[dict[str, Any]] = [
            {
                "id": getattr(event, "id", None),
                "routing_key": getattr(event, "routing_key", ""),
                "payload": getattr(event, "payload", {}),
                "orm": event,
            }
            for event in pending_events
        ]
        
        if event_data:
            # Persist claim and release row locks before external I/O.
            db.commit()

        incr("outbox_pending_batch_size", len(event_data))

        for event in event_data:
            try:
                with timed(
                    "outbox_publish_latency",
                    tags={"routing_key": event["routing_key"]},
                ):
                    await publisher.publish_event(
                        event["routing_key"],
                        event["payload"],
                    )

                repo.mark_published(event["orm"])
                db.commit()

                processed += 1
                incr("outbox_publish_success_count")

            except Exception as exc:
                db.rollback()
                repo.mark_failed(
                    event["orm"],
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
