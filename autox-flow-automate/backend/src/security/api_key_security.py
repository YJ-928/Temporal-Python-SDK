"""
API key security dependency — stub, ready for wiring when auth is added.
"""
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Placeholder — returns None (no auth) until API_KEY env var is set."""
    from src.config.settings import settings
    expected = getattr(settings, "API_KEY", None)
    if expected and api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
