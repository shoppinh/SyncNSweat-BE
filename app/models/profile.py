from __future__ import annotations

import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import ARRAY

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.preferences import Preferences
    from app.models.user import User


class FitnessGoal(enum.Enum):
    STRENGTH = "strength"
    ENDURANCE = "endurance"
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    GENERAL_FITNESS = "general_fitness"

class FitnessLevel(enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[Optional[str]] = mapped_column(String, index=True)
    fitness_goal: Mapped[FitnessGoal] = mapped_column(Enum(FitnessGoal), default=FitnessGoal.GENERAL_FITNESS)
    fitness_level: Mapped[FitnessLevel] = mapped_column(Enum(FitnessLevel), default=FitnessLevel.BEGINNER)
    available_days: Mapped[List[str]] = mapped_column(ARRAY(String), default=lambda: ["Monday", "Wednesday", "Friday"])
    workout_duration_minutes: Mapped[int] = mapped_column(Integer, default=60)

    # Relationships
    user: Mapped["User"] = relationship("User", backref="profile")
    preferences: Mapped[Optional["Preferences"]] = relationship("Preferences", back_populates="profile", uselist=False, cascade="all, delete-orphan")
