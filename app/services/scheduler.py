from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.services.exercise import ExerciseService
from sqlalchemy.orm import Session

class SchedulerService:
    """
    Service for generating workout schedules based on user preferences.
    """
    
    def __init__(self, db: Session):
        self.exercise_service = ExerciseService(db)
    
    def generate_weekly_schedule(
        self,
        user_id: int,
        available_days: List[str],
        fitness_goal: str,
        fitness_level: str,
        available_equipment: List[str],
        workout_duration_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Generate a weekly workout schedule based on user preferences.
        
        Args:
            user_id: The user ID
            available_days: List of days the user is available to workout (e.g., ["Monday", "Wednesday", "Friday"])
            fitness_goal: The user's fitness goal (e.g., "strength", "weight_loss", "muscle_gain")
            fitness_level: The user's fitness level (e.g., "beginner", "intermediate", "advanced")
            available_equipment: List of equipment the user has access to
            target_muscle_groups: List of muscle groups the user wants to focus on
            workout_duration_minutes: The user's preferred workout duration in minutes
            
        Returns:
            A list of workout dictionaries with date, focus, and duration
        """
        # Map days to datetime objects for the current week
        today = datetime.now().date()
        day_of_week = today.weekday() 
        
        # Get the date of the most recent Monday
        monday = today - timedelta(days=day_of_week)
        
        day_map = {
            "Monday": monday,
            "Tuesday": monday + timedelta(days=1),
            "Wednesday": monday + timedelta(days=2),
            "Thursday": monday + timedelta(days=3),
            "Friday": monday + timedelta(days=4),
            "Saturday": monday + timedelta(days=5),
            "Sunday": monday + timedelta(days=6)
        }
        
        # If some dates are in the past, move to next week
        for day, date in day_map.items():
            if date < today:
                day_map[day] = date + timedelta(days=7)
        
        # Determine workout split based on available days and fitness goal
        workout_split = self._determine_workout_split(available_days, fitness_goal)
        
        # Generate workouts for each available day
        workouts: list[Dict[str, Any]] = []
        for i, day in enumerate(available_days):
            focus = workout_split[i % len(workout_split)]
            workout_date = day_map[day]
            
            # Create workout
            workout: Dict[str, Any] = {
                "user_id": user_id,
                "date": datetime.combine(workout_date, datetime.min.time()),
                "focus": focus,
                "duration_minutes": workout_duration_minutes,
                "completed": False
            }
            
            # Generate exercises for this workout
            muscle_groups = self._get_muscle_groups_for_focus(focus)
            exercises = self.exercise_service.generate_workout(
                muscle_groups=muscle_groups,
                available_equipment=available_equipment,
                fitness_level=fitness_level,
                workout_duration_minutes=workout_duration_minutes
            )
            
            workout["exercises"] = exercises
            workouts.append(workout)
        
        return workouts
    
    def _determine_workout_split(self, available_days: List[str], fitness_goal: str) -> List[str]:
        """
        Determine the workout split based on available days and fitness goal.
        
        Args:
            available_days: List of days the user is available to workout
            fitness_goal: The user's fitness goal
            
        Returns:
            A list of workout focuses (e.g., ["Upper Body", "Lower Body"])
        """
        num_days = len(available_days)
        
        if num_days <= 2:
            # For 1-2 days, do full body workouts
            return ["Full Body"]
        elif num_days == 3:
            # For 3 days, do push/pull/legs or upper/lower/full
            if fitness_goal == "muscle_gain":
                return ["Push", "Pull", "Legs"]
            else:
                return ["Upper Body", "Lower Body", "Full Body"]
        elif num_days == 4:
            # For 4 days, do upper/lower split twice
            return ["Upper Body", "Lower Body", "Upper Body", "Lower Body"]
        else:
            # For 5+ days, do a body part split
            return ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core"]
    
    def _get_muscle_groups_for_focus(self, focus: str) -> List[str]:
        """
        Get the muscle groups for a given workout focus.
        
        Args:
            focus: The workout focus (e.g., "Upper Body", "Push")
            
        Returns:
            A list of muscle groups
        """
        focus_map = {
            "Full Body": ["chest", "back", "quads", "hamstrings", "shoulders", "biceps", "triceps", "abs"],
            "Upper Body": ["chest", "back", "shoulders", "biceps", "triceps"],
            "Lower Body": ["quads", "hamstrings", "glutes", "calves"],
            "Push": ["chest", "shoulders", "triceps"],
            "Pull": ["back", "biceps", "forearms"],
            "Legs": ["quads", "hamstrings", "glutes", "calves"],
            "Chest": ["chest", "triceps"],
            "Back": ["back", "biceps"],
            "Shoulders": ["shoulders", "traps"],
            "Arms": ["biceps", "triceps", "forearms"],
            "Core": ["abs", "lower_back"]
        }
        
        return focus_map.get(focus, ["chest", "back", "quads"])  # Default to some major muscle groups
