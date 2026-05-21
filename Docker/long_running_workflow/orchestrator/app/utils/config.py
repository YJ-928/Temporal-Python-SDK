"""Application configuration using Pydantic Settings v2."""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Temporal ─────────────────────────────────────────────────────────────
    TEMPORAL_HOST: str = "temporal:7233"
    TEMPORAL_NAMESPACE: str = "default"
    TASK_QUEUE: str = "orchestrator-queue"

    # ── FastAPI Orchestrator ──────────────────────────────────────────────────
    ORCHESTRATOR_API_HOST: str = "0.0.0.0"
    ORCHESTRATOR_API_PORT: int = 8000
    # URL that the Temporal worker uses to reach the FastAPI service
    ORCHESTRATOR_API_URL: str = "http://orchestrator:8000"

    # ── Workflow paths ────────────────────────────────────────────────────────
    WORKFLOWS_DIR: str = "/app/workflows/json"

    # ── Docker execution ──────────────────────────────────────────────────────
    RUNNER_IMAGE: str = "zigflow-runner:latest"
    # Docker network shared by all containers so they can reach Temporal
    DOCKER_NETWORK: str = "temporal-network"
    # Temporal address visible *inside* runner containers (Docker service name)
    DOCKER_TEMPORAL_HOST: str = "temporal:7233"

    # ── Execution limits ──────────────────────────────────────────────────────
    EXECUTION_TIMEOUT_SECONDS: int = 3600  # 1 hour per container
    # After this many executions, the parent workflow calls continue_as_new
    MAX_EXECUTIONS_BEFORE_CAN: int = 50

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "case_sensitive": True}


@lru_cache
def get_settings() -> Settings:
    return Settings()
