"""FastAPI application — Zigflow Execution Orchestrator."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.utils.config import get_settings
from app.utils.logging import setup_logging

settings = get_settings()
setup_logging(settings.LOG_LEVEL)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    logger.info(
        "Starting Zigflow Execution Orchestrator",
        extra={"temporal_host": settings.TEMPORAL_HOST, "task_queue": settings.TASK_QUEUE},
    )
    yield
    logger.info("Shutting down Zigflow Execution Orchestrator")


app = FastAPI(
    title="Zigflow Execution Orchestrator",
    description=(
        "Distributed workflow execution platform.\n\n"
        "**Architecture:** Temporal (orchestration) → FastAPI (execution trigger) "
        "→ ephemeral Docker containers (isolated Zigflow runtime)."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1", tags=["execution"])


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "service": "Zigflow Execution Orchestrator",
        "version": "1.0.0",
        "docs": "/docs",
    }
