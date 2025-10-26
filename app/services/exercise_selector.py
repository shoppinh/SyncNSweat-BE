import random
from typing import List, Dict, Any, Optional

from app.models.workout import Exercise
from app.schemas.exercise import WorkoutExerciseResponse
from app.services.exercise import ExerciseService
from app.utils.helper import safe_int_convert
from sqlalchemy.orm import Session

class ExerciseSelectorService:
    """
    Service for selecting exercises for a workout based on focus, user level, and equipment.
    Ensures variety by tracking recently used exercises.
    """
    
    def __init__(self, db: Session):
        self.exercise_service = ExerciseService(db)
    
    def select_exercises_for_workout(
        self,
        focus: str,
        fitness_level: str,
        available_equipment: List[str],
        workout_duration_minutes: int,
        recently_used_exercises: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Select exercises for a workout based on focus, user level, and equipment.
        
        Args:
            focus: The focus of the workout (e.g., "Upper Body", "Push")
            fitness_level: The user's fitness level (e.g., "beginner", "intermediate", "advanced")
            available_equipment: List of equipment the user has access to
            workout_duration_minutes: The user's preferred workout duration in minutes
            recently_used_exercises: List of recently used exercise IDs to avoid
            
        Returns:
            A list of exercise dictionaries
        """
        if not recently_used_exercises:
            recently_used_exercises = []
        
        # Get muscle groups for he focus
        muscle_groups = self._get_muscle_groups_for_focus(focus)
        
        # Get exercises for each muscle group
        all_exercises: List[Exercise] = []
        for muscle in muscle_groups:
            try:
                muscle_exercises = self.exercise_service.get_exercises_by_muscle(muscle)[:3]
                # Filter by available equipment
                filtered_exercises = [
                    ex for ex in muscle_exercises
                    if ex.equipment in available_equipment
                ]
                # Filter out recently used exercises
                filtered_exercises = [
                    ex for ex in filtered_exercises
                    if ex.id not in recently_used_exercises
                ]
                all_exercises.extend(filtered_exercises)
            except Exception:
                # If API call fails, continue with other muscle groups
                continue
        
        # If we don't have enough exercises after filtering, include some recently used ones
        if len(all_exercises) < 3:
            for muscle in muscle_groups:
                try:
                    muscle_exercises = self.exercise_service.get_exercises_by_muscle(muscle)
                    # Filter by available equipment only
                    filtered_exercises = [
                        ex for ex in muscle_exercises
                        if ex.equipment in available_equipment
                    ]
                    # Add exercises that weren't already added
                    for ex in filtered_exercises:
                        if not any(e.id == ex.id for e in all_exercises):
                            all_exercises.append(ex)
                except Exception:
                    # If API call fails, continue with other muscle groups
                    continue
        
        # Shuffle exercises to ensure variety
        random.shuffle(all_exercises)
        
        # Limit the total number of exercises based on workout duration
        # Assuming each exercise takes about 10 minutes (including rest)
        max_exercises = max(3, workout_duration_minutes // 10)
        selected_exercises = all_exercises[:max_exercises]
        
        # Add workout-specific details
        workout_exercises = []
        for i, ex in enumerate(selected_exercises):
            # Determine sets and reps based on fitness level
            if fitness_level.lower() == "beginner":
                sets = 3
                reps = "8-10"
                rest_seconds = 60
            elif fitness_level.lower() == "intermediate":
                sets = 4
                reps = "10-12"
                rest_seconds = 45
            else:  # advanced
                sets = 5
                reps = "12-15"
                rest_seconds = 30

            exercise_details = {
                "exercise_id": safe_int_convert(ex.id),
                "sets": sets,
                "reps": reps,
                "rest_seconds": rest_seconds,
                "order": i + 1,
            }
            workout_exercises.append(exercise_details)
        
        return workout_exercises
    
    def swap_exercise(
        self,
        exercise_id: int,
        muscle_group: str,
        equipment: str,
        fitness_level: str,
        available_equipment: List[str],
        recently_used_exercises: List[int] = None
    ) -> Dict[str, Any]:
        """
        Swap an exercise with another one that targets the same muscle group.
        
        Args:
            exercise_id: The ID of the exercise to swap
            muscle_group: The muscle group of the exercise
            equipment: The equipment used for the exercise
            fitness_level: The user's fitness level
            available_equipment: List of equipment the user has access to
            recently_used_exercises: List of recently used exercise IDs to avoid
            
        Returns:
            A dictionary with the new exercise details
        """
        if not recently_used_exercises:
            recently_used_exercises = []
        
        # Add the current exercise to recently used
        if exercise_id not in recently_used_exercises:
            recently_used_exercises.append(exercise_id)
        
        # Get exercises for the muscle group
        try:
            muscle_exercises = self.exercise_service.get_exercises_by_muscle(muscle_group)
            
            # Filter by available equipment
            filtered_exercises = [
                ex for ex in muscle_exercises
                if not ex.get("equipment") or ex.get("equipment") in available_equipment
            ]
            
            # Filter out recently used exercises
            filtered_exercises = [
                ex for ex in filtered_exercises
                if ex.get("id") not in recently_used_exercises
            ]
            
            # If we don't have any exercises after filtering, include some recently used ones
            if not filtered_exercises:
                filtered_exercises = [
                    ex for ex in muscle_exercises
                    if not ex.get("equipment") or ex.get("equipment") in available_equipment
                ]
            
            # If we still don't have any exercises, try to get exercises for a similar muscle group
            if not filtered_exercises:
                similar_muscles = self._get_similar_muscle_groups(muscle_group)
                for similar_muscle in similar_muscles:
                    try:
                        similar_exercises = self.exercise_service.get_exercises_by_muscle(similar_muscle)
                        # Filter by available equipment
                        similar_filtered = [
                            ex for ex in similar_exercises
                            if not ex.get("equipment") or ex.get("equipment") in available_equipment
                        ]
                        filtered_exercises.extend(similar_filtered)
                    except Exception:
                        # If API call fails, continue with other muscle groups
                        continue
            
            # If we still don't have any exercises, return a default exercise
            if not filtered_exercises:
                return {
                    "exercise_id": "default",
                    "name": f"Default {muscle_group.capitalize()} Exercise",
                    "description": ["No suitable replacement found. Please try a different exercise."],
                    "muscle_group": muscle_group,
                    "equipment": "bodyweight",
                    "sets": 3,
                    "reps": "10-12",
                    "rest_seconds": 60
                }
            
            # Select a random exercise from the filtered list
            new_exercise = random.choice(filtered_exercises)
            
            # Determine sets and reps based on fitness level
            if fitness_level.lower() == "beginner":
                sets = 3
                reps = "8-10"
                rest_seconds = 60
            elif fitness_level.lower() == "intermediate":
                sets = 4
                reps = "10-12"
                rest_seconds = 45
            else:  # advanced
                sets = 5
                reps = "12-15"
                rest_seconds = 30
            
            return {
                "exercise_id": new_exercise.get("id"),
                "name": new_exercise.get("name"),
                "description": new_exercise.get("instructions", []),
                "muscle_group": new_exercise.get("target"),
                "equipment": new_exercise.get("equipment"),
                "sets": sets,
                "reps": reps,
                "rest_seconds": rest_seconds
            }
            
        except Exception:
            # If API call fails, return a default exercise
            return {
                "exercise_id": "default",
                "name": f"Default {muscle_group.capitalize()} Exercise",
                "description": ["API error. Please try again later."],
                "muscle_group": muscle_group,
                "equipment": "bodyweight",
                "sets": 3,
                "reps": "10-12",
                "rest_seconds": 60
            }
    
    def _get_muscle_groups_for_focus(self, focus: str) -> List[str]:
        """
        Get the muscle groups for a given workout focus.
        
        Args:
            focus: The workout focus (e.g., "Upper Body", "Push")
            
        Returns:
            A list of muscle groups
        """
        
        focus_map = {
            "Full Body": ["abductors", "abs", "adductors", "biceps", "calves", "cardiovascular system", "delts", "forearms", "glutes", "hamstrings", "lats", "levator scapulae", "pectorals", "quads", "serratus anterior", "spine", "traps", "triceps", "upper back"],
            "Upper Body": ["biceps", "delts", "forearms", "lats", "levator scapulae", "pectorals", "serratus anterior", "traps", "triceps", "upper back"],
            "Lower Body": ["abductors", "adductors", "calves", "glutes", "hamstrings", "quads"],
            "Push": ["delts", "pectorals", "serratus anterior", "triceps"],
            "Pull": ["biceps", "forearms", "lats", "upper back"],
            "Legs": ["abductors", "adductors", "calves", "glutes", "hamstrings", "quads"],
            "Chest": ["pectorals", "serratus anterior"],
            "Back": ["lats", "levator scapulae", "upper back"],
            "Shoulders": ["delts", "traps"],
            "Arms": ["biceps", "forearms", "triceps"],
            "Core": ["abs", "spine"]
        }
        
        return focus_map.get(focus, ["pectorals", "serratus anterior"])  # Default to some major muscle groups
    
    def _get_similar_muscle_groups(self, muscle_group: str) -> List[str]:
        """
        Get similar muscle groups for a given muscle group.
        
        Args:
            muscle_group: The muscle group
            
        Returns:
            A list of similar muscle groups
        """
        similarity_map = {
            "chest": ["shoulders", "triceps"],
            "back": ["biceps", "shoulders"],
            "shoulders": ["chest", "triceps"],
            "biceps": ["back", "forearms"],
            "triceps": ["chest", "shoulders"],
            "forearms": ["biceps", "back"],
            "quads": ["hamstrings", "glutes"],
            "hamstrings": ["quads", "glutes"],
            "glutes": ["hamstrings", "quads"],
            "calves": ["quads", "hamstrings"],
            "abs": ["lower_back", "obliques"],
            "lower_back": ["abs", "glutes"],
            "obliques": ["abs", "lower_back"],
            "traps": ["shoulders", "back"]
        }
        
        return similarity_map.get(muscle_group, [])
