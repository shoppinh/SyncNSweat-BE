from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Final, cast

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.messaging.connection import RabbitMQConnectionManager
from app.messaging.consumer import EventConsumer
from app.messaging.events import (EventEnvelope, EventType,
                                  create_event_envelope)
from app.observability.metrics import incr, timed
from app.repositories.preferences import PreferencesRepository
from app.repositories.profile import ProfileRepository
from app.repositories.workout import WorkoutRepository
from app.repositories.workout_request import WorkoutRequestRepository
from app.services.outbox import OutboxService

QUEUE_NAME: Final[str] = "context-builder"
ROUTING_KEY: Final[str] = "workout.requested"


def _safe_json(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    return {}

def process_event(message_payload: Dict[str, Any]) -> None:
    envelope = EventEnvelope.model_validate(message_payload)
    incr("context_worker_received_count")

    request_id = int(envelope.payload["request_id"])
    user_id = int(envelope.payload["user_id"])
    profile_id = int(envelope.payload["profile_id"])

    db: Session = SessionLocal()
    request_repo = WorkoutRequestRepository(db)
    outbox_service = OutboxService(db)

    try:
        with timed("context_build_latency"):
            with db.begin():
                request = request_repo.get_by_id(request_id)
                if request is None:
                    raise ValueError(f"workout request not found: {request_id}")

                next_event = create_event_envelope(
                    event_type=EventType.CONTEXT_PREPARED,
                    source="worker.context",
                    payload={
                        "request_id": request_id,
                        "user_id": user_id,
                        "profile_id": profile_id,
                    },
                    saga_id=envelope.saga_id,
                    correlation_id=envelope.correlation_id,
                )

                request_repo.set_status(request, status="CONTEXT_READY")
                outbox_service.enqueue_event(
                    event_id=next_event.event_id,
                    routing_key="workout.context.ready",
                    exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
                    payload=next_event.model_dump(mode="json"),
                )
        incr("context_worker_success_count")
    except Exception as exc:
        with db.begin():
            request = request_repo.get_by_id(request_id)
            if request is not None:
                request_repo.set_status(
                    request,
                    status="FAILED",
                    error_code="CONTEXT_BUILD_FAILED",
                    error_message=str(exc),
                )
        incr("context_worker_failure_count")
    finally:
        db.close()


async def _handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):
        raw = json.loads(message.body.decode("utf-8"))
        process_event(_safe_json(raw))


async def run_worker() -> None:
    manager = RabbitMQConnectionManager(
        amqp_url=settings.RABBITMQ_URL,
        exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
    )
    consumer = EventConsumer(manager)

    await consumer.consume(
        queue_name=QUEUE_NAME,
        routing_key=ROUTING_KEY,
        handler=_handle_message,
    )


if __name__ == "__main__":
    asyncio.run(run_worker())
