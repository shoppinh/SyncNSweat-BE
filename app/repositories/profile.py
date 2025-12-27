"""
Profile repository for database operations.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[Profile]):
    """
    Repository for Profile model operations.
    """

    def __init__(self, db: Session):
        super().__init__(Profile, db)

    def get_by_user_id(self, user_id: int) -> Optional[Profile]:
        """
        Get profile by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Profile instance or None if not found
        """
        return self.get_one_by(user_id=user_id)
