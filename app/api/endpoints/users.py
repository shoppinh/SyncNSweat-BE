from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.core.security import get_password_hash, get_current_user
from app.api.endpoints.auth import register
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

    updated_user = current_user

    if user_in.password:
        hashed_password = get_password_hash(user_in.password)
        setattr(updated_user, "hashed_password", hashed_password)
    
    if user_in.email:
        # Check if email is already taken
        if user_in.email != updated_user.email:
            db_user = db.query(User).filter(User.email == user_in.email).first()
            if db_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES["EMAIL_ALREADY_REGISTERED"]
                )
        setattr(updated_user, "email", user_in.email)
    
    db.add(updated_user)
    db.commit()
    db.refresh(updated_user)
    return updated_user

@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: int,
    db: Session = Depends(get_db)):
    """
    Get user by ID.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
