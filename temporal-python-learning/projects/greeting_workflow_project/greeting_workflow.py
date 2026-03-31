"""
Greeting Workflow — Workflow Definition

A simple Workflow that accepts a name, calls a greeting Activity, and returns
the result. Demonstrates the fundamental Workflow → Activity pattern.
"""

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from greet_activity import greet


TASK_QUEUE = "greeting-tasks"


@workflow.defn
class GreetingWorkflow:
    """Workflow that greets a person by name."""

    @workflow.run
    async def run(self, name: str) -> str:
        greeting = await workflow.execute_activity(
            greet,
            name,
            start_to_close_timeout=timedelta(seconds=10),
        )
        workflow.logger.info(f"Greeting composed: {greeting}")
        return greeting
