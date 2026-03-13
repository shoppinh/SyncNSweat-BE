from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import and_, asc, desc, or_, text
from sqlalchemy.orm import Session

from app.models.outbox_event import OutboxEvent
from app.repositories.base import BaseRepository


class OutboxEventRepository(BaseRepository[OutboxEvent]):
    def __init__(self, db: Session):
        super().__init__(OutboxEvent, db)

    def enqueue(
        self,
        *,
        event_id: str,
        routing_key: str,
        exchange_name: str,
        payload: Dict[str, Any],
    ) -> OutboxEvent:
        event = OutboxEvent(
            event_id=event_id,
            routing_key=routing_key,
            exchange_name=exchange_name,
            payload=payload,
            status="PENDING",
            attempt_count=0,
        )
        self.db.add(event)
        return event

    def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        now = datetime.now(timezone.utc)
        # Atomically claim pending events using a single UPDATE ... RETURNING
        # so this repository can participate in a broader/global transaction
        # managed by the caller. We do NOT commit/rollback here.
        sql = text(
            """
            WITH cte AS (
              SELECT id
              FROM outbox_events
              WHERE published_at IS NULL
                AND (
                  status = 'PENDING'
                  OR (status = 'FAILED' AND (next_retry_at IS NULL OR next_retry_at <= :now))
                )
              ORDER BY created_at
              LIMIT :limit
              FOR UPDATE SKIP LOCKED
            )
            UPDATE outbox_events
            SET status = 'IN_PROGRESS'
            WHERE id IN (SELECT id FROM cte)
            RETURNING id
            """
        )

        result = self.db.execute(sql, {"now": now, "limit": limit})
        rows = result.fetchall()
        ids = [r[0] for r in rows]

        if not ids:
            return []

        # Load ORM instances for the claimed rows and return them. Do not
        # commit here; caller's transaction should handle persistence.
        pending = (
            self.db.query(OutboxEvent)
            .filter(OutboxEvent.id.in_(ids))
            .order_by(asc(OutboxEvent.created_at))
            .all()
        )

        return pending

    def mark_published(self, event: OutboxEvent) -> None:
        event.status = "PUBLISHED"
        event.published_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        event.next_retry_at = None  # type: ignore[assignment]
        event.last_error = None
        self.db.add(event)

    def mark_failed(
        self,
        event: OutboxEvent,
        *,
        error_message: str,
        retry_after_seconds: int = 30,
    ) -> None:
        event.status = "FAILED"
        event.attempt_count = (event.attempt_count or 0) + 1
        event.next_retry_at = datetime.now(timezone.utc) + timedelta(
            seconds=retry_after_seconds
        )  # type: ignore[assignment]
        event.last_error = error_message[:4000]
        self.db.add(event)

    def get_latest_by_saga_and_event_type(
        self,
        *,
        saga_id: str,
        event_type: str,
    ) -> OutboxEvent | None:
        return (
            self.db.query(OutboxEvent)
            .filter(OutboxEvent.payload["saga_id"].astext == saga_id)
            .filter(OutboxEvent.payload["event_type"].astext == event_type)
            .order_by(desc(OutboxEvent.created_at))
            .first()
        )
