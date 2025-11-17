from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any

class PreferencesBase(BaseModel):
    available_equipment: Optional[List[str]] = None
    music_genres: Optional[List[str]] = None
    music_tempo: Optional[str] = None
    target_muscle_groups: Optional[List[str]] = None
    exercise_types: Optional[List[str]] = None
    spotify_connected: Optional[bool] = None
    spotify_data: Optional[Dict[str, Any]] = None
class PreferencesCreate(PreferencesBase):
    pass

class PreferencesUpdate(PreferencesBase):
    pass

class PreferencesResponse(PreferencesBase):
    id: int
    profile_id: int

    model_config = ConfigDict(populate_by_name=True,from_attributes=True)
