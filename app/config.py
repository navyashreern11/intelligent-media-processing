import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./media_processing.db"
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    BLUR_THRESHOLD: float = 100.0
    LOW_LIGHT_THRESHOLD: float = 60.0
    MIN_IMAGE_WIDTH: int = 200
    MIN_IMAGE_HEIGHT: int = 200
    MAX_RETRIES: int = 3
    TESSERACT_CMD: str = ""

    # Model configuration to load from .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
