from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.types import ARRAY
from app.db.session import Base
import enum

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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name = Column(String, index=True)
    fitness_goal = Column(Enum(FitnessGoal), default=FitnessGoal.GENERAL_FITNESS)
    fitness_level = Column(Enum(FitnessLevel), default=FitnessLevel.BEGINNER)
    available_days = Column(ARRAY(String), default=["Monday", "Wednesday", "Friday"])
    workout_duration_minutes = Column(Integer, default=60)
    
    # Relationships
    user = relationship("User", backref="profile")
    preferences = relationship("Preferences", back_populates="profile", uselist=False, cascade="all, delete-orphan")
