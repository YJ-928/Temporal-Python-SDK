"""
Greeting Workflow — Activity Definition

A simple Activity that composes a greeting string.
"""

from temporalio import activity


@activity.defn
async def greet(name: str) -> str:
    """Return a greeting for the given name."""
    activity.logger.info(f"Composing greeting for {name}")
    return f"Hello, {name}! Welcome to Temporal."
