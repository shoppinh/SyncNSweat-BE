from typing import List, Optional

from pydantic import BaseModel, ConfigDict

class ExerciseBase(BaseModel):
    name: str
    instructions: Optional[List[str]] = None
    target: str
    secondary_muscles: Optional[List[str]] = None
    gif_url: Optional[str] = None
    equipment: Optional[str] = None
    body_part: Optional[str] = None

class ExerciseCreate(ExerciseBase):
    name: str

class ExerciseUpdate(ExerciseBase):
    pass
class ExerciseSearch(ExerciseBase):
    name: Optional[str] = None
    target: Optional[str] = None

class ExerciseResponse(ExerciseBase):
    id: int

class WorkoutExerciseBase(BaseModel):
    order: int
    sets: int
    reps: str
    rest_seconds: int
    completed_sets: Optional[int] = 0
    weights_used: Optional[List[str]] = None
    exercise: Optional[ExerciseResponse] = None

class WorkoutExerciseCreate(WorkoutExerciseBase):
    pass

class WorkoutExerciseUpdate(BaseModel):
    completed_sets: Optional[int] = None
    weights_used: Optional[List[str]] = None

class WorkoutExerciseResponse(WorkoutExerciseBase):
    model_config = ConfigDict(from_attributes=True)

