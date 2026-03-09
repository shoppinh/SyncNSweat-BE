from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.workout_request import WorkflowState
from app.repositories.base import BaseRepository


class WorkflowStateRepository(BaseRepository[WorkflowState]):
    def __init__(self, db: Session):
        super().__init__(WorkflowState, db)

    def get_by_saga_id(self, saga_id: str) -> Optional[WorkflowState]:
        return self.db.query(WorkflowState).filter(WorkflowState.saga_id == saga_id).first()

    def get_or_create(self, *, saga_id: str, request_id: int) -> WorkflowState:
        existing = self.get_by_saga_id(saga_id)
        if existing is not None:
            return existing

        state = WorkflowState(saga_id=saga_id, request_id=request_id)
        self.db.add(state)
        self.db.flush()
        return state
