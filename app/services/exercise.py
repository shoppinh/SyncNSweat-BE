from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.workout import Exercise, Workout
from app.repositories.exercise import ExerciseRepository
from app.repositories.workout import WorkoutRepository


class ExerciseService:
    def __init__(self, db: Session):
        self.api_key = settings.EXERCISE_API_KEY
        self.api_host = settings.EXERCISE_API_HOST
        self.exercise_repo = ExerciseRepository(db)
        self.workout_repo = WorkoutRepository(db)

    # Start of external source methods
    def get_exercises_from_external_source(
        self, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get a list of exercises.
        """
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.api_host}

        response = requests.get(
            f"https://{self.api_host}/exercises", headers=headers, params=params
        )
        return response.json()

    def get_exercise_by_id_from_external_source(
        self, exercise_id: str
    ) -> Dict[str, Any]:
        """
        Get an exercise by ID.
        """
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.api_host}

        response = requests.get(
            f"https://{self.api_host}/exercises/exercise/{exercise_id}", headers=headers
        )
        return response.json()

    def get_exercises_by_muscle_from_external_source(
        self, muscle: str
    ) -> List[Dict[str, Any]]:
        """
        Get exercises by target muscle.
        Accepted params: ["abductors","abs","adductors","biceps","calves","cardiovascular system","delts","forearms","glutes","hamstrings","lats","levator scapulae","pectorals","quads","serratus anterior","spine","traps","triceps","upper back"]
        """
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.api_host}

        response = requests.get(
            f"https://{self.api_host}/exercises/target/{muscle}", headers=headers
        )
        return response.json()

    def get_exercises_by_equipment_from_external_source(
        self, equipment: str
    ) -> List[Dict[str, Any]]:
        """
        Get exercises by equipment.
        """
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.api_host}

        response = requests.get(
            f"https://{self.api_host}/exercises/equipment/{equipment}", headers=headers
        )
        return response.json()

    def get_exercise_by_name_external_source(self, name: str) -> List[Dict[str, Any]]:
        """
        Get exercises by name.
        """
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.api_host}

        response = requests.get(
            f"https://{self.api_host}/exercises/name/{name}", headers=headers
        )
        return response.json()

    # End of external source methods

    # Start of internal methods
    def get_exercises(self) -> List[Exercise]:
        """
        Get a list of exercises.
        """
        return self.exercise_repo.get_all()

    def get_exercise_by_id(self, exercise_id: int) -> Optional[Exercise]:
        """
        Get an exercise by ID.
        """
        return self.exercise_repo.get_by_id(exercise_id)

    def get_exercises_by_target(self, target: str) -> List[Exercise]:
        """
        Get exercises by target muscle.
        """
        return self.exercise_repo.get_by_target(target)

    def get_exercises_by_equipment(self, equipment: str) -> List[Exercise]:
        """
        Get exercises by equipment.
        """
        return self.exercise_repo.get_by_equipment(equipment)

        
    def get_recent_workouts_for_user(self, user_id: int, limit: int = 5) -> list[Workout]:
        """
        Get recent workouts for a user.
        """
        return self.workout_repo.get_all_with_exercises(user_id=user_id, limit=limit, skip=0)

    def get_seed_exercises(self, current_user: User) -> list[Exercise]:
        """
        Get a list of seed exercises based on user's workout history.
        """
        # Placeholder logic: In a real implementation, this would analyze the user's workout history.
        recent_workouts = self.get_recent_workouts_for_user(user_id=getattr(current_user, "id"), limit=30)
        seed_exercises: list[Exercise] = []
        for workout in recent_workouts:
            seed_exercises.extend(we.exercise for we in workout.workout_exercises)
        return seed_exercises

    # End of internal methods