from sqlalchemy import Column, Index, Integer, PrimaryKeyConstraint, String, ForeignKey, DateTime, Text, ARRAY, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    date = Column(DateTime(timezone=True), index=True)
    focus = Column(String)  # e.g., "Upper Body", "Lower Body", "Push", "Pull", "Legs"
    duration_minutes = Column(Integer)
    playlist_id = Column(String, nullable=True)  # Spotify playlist ID
    playlist_name = Column(String, nullable=True)
    playlist_url = Column(String, nullable=True)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="workouts")
    workout_exercises = relationship("WorkoutExercise", back_populates="workout", cascade="all, delete-orphan")

class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    workout_id = Column(Integer, ForeignKey("workouts.id", ondelete="CASCADE"))
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"))  # ID from external exercise API
    sets = Column(Integer)
    reps = Column(String)  # Could be "8-12" or just "10"
    order = Column(Integer)  # Order in the workout
    rest_seconds = Column(Integer)

    # For tracking progress
    completed_sets = Column(Integer, default=0)
    weights_used = Column(ARRAY(String), default=[])  # e.g., ["20kg", "22.5kg", "25kg"]

    # Define composite primary key
    __table_args__ = (
        PrimaryKeyConstraint('workout_id', 'exercise_id'),
        Index('idx_workout_exercise_order', 'workout_id', 'order', unique=True)  # Ensure order is unique within a workout
    )
    
    # Relationships
    workout = relationship("Workout", back_populates="workout_exercises")
    exercise = relationship("Exercise", back_populates="workout_exercises")
    
class Exercise(Base):
    __tablename__ = "exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    body_part = Column(String, nullable=True)
    target = Column(String)
    secondary_muscles = Column(ARRAY(String), nullable=True)
    equipment = Column(String, nullable=True)
    gif_url = Column(String, nullable=True)
    instructions = Column(ARRAY(String), nullable=True)
    
    # Relationships
    workout_exercises = relationship("WorkoutExercise", back_populates="exercise", cascade="all, delete-orphan")

