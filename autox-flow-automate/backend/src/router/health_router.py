"""
Health check routes.
"""
import asyncio
import urllib.request
import json
from fastapi import APIRouter
from temporalio.client import Client
from ..config import settings, get_logger
from ..service.registration_service import registration_service

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


def _zigflow_base_url() -> str:
    return f"http://{settings.ZIGFLOW_RUNTIME_HOST}:{settings.ZIGFLOW_RUNTIME_PORT}"


def _http_get_json(url: str, timeout: int) -> dict | None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:  # noqa: S310
            return json.loads(r.read())
    except Exception:
        return None


def _http_check_ok(url: str, timeout: int) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:  # noqa: S310
            return r.status == 200
    except Exception:
        return False


async def _check_temporal_connection() -> bool:
    """Open a probe connection to Temporal and close it immediately — no leak."""
    client = None
    try:
        client = await asyncio.wait_for(
            Client.connect(settings.TEMPORAL_ADDRESS),
            timeout=settings.TEMPORAL_HEALTH_TIMEOUT,
        )
        return True
    except Exception as exc:
        logger.warning(f"Temporal health check failed: {exc}")
        return False
    finally:
        if client is not None:
            try:
                await client.close()
            except Exception:
                pass


@router.get("/temporal")
async def check_temporal_health():
    """Check health of the Temporal server."""
    healthy = await _check_temporal_connection()
    if healthy:
        return {"healthy": True}
    return {"healthy": False, "detail": "Cannot reach Temporal server"}


@router.get("/runtime")
async def check_runtime_health():
    """Check health of the Zigflow runtime daemon and registrations count."""
    res = await asyncio.to_thread(
        _http_get_json, f"{_zigflow_base_url()}/health", 2
    )
    if res is None:
        logger.warning("Zigflow runtime health check failed")
        zigflow_ok = False
    else:
        zigflow_ok = res.get("healthy", False)

    regs = registration_service.get_all_registrations()
    registered_count = len([k for k, v in regs.items() if v.get("registered")])

    return {
        "zigflow": zigflow_ok,
        "registered_workflows": registered_count,
    }


@router.get("/system")
async def check_system_health():
    """Aggregate health status of all systems."""
    zigflow_url = _zigflow_base_url()
    temporal_ok, res, agent_results = await asyncio.gather(
        _check_temporal_connection(),
        asyncio.to_thread(_http_get_json, f"{zigflow_url}/health", 1),
        _check_all_agents(),
    )

    runtime_ok = res.get("healthy", False) if res else False

    return {
        "temporal": temporal_ok,
        "backend": True,
        "runtime": runtime_ok,
        **agent_results,
    }


async def _check_all_agents() -> dict:
    """Check all mock agent endpoints concurrently — ports from settings."""
    ports = {
        "weather_agent": settings.AGENT_WEATHER_PORT,
        "email_validator": settings.AGENT_EMAIL_VALIDATOR_PORT,
        "email_sender": settings.AGENT_EMAIL_SENDER_PORT,
        "summarizer_agent": settings.AGENT_SUMMARIZER_PORT,
    }
    host = settings.AGENT_HOST
    results = await asyncio.gather(*(
        asyncio.to_thread(_http_check_ok, f"http://{host}:{port}/docs", 1)
        for port in ports.values()
    ))
    return dict(zip(ports.keys(), results))
