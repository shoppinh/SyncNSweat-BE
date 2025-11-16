from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, logger, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.profile import Profile
from app.models.preferences import Preferences
from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
)
from app.core.config import settings
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse
from app.services.spotify import SpotifyService

router = APIRouter()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    """
    # Check if user with this email already exists
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_in.password)
    db_user = User(email=user_in.email, hashed_password=hashed_password, is_active=True)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create profile for user if name is provided
    if user_in.name:
        profile = Profile(user_id=db_user.id, name=user_in.name)
        db.add(profile)
        db.commit()
        db.refresh(profile)

        # Create empty preferences
        preferences = Preferences(profile_id=profile.id)
        db.add(preferences)
        db.commit()

    return db_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    return login(form_data, db)


@router.get("/spotify/login")
def spotify_login():
    """
    Initiate Spotify OAuth login flow.
    Redirects user to Spotify authorization URL.
    """
    spotify_service = SpotifyService()
    redirect_uri = f"{settings.SPOTIFY_REDIRECT_URL}/api/v1/auth/spotify/callback"
    auth_url = spotify_service.get_auth_url(redirect_uri, state="login")  # Use "login" as state to indicate login flow
    return {"auth_url": auth_url}


@router.get("/spotify/callback/")
async def spotify_callback(
    code: str = Query(None, description="Spotify authorization code"),
    state: str = Query(None, description="State parameter indicating flow type (e.g., 'login' or 'connection')"),  

    error: str = Query(None, description="Spotify error, if any"),
    db: Session = Depends(get_db),
):
    """
    Handle Spotify OAuth callback for login or connection.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Spotify authentication error: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required",
        )

    # Exchange code for access token
    spotify_service = SpotifyService()
    redirect_uri = f"{settings.SPOTIFY_REDIRECT_URL}/api/v1/auth/spotify/callback"
    token_data = spotify_service.get_access_token_with_interceptor(code, redirect_uri)

    if "error" in token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Spotify token error: {token_data['error']}",
        )

    # Get user profile from Spotify
    access_token = token_data.get("access_token") or ""
    refresh_token = token_data.get("refresh_token")
    expires_at = token_data.get("expires_at")
    user_profile = await spotify_service.get_user_profile(access_token, refresh_token, expires_at)
    spotify_user_id = user_profile.get("id")
    email = user_profile.get("email")

    if not spotify_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve Spotify user ID",
        )

    # Check if user exists by Spotify ID
    existing_user = db.query(User).filter(User.spotify_user_id == spotify_user_id).first()

    if existing_user:
        # User exists, log them in
        user = existing_user

        # Update or create preferences with Spotify data
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if profile:
            preferences = db.query(Preferences).filter(Preferences.profile_id == profile.id).first()
            if not preferences:
                preferences = Preferences(profile_id=profile.id)
                db.add(preferences)
                db.commit()
                db.refresh(preferences)

            preferences.spotify_connected = True
            preferences.spotify_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": token_data.get("expires_in"),
                "expires_at": expires_at,
                "token_type": token_data.get("token_type"),
            }
    else:
        # Check if email is already registered
        if email and db.query(User).filter(User.email == email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please login with email/password and connect Spotify.",
            )

        # Create new user
        user = User(
            email=email or f"spotify_{spotify_user_id}@spotify.local",
            spotify_user_id=spotify_user_id,
            is_active=True,
            hashed_password=get_password_hash(settings.DEFAULT_SPOTIFY_USER_PASSWORD)
        )
        db.add(user)
        db.refresh(user)

        # Create profile
        profile = Profile(user_id=user.id, name=user_profile.get("display_name", ""))
        db.add(profile)
        db.commit()
        db.refresh(profile)

        # Create preferences
        preferences = Preferences(profile_id=profile.id, spotify_connected=True, spotify_data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": token_data.get("expires_in"),
            "expires_at": expires_at,
            "token_type": token_data.get("token_type"),
        })
        db.add(preferences)
        db.commit()
        db.refresh(preferences)

        # Fetch and store user data
        try:
            top_artists = await spotify_service.get_current_user_top_artists(access_token, refresh_token, expires_at)
            top_tracks = await spotify_service.get_current_user_top_tracks(access_token, refresh_token, expires_at)
            preferences.top_artists = [artist["name"] for artist in top_artists.get("items", [])]
            preferences.top_tracks = [track["name"] for track in top_tracks.get("items", [])]
        except Exception as e:
            # Log error but don't fail login
            print(f"Error fetching user data: {e}")
            logger.logger.error(f"Error fetching Spotify user data: {e}", exc_info=True)

        db.commit()

    # Generate JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jwt_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {
        "jwt_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "spotify_connected": True,
        }
    }
