from typing import List, Optional

from pydantic import BaseModel, ConfigDict

class ExerciseBase(BaseModel):
    name: str
    body_part: Optional[str] = None
    target: str
    secondary_muscles: Optional[List[str]] = None
    equipment: Optional[str] = None
    gif_url: Optional[str] = None
    instructions: Optional[List[str]] = None

class ExerciseCreate(ExerciseBase):
    name: str

class ExerciseUpdate(ExerciseBase):
    pass
class ExerciseSearch(ExerciseBase):
    name: Optional[str] = None  # type: ignore[override]
    target: Optional[str] = None  # type: ignore[override]

class ExerciseResponse(ExerciseBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

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

