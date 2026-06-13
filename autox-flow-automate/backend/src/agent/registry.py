"""
Agent Registry

Single source of truth for all agent services in the system.
This registry defines all available agents, their endpoints, and metadata.

CRITICAL: This is METADATA ONLY.
- NO lifecycle management (start/stop agents)
- NO health checks
- NO port management
- Pure lookup: agent_id → metadata dict

Usage:
    from src.agent.registry import AgentRegistry

    # Get agent metadata
    agent = AgentRegistry.get_agent("weather-agent")
    url = AgentRegistry.get_url("weather-agent")

    # Check existence
    if AgentRegistry.has_agent("weather-agent"):
        ...

    # List all agents
    agents = AgentRegistry.list_agents()
"""
from typing import Dict, Optional


class AgentRegistry:
    """
    Static metadata lookup table for agent services.

    CRITICAL: This is METADATA ONLY.
    - NO lifecycle management (start/stop agents)
    - NO health checks
    - NO port management
    - Pure lookup: agent_id → metadata dict

    IMPORTANT: All methods are class methods.
    Registry is configuration, not state.
    No instance creation needed.
    """

    _agents: Dict[str, Dict[str, any]] = {
        "weather-agent": {
            "url": "http://localhost:11000/execute",
            "method": "POST",
            "port": 11000,
            "description": "Weather lookup service for cities worldwide",
            "request_schema": {
                "city": "string"
            },
            "response_schema": {
                "success": "boolean",
                "city": "string",
                "temperature": "integer",
                "condition": "string"
            }
        },
        "email-validator-agent": {
            "url": "http://localhost:11001/execute",
            "method": "POST",
            "port": 11001,
            "description": "Email validation service using regex patterns",
            "request_schema": {
                "email": "string"
            },
            "response_schema": {
                "success": "boolean",
                "is_valid": "boolean",
                "domain": "string"
            }
        },
        "email-sender-agent": {
            "url": "http://localhost:11002/execute",
            "method": "POST",
            "port": 11002,
            "description": "Mock email sending service with JSON persistence",
            "request_schema": {
                "to": "string",
                "subject": "string",
                "body": "string"
            },
            "response_schema": {
                "success": "boolean",
                "message_id": "string"
            }
        },
        "summarizer-agent": {
            "url": "http://localhost:11003/execute",
            "method": "POST",
            "port": 11003,
            "description": "Mock summarizing service",
            "request_schema": {
                "text": "string"
            },
            "response_schema": {
                "summary": "string"
            }
        }
    }

    @classmethod
    def get_agent(cls, agent_id: str) -> Optional[Dict]:
        """
        Get agent metadata by ID.

        Args:
            agent_id: Agent identifier (e.g., "weather-agent")

        Returns:
            Agent metadata dict if found, None otherwise
        """
        return cls._agents.get(agent_id)

    @classmethod
    def get_url(cls, agent_id: str) -> Optional[str]:
        """
        Get the execution URL for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent URL if found, None otherwise
        """
        agent = cls._agents.get(agent_id)
        return agent["url"] if agent else None

    @classmethod
    def register_agent(cls, agent_id: str, metadata: Dict) -> None:
        """
        Register new agent metadata.

        Args:
            agent_id: Agent identifier
            metadata: Agent metadata dict
        """
        cls._agents[agent_id] = metadata

    @classmethod
    def list_agents(cls) -> list[str]:
        """
        List all registered agent IDs.

        Returns:
            List of agent identifiers
        """
        return list(cls._agents.keys())

    @classmethod
    def has_agent(cls, agent_id: str) -> bool:
        """
        Check if agent is registered.

        Args:
            agent_id: Agent identifier

        Returns:
            True if agent exists, False otherwise
        """
        return agent_id in cls._agents


# ============================================================================
# Backward Compatibility Functions
# These functions provide backward compatibility with existing code.
# New code should use AgentRegistry class methods directly.
# ============================================================================

def get_agent_url(agent_name: str) -> Optional[str]:
    """
    DEPRECATED: Use AgentRegistry.get_url() instead.

    Get the execution URL for a specific agent.

    Args:
        agent_name: Name of the agent (e.g., "weather-agent")

    Returns:
        Agent URL if found, None otherwise
    """
    return AgentRegistry.get_url(agent_name)


def get_agent_info(agent_name: str) -> Optional[Dict]:
    """
    DEPRECATED: Use AgentRegistry.get_agent() instead.

    Get full information for a specific agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Agent info dict if found, None otherwise
    """
    return AgentRegistry.get_agent(agent_name)


def list_agents() -> list[str]:
    """
    DEPRECATED: Use AgentRegistry.list_agents() instead.

    Get list of all registered agent names.

    Returns:
        List of agent identifiers
    """
    return AgentRegistry.list_agents()


def is_agent_registered(agent_name: str) -> bool:
    """
    DEPRECATED: Use AgentRegistry.has_agent() instead.

    Check if an agent is registered.

    Args:
        agent_name: Agent identifier

    Returns:
        True if agent exists, False otherwise
    """
    return AgentRegistry.has_agent(agent_name)


# Legacy constant for backward compatibility
AGENT_REGISTRY = AgentRegistry._agents
