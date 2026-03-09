from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import ARRAY

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.profile import Profile


class Preferences(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), unique=True)

    # Equipment preferences
    available_equipment: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Music preferences
    music_genres: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    music_tempo: Mapped[str] = mapped_column(String, default="medium")

    # Exercise preferences
    target_muscle_groups: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    exercise_types: Mapped[List[str]] = mapped_column(ARRAY(String), default=lambda: ["strength", "cardio"])

    # Spotify integration
    spotify_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    spotify_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, default=dict)
    top_artists: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    top_tracks: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Relationship
    profile: Mapped["Profile"] = relationship("Profile", back_populates="preferences")
