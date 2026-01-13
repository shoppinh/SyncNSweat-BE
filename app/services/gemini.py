import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from google import genai
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.preferences import Preferences
from app.models.profile import FitnessLevel, Profile
from app.models.workout import Exercise
from app.services.spotify import SpotifyService


class GeminiService:
    def __init__(self, db: Session, profile: Profile, preferences: Preferences):
        """
        Initializes the Gemini Service client using the API key from settings.
        """
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash-lite"
        self.spotify_service = SpotifyService(db, profile, preferences)
        self.profile = profile
        self.preferences = preferences

    async def get_workout_recommendations(self) -> Dict[str, Any]:
        """
        Generate personalized workout recommendations using the Gemini AI model asynchronously.
        """
        # Determine number of exercises without evaluating SQLAlchemy ColumnElement truthiness
        #
        num_exercises = self._get_num_exercises_based_on_fitness_level()

        prompt = f"""
        As a fitness expert, create a personalized workout plan for:
        - Fitness level: {getattr(self.profile, "fitness_level", "beginner")}
        - Fitness goal: {getattr(self.profile, "fitness_goal", "general_fitness")}
        - Workout duration: {getattr(self.profile, "workout_duration_minutes", 45)}
        - Preferences:
         + Available equipment: {getattr(self.preferences, "available_equipment", ["dumbbells", "resistance bands"])}
         + Target muscle groups: {getattr(self.preferences, "target_muscle_groups", [])}
         + Exercise types: {getattr(self.preferences, "exercise_types", ["strength", "cardio"])}
         + Number of exercises: {num_exercises}


        Format the response as a valid JSON object with the following keys:
        - "workout_exercises": a list of exercise objects, each with "name","sets","reps","rest_seconds", "body_part", "target", "secondary_muscles", "equipment", "instructions". The "instructions" should be a list of step-by-step strings. The "secondary_muscles" should be a list of strings. The "equipment" should specify the required equipments in concatenated string format.
        - "focus": a string representing the workout focus, e.g., "Upper Body", "Lower Body", "Push", "Pull", "Legs".
        - "duration_minutes": an integer for the recommended workout duration in minutes.
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name, contents=prompt
            )
        except Exception as e:
            print(f"Error generating AI response for workout recommendations. {e}")
            return {
                "workout_exercises": [],
                "duration_minutes": 45,
                "spotify_playlist": "default-workout-playlist",
            }

        try:
            # Clean up potential markdown formatting from the response
            if response.text is None:
                return {
                    "workout_exercises": [],
                    "duration_minutes": 45,
                    "spotify_playlist": "default-workout-playlist",
                }
            cleaned_response = (
                response.text.strip().lstrip("```json").rstrip("```").strip()
            )
            return json.loads(cleaned_response)
        except (json.JSONDecodeError, AttributeError):
            return {
                "workout_exercises": [],
                "duration_minutes": 45,
                "spotify_playlist": "default-workout-playlist",
            }

    def _get_num_exercises_based_on_fitness_level(self) -> int:
        """
        Determine the number of exercises based on the user's fitness level.
        """
        val = getattr(self.profile, "fitness_level", None)
        if isinstance(val, FitnessLevel) and val == FitnessLevel.ADVANCED:
            return 8
        elif isinstance(val, FitnessLevel) and val == FitnessLevel.INTERMEDIATE:
            return 6
        else:
            return 4

    async def get_workout_schedule_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate personalized workout schedule recommendations using the Gemini AI model asynchronously.
        """

        num_exercises = self._get_num_exercises_based_on_fitness_level()
        prompt = f"""
        As a fitness expert, create a personalized weekly workout schedule for:
        - Fitness level: {getattr(self.profile, "fitness_level", "beginner")}
        - Fitness goal: {getattr(self.profile, "fitness_goal", "general_fitness")}
        - Available days: {getattr(self.profile, "available_days", ["Monday", "Wednesday", "Friday"])}
        - Workout duration: {getattr(self.profile, "workout_duration_minutes", 45)}
        - Number of exercises per day: {num_exercises}
        - Preferences:
         + Available equipment: {getattr(self.preferences, "available_equipment", ["dumbbells", "resistance bands"])}
         + Target muscle groups: {getattr(self.preferences, "target_muscle_groups", [])}
         + Exercise types: {getattr(self.preferences, "exercise_types", ["strength", "cardio"])}

        Format the response as a valid JSON array where each element is an object with the following keys:
        - "workout_exercises": a list of exercise objects, each with "name","sets","reps","rest_seconds", "body_part", "target", "secondary_muscles", "equipment", "instructions". The "instructions" should be a list of step-by-step strings. The "secondary_muscles" should be a list of strings. The "equipment" should specify the required equipments in concatenated string format.
        - "duration_minutes": an integer for the recommended workout duration in minutes.
        - "focus": a string representing the workout focus, e.g., "Upper Body", "Lower Body", "Push", "Pull", "Legs".
        - "date": the day of the week for this workout.
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name, contents=prompt
            )
        except Exception as e:
            print(
                f"Error generating AI response for workout schedule recommendations. {e}"
            )
            return []

        try:
            # Clean up potential markdown formatting from the response
            if response.text is None:
                return []
            cleaned_response = (
                response.text.strip().lstrip("```json").rstrip("```").strip()
            )
            return json.loads(cleaned_response)
        except (json.JSONDecodeError, AttributeError):
            return []

    async def get_spotify_playlist_recommendations(
        self, workout: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """_summary_
        Create spotify playlist recommendations based on user's preferences and current workout

        Args:
            workout (Optional[Dict[str, Any]], optional): _description_. Defaults to None.

        Returns:
            Dict[str, Any]: _description_
        """
        # Fetch user's Spotify data
        # This assumes you have the user's Spotify access token stored and refreshed
        if getattr(self.preferences, "spotify_data", None) is None:
            return {
                "message": "Spotify data is not available. Please connect your Spotify account and try again.",
                "playlist_recommendations": [],
                "playlist_url": None,
                "playlist_id": None,
                "playlist_name": None,
            }
        try:
            # Example: Get user's top tracks
            top_tracks = await self.spotify_service.get_current_user_top_tracks()
            # I want to check the results
            top_track_names = [track["name"] for track in top_tracks["items"]]
            # Example: Get user's top artists
            top_artists = await self.spotify_service.get_current_user_top_artists()
            top_artist_names = [artist["name"] for artist in top_artists["items"]]

        except (json.JSONDecodeError, AttributeError):
            # Catch 401 error here
            return {
                "message": "Error fetching Spotify data. Please ensure your Spotify account is connected and try again.",
                "playlist_recommendations": [],
                "playlist_url": None,
                "playlist_id": None,
                "playlist_name": None,
            }

        prompt = f"""
        You are a music curator. Your goal is to recommend a Spotify playlist based on the user's preferences and current workout exercise.
        Here's the user's information:
        - Preferred Genres: {", ".join(getattr(self.preferences, "music_genres", [])) if getattr(self.preferences, "music_genres", []) else "None"}
        - User's Top Tracks: {", ".join(top_track_names[:10]) if top_track_names else "None"}
        - User's Top Artists: {", ".join(top_artist_names[:10]) if top_artist_names else "None"}
        - Current Workout Exercises : {", ".join([ex.get("name", "") for ex in workout.get("workout_exercises", [])]) if workout and workout.get("workout_exercises") else "None"}
        - Focus : {workout.get("focus") if workout else "general fitness"}

        Please suggest the number of songs for a Spotify playlist to make sure it lasts exactly the duration of {getattr(self.profile, "workout_duration_minutes", 45)} minutes. 
        Provide the output in a structured JSON format with no additional text.
        - The JSON should have a 'playlist_recommendations' key, which is a list of dicts. Each dict should have:
            + 'song_title': (string)
            + 'artist_name': (string)
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name, contents=prompt
            )

            if response.text is None:
                return {
                    "message": "Error generating playlist recommendations. Please try again.",
                    "playlist_recommendations": [],
                    "playlist_url": None,
                }

            response_text = (
                response.text.strip().lstrip("```json").rstrip("```").strip()
            )
            playlist_recommendations_json = json.loads(response_text)

            user_spotify_profile = await self.spotify_service.get_user_profile()

            # Now, use your SpotifyClient to search for these tracks and potentially create a playlist
            recommended_tracks_uris: List[str] = []
            for rec in playlist_recommendations_json["playlist_recommendations"]:
                search_query = f"track:{rec['song_title']} artist:{rec['artist_name']}"
                search_results = await self.spotify_service.search_tracks(
                    search_query=search_query
                )
                if search_results and search_results["tracks"]["items"]:
                    recommended_tracks_uris.append(
                        search_results["tracks"]["items"][0]["uri"]
                    )

            if recommended_tracks_uris:
                # Create a new playlist
                fitness_goal_val = getattr(self.profile, "fitness_goal", None)
                fitness_goal_str = getattr(fitness_goal_val, "value", None) or (
                    str(fitness_goal_val)
                    if fitness_goal_val is not None
                    else "general_fitness"
                )
                fitness_level_val = getattr(self.profile, "fitness_level", None)
                fitness_level_str = getattr(fitness_level_val, "value", None) or (
                    str(fitness_level_val)
                    if fitness_level_val is not None
                    else "beginner"
                )
                playlist_name = f"SyncNSweat - {self.profile.name} - {fitness_goal_str} - {fitness_level_str} - {datetime.now().strftime('%Y-%m-%d')} Playlist"
                new_playlist = await self.spotify_service.create_playlist(
                    user_spotify_profile.get("id", ""),
                    playlist_name,
                    public=False,
                )
                if new_playlist:
                    await self.spotify_service.add_tracks_to_playlist(
                        new_playlist["id"], recommended_tracks_uris
                    )
                    return {
                        "message": "Playlist created and tracks added!",
                        "playlist_url": new_playlist["external_urls"]["spotify"],
                        "playlist_id": new_playlist["id"],
                        "playlist_name": new_playlist["name"],
                    }
                else:
                    return {"message": "Could not create Spotify playlist."}
            else:
                return {"message": "No tracks found for the recommendations."}

        except Exception as e:
            print(f"Error processing playlist recommendations: {e}")
            return {
                "message": "Error processing playlist recommendations. Please try again.",
                "playlist_recommendations": [],
                "playlist_url": None,
            }

    async def get_spotify_playlist_schedule_recommendations(
        self, workouts: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """_summary_

        Generate Spotify playlist recommendations for a set of scheduled workouts.

        This method uses the user's stored Spotify preferences (such as top tracks,
        top artists, and preferred genres) together with the provided scheduled
        workouts to ask the Gemini model for suitable playlist suggestions.

        Args:
            workouts: Optional list of dictionaries describing scheduled workouts
                for which playlist recommendations should be generated. Each
                dictionary is expected to contain basic metadata about a workout
                (for example, name, type, duration, or intensity) that can be
                included in the model prompt. If None, the method will rely only
                on the user's Spotify data and any default workout context.

        Returns:
            List[Dict[str, Any]]: A list of playlist recommendation objects. Each
                item typically corresponds to one scheduled workout and includes
                model-generated metadata describing the workout context and one or
                more recommended Spotify playlists or tracks suitable for that
                workout. An empty list is returned if Spotify data is unavailable
                or an error occurs while fetching the user's Spotify information.
        """

        if getattr(self.preferences, "spotify_data", None) is None:
            print(
                "Spotify data is not available. Please connect your Spotify account and try again."
            )
            return []
        try:
            # Example: Get user's top tracks
            top_tracks = await self.spotify_service.get_current_user_top_tracks()
            # I want to check the results
            top_track_names = [track["name"] for track in top_tracks["items"]]

            # Example: Get user's top artists
            top_artists = await self.spotify_service.get_current_user_top_artists()
            top_artist_names = [artist["name"] for artist in top_artists["items"]]

        except (json.JSONDecodeError, AttributeError):
            # Catch 401 error here
            print(
                "Error fetching Spotify data. Please ensure your Spotify account is connected and try again."
            )
            return []

        prompt = f"""
        You are a music curator. Your goal is to recommend a list of Spotify playlist based on the user's preferences and current workout exercise.
        Here's the user's information:
        - Preferred Genres: {", ".join(getattr(self.preferences, "music_genres", [])) if getattr(self.preferences, "music_genres", []) else "None"}
        - User's Top Tracks: {", ".join(top_track_names[:10]) if top_track_names else "None"}
        - User's Top Artists: {", ".join(top_artist_names[:10]) if top_artist_names else "None"}
        - Focus : {", ".join([workout.get("focus", "general fitness") for workout in workouts]) if workouts else "general fitness"}
        
        
        Each playlist has to last within a duration of {getattr(self.profile, "workout_duration_minutes", 45)} minutes.
        
                Return ONLY valid JSON (no markdown, comments, or surrounding text). The top-level value must be a JSON array where each element is an object representing one playlist:
                - Each playlist object must contain a single key, "playlist_recommendations", whose value is a list of song objects.
                - Each song object must contain exactly two string fields: "song_title" and "artist_name".
                - Ensure each playlist in the array lasts approximately {getattr(self.profile, "workout_duration_minutes", 45)} minutes by choosing an appropriate number of songs.
                - Do NOT include explanations, headings, code fences (```) or extraneous keys. Follow this exact shape and the example below.
                Example output (strict JSON):
                [
                    {{
                        "playlist_recommendations": [
                            {{"song_title": "Song A", "artist_name": "Artist A"}},
                            {{"song_title": "Song B", "artist_name": "Artist B"}}
                        ]
                    }},
                    {{
                        "playlist_recommendations": [
                            {{"song_title": "Song C", "artist_name": "Artist C"}}
                        ]
                    }}
                ]
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name, contents=prompt
            )

            if response.text is None:
                print("Error generating playlist recommendations. Please try again.")
                return []

            response_text = (
                response.text.strip().lstrip("```json").rstrip("```").strip()
            )
            playlists_recommendations_json = json.loads(response_text)

            user_spotify_profile = await self.spotify_service.get_user_profile()

            # Now, use your SpotifyClient to search for these tracks and potentially create a playlist
            result: List[Dict[str, Any]] = []
            for playlist_recommendations_json in playlists_recommendations_json:
                recommended_tracks_uris: List[str] = []
                for rec in playlist_recommendations_json["playlist_recommendations"]:
                    search_query = (
                        f"track:{rec['song_title']} artist:{rec['artist_name']}"
                    )
                    search_results = await self.spotify_service.search_tracks(
                        search_query=search_query
                    )
                    if search_results and search_results["tracks"]["items"]:
                        recommended_tracks_uris.append(
                            search_results["tracks"]["items"][0]["uri"]
                        )

                if recommended_tracks_uris:
                    # Create a new playlist
                    fitness_goal_val = getattr(self.profile, "fitness_goal", None)
                    fitness_goal_str = getattr(fitness_goal_val, "value", None) or (
                        str(fitness_goal_val)
                        if fitness_goal_val is not None
                        else "general_fitness"
                    )
                    fitness_level_val = getattr(self.profile, "fitness_level", None)
                    fitness_level_str = getattr(fitness_level_val, "value", None) or (
                        str(fitness_level_val)
                        if fitness_level_val is not None
                        else "beginner"
                    )
                    playlist_name = f"SyncNSweat - {self.profile.name} - {fitness_goal_str} - {fitness_level_str} - {datetime.now().strftime('%Y-%m-%d')} Playlist"
                    new_playlist = await self.spotify_service.create_playlist(
                        user_spotify_profile.get("id", ""),
                        playlist_name,
                        public=False,
                    )
                    if new_playlist:
                        await self.spotify_service.add_tracks_to_playlist(
                            new_playlist["id"], recommended_tracks_uris
                        )
                        result.append(
                            {
                                "playlist_url": new_playlist["external_urls"][
                                    "spotify"
                                ],
                                "playlist_id": new_playlist["id"],
                                "playlist_name": new_playlist["name"],
                            }
                        )

                    else:
                        print("Could not create Spotify playlist.")
                        return []
                else:
                    print("No tracks found for the recommendations.")
                    return []
            return result
        except Exception as e:
            print(f"Error processing playlist recommendations: {e}")
            return []

    async def _retry_call(
        self, coro_func: Callable[..., Any], *coro_args: Any, retries: int = 2
    ) -> Any:
        """Utility to retry an async coroutine function a small number of times."""
        last: Optional[Any] = None
        for _ in range(retries):
            try:
                return await coro_func(*coro_args)
            except Exception:
                last = None
        return last

    def _normalize_exercise(self, ex: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize a single exercise entry from the LLM into a predictable dict or return None."""

        # Extract name from various possible keys
        name = ex.get("name") or ex.get("exercise") or ex.get("title")  # type: ignore
        if not name:
            return None

        body_part = ex.get("body_part")  # type: ignore
        target = ex.get("target")  # type: ignore
        equipment = ex.get("equipment")  # type: ignore
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
            "instructions": instructions,
            "sets": int(sets)
            if isinstance(sets, (int, float, str)) and str(sets).isdigit()
            else 3,
            "reps": str(reps) if reps else "10",
            "rest_seconds": int(rest_seconds)
            if isinstance(rest_seconds, (int, float, str))
            and str(rest_seconds).isdigit()
            else 60,
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

    def _normalize_workout(
        self, raw_plan: Any, user_profile: Profile
    ) -> Dict[str, Any]:
        """Normalize a raw LLM workout plan into a predictable dict shape."""
        fallback: Dict[str, Any] = {
            "workout_exercises": [],
            "duration_minutes": getattr(user_profile, "workout_duration_minutes", 45)
            or 45,
            "focus": None,
            "date": None,
        }
        if not isinstance(raw_plan, dict):
            return fallback

        exercises_raw = raw_plan.get("workout_exercises") or []  # type: ignore
        normalized: List[Dict[str, Any]] = []
        if isinstance(exercises_raw, list):
            for ex in exercises_raw:
                norm = self._normalize_exercise(ex)
                if norm:
                    normalized.append(norm)

        duration_val = (
            raw_plan.get("duration_minutes")
            or getattr(user_profile, "workout_duration_minutes", 45)
            or 45
        )  # type: ignore
        date_val = raw_plan.get("date") or None  # type: ignore
        focus_val = raw_plan.get("focus") or None  # type: ignore

        out: Dict[str, Any] = {
            "workout_exercises": normalized,
            "duration_minutes": int(duration_val) if duration_val else 45,  # type: ignore
            "date": date_val,
            "focus": focus_val,
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
        raw_plan = await self.get_workout_recommendations()
        workout_plan = self._normalize_workout(raw_plan, self.profile)

        # Get or create Spotify playlist based on profile/preferences, with retry.
        #
        playlist_result: Dict[
            str, Any
        ] = await self.get_spotify_playlist_recommendations(workout=workout_plan)
        if not playlist_result:
            playlist_result = {
                "message": "Unable to generate playlist from LLM/Spotify.",
                "playlist_recommendations": [],
                "playlist_url": None,
                "playlist_id": None,
                "playlist_name": None,
            }

        return {"workout_plan": workout_plan, "playlist": playlist_result}

    async def get_workout_and_playlist_schedule(self) -> Dict[str, Any]:
        """
        Convenience method that returns both an AI workout plan and a Spotify playlist
        recommendation/create result for scheduled workouts. Return a list of dicts with keys "workout_plan" and
        "playlist". Any errors from either step are included in the corresponding
        value as a message.
        """
        # Use class helpers to call LLM and normalize results
        raw_plans = await self.get_workout_schedule_recommendations()
        workout_plans: List[Dict[str, Any]] = []
        for raw_plan in raw_plans:
            workout_plan = self._normalize_workout(raw_plan, self.profile)
            workout_plans.append(workout_plan)

        # Get or create Spotify playlist based on profile/preferences, with retry.
        #
        playlist_result: List[
            Dict[str, Any]
        ] = await self.get_spotify_playlist_schedule_recommendations(
            workouts=workout_plans
        )

        # Merge workout plans with their corresponding playlists
        for i in range(min(len(workout_plans), len(playlist_result))):
            workout_plans[i]["playlist"] = playlist_result[i]
        return {"workout_plans": workout_plans}

    async def get_exercise_swap(
        self,
        current_exercise: Exercise,
        target_muscle_groups: List[str],
        fitness_level: str,
        available_equipment: List[str],
        recently_used_exercise_names: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Generate an alternative exercise targeting the same muscle group.
        """
        prompt = f"""
        Suggest an alternative exercise to '{current_exercise.name}' that targets the '{",".join(target_muscle_groups) if target_muscle_groups else "general"}' muscle group. The alternative exercise should match the user's fitness level '{fitness_level}' and utilize the available equipment: {", ".join(available_equipment) if available_equipment else "bodyweight only"}. Avoid suggesting exercises that the user has recently performed: {", ".join(recently_used_exercise_names) if recently_used_exercise_names else "none"}.
        Provide the response in JSON format with the following keys:
        - "name": Name of the alternative exercise
        - "body_part": Primary body part targeted
        - "target": Target muscle group
        - "equipment": Equipment needed
        - "instructions": List of step-by-step instructions
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name, contents=prompt
            )
        except Exception as e:
            print(f"Error generating AI response for exercise swap: {e}")
            return None

        try:
            if response.text is None:
                return None
            cleaned_response = (
                response.text.strip().lstrip("```json").rstrip("```").strip()
            )
            exercise_data = json.loads(cleaned_response)
            normalized_exercise = self._normalize_exercise(exercise_data)
            return normalized_exercise
        except (json.JSONDecodeError, AttributeError):
            return None
