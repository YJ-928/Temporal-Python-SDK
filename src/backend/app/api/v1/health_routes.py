"""
Health check routes.
"""
import urllib.request
import json
from fastapi import APIRouter, HTTPException, status
from temporalio.client import Client
from ...config import settings, get_logger
from ...services.registration_service import registration_service

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/temporal")
async def check_temporal_health():
    """Check health of the Temporal server."""
    try:
        client = await Client.connect(settings.TEMPORAL_ADDRESS)
        # Verify connection by attempting to list namespaces (lightweight)
        # If connect works, we are healthy
        return {"healthy": True}
    except Exception as e:
        logger.warning(f"Temporal health check failed: {e}")
        return {"healthy": False, "detail": str(e)}


@router.get("/runtime")
async def check_runtime_health():
    """Check health of the Zigflow runtime daemon and registrations count."""
    zigflow_ok = False
    try:
        req = urllib.request.Request("http://localhost:3005/health")
        with urllib.request.urlopen(req, timeout=2) as r:
            res = json.loads(r.read())
            zigflow_ok = res.get("healthy", False)
    except Exception as e:
        logger.warning(f"Zigflow runtime health check failed: {e}")

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
    except Exception:
        pass

    # Check Agents (Weather, Validator, Sender)
    agents_ok = True
    for port in [11000, 11001, 11002]:
        try:
            req = urllib.request.Request(f"http://localhost:{port}/docs")
            with urllib.request.urlopen(req, timeout=1) as r:
                if r.status != 200:
                    agents_ok = False
        except Exception:
            agents_ok = False

    # Check Runtime
    runtime_ok = False
    try:
        req = urllib.request.Request("http://localhost:3005/health")
        with urllib.request.urlopen(req, timeout=1) as r:
            res = json.loads(r.read())
            runtime_ok = res.get("healthy", False)
    except Exception:
        pass

    return {
        "temporal": temporal_ok,
        "backend": True,
        "agents": agents_ok,
        "runtime": runtime_ok
    }
