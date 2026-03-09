
from pydantic import BaseModel


class CandidateResponse(BaseModel):
    id: int
    name: str
    score: float