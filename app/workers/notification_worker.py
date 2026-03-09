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
from app.messaging.events import EventEnvelope, EventType
from app.observability.metrics import incr, timed
from app.repositories.workout_request import WorkoutRequestRepository

QUEUE_NAME: Final[str] = "notification"


def _safe_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return cast(Dict[str, Any], value)
    return {}


def process_event(payload: Dict[str, Any]) -> None:
    envelope = EventEnvelope.model_validate(payload)
    incr("notification_worker_received_count")
    request_id_value = envelope.payload.get("request_id")
    if request_id_value is None:
        return
    request_id = int(request_id_value)

    db: Session = SessionLocal()
    repo = WorkoutRequestRepository(db)

    try:
        with timed("notification_latency"):
            with db.begin():
                request = repo.get_by_id(request_id)
                if request is None:
                    return

                if envelope.event_type == EventType.WORKOUT_PLAN_COMPLETED:
                    repo.set_status(request, status="COMPLETED")
                elif envelope.event_type == EventType.WORKOUT_PLAN_FAILED:
                    repo.set_status(
                        request,
                        status="FAILED",
                        error_code="PIPELINE_FAILED",
                        error_message=_safe_json(envelope.payload).get("error_message"),
                    )
        incr("notification_worker_success_count")
    finally:
        db.close()


async def _handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):
        body = json.loads(message.body.decode("utf-8"))
        process_event(_safe_json(body))


async def run_worker() -> None:
    manager = RabbitMQConnectionManager(
        amqp_url=settings.RABBITMQ_URL,
        exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
    )
    consumer = EventConsumer(manager)

    await asyncio.gather(
        consumer.consume(
            queue_name=QUEUE_NAME,
            routing_key="workout.completed",
            handler=_handle_message,
        ),
        consumer.consume(
            queue_name=QUEUE_NAME,
            routing_key="workout.failed",
            handler=_handle_message,
        ),
    )


if __name__ == "__main__":
    asyncio.run(run_worker())
