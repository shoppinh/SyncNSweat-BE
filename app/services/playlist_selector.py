import random
import time
from typing import Any, Dict, List, Optional, cast

from sqlalchemy.orm import Session

from app.models.preferences import Preferences
from app.models.profile import Profile
from app.services.spotify import SpotifyService


class PlaylistSelectorService:
    """
    Service for selecting playlists based on workout type and user preferences.
    """
    
    def __init__(self, db:Session, profile: Profile, preferences: Preferences):
        self.spotify_service = SpotifyService(db, profile, preferences)
        self.energy_map = {
            "strength": 0.8,
            "endurance": 0.72,
            "weight_loss": 0.75,
            "muscle_gain": 0.85,
            "general_fitness": 0.7,
        }
        
        self.tempo_map = {
            "slow": 100,
            "medium": 130,
            "fast": 160,
            "mixed": 125
        }

        
    
    def _api_get(self,path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.spotify_service.make_api_call(
            method="GET",
            url=f"{self.spotify_service.api_base_url}{path}",
            params=params,
        )

    def _api_post(self,path: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.spotify_service.make_api_call(
            method="POST",
            url=f"{self.spotify_service.api_base_url}{path}",
            json_data=json_data,
        )

    def _raise_if_auth_error(self,resp: Dict[str, Any], context: str) -> None:
        err = resp.get("error")
        if not err:
            return
        if not isinstance(err, dict):
            return
        err_dict = cast(Dict[str, Any], err)
        status_any: Any = err_dict.get("status")
        status = int(status_any) if isinstance(status_any, (int, float)) else None
        if status in (401, 403):
            raise Exception(f"Spotify authentication failed during {context}: {err}")

    def shuffle_top_and_recent_tracks(
        self,
        fitness_goal: str,
        duration_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Select a playlist for a workout based on the workout focus and user preferences.
        
        Args:
            fitness_goal: The fitness goal of the user (e.g., "Strength", "Endurance")
            duration_minutes: Optional duration of the workout in minutes
            
        Returns:
            A dictionary with playlist information
        """

        max_duration_ms = duration_minutes * 60 * 1000 if duration_minutes is not None else 60 * 60 * 1000

        # Step 1: Fetch user profile
        user = self._api_get("/me")
        self._raise_if_auth_error(user, "GET /me")
        user_id = user.get("id")
        if not user_id:
            raise Exception("Spotify authentication failed: missing user id")

        # Step 2: Fetch taste signals
        top_tracks_resp = self._api_get(
            "/me/top/tracks",
            params={"limit": 50, "time_range": "medium_term"},
        )
        self._raise_if_auth_error(top_tracks_resp, "GET /me/top/tracks")
        recent_resp = self._api_get(
            "/me/player/recently-played",
            params={"limit": 10},
        )
        self._raise_if_auth_error(recent_resp, "GET /me/player/recently-played")

        top_tracks_items = cast(List[Any], top_tracks_resp.get("items") or [])
        recent_items_raw = cast(List[Any], recent_resp.get("items") or [])
        top_tracks = [cast(Dict[str, Any], t) for t in top_tracks_items if isinstance(t, dict)]
        recent_items = [cast(Dict[str, Any], i) for i in recent_items_raw if isinstance(i, dict)]
        recent_tracks = [cast(Dict[str, Any], i["track"]) for i in recent_items if isinstance(i.get("track"), dict)]
        
        # Step 2.5: Combine and shuffle
        combined_tracks = top_tracks + recent_tracks
        random.shuffle(combined_tracks)

        # Step 3: Filter and enforce duration
        chosen_uris: List[str] = []
        total_ms = 0
        seen_track_ids: set[str] = set()
        
        def _accumulate_from_tracks(tracks: List[Dict[str, Any]]) -> None:
            nonlocal total_ms
            for t in tracks:
                if total_ms >= max_duration_ms:
                    break
                tid = t.get("id")
                if not tid or tid in seen_track_ids:
                    continue
                uri = t.get("uri")
                dur = t.get("duration_ms")
                if not uri or not isinstance(dur, int):
                    continue
                seen_track_ids.add(tid)
                chosen_uris.append(uri)
                total_ms += dur

        _accumulate_from_tracks(combined_tracks)

        # If recommendations are empty, fall back to available tracks
        if not chosen_uris:
            raise Exception("No suitable tracks found for playlist creation")
            
        # Step 4: Create playlist
        safe_focus = (fitness_goal or "Workout").strip() or "Workout"
        auto_name_parts = ["SyncNSweat", safe_focus, "Randomized"]
        playlist_name = " ".join(auto_name_parts) + " Playlist"
        description = "Auto-generated fallback playlist with enforced duration"

        playlist = self._api_post(
            f"/users/{user_id}/playlists",
            json_data={
                "name": playlist_name,
                "public": False,
                "description": description,
            },
        )
        self._raise_if_auth_error(playlist, "POST /users/{user_id}/playlists")
        playlist_id = playlist.get("id")
        if not playlist_id:
            # Non-auth failures should not crash the flow per spec; return best-effort.
            return {
                "id": None,
                "name": playlist_name,
                "description": description,
                "external_url": None,
                "image_url": None,
                "tracksAdded": 0,
                "durationMinutes": 0,
                "strategyUsed": "FALLBACK",
                "createdAt": int(time.time()),
            }

        # Step 5: Add tracks
        if chosen_uris:
            add_resp = self._api_post(
                f"/playlists/{playlist_id}/tracks",
                json_data={"uris": chosen_uris},
            )
            self._raise_if_auth_error(add_resp, "POST /playlists/{playlist_id}/tracks")

        external_urls_any: Any = playlist.get("external_urls")
        external_urls: Dict[str, Any] = cast(Dict[str, Any], external_urls_any) if isinstance(external_urls_any, dict) else {}

        images_any: Any = playlist.get("images")
        images: List[Any] = cast(List[Any], images_any) if isinstance(images_any, list) else []
        image_url = None
        if images and isinstance(images[0], dict):
            image_url = cast(Dict[str, Any], images[0]).get("url")

        return {
            "id": playlist_id,
            "name": playlist.get("name") or playlist_name,
            "description": playlist.get("description") or description,
            "external_url": external_urls.get("spotify"),
            "image_url": image_url,
        }
    
    def calculate_target_params(
    self,
    fitness_goal: Optional[str] = None,
    music_tempo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """        Calculate target parameters for recommendations based on workout type and music tempo.
        """
        # Map workout type to energy level
        fitness_goal_key = fitness_goal or ""
        tempo_key = music_tempo or ""
        target_energy = self.energy_map.get(fitness_goal_key, 0.7)
        target_tempo = self.tempo_map.get(tempo_key.lower(), 130)

        return {
            "target_energy": target_energy,
            "target_tempo": target_tempo
        }
        
