import sys
import logging
from loguru import logger
from src.core.config import settings

class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_logging():
    """Configures application logging with JSON formatting for observability."""
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
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
