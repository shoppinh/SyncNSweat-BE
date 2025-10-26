import pytest
from app.services.gemini import GeminiService
from app.core.config import settings

@pytest.fixture
def gemini_service():
    return GeminiService()

def test_gemini_config():
    """Test that all required Gemini configurations are present"""
    assert settings.GOOGLE_CLOUD_PROJECT_ID is not None, "Project ID not configured"
    assert settings.GEMINI_API_KEY is not None, "API key not configured"
    assert settings.GEMINI_LOCATION is not None, "Location not configured"

async def test_gemini_service_initialization(gemini_service):
    """Test that GeminiService can be initialized"""
    assert gemini_service is not None
    assert gemini_service.model is not None

async def test_preference_analysis(gemini_service):
    """Test basic preference analysis functionality"""
    test_preferences = {
        "preferred_genres": ["pop", "rock"],
        "energy_level": "high",
        "workout_intensity": "moderate"
    }
    
    result = await gemini_service.analyze_preferences(
        user_preferences=test_preferences,
        fitness_goal="weight_loss"
    )
    
    assert isinstance(result, dict)
    assert "recommended_genres" in result
    assert "target_bpm" in result
    assert "energy_level" in result
    assert "valence_level" in result