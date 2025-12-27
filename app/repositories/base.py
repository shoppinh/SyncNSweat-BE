"""
Base repository with generic CRUD operations.
"""
from typing import Any, Dict, Generic, List, Optional, Protocol, Type, TypeVar

from sqlalchemy import func
from sqlalchemy.orm import Session


class HasID(Protocol):
    id: Any

ModelType = TypeVar("ModelType", bound=HasID)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class with common CRUD operations.
    """

    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize repository with model class and database session.
        
        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Get a single record by ID.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Get all records with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of model instances
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def filter_by(self, skip: int = 0, limit: int = 100, **filters: Any) -> List[ModelType]:
        """
        Filter records by field values with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Field name and value pairs to filter by
            
        Returns:
            List of model instances matching the filters
        """
        query = self.db.query(self.model)
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)
        return query.offset(skip).limit(limit).all()

    def get_one_by(self, **filters: Any) -> Optional[ModelType]:
        """
        Get a single record by field values.
        
        Args:
            **filters: Field name and value pairs to filter by
            
        Returns:
            Model instance or None if not found
        """
        query = self.db.query(self.model)
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)
        return query.first()

    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record.
        
        Args:
            obj_in: Dictionary of field values
            
        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        """
        Update an existing record.
        
        Args:
            db_obj: Model instance to update
            obj_in: Dictionary of field values to update
            
        Returns:
            Updated model instance
        """
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, db_obj: ModelType) -> None:
        """
        Delete a record.
        
        Args:
            db_obj: Model instance to delete
        """
        self.db.delete(db_obj)
        self.db.commit()

    def exists(self, **filters: Any) -> bool:
        """
        Check if a record exists with given filters.
        
        Args:
            **filters: Field name and value pairs to filter by
            
        Returns:
            True if record exists, False otherwise
        """
        query = self.db.query(self.model)
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)
        return query.first() is not None

    def count(self, **filters: Any) -> int:
        """
        Count records matching filters.
        
        Args:
            **filters: Field name and value pairs to filter by
            
        Returns:
            Number of matching records
        """
        query = self.db.query(func.count(self.model.id))
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)
        return query.scalar()
