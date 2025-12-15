import random
import time
from typing import Any, Dict, List, Optional, cast
from app.models.preferences import Preferences
from app.models.profile import Profile
from app.services.spotify import SpotifyService
from sqlalchemy.orm import Session


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

    # TODO: Use this method as fallback in playlist selection if Gemini API fails
    def select_playlist_for_workout(
        self,
        fitness_goal: str,
        music_genres: List[str],
        music_tempo: str,
        duration_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Select a playlist for a workout based on the workout focus and user preferences.
        
        Args:
            access_token: Spotify access token
            workout_focus: The focus of the workout (e.g., "Upper Body", "Push")
            music_genres: List of user's preferred music genres
            music_tempo: User's preferred music tempo (e.g., "slow", "medium", "fast")
            recently_used_playlists: List of recently used playlist IDs to avoid
            
        Returns:
            A dictionary with playlist information
        """

        max_duration_ms = duration_minutes * 60 * 1000 if duration_minutes is not None else 60 * 60 * 1000

        # Step 1: Fetch user profile
        user = self._api_get("/me")
        self._raise_if_auth_error(user, "GET /me")
        user_id = user.get("id")
        user_country = user.get("country")
        if not user_id:
            raise Exception("Spotify authentication failed: missing user id")

        # Step 2: Fetch taste signals
        top_tracks_resp = self._api_get(
            "/me/top/tracks",
            params={"limit": 10, "time_range": "medium_term"},
        )
        self._raise_if_auth_error(top_tracks_resp, "GET /me/top/tracks")
        top_artists_resp = self._api_get(
            "/me/top/artists",
            params={"limit": 5, "time_range": "medium_term"},
        )
        self._raise_if_auth_error(top_artists_resp, "GET /me/top/artists")
        recent_resp = self._api_get(
            "/me/player/recently-played",
            params={"limit": 10},
        )
        self._raise_if_auth_error(recent_resp, "GET /me/player/recently-played")

        top_tracks_items = cast(List[Any], top_tracks_resp.get("items") or [])
        top_artists_items = cast(List[Any], top_artists_resp.get("items") or [])
        recent_items_raw = cast(List[Any], recent_resp.get("items") or [])
        top_tracks = [cast(Dict[str, Any], t) for t in top_tracks_items if isinstance(t, dict)]
        top_artists = [cast(Dict[str, Any], a) for a in top_artists_items if isinstance(a, dict)]
        recent_items = [cast(Dict[str, Any], i) for i in recent_items_raw if isinstance(i, dict)]
        recent_tracks = [cast(Dict[str, Any], i["track"]) for i in recent_items if isinstance(i.get("track"), dict)]

        # Step 3: Validate preferred genres
        genre_seeds_resp = self._api_get("/recommendations/available-genre-seeds")
        self._raise_if_auth_error(genre_seeds_resp, "GET /recommendations/available-genre-seeds")
        available_genres = set(genre_seeds_resp.get("genres") or [])
        requested_genres = [g.strip().lower() for g in (music_genres or []) if g and g.strip()]
        requested_genres = requested_genres[:5]
        validated_genres = [g for g in requested_genres if g in available_genres]

        # Step 4: Select recommendation seeds (max total 5)
        seed_track_ids: List[str] = []
        for t in top_tracks[:3]:
            tid = t.get("id")
            if tid:
                seed_track_ids.append(tid)

        seed_artist_ids: List[str] = []
        for a in top_artists[:2]:
            aid = a.get("id")
            if aid:
                seed_artist_ids.append(aid)

        remaining_seed_slots = max(0, 5 - (len(seed_track_ids) + len(seed_artist_ids)))
        seed_genres = validated_genres[:remaining_seed_slots]

        # Step 5: Compute average audio profile
        avg_energy: Optional[float] = None
        avg_valence: Optional[float] = None
        avg_danceability: Optional[float] = None
        avg_tempo: Optional[float] = None

        if seed_track_ids:
            features_resp = self._api_get(
                "/audio-features",
                params={"ids": ",".join(seed_track_ids)},
            )
            self._raise_if_auth_error(features_resp, "GET /v1/audio-features")
            raw_features = cast(List[Any], features_resp.get("audio_features") or [])
            features = [cast(Dict[str, Any], f) for f in raw_features if isinstance(f, dict)]

            def _avg(key: str) -> Optional[float]:
                vals: List[float] = []
                for f in features:
                    raw_val = f.get(key)
                    if isinstance(raw_val, (int, float)):
                        vals.append(float(raw_val))
                if not vals:
                    return None
                return float(sum(vals) / len(vals))

            avg_energy = _avg("energy")
            avg_valence = _avg("valence")
            avg_danceability = _avg("danceability")
            avg_tempo = _avg("tempo")

        # If audio features were missing, fall back to workout-derived targets
        fallback_targets = self.calculate_target_params(fitness_goal,music_tempo)
        target_energy = avg_energy if avg_energy is not None else fallback_targets.get("target_energy", 0.7)
        target_tempo = avg_tempo if avg_tempo is not None else fallback_targets.get("target_tempo", 130)
        target_valence = avg_valence if avg_valence is not None else 0.5
        target_danceability = avg_danceability if avg_danceability is not None else 0.5

        # Step 6: Request recommendations (retry once)
        rec_params: Dict[str, Any] = {
            "limit": 50,
            "market": user_country,
            "target_energy": target_energy,
            "target_valence": target_valence,
            "target_danceability": target_danceability,
            "target_tempo": target_tempo,
        }
        if seed_track_ids:
            rec_params["seed_tracks"] = ",".join(seed_track_ids)
        if seed_artist_ids:
            rec_params["seed_artists"] = ",".join(seed_artist_ids)
        if seed_genres:
            rec_params["seed_genres"] = ",".join(seed_genres)

        recommendations_resp = self._api_get("/recommendations", params=rec_params)
        self._raise_if_auth_error(recommendations_resp, "GET /recommendations")
        rec_tracks_raw = cast(List[Any], recommendations_resp.get("tracks") or [])
        rec_tracks = [cast(Dict[str, Any], t) for t in rec_tracks_raw if isinstance(t, dict)]
        if not rec_tracks:
            # one retry per spec
            recommendations_resp = self._api_get("/recommendations", params=rec_params)
            self._raise_if_auth_error(recommendations_resp, "GET /recommendations (retry)")
            rec_tracks_raw = cast(List[Any], recommendations_resp.get("tracks") or [])
            rec_tracks = [cast(Dict[str, Any], t) for t in rec_tracks_raw if isinstance(t, dict)]

        # Step 7: Filter and enforce duration
        seed_track_set = set(seed_track_ids)
        chosen_uris: List[str] = []
        total_ms = 0
        seen_track_ids: set[str] = set()

        def _accumulate_from_tracks(tracks: List[Dict[str, Any]]) -> None:
            nonlocal total_ms
            for t in tracks:
                if total_ms >= max_duration_ms:
                    break
                tid = t.get("id")
                if not tid or tid in seen_track_ids or tid in seed_track_set:
                    continue
                uri = t.get("uri")
                dur = t.get("duration_ms")
                if not uri or not isinstance(dur, int):
                    continue
                seen_track_ids.add(tid)
                chosen_uris.append(uri)
                total_ms += dur

        _accumulate_from_tracks(rec_tracks)

        # If recommendations are empty, fall back to available tracks
        if not chosen_uris:
            combined: List[Dict[str, Any]] = top_tracks + recent_tracks
            random.shuffle(combined)
            _accumulate_from_tracks(combined)

        # If still empty, do not hard-fail (unless auth failed). Create an empty playlist.
        # Step 8: Create playlist
        safe_focus = (fitness_goal or "Workout").strip() or "Workout"
        safe_tempo = (music_tempo or "").strip()
        auto_name_parts = ["SyncNSweat", safe_focus]
        if safe_tempo:
            auto_name_parts.append(safe_tempo.capitalize())
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

        # Step 9: Add tracks
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
        
