from typing import Any, Dict, List, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.preferences import Preferences
from app.models.profile import Profile
from app.models.user import User
from app.repositories.preferences import PreferencesRepository
from app.repositories.profile import ProfileRepository
from app.repositories.workout import WorkoutRepository
from app.services.gemini import GeminiService
from app.services.playlist_selector import PlaylistSelectorService
from app.services.spotify import SpotifyService

router = APIRouter()


@router.get("/spotify/recommendations")
async def get_spotify_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get Spotify playlist recommendations based on user preferences and workout type using Gemini service.
    """
    
    profile_repo = ProfileRepository(db)
    preferences_repo = PreferencesRepository(db)
    
    # Get user profile and preferences
    profile = profile_repo.get_one_by(user_id=current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    preferences = preferences_repo.get_one_by(profile_id=profile.id)
    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found"
        )

    # Check if Spotify is connected
    if not bool(preferences.spotify_connected):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Spotify not connected"
        )

    # Get Spotify access token from preferences
    spotify_data = preferences.spotify_data or {}
    if "access_token" not in spotify_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spotify access token not found",
        )


    # Initialize SpotifyService
    gemini_service = GeminiService(db, profile, preferences)

    # Get seed tracks and genres based on preferences and workout type
    # seed_tracks = spotify_service.get_seed_tracks(
    #     access_token=access_token,
    #     genres=preferences.music_genres,
    # )


    # Get recommendations from Gemini
    recommendations = await gemini_service.get_spotify_playlist_recommendations()

    # Create a new playlist for the workout
    # playlist = spotify_service.create_workout_playlist(
    #     access_token=access_token,
    #     track_uris=[track["uri"] for track in recommendations["tracks"]],
    #     user_id=current_user.id,
    # )

    return recommendations
@router.get("/spotify/playlists")
async def get_user_playlists(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Dict[str, List[Dict[str, Any]]]:
    """
    List user's Spotify playlists. 
    """
    # Get user profile and preferences
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    preferences = (
        db.query(Preferences).filter(Preferences.profile_id == profile.id).first()
    )
    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found"
        )

    # Check if Spotify is connected
    if not bool(preferences.spotify_connected):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Spotify not connected"
        )

    # Initialize SpotifyService with a persistence callback so the
    # interceptor can save refreshed tokens back to the user's preferences.
    spotify_data = preferences.spotify_data or {}
    if not spotify_data.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spotify access token not found",
        )
    # Provide DB/profile/preferences so the service can refresh & persist tokens
    spotify_service = SpotifyService(db, profile, preferences)

    try:
        resp = await spotify_service.get_user_playlists(limit=50)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spotify API error: {e}")

    items = resp.get("items", []) 
    if not items:
        return {"playlists": []}

    playlists: List[Dict[str, Any]] = []
    for p in items:
        playlists.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "tracks": p.get("tracks", {}).get("total") if isinstance(p.get("tracks"), dict) else None,
                "external_url": p.get("external_urls", {}).get("spotify") if isinstance(p.get("external_urls"), dict) else None,
                "image_url": p.get("images", [None])[0].get("url") if p.get("images") and isinstance(p.get("images"), list) and p.get("images")[0] else None,
            }
        )

    return {"playlists": playlists}


@router.get("/workout/{workout_id}/refresh")
async def refresh_playlist_for_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
)-> Dict[str, Any]:
    """
    Get a new playlist for a workout using Gemini Service and fallback to Playlist Selector Service.
    """
    # Get the workout
    workout_repo = WorkoutRepository(db)
    profile_repo = ProfileRepository(db)
    preferences_repo = PreferencesRepository(db)

    workout = workout_repo.get_one_by(user_id=current_user.id, id=workout_id)
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found"
        )

    # Get user profile and preferences
    profile = profile_repo.get_one_by(user_id=current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    preferences = preferences_repo.get_one_by(profile_id=profile.id)
    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found"
        )

    # Ensure we have an access token available
    spotify_data = preferences.spotify_data or {}
    access_token = spotify_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spotify access token not found",
        )

    # Try to generate/create a playlist via GeminiService (which may call SpotifyService internally)
    gemini_service = GeminiService(db, profile, preferences)
    try:
        result = await gemini_service.get_spotify_playlist_recommendations(workout_exercises=workout.workout_exercises)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating playlist: {e}")

    # Check for a created playlist in the result
    playlist_id = result.get("playlist_id", None)
    playlist_name = result.get("playlist_name", None) 
    playlist_url = result.get("playlist_url", None)

    if playlist_id and playlist_name and playlist_url:
        workout_repo.update(workout, {
            "playlist_id": playlist_id,
            "playlist_name": playlist_name,
            "playlist_url": playlist_url,
        })
        return {
            "playlist_id": playlist_id,
            "playlist_name": playlist_name,
            "external_url": playlist_url,
            "message": "Selected new playlist for workout",
        }

    else:
        
        # Fallback: use local playlist selector (requires the access token)
        playlist_selector = PlaylistSelectorService(db,profile,preferences)
        playlist = playlist_selector.shuffle_top_and_recent_tracks(
            fitness_goal=profile.fitness_goal.value,
            duration_minutes=cast(int, profile.workout_duration_minutes),
        )

        workout_repo.update(workout, {
            "playlist_id": playlist["id"],
            "playlist_name": playlist["name"],
            "playlist_url": playlist["external_url"],
        })

        return {
            "playlist_id": playlist["id"],
            "playlist_name": playlist["name"],
            "external_url": playlist["external_url"],
            "image_url": playlist["image_url"],
            "message": "Selected new playlist for workout (fallback selector)",
        }

