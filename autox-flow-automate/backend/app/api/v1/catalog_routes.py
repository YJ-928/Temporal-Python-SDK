from fastapi import APIRouter
from ...agents.registry import AgentRegistry

router = APIRouter(prefix="/catalog", tags=["Catalog"])


def _display_name(agent_id: str) -> str:
    return agent_id.replace("-", " ").title()


# Mock operations handled by POST /api/v1/actions/{operation}.
# These are the valid values for the ACTION node's "operation" field.
# Each operation is dispatched by the mock_action handler in register.py.
MOCK_OPERATIONS = [
    {
        "id": "send_rain_alert",
        "name": "Send Rain Alert",
        "description": "Sends a rain alert notification. Used by weather-assistant workflow.",
    },
    {
        "id": "send_weather_summary",
        "name": "Send Weather Summary",
        "description": "Sends a weather summary notification. Used by weather-assistant workflow.",
    },
    {
        "id": "send_email",
        "name": "Send Email",
        "description": "Sends an email via mock email service.",
    },
    {
        "id": "noop",
        "name": "No-Op",
        "description": "No operation — passes through without side effects.",
    },
    {
        "id": "account_lookup",
        "name": "Account Lookup",
        "description": "Looks up account status by account_id. Used by account-routing workflow.",
    },
    {
        "id": "assign_support_case",
        "name": "Assign Support Case",
        "description": "Assigns a support case for an account.",
    },
    {
        "id": "assign_billing_case",
        "name": "Assign Billing Case",
        "description": "Assigns a billing case for an account.",
    },
    {
        "id": "fetch_info",
        "name": "Fetch Info",
        "description": "Generic info fetch operation.",
    },
]


@router.get("/agents", summary="List registered agents for the AGENT node dropdown")
async def get_catalog_agents():
    """
    Returns all agents registered in AgentRegistry.
    The AGENT node uses the id to look up the execute URL at compile time.
    """
    return [
        {
            "id": agent_id,
            "name": _display_name(agent_id),
            "url": meta.get("url", ""),
            "description": meta.get("description", ""),
            "request_schema": meta.get("request_schema", {}),
        }
        for agent_id, meta in AgentRegistry._agents.items()
    ]


@router.get("/operations", summary="List available mock operations for the ACTION node dropdown")
async def get_catalog_operations():
    """
    Returns the valid operation identifiers for the ACTION node.
    These map to handlers in POST /api/v1/actions/{operation}.
    The ACTION node stores the operation id (e.g. 'send_email'), NOT a URL.
    """
    return MOCK_OPERATIONS
