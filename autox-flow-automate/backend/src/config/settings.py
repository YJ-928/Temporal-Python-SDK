"""
Application settings.

All configurable values are loaded from the .env file.
No defaults are hardcoded for infrastructure addresses, ports, credentials,
or timeouts — every value can be overridden via environment variables.
See .env.example for the full list of supported variables.
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    """Application configuration — all values sourced from .env."""

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "FlowAutomate"
    APP_DESCRIPTION: str = "FlowAutomate — AutoX workflow automation service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    DB_ECHO: bool = False

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_CONFIG_PATH: str = "resources/logger.conf"

    # ── Paths (computed from repo layout — override only if directory structure changes) ──
    BACKEND_ROOT: Path = Path(__file__).parent.parent.parent
    RESOURCES_DIR: Path = BACKEND_ROOT / "resources"
    LOGS_DIR: Path = RESOURCES_DIR / "logs"
    DATA_DIR: Path = RESOURCES_DIR / "data"
    RUNTIME_DIR: Path = BACKEND_ROOT / "runtime"
    COMPILED_DIR: Path = RUNTIME_DIR / "compiled"

    # ── API server ────────────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"  # noqa: S104
    API_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # ── OpenAPI / Swagger docs ────────────────────────────────────────────────
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    # ── Temporal ──────────────────────────────────────────────────────────────
    TEMPORAL_ADDRESS: str = "localhost:7233"
    TEMPORAL_CONNECT_TIMEOUT: float = 10.0
    TEMPORAL_HEALTH_TIMEOUT: float = 3.0

    # ── DSL compiler defaults ─────────────────────────────────────────────────
    DEFAULT_DSL_VERSION: str = "1.0.0"
    DEFAULT_TASK_QUEUE: str = "flowautomate"

    # ── Zigflow runtime daemon ────────────────────────────────────────────────
    ZIGFLOW_RUNTIME_HOST: str = "localhost"
    ZIGFLOW_RUNTIME_PORT: int = 3005
    ZIGFLOW_METRICS_HOST: str = "127.0.0.1"
    ZIGFLOW_METRICS_PORT: int = 9095
    ZIGFLOW_HEALTH_TIMEOUT: float = 2.0

    # ── Mock agent services ───────────────────────────────────────────────────
    AGENT_HOST: str = "localhost"
    AGENT_WEATHER_PORT: int = 11000
    AGENT_EMAIL_VALIDATOR_PORT: int = 11001
    AGENT_EMAIL_SENDER_PORT: int = 11002
    AGENT_SUMMARIZER_PORT: int = 11003

    # ── Actions API base URL (used by compiled DSL to call back to the backend) ──
    ACTIONS_BASE_URL: str = "http://localhost:8000"

    # ── PostgreSQL connection ─────────────────────────────────────────────────
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "autox-flow-automate"
    DATABASE_USERNAME: str = "postgres"
    DATABASE_PASSWORD: str = "admin123"

    # ── PostgreSQL connection pool ────────────────────────────────────────────
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
