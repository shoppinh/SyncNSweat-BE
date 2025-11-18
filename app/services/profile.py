from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.profile import Profile

class ProfileService:
    def __init__(self, db: Session):
        self.db = db

    def get_profile_by_user_id(self, user_id: int) -> Optional[Profile]:
        return self.db.query(Profile).filter(Profile.user_id == user_id).first()

    def create_profile_for_user(self, user_id: int, profile_data: Dict[str, Any]) -> Profile:
        profile = Profile(user_id=user_id, **profile_data)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile


    def update_profile(self, profile: Profile, update_data: Dict[str, Any]) -> Profile:
        for field, value in update_data.items():
            setattr(profile, field, value)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
