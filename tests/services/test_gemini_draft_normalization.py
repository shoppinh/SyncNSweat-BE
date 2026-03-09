from app.services.gemini import GeminiService


def test_normalize_draft_limits_and_shapes():
    service = GeminiService.__new__(GeminiService)

    raw = {
        "focus": "Lower Body",
        "duration_minutes": "50",
        "exercise_candidates": [
            {"name": "Squat", "target_hint": "quads"},
            {"exercise": "Lunge", "target": "glutes"},
        ]
        * 5,
        "song_candidates": [
            {"song_title": "Track 1", "artist_name": "Artist 1"},
            {"title": "Track 2", "artist": "Artist 2"},
        ]
        * 12,
    }

    normalized = service._normalize_draft(raw, default_duration=45)

    assert normalized["focus"] == "Lower Body"
    assert normalized["duration_minutes"] == 50
    assert len(normalized["exercise_candidates"]) == 8
    assert len(normalized["song_candidates"]) == 20


def test_normalize_draft_fallback_for_invalid_input():
    service = GeminiService.__new__(GeminiService)

    normalized = service._normalize_draft(raw_draft="invalid", default_duration=45)

    assert normalized["focus"] == "General"
    assert normalized["duration_minutes"] == 45
    assert normalized["exercise_candidates"] == []
    assert normalized["song_candidates"] == []
