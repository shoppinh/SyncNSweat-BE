from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "Sync & Sweat"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development_secret_key")
    DATABASE_URI: str = os.getenv(
        "DATABASE_URI", "postgresql://postgres:postgres@localhost/syncnsweat"
    )
    API_URL: str = os.getenv("API_URL", "http://localhost:8000")
    SPOTIFY_REDIRECT_URL: str = os.getenv(
        "SPOTIFY_REDIRECT_URL", "http://localhost:8000"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Spotify API settings
    SPOTIFY_CLIENT_ID: Optional[str] = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET: Optional[str] = os.getenv("SPOTIFY_CLIENT_SECRET")

    # Exercise API settings
    EXERCISE_API_KEY: Optional[str] = os.getenv("EXERCISE_API_KEY")
    EXERCISE_API_HOST: Optional[str] = os.getenv("EXERCISE_API_HOST")
    
    # Google Gemini settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEFAULT_SPOTIFY_USER_PASSWORD: str = os.getenv("DEFAULT_SPOTIFY_USER_PASSWORD", "")


settings = Settings()
