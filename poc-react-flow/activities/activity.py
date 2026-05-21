"""
Temporal activities for executing agents by name.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from temporalio import activity

from agents.pydantic import (
    get_hotel_recommendation,
    get_restaurant_recommendation,
    parse_intent,
)

# Supported agent names (use these when calling the activity)
AGENT_INTENT = "intent"
AGENT_HOTEL = "hotel"
AGENT_RESTAURANT = "restaurant"

# Registry: agent_name -> async (user_query) -> Pydantic model with .model_dump()
AgentRunner = Callable[[str], Awaitable[Any]]

AGENT_REGISTRY: dict[str, AgentRunner] = {
    AGENT_INTENT: parse_intent,
    AGENT_HOTEL: get_hotel_recommendation,
    AGENT_RESTAURANT: get_restaurant_recommendation,
}


@activity.defn(name="activity.execute_agent")
async def execute_agent(user_query: str, agent_name: str) -> dict:
    """
    Execute an agent by name with the given user query.

    Args:
        user_query: The user's question or request.
        agent_name: One of "intent", "hotel", or "restaurant".

    Returns:
        For "intent": {"type": "HOTEL" | "RESTAURANT" | "OTHER"}.
        For "hotel" / "restaurant": {"text": "<AI generated answer>"}.

    Raises:
        ValueError: If agent_name is not supported.
    """
    key = agent_name.strip().lower()
    runner = AGENT_REGISTRY.get(key)
    if runner is None:
        raise ValueError(
            f"Unknown agent_name: {agent_name!r}. "
            f"Use one of: {list(AGENT_REGISTRY.keys())}"
        )
    result = await runner(user_query)
    return result.model_dump()


@activity.defn(name="activity.say_hello")
def say_hello(name: str) -> str:
    """Legacy activity; kept if workflows depend on it."""
    return f"Hello, {name}!"
