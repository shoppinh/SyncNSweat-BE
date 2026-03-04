"""
WorkoutRequest repository for database operations.
"""

from sqlalchemy.orm import Session

from app.models.workout_request import WorkoutRequest
from app.repositories.base import BaseRepository


class WorkoutRequestRepository(BaseRepository[WorkoutRequest]):
    """
    Repository for WorkoutRequest model operations.
    """

    def __init__(self, db: Session):
        super().__init__(WorkoutRequest, db)
