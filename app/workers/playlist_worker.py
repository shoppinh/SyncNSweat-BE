from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Final, List, Optional, cast

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.messaging.connection import RabbitMQConnectionManager
from app.messaging.consumer import EventConsumer
from app.messaging.events import EventEnvelope, EventType, create_event_envelope
from app.observability.metrics import incr, timed
from app.repositories.preferences import PreferencesRepository
from app.repositories.profile import ProfileRepository
from app.repositories.workout_request import WorkoutRequestRepository
from app.services.outbox import OutboxService
from app.services.playlist_selector import PlaylistSelectorService
from app.services.spotify import SpotifyService

QUEUE_NAME: Final[str] = "playlist-generation"
ROUTING_KEY: Final[str] = "workout.draft.generated"


def _safe_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return cast(Dict[str, Any], value)
    return {}


MIN_AI_MAPPED_TRACKS: Final[int] = 8


def _unavailable_playlist(*, source: str = "fallback_none") -> Dict[str, Any]:
    return {
        "id": None,
        "name": None,
        "description": "Playlist unavailable",
        "external_url": None,
        "image_url": None,
        "status": "unavailable",
        "source": source,
    }


async def _resolve_playlist_from_ai_candidates(
    db: Session,
    *,
    profile_id: int,
    draft: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    profile_repo = ProfileRepository(db)
    preferences_repo = PreferencesRepository(db)

    profile = profile_repo.get_by_id(profile_id)
    preferences = preferences_repo.get_by_profile_id(profile_id)
    if profile is None or preferences is None:
        return None

    song_candidates = cast(List[Dict[str, Any]], draft.get("song_candidates") or [])
    if not song_candidates:
        return None

    spotify_service = SpotifyService(db, profile, preferences)
    # make_api_call() is synchronous; run it in a thread executor so it does
    # not block the event loop while waiting on the HTTP response.
    loop = asyncio.get_running_loop()
    me = await loop.run_in_executor(
        None,
        lambda: spotify_service.make_api_call(
            method="GET",
            url=f"{spotify_service.api_base_url}/me",
        ),
    )
    user_id = me.get("id")
    if not user_id:
        return None

    uris: List[str] = []
    for candidate in song_candidates:
        title = str(candidate.get("song_title") or "").strip()
        artist = str(candidate.get("artist_name") or "").strip()
        if not title:
            continue
        query = f"track:{title}"
        if artist:
            query += f" artist:{artist}"
        search = await spotify_service.search_tracks(search_query=query)
        items = cast(List[Dict[str, Any]], search.get("tracks", {}).get("items") or [])
        if not items:
            continue
        uri = items[0].get("uri")
        if isinstance(uri, str) and uri not in uris:
            uris.append(uri)

    if len(uris) < MIN_AI_MAPPED_TRACKS:
        return None

    fitness_goal = getattr(getattr(profile, "fitness_goal", None), "value", "general_fitness")
    playlist_name = f"SyncNSweat {fitness_goal} AI Mix"
    description = "Auto-generated playlist from AI song candidates"
    playlist = await spotify_service.create_playlist(
        user_id=user_id,
        name=playlist_name,
        description=description,
        public=False,
    )
    playlist_id = playlist.get("id")
    if not playlist_id:
        return None

    await spotify_service.add_tracks_to_playlist(playlist_id=playlist_id, track_uris=uris)

    external_urls = cast(Dict[str, Any], playlist.get("external_urls") or {})
    images = cast(List[Dict[str, Any]], playlist.get("images") or [])
    image_url = images[0].get("url") if images else None
    return {
        "id": playlist_id,
        "name": playlist.get("name") or playlist_name,
        "description": playlist.get("description") or description,
        "external_url": external_urls.get("spotify"),
        "image_url": image_url,
        "status": "resolved_from_ai",
        "source": "ai_song_candidates",
    }


async def _resolve_playlist(
    db: Session,
    *,
    profile_id: int,
    draft: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        ai_playlist = await _resolve_playlist_from_ai_candidates(
            db,
            profile_id=profile_id,
            draft=draft,
        )
    except Exception:
        ai_playlist = None
    if ai_playlist is not None:
        return ai_playlist

    profile_repo = ProfileRepository(db)
    preferences_repo = PreferencesRepository(db)
    profile = profile_repo.get_by_id(profile_id)
    preferences = preferences_repo.get_by_profile_id(profile_id)
    if profile is None or preferences is None:
        incr("playlist_fail_open_count")
        return _unavailable_playlist()

    try:
        selector = PlaylistSelectorService(db, profile, preferences)
        fallback_playlist = selector.shuffle_top_and_recent_tracks(
            fitness_goal=getattr(getattr(profile, "fitness_goal", None), "value", "general_fitness"),
            duration_minutes=getattr(profile, "workout_duration_minutes", 45),
        )
        if not fallback_playlist:
            incr("playlist_fail_open_count")
            return _unavailable_playlist()
        fallback_playlist["status"] = "resolved_from_fallback"
        fallback_playlist["source"] = "shuffle_top_and_recent_tracks"
        return fallback_playlist
    except Exception:
        incr("playlist_fail_open_count")
        return _unavailable_playlist()


async def process_event(payload: Dict[str, Any]) -> None:
    envelope = EventEnvelope.model_validate(payload)
    incr("playlist_worker_received_count")

    request_id = int(envelope.payload["request_id"])
    profile_id = int(envelope.payload["profile_id"])
    draft = _safe_json(envelope.payload.get("draft"))

    db: Session = SessionLocal()
    request_repo = WorkoutRequestRepository(db)
    outbox_service = OutboxService(db)

    try:

        with db.begin():
            request = request_repo.get_by_id(request_id)
            if request is None:
                return

            with timed("playlist_generation_latency"):
                playlist = await _resolve_playlist(
                    db,
                    profile_id=profile_id,
                    draft=draft,
                )
            next_event = create_event_envelope(
                event_type=EventType.PLAYLIST_READY,
                source="worker.playlist",
                payload={
                    "request_id": request_id,
                    "profile_id": profile_id,
                    "playlist": playlist,
                },
                saga_id=envelope.saga_id,
                correlation_id=envelope.correlation_id,
            )
            with db.begin_nested():
                request_repo.set_status(request, status="PARTIAL_READY")
                outbox_service.enqueue_event(
                    event_id=next_event.event_id,
                    routing_key="playlist.ready",
                    exchange_name=settings.RABBITMQ_EXCHANGE_NAME,
                    payload=next_event.model_dump(mode="json"),
                )
        incr("playlist_worker_success_count")
    except Exception as exc:
        with db.begin():
            request = request_repo.get_by_id(request_id)
            if request is not None:
                request_repo.set_status(
                    request,
                    status="FAILED",
                    error_code="PLAYLIST_GENERATION_FAILED",
                    error_message=str(exc),
                )
        incr("playlist_worker_failure_count")
    finally:
        db.close()


async def _handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):
        body = json.loads(message.body.decode("utf-8"))
        await process_event(_safe_json(body))


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
