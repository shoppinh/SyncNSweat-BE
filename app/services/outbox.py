from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models.outbox_event import OutboxEvent
from app.repositories.outbox_event import OutboxEventRepository


class OutboxService:
    """Service for transactional outbox event enqueueing."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = OutboxEventRepository(db)

    def enqueue_event(
        self,
        *,
        event_id: str,
        routing_key: str,
        exchange_name: str,
        payload: Dict[str, Any],
    ) -> OutboxEvent:
        # Intentionally no commit here to allow caller-owned transactions.
        return self.repo.enqueue(
            event_id=event_id,
            routing_key=routing_key,
            exchange_name=exchange_name,
            payload=payload,
        )
