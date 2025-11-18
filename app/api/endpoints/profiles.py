from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate
from app.schemas.preferences import PreferencesCreate, PreferencesResponse, PreferencesUpdate
from app.core.security import get_current_user

# Services
from app.services.profile import ProfileService
from app.services.preferences import PreferencesService

router = APIRouter()

@router.get("/me", response_model=ProfileResponse)
def read_profile_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile.
    """
    profile = ProfileService(db).get_profile_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
        
    return profile

@router.post("/", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_in: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new profile for the current user.
    """
    # Check if user already has a profile
    db_profile = ProfileService(db).get_profile_by_user_id(current_user.id)
    if db_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a profile"
        )
    
    # Create new profile via service
    profile_data = {
        "name": profile_in.name,
        "fitness_goal": profile_in.fitness_goal,
        "fitness_level": profile_in.fitness_level,
        "available_days": profile_in.available_days,
        "workout_duration_minutes": profile_in.workout_duration_minutes,
    }
    db_profile = ProfileService(db).create_profile_for_user(current_user.id, profile_data)
    return db_profile

@router.put("/me", response_model=ProfileResponse)
def update_profile_me(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.
    """
    profile = ProfileService(db).get_profile_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    # Update via service
    update_data = profile_in.dict(exclude_unset=True)
    updated = ProfileService(db).update_profile(profile, update_data)
    return updated

@router.get("/me/preferences", response_model=PreferencesResponse)
def read_preferences_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's preferences.
    """
    profile = ProfileService(db).get_profile_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    preferences = PreferencesService(db).get_preferences_by_profile_id(profile.id)
    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preferences not found"
        )
    
    return preferences

@router.post("/me/preferences", response_model=PreferencesResponse, status_code=status.HTTP_201_CREATED)
def create_preferences_me(
    preferences_in: PreferencesCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create preferences for the current user.
    """
    profile = ProfileService(db).get_profile_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Check if preferences already exist
    db_preferences = PreferencesService(db).get_preferences_by_profile_id( profile.id)
    if db_preferences:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preferences already exist"
        )
    
    # Create new preferences
    db_preferences = PreferencesService(db).update_spotify_tokens( profile.id, preferences_in.dict())
    return db_preferences

@router.put("/me/preferences", response_model=PreferencesResponse)
def update_preferences_me(
    preferences_in: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's preferences.
    """
    profile = ProfileService(db).get_profile_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    preferences = PreferencesService(db).get_preferences_by_profile_id(profile.id)
    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preferences not found"
        )
    
    update_data = preferences_in.dict(exclude_unset=True)
    # Reuse update_spotify_tokens for general preference updates when spotify fields are present,
    # otherwise apply simple updates directly.
    for field, value in update_data.items():
        setattr(preferences, field, value)
    db.add(preferences)
    db.commit()
    db.refresh(preferences)
    return preferences
