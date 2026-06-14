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


async def _check_temporal_connection() -> bool:
    """Open a probe connection to Temporal and close it immediately — no leak."""
    client = None
    try:
        client = await asyncio.wait_for(
            Client.connect(settings.TEMPORAL_ADDRESS), timeout=3.0
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
    temporal_ok, res, agent_results = await asyncio.gather(
        _check_temporal_connection(),
        asyncio.to_thread(_http_get_json, "http://localhost:3005/health", 1),
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
    """Check all mock agent endpoints concurrently."""
    ports = {
        "weather_agent": 11000,
        "email_validator": 11001,
        "email_sender": 11002,
        "summarizer_agent": 11003,
    }
    results = await asyncio.gather(*(
        asyncio.to_thread(_http_check_ok, f"http://localhost:{port}/docs", 1)
        for port in ports.values()
    ))
    return dict(zip(ports.keys(), results))
