"""
Exercise repository for database operations.
"""
from typing import Any, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.workout import Exercise, Workout, WorkoutExercise
from app.repositories.base import BaseRepository


class ExerciseRepository(BaseRepository[Exercise]):
    """
    Repository for Exercise model operations.
    """

    def __init__(self, db: Session):
        super().__init__(Exercise, db)

    def search_by_name(self, search: str, skip: int = 0, limit: int = 100) -> List[Exercise]:
        """
        Search exercises by name (case-insensitive partial match).
        
        Args:
            search: Search term
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Exercise instances matching the search term
        """
        return (
            self.db.query(Exercise)
            .filter(Exercise.name.ilike(f"%{search}%"))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_body_part(self, body_part: str, skip: int = 0, limit: int = 100) -> List[Exercise]:
        """
        Get exercises by body part.
        
        Args:
            body_part: Body part to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Exercise instances
        """
        return self.filter_by(body_part=body_part, skip=skip, limit=limit)

    def get_by_equipment(self, equipment: str, skip: int = 0, limit: int = 100) -> List[Exercise]:
        """
        Get exercises by equipment.
        
        Args:
            equipment: Equipment to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Exercise instances
        """
        return self.filter_by(equipment=equipment, skip=skip, limit=limit)

    def get_by_target(self, target: str, skip: int = 0, limit: int = 100) -> List[Exercise]:
        """
        Get exercises by target muscle.
        
        Args:
            target: Target muscle to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Exercise instances
        """
        return self.filter_by(target=target, skip=skip, limit=limit)

    def get_by_name_exact(self, name: str) -> Optional[Exercise]:
        """
        Get exercise by exact name match (case-insensitive).
        
        Args:
            name: Exercise name
            
        Returns:
            Exercise instance or None if not found
        """
        return (
            self.db.query(Exercise)
            .filter(func.lower(Exercise.name) == func.lower(name))
            .first()
        )

    def bulk_insert(self, exercises: List[dict[str, Any]]) -> None:
        """
        Bulk insert exercises.
        
        Args:
            exercises: List of exercise dictionaries
        """
        self.db.bulk_insert_mappings(Exercise.__mapper__, exercises)
        self.db.flush()
        
    def delete_all(self) -> None:
        """
        Delete all exercises from the database.
        """
        self.db.query(Exercise).delete()
        self.db.flush()

    def get_all_names(self) -> List[tuple[int, str]]:
        """
        Return a list of (id, name) tuples for all exercises. Lightweight helper
        intended for building fuzzy-match candidate lists without loading full rows.
        """
        rows = self.db.query(Exercise.id, Exercise.name).all()
        return [(r[0], r[1]) for r in rows]

    def get_seed_exercises_for_user(
        self,
        user_id: int,
        personal_limit: int = 30,
        global_limit: int = 30,
        top_k: int = 20,
        available_equipment: Optional[List[str]] = None,
        target_muscle_groups: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Build a weighted seed list of exercise names for the given user.

        Strategy:
        - Query the user's recent/frequent exercises (by count, then recency).
        - Query globally popular exercises as fallback.
        - Merge, de-duplicate, and apply simple weighting by repeating top personal items.

        Returns a list of exercise names (strings). Names may be repeated to indicate higher weight.
        """
        # Build base personal query: count usages per exercise for this user
        personal_q = (
            self.db.query(Exercise.id, Exercise.name)
            .join(WorkoutExercise, WorkoutExercise.exercise_id == Exercise.id)
            .join(Workout, Workout.id == WorkoutExercise.workout_id)
            .filter(Workout.user_id == user_id)
            .group_by(Exercise.id, Exercise.name)
            .order_by(func.count().desc())
            .limit(personal_limit)
        )

        # Apply optional filters (equipment/target) to narrow candidates
        if available_equipment:
            eqs = [e.lower() for e in available_equipment if e]
            personal_q = personal_q.filter(
                (Exercise.equipment == None) | (func.lower(Exercise.equipment).in_(eqs))
            )
        if target_muscle_groups:
            targets = [t.lower() for t in target_muscle_groups if t]
            personal_q = personal_q.filter(func.lower(Exercise.target).in_(targets))

        personal_rows = personal_q.all()
        personal_names = [r[1] for r in personal_rows]

        # Global popular exercises
        global_q = (
            self.db.query(Exercise.id, Exercise.name, func.count().label("usage_count"))
            .join(WorkoutExercise, WorkoutExercise.exercise_id == Exercise.id)
            .join(Workout, Workout.id == WorkoutExercise.workout_id)
            .group_by(Exercise.id, Exercise.name)
            .order_by(func.count().desc())
            .limit(global_limit)
        )
        if available_equipment:
            eqs = [e.lower() for e in available_equipment if e]
            global_q = global_q.filter(
                (Exercise.equipment == None) | (func.lower(Exercise.equipment).in_(eqs))
            )
        if target_muscle_groups:
            targets = [t.lower() for t in target_muscle_groups if t]
            global_q = global_q.filter(func.lower(Exercise.target).in_(targets))

        global_rows = global_q.all()
        global_names = [r[1] for r in global_rows if r[1] not in personal_names]

        # Merge with weighting: repeat top personal items more times to bias the seed
        weighted: List[str] = []
        for i, name in enumerate(personal_names):
            if i < 5:
                repeats = 3
            elif i < 15:
                repeats = 2
            else:
                repeats = 1
            weighted.extend([name] * repeats)

        # Add some global names with lower weight
        for i, name in enumerate(global_names):
            if len(weighted) >= top_k * 3:
                break
            weighted.append(name)

        # Produce final seed list trimmed to top_k (preserving weight ordering)
        final: List[str] = []
        for name in weighted:
            if len(final) >= top_k:
                break
            final.append(name)

        # If still empty, fallback to a simple top global list
        if not final and global_names:
            final = global_names[: min(top_k, len(global_names))]

        return final