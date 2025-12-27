from typing import List

from app.api.endpoints.workouts import EXERCISE_NOT_FOUND
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.workout import Exercise
from app.schemas.exercise import (ExerciseCreate, ExerciseResponse, ExerciseSearch, ExerciseUpdate)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
def create_exercise(exercise: ExerciseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """_summary_

    Args:
        exercise (ExerciseCreate): _description_
        db (Session, optional): _description_. Defaults to Depends(get_db).
        current_user (User, optional): _description_. Defaults to Depends(get_current_user).

    Returns:
        _type_: _description_
    """    
    db_exercise = Exercise(**exercise.model_dump())    
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)    
    return db_exercise

@router.get("/", response_model=List[ExerciseResponse])
def read_exercises(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """_summary_

    Args:
        skip (int, optional): _description_. Defaults to 0.
        limit (int, optional): _description_. Defaults to 100.
        db (Session, optional): _description_. Defaults to Depends(get_db).

    Returns:
        _type_: _description_
    """    
    exercises = db.query(Exercise).offset(skip).limit(limit).all()    
    return exercises

@router.post("/search", response_model=List[ExerciseResponse])
def search_exercises(search_query: ExerciseSearch, db: Session = Depends(get_db)):
    """_summary_

    Args:
        search_query (str): _description_
        db (Session, optional): _description_. Defaults to Depends(get_db).

    Returns:
        _type_: _description_
    """
    query = db.query(Exercise)
    if search_query.name:
        query = query.filter(Exercise.name.ilike(f"%{search_query.name}%"))
        
    if search_query.body_part:
        query = query.filter(Exercise.body_part.ilike(f"%{search_query.body_part}%"))
        
    if search_query.target:
        query = query.filter(Exercise.target.ilike(f"%{search_query.target}%"))
    
    if search_query.equipment:
        query = query.filter(Exercise.equipment.ilike(f"%{search_query.equipment}%"))
        
    exercises = query.all()
    return exercises

@router.get("/{exercise_id}", response_model=ExerciseResponse)
def read_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """_summary_

    Args:
        exercise_id (int): _description_
        db (Session, optional): _description_. Defaults to Depends(get_db).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """    
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()    
    if exercise is None:
        raise HTTPException(status_code=404, detail=EXERCISE_NOT_FOUND)    
    return exercise

@router.put("/{exercise_id}", response_model=ExerciseResponse)
def update_exercise(exercise_id: int, exercise: ExerciseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """_summary_

    Args:
        exercise_id (int): _description_
        exercise (ExerciseUpdate): _description_
        db (Session, optional): _description_. Defaults to Depends(get_db).
        current_user (User, optional): _description_. Defaults to Depends(get_current_user).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """        
    db_exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if db_exercise is None:        
        raise HTTPException(status_code=404, detail=EXERCISE_NOT_FOUND)
    for key, value in exercise.model_dump(exclude_unset=True).items():        
        setattr(db_exercise, key, value)
    db.commit()
    db.refresh(db_exercise)    
    return db_exercise

@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """_summary_

    Args:
        exercise_id (int): _description_
        db (Session, optional): _description_. Defaults to Depends(get_db).
        current_user (User, optional): _description_. Defaults to Depends(get_current_user).

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """    
    db_exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()    
    if db_exercise is None:
        raise HTTPException(status_code=404, detail=EXERCISE_NOT_FOUND)    
    db.delete(db_exercise)
    db.commit()
    return {"ok": True}
