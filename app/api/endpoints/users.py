from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.endpoints.auth import register
from app.core.security import get_current_user, get_password_hash
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.utils.constant import ERROR_MESSAGES

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user.
    """
    return register(user_in, db)

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    """
    Get current user.
    """
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update current user.
    """
    user_repo = UserRepository(db)
    update_data: Dict[str, Any] = {}

    if user_in.password:
        update_data["hashed_password"] = get_password_hash(user_in.password)
    
    if user_in.email:
        # Check if email is already taken
        if user_in.email != current_user.email:
            if user_repo.email_exists(user_in.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES["EMAIL_ALREADY_REGISTERED"]
                )
        update_data["email"] = user_in.email
    
    updated_user = user_repo.update(current_user, update_data)
    return updated_user

@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: int,
    db: Session = Depends(get_db)):
    """
    Get user by ID.
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
