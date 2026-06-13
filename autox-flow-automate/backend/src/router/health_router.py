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


@router.get("/temporal")
async def check_temporal_health():
    """Check health of the Temporal server."""
    try:
        await Client.connect(settings.TEMPORAL_ADDRESS)
        return {"healthy": True}
    except Exception as e:
        logger.warning(f"Temporal health check failed: {e}")
        return {"healthy": False, "detail": str(e)}


@router.get("/runtime")
async def check_runtime_health():
    """Check health of the Zigflow runtime daemon and registrations count."""
    res = await asyncio.to_thread(_http_get_json, "http://localhost:3005/health", 2)
    if res is None:
        logger.warning("Zigflow runtime health check failed")
        zigflow_ok = False
    else:
        zigflow_ok = res.get("healthy", False)

    regs = registration_service.get_all_registrations()
    registered_count = len([k for k, v in regs.items() if v.get("registered")])

    return {
        "zigflow": zigflow_ok,
        "registered_workflows": registered_count
    }


@router.get("/system")
async def check_system_health():
    """Aggregate health status of all systems."""
    # Check Temporal
    temporal_ok = False
    try:
        await Client.connect(settings.TEMPORAL_ADDRESS)
        temporal_ok = True
    except Exception:  # noqa: S110
        pass

    # Check Runtime
    res = await asyncio.to_thread(_http_get_json, "http://localhost:3005/health", 1)
    runtime_ok = res.get("healthy", False) if res else False

    # Check Agents individually
    agent_health = {}
    ports = {
        "weather_agent": 11000,
        "email_validator": 11001,
        "email_sender": 11002,
    }
    for name, port in ports.items():
        ok = await asyncio.to_thread(_http_check_ok, f"http://localhost:{port}/docs", 1)
        agent_health[name] = ok

    return {
        "temporal": temporal_ok,
        "backend": True,
        "runtime": runtime_ok,
        "weather_agent": agent_health["weather_agent"],
        "email_validator": agent_health["email_validator"],
        "email_sender": agent_health["email_sender"],
    }
