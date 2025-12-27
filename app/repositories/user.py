"""
User repository for database operations.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Repository for User model operations.
    """

    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User instance or None if not found
        """
        return self.db.query(User).filter(User.email == email).first()

    def get_by_spotify_user_id(self, spotify_user_id: str) -> Optional[User]:
        """
        Get user by Spotify user ID.
        
        Args:
            spotify_user_id: Spotify user ID
            
        Returns:
            User instance or None if not found
        """
        return self.db.query(User).filter(User.spotify_user_id == spotify_user_id).first()

    def email_exists(self, email: str) -> bool:
        """
        Check if email is already registered.
        
        Args:
            email: Email address to check
            
        Returns:
            True if email exists, False otherwise
        """
        return self.exists(email=email)
