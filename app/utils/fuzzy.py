from typing import List

from rapidfuzz import fuzz

from app.schemas.candidate import CandidateResponse


def _score(query: str, choice: str) -> float:
    """Return a similarity score (0-100) between query and choice.

    Uses rapidfuzz if available, otherwise falls back to difflib SequenceMatcher.
    """
    return float(fuzz.token_sort_ratio(query, choice))


def fuzzy_match_candidates(
    query: str, candidates: list[tuple[int, str]], limit: int = 5, score_cutoff: float = 60.0
) -> list[CandidateResponse]:
    """Return top candidate matches ordered by similarity.

    candidates: list of (id, name)
    Returns list of CandidateResponse
    """
    scored: list[CandidateResponse] = []
    for cid, name in candidates:
        score = _score(query, name)
        if score >= score_cutoff:
            scored.append(CandidateResponse(id=cid, name=name, score=score))

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:limit]


def get_top_candidate_by_repo(
    query: str, candidate_names: List[tuple[int, str]],limit: int = 5, score_cutoff: float = 80.0,
) -> CandidateResponse | None:
    """Query an ExerciseRepository for lightweight candidates and return the best match dict or None.

    `exercise_repo` is expected to implement `get_all_names()` which returns (id, name) tuples.
    """
    matches = fuzzy_match_candidates(query, candidates = candidate_names, limit=limit, score_cutoff=score_cutoff)
    return matches[0] if matches else None
