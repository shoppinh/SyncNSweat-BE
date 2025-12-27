"""
Preferences repository for database operations.
"""
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.preferences import Preferences
from app.repositories.base import BaseRepository


class PreferencesRepository(BaseRepository[Preferences]):
    """
    Repository for Preferences model operations.
    """

    def __init__(self, db: Session):
        super().__init__(Preferences, db)

    def get_by_profile_id(self, profile_id: int) -> Optional[Preferences]:
        """
        Get preferences by profile ID.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            Preferences instance or None if not found
        """
        return self.get_one_by(profile_id=profile_id)

    def update_spotify_data(self, preferences: Preferences, spotify_data: Dict[str, Any]) -> Preferences:
        """
        Update Spotify data (JSONB field) with proper change tracking.
        
        Args:
            preferences: Preferences instance to update
            spotify_data: Dictionary of Spotify data to update
            
        Returns:
            Updated Preferences instance
        """
        setattr(preferences, "spotify_data", spotify_data)
        flag_modified(preferences, "spotify_data")
        self.db.add(preferences)
        self.db.commit()
        self.db.refresh(preferences)
        return preferences

    def update_with_flag_modified(self, preferences: Preferences, field: str, value: Any) -> Preferences:
        """
        Update a JSONB field with proper change tracking.
        
        Args:
            preferences: Preferences instance to update
            field: Field name to update
            value: New value for the field
            
        Returns:
            Updated Preferences instance
        """
        setattr(preferences, field, value)
        flag_modified(preferences, field)
        self.db.add(preferences)
        self.db.commit()
        self.db.refresh(preferences)
        return preferences
