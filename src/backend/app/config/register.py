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
    from ..api.v1.health_routes import router as health_router
    from ..api.v1.catalog_routes import router as catalog_router

    _v1 = settings.API_V1_PREFIX
    app.include_router(workflow_router, prefix=_v1)
    app.include_router(execution_router, prefix=_v1)
    app.include_router(health_router, prefix=_v1)
    app.include_router(catalog_router, prefix=_v1)

    @app.get(
        f"{_v1}/actions",
        tags=["Actions"],
        summary="List available mock operations",
        description=(
            "Returns all valid operation identifiers that can be used as the `{operation}` "
            "path parameter in `POST /api/v1/actions/{operation}`. "
            "Use this to discover which operations are available when configuring an ACTION node."
        ),
    )
    async def list_actions():
        from ..api.v1.catalog_routes import MOCK_OPERATIONS
        return MOCK_OPERATIONS

    @app.post(f"{_v1}/actions/{{operation}}", tags=["Actions"])
    async def mock_action(operation: str, request: Request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        logger.info(f"Mock action '{operation}' invoked with body: {body}")

        if operation == "send_email":
            return {
                "status": "success",
                "message_id": "abc123"
            }
        elif operation == "account_lookup":
            acct_id = body.get("account_id")
            if acct_id == "active-123":
                return {
                    "active": True,
                    "type": "support"
                }
            else:
                return {
                    "active": False
                }
        elif operation == "assign_support_case":
            return {
                "status": "success",
                "case_id": "case-support-999"
            }
        elif operation == "assign_billing_case":
            return {
                "status": "success",
                "case_id": "case-billing-888"
            }

        return {
            "status": "success",
            "operation": operation,
            "city": body.get("city"),
            "message": f"Action {operation} executed successfully for {body.get('city')}"
        }

    @app.get(
        f"{_v1}/agents",
        tags=["Agents"],
        summary="List registered agents",
        description=(
            "Returns all agents registered in AgentRegistry. "
            "Use this to discover which agents are available when configuring an AGENT node. "
            "Each agent entry includes its ID, execute URL, expected inputs, and outputs."
        ),
    )
    async def list_agents():
        from ..agents.registry import AgentRegistry

        def _display_name(agent_id: str) -> str:
            return agent_id.replace("-", " ").title()

        return [
            {
                "id": agent_id,
                "name": _display_name(agent_id),
                "url": meta.get("url", ""),
                "method": meta.get("method", "POST"),
                "port": meta.get("port"),
                "description": meta.get("description", ""),
                "request_schema": meta.get("request_schema", {}),
                "response_schema": meta.get("response_schema", {}),
            }
            for agent_id, meta in AgentRegistry._agents.items()
        ]

    logger.info("Routers registered")


def register_events(app: FastAPI) -> None:
    """
    Register startup and shutdown events.

    Args:
        app: FastAPI application instance
    """

    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")

        # Verify zigflow CLI is installed on PATH
        import shutil
        import asyncio
        if not shutil.which("zigflow"):
            logger.critical("❌ zigflow command-line tool is not installed or not found on PATH.")
            raise RuntimeError("zigflow CLI tool not found on PATH. Please install zigflow before starting the application.")

        try:
            proc = await asyncio.create_subprocess_exec(
                "zigflow", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            logger.info(f"✓ zigflow CLI version: {stdout.decode().strip() or 'unknown'}")
        except Exception as e:
            logger.warning(f"Unable to determine zigflow version: {e}")

        # Sync pre-existing compiled workflows
        from ..services.registration_service import registration_service
        try:
            await registration_service.sync_pre_existing()
            logger.info("✓ Sync of pre-existing compiled workflows complete")
        except Exception as e:
            logger.error(f"Failed to sync compiled workflows on startup: {e}")

    @app.on_event("shutdown")
    async def shutdown_event():
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
