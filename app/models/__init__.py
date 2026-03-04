from app.models.user import User
from app.models.profile import Profile, FitnessGoal, FitnessLevel
from app.models.preferences import Preferences
from app.models.workout import Workout, WorkoutExercise, Exercise
from app.models.refresh_token import RefreshToken
from app.models.outbox_event import OutboxEvent
from app.models.workout_request import WorkoutRequest, WorkflowState

# For Alembic to detect models
__all__ = [
    "User",
    "Profile",
    "FitnessGoal",
    "FitnessLevel",
    "Preferences",
    "Workout",
    "WorkoutExercise",
    "Exercise",
    "RefreshToken",
    "OutboxEvent",
    "WorkoutRequest",
    "WorkflowState",
]
