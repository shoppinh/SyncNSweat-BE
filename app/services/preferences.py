import time
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.preferences import Preferences
from app.repositories.preferences import PreferencesRepository
from app.repositories.profile import ProfileRepository


class PreferencesService:
    def __init__(self, db: Session):
        self.db = db
        self.profile_repo = ProfileRepository(db)
        self.preferences_repo = PreferencesRepository(db)

    def get_preferences_by_user_id(self, user_id: int) -> Optional[Preferences]:
        """Return Preferences for a given user_id (via Profile).

        Returns None when either profile or preferences do not exist.
        """
        profile = self.profile_repo.get_by_user_id(user_id)
        if not profile:
            return None
        return self.preferences_repo.get_by_profile_id(profile.id)

    def get_preferences_by_profile_id(self, profile_id: int) -> Optional[Preferences]:
        return self.preferences_repo.get_by_profile_id(profile_id)

    def update_spotify_tokens(self, profile_id: int, token_data: Dict[str, Any]) -> Preferences:
        """Update or create Preferences.spotify_data and spotify_connected based on token_data.
        token_data is expected to contain at least `access_token` and optionally
        `refresh_token`, `expires_in`, `token_type`.
        """
        preferences = self.preferences_repo.get_by_profile_id(profile_id)
        if not preferences:
            preferences = self.preferences_repo.create({"profile_id": profile_id})
            
        # Merge token-related info into spotify_data but only overwrite when
        # the provided value is not None. This preserves existing values when
        # a refresh response doesn't include every field.
        current: Dict[str, Any] = getattr(preferences, "spotify_data", {}) 
        
        # Explicitly update fields only when provided (not None)
        if token_data.get("access_token") is not None:
            current["access_token"] = token_data.get("access_token")
        if token_data.get("refresh_token") is not None:
            current["refresh_token"] = token_data.get("refresh_token")
        if token_data.get("expires_in") is not None:
            updated_expires_in = token_data.get("expires_in", 3600)
            current["expires_in"] = updated_expires_in
            # compute expires_at for convenience if expires_in provided
            current["expires_at"] = time.time() + float(updated_expires_in)
        if token_data.get("token_type") is not None:
            current["token_type"] = token_data.get("token_type")
        if token_data.get("expires_at") is not None:
            # allow callers to explicitly set expires_at (e.g., interceptor)
            current["expires_at"] = token_data.get("expires_at")
        
        # Update spotify_data with flag_modified handling
        preferences = self.preferences_repo.update_spotify_data(preferences, current)
        
        # Update spotify_connected flag
        preferences = self.preferences_repo.update(preferences, {"spotify_connected": True})
        
        return preferences
