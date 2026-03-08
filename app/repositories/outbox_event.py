from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import and_, asc, desc, or_
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
        # Claim pending events using row-level locking to avoid multiple
        # workers processing the same event concurrently. We mark claimed
        # rows as IN_PROGRESS and commit so other workers skip them.
        query = (
            self.db.query(OutboxEvent)
            .filter(OutboxEvent.published_at.is_(None))
            .filter(
                or_(
                    OutboxEvent.status == "PENDING",
                    and_(
                        OutboxEvent.status == "FAILED",
                        or_(
                            OutboxEvent.next_retry_at.is_(None),
                            OutboxEvent.next_retry_at <= now,
                        ),
                    ),
                )
            )
            .order_by(asc(OutboxEvent.created_at))
            .limit(limit)
        )

        # Use FOR UPDATE SKIP LOCKED when supported by the DB (e.g. Postgres)
        try:
            pending = query.with_for_update(skip_locked=True).all()
        except Exception:
            # Fallback: if the DB does not support SKIP LOCKED, fall back to
            # a plain select. This may allow duplicate processing in some
            # deployments; prefer a DB that supports row locking.
            pending = query.all()

        # Mark claimed events as IN_PROGRESS so other workers won't pick them
        # up on subsequent polls. Commit here to persist the claim.
        for event in pending:
            event.status = "IN_PROGRESS"
            self.db.add(event)

        if pending:
            try:
                self.db.commit()
            except Exception:
                # If we fail to commit the claim, rollback so events remain
                # available for other workers.
                self.db.rollback()

        return pending

    def mark_published(self, event: OutboxEvent) -> None:
        event.status = "PUBLISHED"
        event.published_at = datetime.now(timezone.utc)
        event.next_retry_at = None
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
        )
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
