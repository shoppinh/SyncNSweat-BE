
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.exercise import ExerciseRepository
from app.services.exercise import ExerciseService

router = APIRouter()

@router.post("/database/sync-external-source")
def synchronize_database(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Synchronize the database with ExerciseDB API
    """
    exercise_service = ExerciseService(db)
    exercise_repo = ExerciseRepository(db)
    
    # Delete all existing exercises
    # Note: This deletes directly via query for efficiency with bulk operations
    db.query(exercise_repo.model).delete()
    db.commit()
    
    # Fetch all exercises from ExerciseDB API
    exercises = [{
        "name": ex["name"],
        "body_part": ex["bodyPart"],
        "target": ex["target"],
        "secondary_muscles": ex["secondaryMuscles"],
        "equipment": ex["equipment"],
        "gif_url": ex["gifUrl"],
        "instructions": ex["instructions"]
    } for ex in exercise_service.get_exercises_from_external_source(params={"limit": 1324})]
    
    # Bulk insert exercises
    exercise_repo.bulk_insert(exercises)
    
    return {"message": "Database synchronized successfully"}
