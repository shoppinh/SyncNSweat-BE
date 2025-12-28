from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.repositories.profile import ProfileRepository


class ProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.profile_repo = ProfileRepository(db)

    def get_profile_by_user_id(self, user_id: int) -> Optional[Profile]:
        return self.profile_repo.get_by_user_id(user_id)

    def create_profile_for_user(self, user_id: int, profile_data: Dict[str, Any]) -> Profile:
        profile_data["user_id"] = user_id
        return self.profile_repo.create(profile_data)

    def update_profile(self, profile: Profile, update_data: Dict[str, Any]) -> Profile:
        return self.profile_repo.update(profile, update_data)
