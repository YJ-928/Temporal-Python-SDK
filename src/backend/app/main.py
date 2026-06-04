"""
FastAPI application entry point.
"""
from .config.register import register_app
from .config.settings import settings


app = register_app()


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.

    Returns:
        Service identifier
    """
    return {"message": settings.APP_NAME, "version": settings.VERSION}


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
    }

