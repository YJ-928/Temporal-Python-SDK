"""
Router registry — add_router(app) registers all APIRouter instances.
Only this file needs to change when a new router is added.
"""
from fastapi import FastAPI
from .workflow_router import router as workflow_router
from .execution_router import router as execution_router
from .health_router import router as health_router
from .catalog_router import router as catalog_router


def add_router(app: FastAPI, prefix: str = "/api/v1") -> None:
    app.include_router(workflow_router, prefix=prefix)
    app.include_router(execution_router, prefix=prefix)
    app.include_router(health_router, prefix=prefix)
    app.include_router(catalog_router, prefix=prefix)
