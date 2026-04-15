"""
Demo POC — All Activities
=========================
Aggregates activity definitions from every Tutorial sub-project into one module,
each section labelled with its origin tutorial.

Phase 1  — Counter               (query_signals_and_heartbeats_example)
Phase 2  — Password Cracker      (activity-loop-until-output)
Phase 3  — Parallel File Proc.   (parallel-file-processing-signals)
Phase 4  — Calculator            (long_running_workflow_calculator)
Phase 5  — Media Processor       (child-workflows_and_continue_as_new)
Phase 6  — Resilience Test       (failing_activity_tutorial)
"""

import asyncio
import random
import string

from temporalio import activity
from temporalio.exceptions import ApplicationError


# Phase 1: Counter

@activity.defn
async def increment_counter(value: int) -> int:
    """Increment a counter by 1 with heartbeats."""
    activity.logger.info(f"increment_counter invoked with value={value}")
    activity.heartbeat(f"Received value: {value}")
    await asyncio.sleep(1)
    result = value + 1
    activity.heartbeat(f"Incremented to: {result}")
    activity.logger.info(f"increment_counter complete: {result}")
    return result


# Phase 2: Password Cracker

@activity.defn
async def generate_pin() -> str:
    """Generate a random 3-digit PIN."""
    activity.logger.info("generate_pin invoked")
    activity.heartbeat("Generating PIN...")
    pin = "".join(random.choices(string.digits, k=3))
    activity.logger.info(f"generate_pin complete: {pin!r}")
    return pin


@activity.defn
async def validate_pin(generated: str, target: str) -> bool:
    """Return True when generated PIN matches the target."""
    activity.logger.info(f"validate_pin invoked: {generated!r} vs {target!r}")
    activity.heartbeat(f"Validating '{generated}' vs '{target}'")
    matched = generated.lower() == target.lower()
    activity.logger.info(f"validate_pin result: {matched}")
    return matched


# Phase 3: Parallel File Processor

@activity.defn
async def process_file(file_id: int) -> str:
    """Simulate file processing for a given file ID with heartbeat progress."""
    activity.logger.info(f"process_file invoked: file_id={file_id}")
    for pct in range(10, 110, 10):
        await asyncio.sleep(0.5)
        activity.heartbeat(f"File {file_id}: {pct}%")
    result = f"File {file_id} processed successfully"
    activity.logger.info(f"process_file complete: {result}")
    return result


# Phase 4: Calculator 

@activity.defn
async def generate_operand() -> int:
    """Generate a random integer operand (1–100)."""
    activity.logger.info("generate_operand invoked")
    value = random.randint(1, 100)
    activity.heartbeat(f"Generated operand: {value}")
    await asyncio.sleep(0.3)
    activity.logger.info(f"generate_operand complete: {value}")
    return value


@activity.defn
async def calculate(a: int, b: int, op: str) -> str:
    """Perform add / subtract / multiply / divide and return a human-readable result."""
    activity.logger.info(f"calculate invoked: {a} {op} {b}")
    activity.heartbeat(f"Computing {a} {op} {b}")
    await asyncio.sleep(0.3)
    if op == "add":
        result = f"{a} + {b} = {a + b}"
    elif op == "subtract":
        result = f"{a} - {b} = {a - b}"
    elif op == "multiply":
        result = f"{a} * {b} = {a * b}"
    elif op == "divide":
        if b == 0:
            result = f"{a} / {b} = undefined (division by zero)"
        else:
            result = f"{a} / {b} = {a // b}"
    else:
        # Non-retryable: invalid input should not trigger automatic retries
        raise ApplicationError(
            f"Unknown operation: {op!r}. Valid ops: add, subtract, multiply, divide.",
            non_retryable=True,
        )
    activity.logger.info(f"calculate complete: {result}")
    return result


# Phase 5: Media Processor (child workflow activities) 

@activity.defn
async def process_file_media() -> str:
    """Simulate file-media processing — used inside FileProcessingChildWorkflow."""
    activity.logger.info("process_file_media invoked")
    activity.heartbeat("File media processing initiated...")
    for pct in range(10, 110, 10):
        activity.heartbeat(f"File media: {pct}%")
        await asyncio.sleep(0.3)
    result = "File media processing complete"
    activity.logger.info(f"process_file_media complete: {result}")
    return result


@activity.defn
async def process_video_media() -> str:
    """Simulate video processing — used inside VideoProcessingChildWorkflow."""
    activity.logger.info("process_video_media invoked")
    activity.heartbeat("Video processing initiated...")
    for pct in range(10, 110, 5):
        activity.heartbeat(f"Video: {pct}%")
        await asyncio.sleep(0.2)
    result = "Video processing complete"
    activity.logger.info(f"process_video_media complete: {result}")
    return result


# Phase 6: Resilience Test ─

@activity.defn
async def random_fail_task() -> str:
    """Randomly fail ~65 % of the time to showcase Temporal retry policies."""
    attempt = activity.info().attempt
    activity.heartbeat(f"Resilience attempt {attempt}")
    activity.logger.info(f"Running resilience attempt {attempt}")
    if random.random() < 0.65:
        raise Exception(f"Random failure on attempt {attempt}")
    return f"Resilience test passed on attempt {attempt}"
