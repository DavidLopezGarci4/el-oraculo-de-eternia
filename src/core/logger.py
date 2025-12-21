import sys
from loguru import logger
from src.core.config import settings

def setup_logging():
    """Configures application logging with JSON formatting for observability."""
    logger.remove()  # Remove default handler

    # Stdout handler (Human readable for Dev, JSON for Prod could be added via env)
    log_level = "DEBUG" if settings.DEBUG else "INFO"
    
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # File handler (Rotation & Retention)
    logger.add(
        "logs/oraculo.log",
        rotation="10 MB",
        retention="1 month",
        level="INFO",
        compression="zip"
    )

    logger.info(f"Logging initialized. Level: {log_level}")

setup_logging()
