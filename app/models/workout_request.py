from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.user import User

class WorkoutRequest(Base):
    __tablename__ = "workout_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    saga_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        SAEnum(
            "PENDING",
            "CONTEXT_READY",
            "DRAFT_READY",
            "PARTIAL_READY",
            "COMPLETED",
            "FAILED",
            name="workout_request_status",
        ),
        nullable=False,
        default="PENDING",
    )
    error_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User")
    profile: Mapped["Profile"] = relationship("Profile")

    __table_args__ = (UniqueConstraint("saga_id", name="uq_saga_id"),)


class WorkflowState(Base):
    __tablename__ = "workflow_state"

    saga_id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("workout_requests.id", ondelete="CASCADE"), nullable=False)
    exercises_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    playlist_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    exercises_event_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), nullable=True)
    playlist_event_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), nullable=True)
    completed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    request: Mapped["WorkoutRequest"] = relationship("WorkoutRequest")
