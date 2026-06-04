"""
FastAPI application registration and configuration.
"""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from .settings import settings
from .logger import get_logger


logger = get_logger(__name__)


def register_middleware(app: FastAPI) -> None:
    """
    Register middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )
    logger.info("Middleware registered")


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers.

    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "Validation error",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError):
        logger.warning(f"Pydantic validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "Validation error",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.error(f"ValueError: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "message": str(exc),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Internal server error",
                "detail": str(exc) if settings.DEBUG else None,
            },
        )

    logger.info("Exception handlers registered")


def register_routers(app: FastAPI) -> None:
    """
    Register API routers.

    Args:
        app: FastAPI application instance
    """
    from ..api.v1.workflow_routes import router as workflow_router
    from ..api.v1.execution_routes import router as execution_router

    app.include_router(workflow_router, prefix="/api/v1")
    app.include_router(execution_router, prefix="/api/v1")
    logger.info("Routers registered")


def register_events(app: FastAPI) -> None:
    """
    Register startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    from .database import close_db

    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
        
        # Verify zigflow CLI is installed on PATH
        import shutil
        import subprocess
        if not shutil.which("zigflow"):
            logger.critical("❌ zigflow command-line tool is not installed or not found on PATH.")
            raise RuntimeError("zigflow CLI tool not found on PATH. Please install zigflow before starting the application.")
        
        try:
            res = subprocess.run(["zigflow", "--version"], capture_output=True, text=True, check=True)
            logger.info(f"✓ zigflow CLI version: {res.stdout.strip() or 'unknown'}")
        except Exception as e:
            logger.warning(f"Unable to determine zigflow version: {e}")

        if settings.DATABASE_URL:
            logger.info("Database configured and ready")

    @app.on_event("shutdown")
    async def shutdown_event():
        await close_db()
        logger.info(f"Shutting down {settings.APP_NAME}")

    logger.info("Events registered")


def register_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description=settings.APP_DESCRIPTION,
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    register_middleware(app)
    register_exception_handlers(app)
    register_routers(app)
    register_events(app)

    logger.info("Application registered successfully")
    return app
