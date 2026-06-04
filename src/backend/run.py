"""
Uvicorn server runner.

Usage:
    python run.py
    python run.py --port 8001
    python run.py --reload
"""
import argparse
import uvicorn


def main():
    """Run the FastAPI application with uvicorn."""
    from app.config import settings

    parser = argparse.ArgumentParser(description="Workflow Compiler Service")
    parser.add_argument(
        "--host",
        type=str,
        default=settings.API_HOST,
        help=f"Host to bind (default: {settings.API_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.API_PORT,
        help=f"Port to bind (default: {settings.API_PORT})",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=settings.LOG_LEVEL.lower(),
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help=f"Log level (default: {settings.LOG_LEVEL.lower()})",
    )

    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
