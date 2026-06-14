"""
Agent Registry

Single source of truth for all agent services in the system.
Agent URLs and ports are loaded from settings so they can be overridden via .env.

CRITICAL: This is METADATA ONLY.
- NO lifecycle management (start/stop agents)
- NO health checks
- NO port management
- Pure lookup: agent_id → metadata dict
"""
from typing import Dict, Optional


def _build_agents() -> Dict[str, Dict]:
    """Build agent metadata dict from settings — called lazily so settings are ready."""
    from ..config.settings import settings
    host = settings.AGENT_HOST

    def _url(port: int) -> str:
        return f"http://{host}:{port}/execute"

    return {
        "weather-agent": {
            "url": _url(settings.AGENT_WEATHER_PORT),
            "method": "POST",
            "port": settings.AGENT_WEATHER_PORT,
            "description": "Weather lookup service for cities worldwide",
            "request_schema": {"city": "string"},
            "response_schema": {
                "success": "boolean",
                "city": "string",
                "temperature": "integer",
                "condition": "string",
            },
        },
        "email-validator-agent": {
            "url": _url(settings.AGENT_EMAIL_VALIDATOR_PORT),
            "method": "POST",
            "port": settings.AGENT_EMAIL_VALIDATOR_PORT,
            "description": "Email validation service using regex patterns",
            "request_schema": {"email": "string"},
            "response_schema": {
                "success": "boolean",
                "is_valid": "boolean",
                "domain": "string",
            },
        },
        "email-sender-agent": {
            "url": _url(settings.AGENT_EMAIL_SENDER_PORT),
            "method": "POST",
            "port": settings.AGENT_EMAIL_SENDER_PORT,
            "description": "Mock email sending service with JSON persistence",
            "request_schema": {"to": "string", "subject": "string", "body": "string"},
            "response_schema": {"success": "boolean", "message_id": "string"},
        },
        "summarizer-agent": {
            "url": _url(settings.AGENT_SUMMARIZER_PORT),
            "method": "POST",
            "port": settings.AGENT_SUMMARIZER_PORT,
            "description": "Mock summarizing service",
            "request_schema": {"text": "string"},
            "response_schema": {"summary": "string"},
        },
    }


class AgentRegistry:
    """
    Metadata lookup table for agent services.
    URLs and ports are sourced from settings, never hardcoded here.
    All methods rebuild from settings on each call — fast (no I/O, just dict construction).
    """

    @classmethod
    def _agents_dict(cls) -> Dict[str, Dict]:
        return _build_agents()

    # _agents exposed as a class-level property via __class_getitem__ is not
    # native Python — callers that need the full dict should use _agents_dict().
    # register.py iterates via this helper.
    @classmethod
    def all_agents(cls) -> Dict[str, Dict]:
        return _build_agents()

    @classmethod
    def get_agent(cls, agent_id: str) -> Optional[Dict]:
        return _build_agents().get(agent_id)

    @classmethod
    def get_url(cls, agent_id: str) -> Optional[str]:
        agent = _build_agents().get(agent_id)
        return agent["url"] if agent else None

    @classmethod
    def register_agent(cls, agent_id: str, metadata: Dict) -> None:
        _build_agents()[agent_id] = metadata

    @classmethod
    def list_agents(cls) -> list[str]:
        return list(_build_agents().keys())

    @classmethod
    def has_agent(cls, agent_id: str) -> bool:
        return agent_id in _build_agents()


# ── Backward compat functions ─────────────────────────────────────────────────
def get_agent_url(agent_name: str) -> Optional[str]:
    return AgentRegistry.get_url(agent_name)

def get_agent_info(agent_name: str) -> Optional[Dict]:
    return AgentRegistry.get_agent(agent_name)

def list_agents() -> list[str]:
    return AgentRegistry.list_agents()

def is_agent_registered(agent_name: str) -> bool:
    return AgentRegistry.has_agent(agent_name)
