from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, db: Session):
        super().__init__(RefreshToken, db)

    def create_token(self, user_id: int, token_hash: str, expires_at: Optional[datetime] = None, device_info: Optional[str] = None, rotated_from_id: Optional[int] = None) -> RefreshToken:
        obj = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=device_info,
            rotated_from_id=rotated_from_id,
        )
        self.db.add(obj)
        self.db.flush()
        self.db.refresh(obj)
        return obj

    def get_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        return self.db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    def revoke(self, token: RefreshToken) -> None:
        setattr(token, "revoked", True) 
        self.db.add(token)
        self.db.flush()

    def revoke_all_for_user(self, user_id: int) -> None:
        self.db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})
        self.db.flush()

    def mark_used(self, token: RefreshToken) -> None:
        setattr(token, "last_used_at", datetime.now(timezone.utc))
        self.db.add(token)
        self.db.flush()
