"""
Activity Helpers

Convenience functions for building retry policies and Activity options.

Usage:
    from utils.activity_helpers import default_retry_policy, activity_options
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from temporalio.common import RetryPolicy


def default_retry_policy(
    max_attempts: int = 3,
    initial_interval_seconds: int = 1,
    backoff_coefficient: float = 2.0,
    max_interval_seconds: int = 30,
) -> RetryPolicy:
    """Return a :class:`RetryPolicy` with sensible defaults.

    Args:
        max_attempts: Maximum number of attempts (including the initial one).
        initial_interval_seconds: First retry interval.
        backoff_coefficient: Multiplier applied to the interval after each retry.
        max_interval_seconds: Cap on the retry interval.

    Returns:
        A configured :class:`RetryPolicy`.
    """
    return RetryPolicy(
        maximum_attempts=max_attempts,
        initial_interval=timedelta(seconds=initial_interval_seconds),
        backoff_coefficient=backoff_coefficient,
        maximum_interval=timedelta(seconds=max_interval_seconds),
    )


def activity_options(
    start_to_close_timeout_seconds: int = 10,
    retry_policy: RetryPolicy | None = None,
) -> Dict[str, Any]:
    """Return a dict suitable for unpacking into ``execute_activity`` kwargs.

    Example::

        result = await workflow.execute_activity(
            my_activity,
            arg,
            **activity_options(start_to_close_timeout_seconds=30),
        )
    """
    opts: Dict[str, Any] = {
        "start_to_close_timeout": timedelta(seconds=start_to_close_timeout_seconds),
    }
    if retry_policy is not None:
        opts["retry_policy"] = retry_policy
    return opts
