"""
Exercise repository for database operations.
"""
from typing import Any, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.workout import Exercise
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
        self.db.commit()
