from fastapi import APIRouter
from app.api.endpoints import users, auth, profiles, workouts, playlists, database, exercises, health

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
router.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
router.include_router(playlists.router, prefix="/playlists", tags=["playlists"])
router.include_router(database.router, prefix="/database", tags=["database"])
router.include_router(health.router, prefix="/health", tags=["health"])