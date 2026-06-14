"""
Application settings.

Environment configuration using Pydantic BaseSettings.
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    """Application configuration."""

    APP_NAME: str = "FlowAutomate"
    APP_DESCRIPTION: str = "FlowAutomate — AutoX workflow automation service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    DB_ECHO: bool = False  # Set True in .env to log all SQL queries

    LOG_LEVEL: str = "INFO"
    LOG_CONFIG_PATH: str = "resources/logger.conf"

    BACKEND_ROOT: Path = Path(__file__).parent.parent.parent
    RESOURCES_DIR: Path = BACKEND_ROOT / "resources"
    LOGS_DIR: Path = RESOURCES_DIR / "logs"
    DATA_DIR: Path = RESOURCES_DIR / "data"
    # Zigflow file watcher still reads compiled DSL files from disk
    RUNTIME_DIR: Path = BACKEND_ROOT / "runtime"
    COMPILED_DIR: Path = RUNTIME_DIR / "compiled"

    DEFAULT_DSL_VERSION: str = "1.0.0"
    DEFAULT_TASK_QUEUE: str = "flowautomate"
    TEMPORAL_ADDRESS: str = "localhost:7233"

    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    # PostgreSQL connection
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "autox-flow-automate"
    DATABASE_USERNAME: str = "postgres"
    DATABASE_PASSWORD: str = "admin123"

    API_HOST: str = "0.0.0.0"  # noqa: S104
    API_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
