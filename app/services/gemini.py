from google import genai
import json
from typing import Dict, Any, cast, List, Callable, Optional

from app.core.config import settings
from app.models.preferences import Preferences
from app.models.profile import FitnessLevel, Profile
from app.services.spotify import SpotifyService
from sqlalchemy.orm import Session
class GeminiService:
    def __init__(self, db:Session, profile: Profile, preferences: Preferences):
        """
        Initializes the Gemini Service client using the API key from settings.
        """
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = 'gemini-2.5-flash'
        self.spotify_service = SpotifyService(db, profile, preferences)  
        self.profile = profile
        self.preferences = preferences

    async def get_workout_recommendations(self) -> Dict[str, Any]:
        """
        Generate personalized workout recommendations using the Gemini AI model asynchronously.
        """
        # Determine number of exercises without evaluating SQLAlchemy ColumnElement truthiness
        val = getattr(self.profile, "fitness_level", None)
        if isinstance(val, FitnessLevel) and val == FitnessLevel.ADVANCED:
            num_exercises = 8
        elif isinstance(val, FitnessLevel) and val == FitnessLevel.INTERMEDIATE:
            num_exercises = 6
        else:
            num_exercises = 4

        prompt = f"""
        As a fitness expert, create a personalized workout plan for:
        - Fitness level: {self.profile.fitness_level if self.profile.fitness_level else 'beginner'}
        - Fitness goal: {self.profile.fitness_goal if self.profile.fitness_goal else 'general_fitness'}
        - Available days: {self.profile.available_days if self.profile.available_days else ['Monday', 'Wednesday', 'Friday']}
        - Workout duration: {self.profile.workout_duration_minutes if self.profile.workout_duration_minutes else 45}
        - Preferences:
         + Available equipment: {self.preferences.available_equipment if self.preferences.available_equipment else ['dumbbells', 'resistance bands']}
         + Target muscle groups: {self.preferences.target_muscle_groups if self.preferences.target_muscle_groups else []}
         + Exercise types: {self.preferences.exercise_types if self.preferences.exercise_types else ['strength', 'cardio']}
         + Number of exercises: {num_exercises}


        Format the response as a valid JSON object with the following keys:
        - "exercises": a list of exercise objects, each with "name","sets","reps","rest_seconds", "body_part", "target", "secondary_muscles", "equipment", "gif_url", "instructions". The "instructions" should be a list of step-by-step strings. The "gif_url" should be a link to a demonstration GIF if available. The "secondary_muscles" should be a list of strings.
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

    async def enhance_playlist_parameters(self) -> Dict[str, Any]:
        """
        Generate enhanced music parameters for workouts using the Gemini AI model asynchronously.
        """
        prompt = f"""
        As a fitness music expert, recommend Spotify API parameters for a  workout based on the following user preferences:
        - User's preferred genres: {self.preferences.get('genres', [])}
        - Workout intensity: {self.preferences.get('intensity', 'medium')}
        - Workout duration: {self.preferences.get('duration_minutes', 45)} minutes

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

    async def recommend_spotify_playlist(self) -> Dict[str, Any]:
        # Fetch user's Spotify data
        # This assumes you have the user's Spotify access token stored and refreshed
        if not self.preferences.spotify_data:
            return {
                "message": "Spotify data is not available. Please connect your Spotify account and try again.",
                "playlist_recommendations": [],
                "playlist_url": None,
                "playlist_id": None,
                "playlist_name": None
            }
        try:
            # Example: Get user's top tracks
            top_tracks = await self.spotify_service.get_current_user_top_tracks()
            # I want to check the results
            top_track_names = [track['name'] for track in top_tracks['items']]

            # Example: Get user's top artists
            top_artists = await self.spotify_service.get_current_user_top_artists()
            top_artist_names = [artist['name'] for artist in top_artists['items']]

        except (json.JSONDecodeError, AttributeError):
            # Catch 401 error here
            return {
                "message": "Error fetching Spotify data. Please ensure your Spotify account is connected and try again.",
                "playlist_recommendations": [],
                "playlist_url": None,
                "playlist_id": None,
                "playlist_name": None
            }

        prompt = f"""
        You are a music curator. Your goal is to recommend a Spotify playlist based on the user's preferences.
        Here's the user's information:
        - Preferred Genres: {', '.join(self.preferences.music_genres) if self.preferences.music_genres else 'None'}
        - User's Top Tracks: {', '.join(top_track_names[:5]) if top_track_names else 'None'}
        - User's Top Artists: {', '.join(top_artist_names[:5]) if top_artist_names else 'None'}

        Please suggest 15-20 songs and artists for a Spotify playlist to make sure it lasts within the duration of {self.profile.workout_duration_minutes} minutes. Provide the output in a structured JSON format.
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
            
            user_spotify_profile = await self.spotify_service.get_user_profile()


            # Now, use your SpotifyClient to search for these tracks and potentially create a playlist
            recommended_tracks_uris = []
            for rec in playlist_recommendations_json['playlist_recommendations']:
                search_query = f"track:{rec['song_title']} artist:{rec['artist_name']}"
                search_results = await self.spotify_service.search_tracks(search_query=search_query)
                if search_results and search_results['tracks']['items']:
                    recommended_tracks_uris.append(search_results['tracks']['items'][0]['uri'])

            if recommended_tracks_uris:
                # Create a new playlist
                playlist_genres = ', '.join(self.preferences.music_genres or []) if getattr(self.preferences, 'music_genres', None) else ''
                fitness_goal_val = getattr(self.profile, 'fitness_goal', None)
                fitness_goal_str = getattr(fitness_goal_val, 'value', None) or (str(fitness_goal_val) if fitness_goal_val is not None else 'general_fitness')
                fitness_level_val = getattr(self.profile, 'fitness_level', None)
                fitness_level_str = getattr(fitness_level_val, 'value', None) or (str(fitness_level_val) if fitness_level_val is not None else 'beginner')
                playlist_name = f"SyncNSweat - {playlist_genres} {fitness_goal_str}, {fitness_level_str} Playlist"
                new_playlist = await self.spotify_service.create_playlist(user_spotify_profile.get('id', ''), playlist_name, public=False, )
                if new_playlist:
                    await self.spotify_service.add_tracks_to_playlist(new_playlist['id'], recommended_tracks_uris)
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

    def _normalize_exercise(self, ex: Dict[str,Any]) -> Optional[Dict[str, Any]]:
        """Normalize a single exercise entry from the LLM into a predictable dict or return None."""
        
        # Extract name from various possible keys
        name = ex.get("name") or ex.get("exercise") or ex.get("title")  # type: ignore
        if not name:
            return None

        body_part = ex.get("body_part")  # type: ignore
        target = ex.get("target")  # type: ignore
        equipment = ex.get("equipment")  # type: ignore
        gif_url = ex.get("gif_url")  # type: ignore
        sets = ex.get("sets")  # type: ignore
        reps = ex.get("reps")  # type: ignore
        rest_seconds = ex.get("rest_seconds")  # type: ignore
        secondary_muscles = self._parse_secondary_muscles(ex.get("secondary_muscles"))  # type: ignore
        instructions = self._parse_instructions(ex.get("instructions"))  # type: ignore

        return {
            "name": str(name) if name else "",
            "target": str(target) if target else "",
            "body_part": str(body_part) if body_part else "",
            "secondary_muscles": secondary_muscles,
            "equipment": str(equipment) if equipment else "",
            "gif_url": str(gif_url) if gif_url else "",
            "instructions": instructions,
            "sets": int(sets) if isinstance(sets, (int, float, str)) and str(sets).isdigit() else 3,
            "reps": str(reps) if reps else "10",
            "rest_seconds": int(rest_seconds) if isinstance(rest_seconds, (int, float, str)) and str(rest_seconds).isdigit() else 60,
        }

    def _parse_secondary_muscles(self, raw: Any) -> List[str]:
        """Parse secondary muscles from various possible input formats."""
        if isinstance(raw, list):
            return [str(muscle) for muscle in raw if isinstance(muscle, str)]
        elif isinstance(raw, str):
            return [muscle.strip() for muscle in raw.split(",")]
        return []

    def _parse_instructions(self, raw: Any) -> List[str]:
        """Parse instructions from various possible input formats."""
        if isinstance(raw, list):
            return [step.strip() for step in raw if isinstance(step, str)]
        elif isinstance(raw, str):
            return [raw.strip()]
        return []

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

    async def get_workout_and_playlist(self) -> Dict[str, Any]:
        """
        Convenience method that returns both an AI workout plan and a Spotify playlist
        recommendation/create result. Returns a dict with keys "workout_plan" and
        "playlist". Any errors from either step are included in the corresponding
        value as a message.
        """
        # Use class helpers to call LLM and normalize results
        raw_plan = await self._retry_call(self.get_workout_recommendations,  retries=2)
        workout_plan = self._normalize_workout(raw_plan, self.profile)

        # Get or create Spotify playlist based on profile/preferences, with retry.
        raw_playlist = await self._retry_call(self.recommend_spotify_playlist, retries=2)
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