"""
WorkoutRequest repository for database operations.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.workout_request import WorkoutRequest
from app.repositories.base import BaseRepository


class WorkoutRequestRepository(BaseRepository[WorkoutRequest]):
    """
    Repository for WorkoutRequest model operations.
    """

    def __init__(self, db: Session):
        super().__init__(WorkoutRequest, db)

    def get_by_saga_id(self, saga_id: str) -> Optional[WorkoutRequest]:
        return (
            self.db.query(WorkoutRequest)
            .filter(WorkoutRequest.saga_id == saga_id)
            .first()
        )

    def set_status(
        self,
        request: WorkoutRequest,
        *,
        status: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        request.status = status
        request.error_code = error_code
        request.error_message = error_message
        self.db.add(request)
