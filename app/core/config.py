import os
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

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
    # NOTE: Default used to be 11520 minutes (8 days). It was intentionally reduced to
    # 60 minutes (1 hour) to improve security by limiting token lifetime. Deployments
    # that require longer-lived tokens should set ACCESS_TOKEN_EXPIRE_MINUTES in
    # the environment to override this default.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    USE_ASYNC_WORKOUT_PIPELINE: bool = os.getenv(
        "USE_ASYNC_WORKOUT_PIPELINE", "false"
    ).lower() in ("1", "true", "yes", "on")
    ASYNC_PIPELINE_STRICT_MODE: bool = os.getenv(
        "ASYNC_PIPELINE_STRICT_MODE", "false"
    ).lower() in ("1", "true", "yes", "on")
    ASYNC_PIPELINE_ROLLOUT_PERCENT: int = int(
        os.getenv("ASYNC_PIPELINE_ROLLOUT_PERCENT", 100)
    )

    # Spotify API settings
    SPOTIFY_CLIENT_ID: Optional[str] = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET: Optional[str] = os.getenv("SPOTIFY_CLIENT_SECRET")

    # Exercise API settings
    EXERCISE_API_KEY: Optional[str] = os.getenv("EXERCISE_API_KEY")
    EXERCISE_API_HOST: Optional[str] = os.getenv("EXERCISE_API_HOST")
    
    # Google Gemini settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEFAULT_SPOTIFY_USER_PASSWORD: str = os.getenv("DEFAULT_SPOTIFY_USER_PASSWORD", "")

    # RabbitMQ settings (planned async pipeline)
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    RABBITMQ_EXCHANGE_NAME: str = os.getenv(
        "RABBITMQ_EXCHANGE_NAME", "syncnsweat.events"
    )


settings = Settings()
