from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.endpoints.workouts import EXERCISE_NOT_FOUND
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.exercise import ExerciseRepository
from app.schemas.exercise import (ExerciseCreate, ExerciseResponse,
                                  ExerciseSearch, ExerciseUpdate)

router = APIRouter()

@router.post("/", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
def create_exercise(exercise: ExerciseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exercise_repo = ExerciseRepository(db)
    db_exercise = exercise_repo.create(exercise.model_dump())
    return db_exercise

@router.get("/", response_model=List[ExerciseResponse])
def read_exercises(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    exercise_repo = ExerciseRepository(db)
    exercises = exercise_repo.get_all(skip, limit)
    return exercises

@router.post("/search", response_model=List[ExerciseResponse])
def search_exercises(search_query: ExerciseSearch, db: Session = Depends(get_db)):
    exercise_repo = ExerciseRepository(db)
    
    if search_query.name:
        exercises = exercise_repo.search_by_name(search_query.name)
    elif search_query.body_part:
        exercises = exercise_repo.get_by_body_part(search_query.body_part)
    elif search_query.target:
        exercises = exercise_repo.get_by_target(search_query.target)
    elif search_query.equipment:
        exercises = exercise_repo.get_by_equipment(search_query.equipment)
    else:
        exercises = exercise_repo.get_all()
        
    return exercises

@router.get("/{exercise_id}", response_model=ExerciseResponse)
def read_exercise(exercise_id: int, db: Session = Depends(get_db)):
    exercise_repo = ExerciseRepository(db)
    exercise = exercise_repo.get_by_id(exercise_id)
    if exercise is None:
        raise HTTPException(status_code=404, detail=EXERCISE_NOT_FOUND)
    return exercise

@router.put("/{exercise_id}", response_model=ExerciseResponse)
def update_exercise(exercise_id: int, exercise: ExerciseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exercise_repo = ExerciseRepository(db)
    db_exercise = exercise_repo.get_by_id(exercise_id)
    if db_exercise is None:
        raise HTTPException(status_code=404, detail=EXERCISE_NOT_FOUND)
    
    update_data = exercise.model_dump(exclude_unset=True)
    db_exercise = exercise_repo.update(db_exercise, update_data)
    return db_exercise

@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exercise_repo = ExerciseRepository(db)
    db_exercise = exercise_repo.get_by_id(exercise_id)
    if db_exercise is None:
        raise HTTPException(status_code=404, detail=EXERCISE_NOT_FOUND)
    
    exercise_repo.delete(db_exercise)
    return {"ok": True}
