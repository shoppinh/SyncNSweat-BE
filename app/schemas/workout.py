from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schemas.exercise import WorkoutExerciseCreate, WorkoutExerciseResponse

class WorkoutBase(BaseModel):
    date: Optional[datetime] = None
    focus: Optional[str] = None
    duration_minutes: Optional[int] = None
    playlist_id: Optional[str] = None
    playlist_name: Optional[str] = None
    completed: Optional[bool] = False

class WorkoutCreate(WorkoutBase):
    date: datetime
    exercises: Optional[List[WorkoutExerciseCreate]] = None
    
class WorkoutSuggest(WorkoutBase):
    fitness_level: Optional[str] = None
    available_equipment: Optional[List[str]] = None

class WorkoutUpdate(WorkoutBase):
    pass

class WorkoutResponse(WorkoutBase):
    id: int
    user_id: int
    created_at: datetime
    workout_exercises: List[WorkoutExerciseResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ScheduleRequest(BaseModel):
    """Request model for generating a workout schedule."""
    regenerate: Optional[bool] = False

class ScheduleResponse(BaseModel):
    """Response model for a generated workout schedule."""
    workouts: List[WorkoutResponse]
    message: str

class UserProfile(BaseModel):
    age: int
    fitness_level: str
    goals: List[str]
    available_equipment: List[str]
    preferences: Optional[Dict[str, Any]] = None

class WorkoutAIResponse(BaseModel):
    workout_plan: Dict[str, Any]
    message: str
