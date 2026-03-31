"""
Translation Workflow — Starter

Usage:
    python starter.py
    python starter.py Alice es
"""

import asyncio
import sys

from temporalio.client import Client

from translation_workflow import TranslationInput, TranslationWorkflow, TASK_QUEUE


async def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    lang = sys.argv[2] if len(sys.argv) > 2 else "es"

    client = await Client.connect("localhost:7233")

    input_data = TranslationInput(name=name, language_code=lang)
    print(f"Starting TranslationWorkflow for {name} (lang={lang})")

    result = await client.execute_workflow(
        TranslationWorkflow.run,
        input_data,
        id=f"translation-{name.lower()}-{lang}",
        task_queue=TASK_QUEUE,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
