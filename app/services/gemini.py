from google import genai
import json
from typing import Dict, Any, cast, List, Callable, Optional
from app.core.config import settings
from app.models.preferences import Preferences
from app.schemas.preferences import PreferencesResponse
from app.schemas.profile import ProfileResponse
from app.models.profile import Profile
from app.services.spotify import SpotifyService

class GeminiService:
    def __init__(self):
        """
        Initializes the Gemini Service client using the API key from settings.
        """
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = 'gemini-2.5-flash'
        self.spotify_service = SpotifyService()  # Assuming you have a SpotifyService class for handling Spotify interactions

    async def get_workout_recommendations(self, user_profile: Profile, user_preferences: Preferences) -> Dict[str, Any]:
        """
        Generate personalized workout recommendations using the Gemini AI model asynchronously.
        """
        prompt = f"""
        As a fitness expert, create a personalized workout plan for:
        - Fitness level: {user_profile.fitness_level if user_profile.fitness_level else 'beginner'}
        - Fitness goal: {user_profile.fitness_goal if user_profile.fitness_goal else 'general_fitness'}
        - Available days: {user_profile.available_days if user_profile.available_days else ['Monday', 'Wednesday', 'Friday']}
        - Workout duration: {user_profile.workout_duration_minutes if user_profile.workout_duration_minutes else 45}
        - Preferences:
         + Available equipment: {user_preferences.available_equipment if user_preferences.available_equipment else ['dumbbells', 'resistance bands']}
         + Target muscle groups: {user_preferences.target_muscle_groups if user_preferences.target_muscle_groups else []}
         + Exercise types: {user_preferences.exercise_types if user_preferences.exercise_types else ['strength', 'cardio']}


        Format the response as a valid JSON object with the following keys:
        - "exercises": a list of exercise objects, each with "name", "sets", "reps", "machine" and "rest" in minutes.
        - "intensity": an integer representing the overall workout intensity from 1 to 10.
        - "duration": an integer for the recommended workout duration in minutes.
        - "notes": a string containing any specific form or safety tips.
        """
        

        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        try:
            # Clean up potential markdown formatting from the response
            cleaned_response = response.text.strip().lstrip('```json').rstrip('```').strip()
            return json.loads(cleaned_response)
        except (json.JSONDecodeError, AttributeError):
            return {
                "exercises": [],
                "intensity": 5,
                "duration": 45,
                "notes": "Unable to parse AI response. Please try again.",
                "spotify_playlist": "default-workout-playlist"
            }

    async def enhance_playlist_parameters(self,  user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate enhanced music parameters for workouts using the Gemini AI model asynchronously.
        """
        prompt = f"""
        As a fitness music expert, recommend Spotify API parameters for a  workout based on the following user preferences:
        - User's preferred genres: {user_preferences.get('genres', [])}
        - Workout intensity: {user_preferences.get('intensity', 'medium')}
        - Workout duration: {user_preferences.get('duration_minutes', 45)} minutes

        Return only a single, valid JSON object with the following keys for the Spotify API:
        - "target_tempo": a number representing the target BPM.
        - "target_energy": a float between 0.0 and 1.0.
        - "target_valence": a float between 0.0 and 1.0.
        - "target_danceability": a float between 0.0 and 1.0.
        """

        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        try:
            # Clean up potential markdown formatting from the response
            cleaned_response = response.text.strip().lstrip('```json').rstrip('```').strip()

            return json.loads(cleaned_response)
        except (json.JSONDecodeError, AttributeError):
            return {
                "target_tempo": 128,
                "target_energy": 0.8,
                "target_valence": 0.7,
                "target_danceability": 0.7
            }

    async def recommend_spotify_playlist(self,user_profile: ProfileResponse, user_preferences: PreferencesResponse):
        # Fetch user's Spotify data
        # This assumes you have the user's Spotify access token stored and refreshed
        try:
            # Example: Get user's top tracks
            top_tracks = await self.spotify_service.get_current_user_top_tracks(user_preferences.spotify_data.get('access_token', ''))
            top_track_names = [track['name'] for track in top_tracks['items']]

            # Example: Get user's top artists
            top_artists = await self.spotify_service.get_current_user_top_artists(user_preferences.spotify_data.get('access_token', ''))
            top_artist_names = [artist['name'] for artist in top_artists['items']]

            # seed_tracks = await self.spotify_service.get_seed_tracks(user_preferences.spotify_data.get('access_token', ''), user_preferences.music_genres)

        except (json.JSONDecodeError, AttributeError):
            return {
                "message": "Error fetching Spotify data. Please ensure your Spotify account is connected and try again.",
                "playlist_recommendations": [],
                "playlist_url": None
            }

        prompt = f"""
        You are a music curator. Your goal is to recommend a Spotify playlist based on the user's preferences.
        Here's the user's information:
        - User ID: {user_profile.id}
        - Preferred Genres: {', '.join(user_preferences.music_genres) if user_preferences.music_genres else 'None'}
        - User's Top Tracks: {', '.join(top_track_names[:5]) if top_track_names else 'None'}
        - User's Top Artists: {', '.join(top_artist_names[:5]) if top_artist_names else 'None'}

        Please suggest 15-20 songs and artists for a Spotify playlist to make sure it lasts within the duration of {user_profile.workout_duration_minutes} minutes. Provide the output in a structured JSON format.
        The JSON should have a 'playlist_recommendations' key, which is a list of dicts.
        Each dict should have:
        - 'song_title': (string)
        - 'artist_name': (string)
        - 'reason': (string) A very brief reason for the recommendation (1-2 sentences).

        Example JSON structure:
        {{
            "playlist_recommendations": [
                {{
                    "song_title": "Blinding Lights",
                    "artist_name": "The Weeknd",
                    "reason": "Upbeat and energetic, perfect for a high-intensity workout."
                }},
                {{
                    "song_title": "Levitating",
                    "artist_name": "Dua Lipa",
                    "reason": "Catchy and motivating, great for keeping the energy high."
                }}
            ]
        }}
        """

        try:
            response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
            
            
            response_text = response.text.strip().lstrip('```json').rstrip('```').strip()
            playlist_recommendations_json = json.loads(response_text)
            
            user_spotify_profile = await self.spotify_service.get_user_profile(user_preferences.spotify_data.get('access_token', ''))


            # Now, use your SpotifyClient to search for these tracks and potentially create a playlist
            recommended_tracks_uris = []
            for rec in playlist_recommendations_json['playlist_recommendations']:
                search_query = f"track:{rec['song_title']} artist:{rec['artist_name']}"
                search_results = await self.spotify_service.search_tracks(user_preferences.spotify_data.get('access_token', ''), search_query)
                if search_results and search_results['tracks']['items']:
                    recommended_tracks_uris.append(search_results['tracks']['items'][0]['uri'])

            if recommended_tracks_uris:
                # Create a new playlist
                playlist_name = f"SyncNSweat - {', '.join(user_preferences.music_genres)} {user_profile.fitness_goal} {user_profile.fitness_level} Playlist"
                new_playlist = await self.spotify_service.create_playlist(user_preferences.spotify_data.get('access_token', ''), user_spotify_profile.get('id', ''), playlist_name, public=False)
                if new_playlist:
                    await self.spotify_service.add_tracks_to_playlist(user_preferences.spotify_data.get('access_token', ''), new_playlist['id'], recommended_tracks_uris)
                    return {"message": "Playlist created and tracks added!", "playlist_url": new_playlist['external_urls']['spotify'], "playlist_id": new_playlist['id'], "playlist_name": new_playlist['name']}
                else:
                    return {"message": "Could not create Spotify playlist."}
            else:
                return {"message": "No tracks found for the recommendations."}

        except (json.JSONDecodeError, AttributeError):
            return {
                "message": "Error processing playlist recommendations. Please try again.",
                "playlist_recommendations": [],
                "playlist_url": None
            }

    async def _retry_call(self, coro_func: Callable[..., Any], *coro_args: Any, retries: int = 2) -> Any:
        """Utility to retry an async coroutine function a small number of times."""
        last: Optional[Any] = None
        for _ in range(retries):
            try:
                return await coro_func(*coro_args)
            except Exception:
                last = None
        return last

    def _normalize_exercise(self, ex: Any) -> Optional[Dict[str, Any]]:
        """Normalize a single exercise entry from the LLM into a predictable dict or return None."""
        if not isinstance(ex, dict):
            return None
        
        # Extract name from various possible keys
        name = ex.get("name") or ex.get("exercise") or ex.get("title")  # type: ignore
        if not name:
            return None

        sets = self._parse_sets(ex.get("sets"))  # type: ignore
        reps = ex.get("reps", "")  # type: ignore
        machine = ex.get("machine") or ex.get("equipment")  # type: ignore
        rest_minutes = self._parse_rest(ex.get("rest"), ex.get("rest_minutes"))  # type: ignore
        notes = ex.get("notes") or ex.get("instruction")  # type: ignore

        return {
            "name": str(name) if name else "",
            "sets": sets,
            "reps": str(reps) if reps else "",
            "machine": str(machine) if machine else None,
            "rest_minutes": rest_minutes,
            "notes": str(notes) if notes else None,
        }

    def _parse_sets(self, sets_val: Any) -> Optional[int]:
        """Parse sets value from various formats."""
        if sets_val is None:
            return None
        if isinstance(sets_val, int):
            return sets_val
        if isinstance(sets_val, (float, str)):
            try:
                return int(str(sets_val).strip().split()[0])
            except (ValueError, IndexError):
                return None
        return None

    def _parse_rest(self, rest: Any, rest_minutes: Any) -> Optional[float]:
        """Parse rest time from various formats."""
        rest_val = rest if rest is not None else rest_minutes
        if rest_val is None:
            return None
        try:
            return float(rest_val)
        except (ValueError, TypeError):
            return None

    def _normalize_workout(self, raw_plan: Any, user_profile: Profile) -> Dict[str, Any]:
        """Normalize a raw LLM workout plan into a predictable dict shape."""
        fallback: Dict[str, Any] = {
            "exercises": [],
            "intensity": 5,
            "duration": getattr(user_profile, "workout_duration_minutes", 45) or 45,
            "notes": "Unable to generate a valid workout plan from the LLM."
        }
        if not isinstance(raw_plan, dict):
            return fallback

        exercises_raw = raw_plan.get("exercises") or []  # type: ignore
        normalized: List[Dict[str, Any]] = []
        if isinstance(exercises_raw, list):
            for ex in exercises_raw:
                norm = self._normalize_exercise(ex)
                if norm:
                    normalized.append(norm)

        intensity_val = raw_plan.get("intensity", 5)  # type: ignore
        duration_val = raw_plan.get("duration") or getattr(user_profile, "workout_duration_minutes", 45) or 45  # type: ignore
        notes_val = raw_plan.get("notes") or None  # type: ignore

        out: Dict[str, Any] = {
            "exercises": normalized,
            "intensity": int(intensity_val) if isinstance(intensity_val, (int, float, str)) else 5,
            "duration": int(duration_val) if duration_val else 45,  # type: ignore
            "notes": notes_val,
        }
        return out

    async def get_workout_and_playlist(self, user_profile: Profile, user_preferences: Preferences) -> Dict[str, Any]:
        """
        Convenience method that returns both an AI workout plan and a Spotify playlist
        recommendation/create result. Returns a dict with keys "workout_plan" and
        "playlist". Any errors from either step are included in the corresponding
        value as a message.
        """
        # Use class helpers to call LLM and normalize results
        raw_plan = await self._retry_call(self.get_workout_recommendations, user_profile, user_preferences, retries=2)
        workout_plan = self._normalize_workout(raw_plan, user_profile)


        # Get or create Spotify playlist based on profile/preferences, with retry.
        raw_playlist = await self._retry_call(self.recommend_spotify_playlist, user_profile, user_preferences, retries=2)
        playlist_result: Dict[str, Any]
        if isinstance(raw_playlist, dict):
            playlist_result = cast(Dict[str, Any], raw_playlist)
        else:
            playlist_result = {
                "message": "Unable to generate playlist from LLM/Spotify.",
                "playlist_recommendations": [],
                "playlist_url": None,
                "playlist_id": None,
                "playlist_name": None
            }

        return {"workout_plan": workout_plan, "playlist": playlist_result}