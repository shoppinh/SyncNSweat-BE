from app.models.user import User
from app.models.profile import Profile, FitnessGoal, FitnessLevel
from app.models.preferences import Preferences
from app.models.workout import Workout, WorkoutExercise, Exercise
from app.models.refresh_token import RefreshToken

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
]