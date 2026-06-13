"""
Application settings.

Environment configuration using Pydantic BaseSettings.
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    """Application configuration."""

    APP_NAME: str = "Workflow Builder Service"
    APP_DESCRIPTION: str = "Workflow Builder Compilation and Validation Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    LOG_LEVEL: str = "INFO"
    LOG_CONFIG_PATH: str = "resources/logger.conf"

    BACKEND_ROOT: Path = Path(__file__).parent.parent.parent
    RESOURCES_DIR: Path = BACKEND_ROOT / "resources"
    RUNTIME_DIR: Path = BACKEND_ROOT / "runtime"
    COMPILED_DIR: Path = RUNTIME_DIR / "compiled"
    LOGS_DIR: Path = RUNTIME_DIR / "logs"

    DEFAULT_DSL_VERSION: str = "1.0.0"
    DEFAULT_TASK_QUEUE: str = "workflow-builder"
    TEMPORAL_ADDRESS: str = "localhost:7233"

    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    API_HOST: str = "0.0.0.0"  # noqa: S104
    API_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
