"""
Translation Workflow — Workflow Definition

Workflow that translates a greeting and a farewell using a class-based
Activity. Includes a durable timer between the two translations to
demonstrate Temporal's timer durability.
"""

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from translate_activity import TranslateActivities

TASK_QUEUE = "translation-tasks"


@dataclass
class TranslationInput:
    name: str
    language_code: str


@workflow.defn
class TranslationWorkflow:
    """Translate a greeting and farewell for the given name."""

    @workflow.run
    async def run(self, input: TranslationInput) -> str:
        greeting = await workflow.execute_activity_method(
            TranslateActivities.translate_greeting,
            input,
            start_to_close_timeout=timedelta(seconds=10),
        )
        workflow.logger.info(f"Translated greeting: {greeting}")

        # Durable timer — survives Worker restarts
        workflow.logger.info("Waiting 5 seconds before farewell translation...")
        await asyncio.sleep(5)

        farewell = await workflow.execute_activity_method(
            TranslateActivities.translate_farewell,
            input,
            start_to_close_timeout=timedelta(seconds=10),
        )
        workflow.logger.info(f"Translated farewell: {farewell}")

        return f"{greeting} ... {farewell}"
