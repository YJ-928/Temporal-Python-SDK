"""
Demo POC — Worker
=================
Registers all workflows and activities on a single task queue so one process
can serve the entire showcase.

Usage:
    python Demo/worker.py
"""

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from activities import (
    increment_counter,
    generate_pin,
    validate_pin,
    process_file,
    generate_operand,
    calculate,
    process_file_media,
    process_video_media,
    random_fail_task,
)
from child_workflows import FileProcessingChildWorkflow, VideoProcessingChildWorkflow
from workflows import TemporalShowcaseWorkflow, TASK_QUEUE


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )

    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            TemporalShowcaseWorkflow,
            FileProcessingChildWorkflow,
            VideoProcessingChildWorkflow,
        ],
        activities=[
            increment_counter,
            generate_pin,
            validate_pin,
            process_file,
            generate_operand,
            calculate,
            process_file_media,
            process_video_media,
            random_fail_task,
        ],
    )

    print(f"Worker listening on task queue: {TASK_QUEUE!r}")
    print("Press Ctrl+C to stop.\n")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
