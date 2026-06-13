"""
Third-party library initialization (logging, tracing, etc.).
Runs once at import time or during lifespan startup.
"""
import logging


def configure_logging(log_level: str = "INFO") -> None:
    """Set up root logger level. Structured logging can be wired here."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
