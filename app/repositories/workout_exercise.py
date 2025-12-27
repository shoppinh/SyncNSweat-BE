"""
WorkoutExercise repository for database operations.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.workout import WorkoutExercise
from app.repositories.base import BaseRepository


class WorkoutExerciseRepository(BaseRepository[WorkoutExercise]):
    """
    Repository for WorkoutExercise model operations (composite key model).
    """

    def __init__(self, db: Session):
        super().__init__(WorkoutExercise, db)

    def get_by_composite_key(self, workout_id: int, exercise_id: int) -> Optional[WorkoutExercise]:
        """
        Get workout exercise by composite key.
        
        Args:
            workout_id: Workout ID
            exercise_id: Exercise ID
            
        Returns:
            WorkoutExercise instance or None if not found
        """
        return (
            self.db.query(WorkoutExercise)
            .filter(WorkoutExercise.workout_id == workout_id)
            .filter(WorkoutExercise.exercise_id == exercise_id)
            .first()
        )

    def get_by_workout_id(self, workout_id: int) -> List[WorkoutExercise]:
        """
        Get all exercises for a specific workout.
        
        Args:
            workout_id: Workout ID
            
        Returns:
            List of WorkoutExercise instances
        """
        return (
            self.db.query(WorkoutExercise)
            .filter(WorkoutExercise.workout_id == workout_id)
            .all()
        )

    def delete_by_composite_key(self, workout_id: int, exercise_id: int) -> None:
        """
        Delete workout exercise by composite key.
        
        Args:
            workout_id: Workout ID
            exercise_id: Exercise ID
        """
        workout_exercise = self.get_by_composite_key(workout_id, exercise_id)
        if workout_exercise:
            self.delete(workout_exercise)

    def create_with_composite_key(self, workout_id: int, exercise_id: int, **kwargs: Any) -> WorkoutExercise:
        """
        Create a new workout exercise with composite key.
        
        Args:
            workout_id: Workout ID
            exercise_id: Exercise ID
            **kwargs: Additional field values
            
        Returns:
            Created WorkoutExercise instance
        """
        data: Dict[str, Any] = {"workout_id": workout_id, "exercise_id": exercise_id, **kwargs}
        result = self.create(data)
        return result