from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.session import Base

class Preferences(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), unique=True)
    
    # Equipment preferences
    available_equipment = Column(ARRAY(String), default=[])
    
    # Music preferences
    music_genres = Column(ARRAY(String), default=[])
    music_tempo = Column(String, default="medium")
    
    # Exercise preferences
    target_muscle_groups = Column(ARRAY(String), default=[])
    exercise_types = Column(ARRAY(String), default=["strength", "cardio"])
    
    # Spotify integration
    spotify_connected = Column(Boolean, default=False)
    spotify_data = Column(JSONB, default={})
    top_artists = Column(ARRAY(String), default=[])
    top_tracks = Column(ARRAY(String), default=[])
    
    # Relationship
    profile = relationship("Profile", back_populates="preferences")
