from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.profile import Profile
from app.models.preferences import Preferences

class PreferencesService:
    def __init__(self, db: Session):
        self.db = db

    def get_preferences_by_user_id(self, user_id: int) -> Optional[Preferences]:
        """Return Preferences for a given user_id (via Profile).

        Returns None when either profile or preferences do not exist.
        """
        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()
        if not profile:
            return None
        return self.db.query(Preferences).filter(Preferences.profile_id == profile.id).first()


    def get_preferences_by_profile_id(self, profile_id: int) -> Optional[Preferences]:
        return self.db.query(Preferences).filter(Preferences.profile_id == profile_id).first()  

    def update_spotify_tokens(self, profile_id: int, token_data: Dict[str, Any]) -> Preferences:
        """Update or create Preferences.spotify_data and spotify_connected based on token_data.
        token_data is expected to contain at least `access_token` and optionally
        `refresh_token`, `expires_in`, `token_type`.
        """
        preferences = self.db.query(Preferences).filter(Preferences.profile_id == profile_id).first()
        if not preferences:
            preferences = Preferences(profile_id=profile_id)
            self.db.add(preferences)
            
        setattr(preferences, "spotify_connected", True)  #
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
            current["expires_in"] = token_data.get("expires_in")
            # compute expires_at for convenience if expires_in provided
            try:
                import time

                current["expires_at"] = time.time() + float(getattr(token_data, "expires_in"))
            except Exception:
                # If computation fails, don't set expires_at
                pass
        if token_data.get("token_type") is not None:
            current["token_type"] = token_data.get("token_type")
        if token_data.get("expires_at") is not None:
            # allow callers to explicitly set expires_at (e.g., interceptor)
            current["expires_at"] = token_data.get("expires_at")
            
        setattr(preferences, "spotify_data", current)

        # Mark the JSONB column as modified so SQLAlchemy tracks the change
        flag_modified(preferences, "spotify_data")

        # Optionally compute expires_at using current time + expires_in here if desired
        self.db.add(preferences)
        self.db.commit()
        self.db.refresh(preferences)
        return preferences
