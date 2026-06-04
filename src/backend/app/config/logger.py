"""
Logging configuration.

Centralized logger setup with support for external config files.
"""
import logging
import logging.config
from pathlib import Path
from .settings import settings


def get_logger(name: str = __name__) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance
    """
    # Try to load logger.conf if it exists
    config_path = settings.BACKEND_ROOT / settings.LOG_CONFIG_PATH

    if config_path.exists():
        try:
            logging.config.fileConfig(str(config_path), disable_existing_loggers=False)
        except Exception as e:
            # Fallback to basic config if file parsing fails
            logging.basicConfig(
                level=getattr(logging, settings.LOG_LEVEL),
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            logging.warning(f"Failed to load logger config from {config_path}: {e}")
    else:
        # Fallback to basic config if file doesn't exist
        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    return logging.getLogger(name)


# Module-level logger for config package
logger = get_logger(__name__)
