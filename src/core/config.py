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

# Streamlit Secrets Support (Priority)
try:
    import streamlit as st
    if st.secrets:
        # Override default env loading if secrets found in st.secrets
        # We can pass them to Settings as init arguments
        secrets_dict = {}
        for key in Settings.__annotations__.keys():
            if key in st.secrets:
                secrets_dict[key] = st.secrets[key]
        
        settings = Settings(**secrets_dict)
    else:
        settings = Settings()
except Exception:
    # Fallback to standard .env if not in streamlit context
    settings = Settings()
except ValidationError as e:
    logger.error(f"Configuration Error: {e}")
    sys.exit(1)
