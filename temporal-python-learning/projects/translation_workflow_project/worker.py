"""
Translation Workflow — Worker

Usage:
    python worker.py
"""

import asyncio

import aiohttp
from temporalio.client import Client
from temporalio.worker import Worker

from translate_activity import TranslateActivities
from translation_workflow import TranslationWorkflow, TASK_QUEUE


async def main():
    client = await Client.connect("localhost:7233")
    async with aiohttp.ClientSession() as session:
        activities = TranslateActivities(session=session)
        worker = Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[TranslationWorkflow],
            activities=[
                activities.translate_greeting,
                activities.translate_farewell,
            ],
        )
        print(f"Translation worker started on '{TASK_QUEUE}'. Ctrl-C to stop.")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
