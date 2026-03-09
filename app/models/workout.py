from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (Boolean, DateTime, ForeignKey, Index, Integer,
                        PrimaryKeyConstraint, String)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import ARRAY

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    date: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), index=True)
    focus: Mapped[Optional[str]] = mapped_column(String)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    playlist_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    playlist_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    playlist_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", backref="workouts")
    workout_exercises: Mapped[List["WorkoutExercise"]] = relationship("WorkoutExercise", back_populates="workout", cascade="all, delete-orphan")


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    workout_id: Mapped[int] = mapped_column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"))
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"))
    sets: Mapped[Optional[int]] = mapped_column(Integer)
    reps: Mapped[Optional[str]] = mapped_column(String)
    order: Mapped[Optional[int]] = mapped_column(Integer)
    rest_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # For tracking progress
    completed_sets: Mapped[int] = mapped_column(Integer, default=0)
    weights_used: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Define composite primary key and indexes
    __table_args__ = (
        PrimaryKeyConstraint('workout_id', 'exercise_id'),
        Index('idx_workout_exercise_order', 'workout_id', 'order', unique=True),
    )

    # Relationships
    workout: Mapped["Workout"] = relationship("Workout", back_populates="workout_exercises")
    exercise: Mapped["Exercise"] = relationship("Exercise", back_populates="workout_exercises")


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    body_part: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    target: Mapped[Optional[str]] = mapped_column(String)
    secondary_muscles: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    equipment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gif_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    instructions: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)

    # Relationships
    workout_exercises: Mapped[List["WorkoutExercise"]] = relationship("WorkoutExercise", back_populates="exercise", cascade="all, delete-orphan")

