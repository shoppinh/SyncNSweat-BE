from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from app.models.profile import FitnessGoal, FitnessLevel

class ProfileBase(BaseModel):
    
    name: Optional[str] = None
    fitness_goal: Optional[FitnessGoal] = None
    fitness_level: Optional[FitnessLevel] = None
    available_days: Optional[List[str]] = None
    workout_duration_minutes: Optional[int] = None
    
    model_config = ConfigDict(populate_by_name=True)
    

class ProfileCreate(ProfileBase):
    name: str

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)
