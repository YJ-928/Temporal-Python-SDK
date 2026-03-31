"""
Temporal Client Helper

Reusable factory for creating a Temporal Client, reading host and namespace
from environment variables (or falling back to sensible defaults).

Usage:
    from utils.temporal_client import get_client
    client = await get_client()
"""

import os

from temporalio.client import Client


async def get_client(
    host: str | None = None,
    namespace: str | None = None,
) -> Client:
    """Connect to the Temporal server.

    Args:
        host: Temporal frontend address (default: ``TEMPORAL_HOST`` env var
              or ``localhost:7233``).
        namespace: Temporal namespace (default: ``TEMPORAL_NAMESPACE`` env var
              or ``default``).

    Returns:
        A connected :class:`temporalio.client.Client`.
    """
    host = host or os.environ.get("TEMPORAL_HOST", "localhost:7233")
    namespace = namespace or os.environ.get("TEMPORAL_NAMESPACE", "default")
    return await Client.connect(host, namespace=namespace)
