"""
Workout repository for database operations.
"""
from datetime import date
from typing import List, Optional, Any

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from app.models.workout import Workout, WorkoutExercise
from app.repositories.base import BaseRepository


class WorkoutRepository(BaseRepository[Workout]):
    """
    Repository for Workout model operations.
    """

    def __init__(self, db: Session):
        super().__init__(Workout, db)

    def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Workout]:
        """
        Get workouts for a specific user with pagination.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Workout instances
        """
        return self.filter_by(user_id=user_id, skip=skip, limit=limit)

    def get_by_id_with_exercises(self, workout_id: int, user_id: Optional[int] = None) -> Optional[Workout]:
        """
        Get workout by ID with eager loading of exercises.
        
        Args:
            workout_id: Workout ID
            user_id: Optional user ID to filter by
            
        Returns:
            Workout instance with exercises loaded or None if not found
        """
        query = self.db.query(Workout).options(
            selectinload(Workout.workout_exercises).selectinload(WorkoutExercise.exercise)
        ).filter(Workout.id == workout_id)
        
        if user_id is not None:
            query = query.filter(Workout.user_id == user_id)
            
        return query.first()

    def get_by_date_range(
        self, 
        user_id: int, 
        start_date: date, 
        end_date: date
    ) -> List[Workout]:
        """
        Get workouts for a user within a date range.
        
        Args:
            user_id: User ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of Workout instances
        """
        return (
            self.db.query(Workout)
            .filter(Workout.user_id == user_id)
            .filter(func.date(Workout.date) >= start_date)
            .filter(func.date(Workout.date) <= end_date)
            .all()
        )

    def get_by_date(self, user_id: int, workout_date: date) -> Optional[Workout]:
        """
        Get workout for a user on a specific date.
        
        Args:
            user_id: User ID
            workout_date: Date to search for
            
        Returns:
            Workout instance or None if not found
        """
        return (
            self.db.query(Workout)
            .filter(Workout.user_id == user_id)
            .filter(func.date(Workout.date) == workout_date)
            # sort by most recent in case of multiple entries
            .order_by(Workout.date.desc())
            .first()
        )

    def get_all_with_exercises(self, user_id: int, filter: Optional[dict[str, Any]] = None, order_by: Optional[str] = None, order_desc: bool = False, skip: int = 0, limit: int = 100) -> List[Workout]:
        """
        Get workouts with exercises eager loaded.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Workout instances with exercises loaded
        """

        # Mapping the order_by parameter to actual model attributes can be added here if needed
        order_clause = Workout.date.desc()  # Default ordering
        if order_by:
            order_column = getattr(Workout, order_by, None)
            if order_column is not None:
                if order_desc:
                    order_clause = order_column.desc()
                else:
                    order_clause = order_column.asc()
        
        # Mapping the filter parameter to actual model attributes can be added here if needed
        filter_clause = filter or {}
        if filter_clause:
            filter_clause = {k: v for k, v in filter_clause.items() if hasattr(Workout, k)}
        
        
        return (
            self.db.query(Workout)
            .options(
                selectinload(Workout.workout_exercises).selectinload(WorkoutExercise.exercise)
            )
            .filter(Workout.user_id == user_id)
            .filter_by(**filter_clause)
            .order_by(order_clause)
            .offset(skip)
            .limit(limit)
            .all()
        )

