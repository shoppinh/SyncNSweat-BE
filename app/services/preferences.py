from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

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

        preferences.spotify_connected = True
        # Store token-related info in spotify_data column (JSON / Text column supported by model)
        preferences.spotify_data = {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
            "token_type": token_data.get("token_type"),
        }

        # Optionally compute expires_at using current time + expires_in here if desired
        self.db.add(preferences)
        self.db.commit()
        self.db.refresh(preferences)
        return preferences
