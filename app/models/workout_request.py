from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class WorkoutRequest(Base):
    __tablename__ = "workout_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    saga_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(
        Enum(
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
    error_code = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")
    profile = relationship("Profile")

    __table_args__ = (UniqueConstraint("saga_id", name="uq_saga_id"),)


class WorkflowState(Base):
    __tablename__ = "workflow_state"

    saga_id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    request_id = Column(
        Integer, ForeignKey("workout_requests.id", ondelete="CASCADE"), nullable=False
    )
    exercises_ready = Column(Boolean, default=False)
    playlist_ready = Column(Boolean, default=False)
    exercises_event_id = Column(UUID(as_uuid=True), nullable=True)
    playlist_event_id = Column(UUID(as_uuid=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    request = relationship("WorkoutRequest")
