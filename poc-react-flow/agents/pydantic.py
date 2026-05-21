"""
Pydantic AI agents: intent parsing, hotel recommendations, and restaurant recommendations.
"""

from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent

# Default model for all agents (override per agent if needed)
_DEFAULT_MODEL = "openai:gpt-4o-mini"


# --- Output models ---

class IntentOutput(BaseModel):
    """Output of the intent parsing agent: { "type": "HOTEL" | "RESTAURANT" | "OTHER" }."""
    type: Literal["HOTEL", "RESTAURANT", "OTHER"]


class TextResponseOutput(BaseModel):
    """Output for recommendation agents: { "text": "<AI generated answer>" }."""
    text: str


# --- 1. Intent parsing agent ---
# Input: user query (string). Output: { "type": "HOTEL" | "RESTAURANT" | "OTHER" }

intent_agent = Agent(
    _DEFAULT_MODEL,
    output_type=IntentOutput,
    name="intent_parsing_agent",
    system_prompt=(
        "You are an intent classifier. Given a user message, classify it into exactly one of: HOTEL, RESTAURANT, or OTHER. "
        "HOTEL = the user is asking about hotels, accommodation, or places to stay. "
        "RESTAURANT = the user is asking about restaurants, food, or places to eat. "
        "OTHER = anything else. Respond only with valid JSON in the form {\"type\": \"HOTEL\"} or {\"type\": \"RESTAURANT\"} or {\"type\": \"OTHER\"}."
    ),
)


# --- 2. Hotel recommendation expert ---
# Input: user query (string). Output: { "text": "<AI generated answer>" }

hotel_agent = Agent(
    _DEFAULT_MODEL,
    output_type=TextResponseOutput,
    name="hotel_recommendation_agent",
    system_prompt=(
        "You are a hotel recommendation expert. Answer the user's question about hotels, accommodation, or places to stay. "
        "Provide helpful, relevant recommendations and information. "
        "Respond with valid JSON in the form {\"text\": \"your answer here\"}."
    ),
)


# --- 3. Restaurant recommendation expert ---
# Input: user query (string). Output: { "text": "<AI generated answer>" }

restaurant_agent = Agent(
    _DEFAULT_MODEL,
    output_type=TextResponseOutput,
    name="restaurant_recommendation_agent",
    system_prompt=(
        "You are a restaurant recommendation expert. Answer the user's question about restaurants, food, or places to eat. "
        "Provide helpful, relevant recommendations and information. "
        "Respond with valid JSON in the form {\"text\": \"your answer here\"}."
    ),
)


# --- Convenience async runners (input: string, output: Pydantic model) ---

async def parse_intent(user_query: str) -> IntentOutput:
    """Parse user query and return intent type: HOTEL, RESTAURANT, or OTHER."""
    result = await intent_agent.run(user_query)
    return result.output


async def get_hotel_recommendation(user_query: str) -> TextResponseOutput:
    """Get hotel recommendations for the user query."""
    result = await hotel_agent.run(user_query)
    return result.output


async def get_restaurant_recommendation(user_query: str) -> TextResponseOutput:
    """Get restaurant recommendations for the user query."""
    result = await restaurant_agent.run(user_query)
    return result.output
