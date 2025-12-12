import requests
from typing import Dict, List, Optional, Any
from app.core.config import settings
from sqlalchemy.orm import Session

from app.models.workout import Exercise

class ExerciseService:
    def __init__(self, db: Session):
        self.api_key = settings.EXERCISE_API_KEY
        self.api_host = settings.EXERCISE_API_HOST
        self.api_url = "https://exercisedb.p.rapidapi.com"
        self.db = db
    
    def get_exercises_from_external_source(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get a list of exercises.
        """
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        
        response = requests.get(f"{self.api_url}/exercises", headers=headers, params=params)
        return response.json()
    
    def get_exercise_by_id_from_external_source(self, exercise_id: str) -> Dict[str, Any]:
        """
        Get an exercise by ID.
        """
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        
        response = requests.get(f"{self.api_url}/exercises/exercise/{exercise_id}", headers=headers)
        return response.json()
    
    def get_exercises_by_muscle_from_external_source(self, muscle: str) -> List[Dict[str, Any]]:
        """
        Get exercises by target muscle.
        Accepted params: ["abductors","abs","adductors","biceps","calves","cardiovascular system","delts","forearms","glutes","hamstrings","lats","levator scapulae","pectorals","quads","serratus anterior","spine","traps","triceps","upper back"]
        """
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        
        response = requests.get(f"{self.api_url}/exercises/target/{muscle}", headers=headers)
        return response.json()
    
    def get_exercises_by_equipment_from_external_source(self, equipment: str) -> List[Dict[str, Any]]:
        """
        Get exercises by equipment.
        """
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        
        response = requests.get(f"{self.api_url}/exercises/equipment/{equipment}", headers=headers)
        return response.json()
    
    def get_exercise_by_name_external_source(self, name: str) -> List[Dict[str, Any]]:
        """
        Get exercises by name.
        """
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
        
        response = requests.get(f"{self.api_url}/exercises/name/{name}", headers=headers)
        return response.json()
    
    # End of external source methods
    
    # Start of internal methods
    def get_exercises(self, params: Optional[Dict[str, Any]] = None) -> List[Exercise]:
        """
        Get a list of exercises.
        """
        return self.db.query(Exercise).all()
    
    def get_exercise_by_id(self, exercise_id: int) -> Optional[Exercise]:
        """
        Get an exercise by ID.
        """
        return self.db.query(Exercise).filter(Exercise.id == exercise_id).first()
    
    def get_exercises_by_muscle(self, muscle: str) -> List[Exercise]:
        """
        Get exercises by target muscle.
        """
        return self.db.query(Exercise).filter(Exercise.target == muscle).all()
    
    def get_exercises_by_equipment(self, equipment: str) -> List[Exercise]:
        """
        Get exercises by equipment.
        """
        return self.db.query(Exercise).filter(Exercise.equipment == equipment).all()
    
    def generate_workout(
        self,
        muscle_groups: List[str],
        available_equipment: List[str],
        fitness_level: str,
        workout_duration_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Generate a workout based on user preferences.
        """
        # This is a placeholder for the actual workout generation logic
        # In a real implementation, we would:
        # 1. Get exercises for the specified muscle groups and equipment
        # 2. Filter by fitness level
        # 3. Select a suitable number of exercises based on workout duration
        # 4. Assign sets, reps, and rest periods based on fitness level and goals
        
        # For now, we'll just return a mock workout
        exercises: List[Dict[str, Any]] = []
        
        # Get some exercises for each muscle group
        for muscle in muscle_groups:
            try:
                muscle_exercises = self.get_exercises_by_muscle_from_external_source(muscle)
                # Filter by available equipment
                filtered_exercises = [
                    ex for ex in muscle_exercises
                    if not ex.get("equipment") or ex.get("equipment") in available_equipment
                ]
                # Take up to 2 exercises per muscle group
                exercises.extend(filtered_exercises[:2])
            except Exception:
                # If API call fails, continue with other muscle groups
                continue
        
        # Limit the total number of exercises based on workout duration
        # Assuming each exercise takes about 10 minutes (including rest)
        max_exercises = max(1, workout_duration_minutes // 10)
        exercises = exercises[:max_exercises]
        
        # Add workout-specific details
        workout_exercises: List[Dict[str, Any]] = []
        for i, ex in enumerate(exercises):
            # Determine sets and reps based on fitness level
            if fitness_level == "beginner":
                sets = 3
                reps = "8-10"
                rest_seconds = 60
            elif fitness_level == "intermediate":
                sets = 4
                reps = "10-12"
                rest_seconds = 45
            else:  # advanced
                sets = 5
                reps = "12-15"
                rest_seconds = 30
            
            workout_exercises.append({
                "exercise_id": ex.get("id"),
                "name": ex.get("name"),
                "description": ex.get("instructions", []),
                "muscle_group": ex.get("target"),
                "equipment": ex.get("equipment"),
                "sets": sets,
                "reps": reps,
                "rest_seconds": rest_seconds,
                "order": i + 1
            })
        
        return workout_exercises
