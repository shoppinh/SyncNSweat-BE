
import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router as api_router
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
# logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Background worker task reference
_outbox_task: Optional[asyncio.Task[None]] = None


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Manage background worker lifecycle alongside the FastAPI app."""
    global _outbox_task
    
    # Optional DB seeding on startup, gated by setting
    if getattr(settings, "ENABLE_STARTUP_SEEDING", False):
        async def seed_exercises():
            try:
                from app.db.session import SessionLocal
                from app.models.workout import Exercise
                from app.repositories.exercise import ExerciseRepository
                from app.services.exercise import ExerciseService

                def sync_seed():
                    with SessionLocal() as db:
                        # Check if the exercises table has any rows
                        if db.query(Exercise).first() is None:
                            logger.info("Exercises table is empty. Syncing from external source...")
                            exercise_repo = ExerciseRepository(db)
                            exercise_service = ExerciseService(db)

                            exercises = [
                                {
                                    "name": ex["name"],
                                    "body_part": ex["bodyPart"],
                                    "target": ex["target"],
                                    "secondary_muscles": ex["secondaryMuscles"],
                                    "equipment": ex["equipment"],
                                    "gif_url": ex["gifUrl"],
                                    "instructions": ex["instructions"],
                                }
                                for ex in exercise_service.get_exercises_from_external_source(
                                    params={"limit": 1324}
                                )
                            ]
                            # Use transaction context for bulk insert to ensure rollback on failure
                            with db.begin():
                                exercise_repo.bulk_insert(exercises)
                            logger.info("Finished syncing external exercises successfully.")
                        else:
                            logger.info("Exercises table already populated. Skipping sync.")

                await asyncio.to_thread(sync_seed)
            except Exception as e:
                logger.warning(f"Failed to check or sync initial exercises: {e}")

        await seed_exercises()

    # Start outbox worker
    try:
        from app.workers.outbox_publisher_worker import \
            run_forever as _outbox_run

        logger.info("Starting outbox worker task")
        _outbox_task = asyncio.create_task(_outbox_run())
        logger.info("Outbox worker started: %s", repr(_outbox_task))
    except Exception:
        logger.exception("Failed to start outbox worker")

    yield

    if _outbox_task is not None:
        logger.info("Shutting down outbox worker: %s", repr(_outbox_task))
        _outbox_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _outbox_task
        logger.info("Outbox worker stopped")



app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

# Set up CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:19000",  # Expo development server
    "http://localhost:19006",  # Expo web
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    """Health-check / welcome endpoint."""
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
