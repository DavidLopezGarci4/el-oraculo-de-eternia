from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError
import sys
from loguru import logger

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "El Oráculo de Eternia"
    VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./oraculo.db"

    # External APIs (Optional for now, required for prod)
    CLOUDINARY_CLOUD_NAME: str | None = None
    CLOUDINARY_API_KEY: str | None = None
    CLOUDINARY_API_SECRET: str | None = None
    
    # Notifications (Telegram)
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )

try:
    settings = Settings()
except ValidationError as e:
    logger.error(f"Configuration Error: {e}")
    sys.exit(1)
