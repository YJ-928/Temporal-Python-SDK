#!/usr/bin/env python3
"""Zigflow Workflow Runner — executes ONE Zigflow workflow inside an ephemeral container.

Execution flow
--------------
1. Validate the workflow JSON file (structure check).
2. Start the Zigflow worker process in the background (subprocess).
3. Wait for the worker to register its workflows with Temporal (grace period).
4. Trigger execution via the Temporal CLI (``temporal workflow start``).
5. Poll ``temporal workflow describe`` until the workflow reaches a terminal state.
6. Extract the result payload from the event history.
7. Emit a single structured JSON object to **stdout** (captured by Docker logs).
8. Terminate the Zigflow worker.
9. Exit with code 0 (success) or 1 (failure).

The parent orchestrator's Docker service reads the last JSON line from stdout
as the authoritative execution result.
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

# ── Logging (stderr only — stdout is reserved for the JSON result line) ────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("runner")


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Zigflow Workflow Runner")
    p.add_argument("--workflow", required=True, help="Workflow filename (e.g. hello-world.json)")
    p.add_argument("--workflow-path", required=True, help="Absolute path to the workflow JSON file")
    p.add_argument("--input", required=True, help="JSON-encoded workflow input")
    p.add_argument("--execution-id", default=str(uuid.uuid4()), help="Unique execution ID")
    p.add_argument("--temporal-host", default=os.getenv("TEMPORAL_HOST", "localhost:7233"))
    p.add_argument("--namespace", default=os.getenv("TEMPORAL_NAMESPACE", "default"))
    p.add_argument("--poll-interval", type=float, default=3.0, help="Seconds between status polls")
    p.add_argument("--timeout", type=int, default=3600, help="Max execution time in seconds")
    p.add_argument("--worker-startup-wait", type=float, default=4.0,
                   help="Seconds to wait for Zigflow worker to register before triggering workflow")
    return p.parse_args()


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_workflow(workflow_path: str) -> Dict[str, Any]:
    """Load and structurally validate the Zigflow workflow JSON.

    Returns the parsed workflow dict.
    Raises ``FileNotFoundError`` or ``ValueError`` on failure.
    """
    if not os.path.isfile(workflow_path):
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    with open(workflow_path) as fh:
        try:
            definition = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in workflow file: {exc}") from exc

    for required_field in ("document", "do"):
        if required_field not in definition:
            raise ValueError(
                f"Invalid Zigflow workflow: missing top-level field '{required_field}'"
            )

    return definition


# ── Zigflow worker ─────────────────────────────────────────────────────────────

def start_zigflow_worker(workflow_path: str) -> subprocess.Popen:  # type: ignore[type-arg]
    """Launch ``zigflow run -f <workflow>`` as a background subprocess."""
    logger.info("Starting Zigflow worker for %s", workflow_path)
    proc = subprocess.Popen(
        ["zigflow", "run", "-f", workflow_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    logger.info("Zigflow worker PID: %d", proc.pid)
    return proc


# ── Temporal CLI helpers ───────────────────────────────────────────────────────

def _run_temporal(
    args: List[str],
    temporal_host: str,
    namespace: str,
    timeout: int = 30,
) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    """Run a ``temporal`` CLI command with standard flags injected."""
    cmd = [
        "temporal",
        "--address", temporal_host,
        "--namespace", namespace,
        "--output", "json",
    ] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def trigger_workflow(
    workflow_type: str,
    task_queue: str,
    workflow_id: str,
    input_data: Dict[str, Any],
    temporal_host: str,
    namespace: str,
) -> bool:
    """Start a Temporal workflow via the CLI. Returns True on success."""
    result = _run_temporal(
        [
            "workflow", "start",
            "--type", workflow_type,
            "--task-queue", task_queue,
            "--workflow-id", workflow_id,
            "--input", json.dumps(input_data),
        ],
        temporal_host=temporal_host,
        namespace=namespace,
    )
    if result.returncode != 0:
        logger.error("Failed to start workflow: %s", result.stderr.strip())
        return False
    logger.info("Workflow started: %s", workflow_id)
    return True


def poll_until_done(
    workflow_id: str,
    temporal_host: str,
    namespace: str,
    poll_interval: float,
    timeout: int,
) -> Dict[str, Any]:
    """Poll ``temporal workflow describe`` until a terminal state is reached.

    Returns a dict with at least ``{"status": "<status>", "workflow_id": "..."}``
    and optionally ``{"error": "..."}`` on non-completed states.

    Raises ``TimeoutError`` if the timeout expires.
    """
    deadline = time.time() + timeout
    terminal_states = {"COMPLETED", "FAILED", "CANCELED", "TERMINATED", "TIMED_OUT"}

    while time.time() < deadline:
        result = _run_temporal(
            ["workflow", "describe", "--workflow-id", workflow_id],
            temporal_host=temporal_host,
            namespace=namespace,
            timeout=15,
        )

        if result.returncode != 0:
            logger.warning("describe failed: %s — retrying", result.stderr.strip())
            time.sleep(poll_interval)
            continue

        try:
            info = json.loads(result.stdout)
        except json.JSONDecodeError:
            time.sleep(poll_interval)
            continue

        # Temporal CLI JSON path varies by version; try both known paths
        raw_status: str = (
            info.get("workflowExecutionInfo", {}).get("status", "")
            or info.get("status", "")
        ).upper()

        logger.info("Workflow %s status: %s", workflow_id, raw_status or "UNKNOWN")

        if raw_status in terminal_states:
            outcome: Dict[str, Any] = {
                "status": raw_status.lower(),
                "workflow_id": workflow_id,
            }
            if raw_status != "COMPLETED":
                outcome["error"] = f"Workflow ended with status: {raw_status}"
            return outcome

        time.sleep(poll_interval)

    raise TimeoutError(
        f"Workflow {workflow_id} did not reach a terminal state within {timeout}s"
    )


def fetch_result(
    workflow_id: str,
    temporal_host: str,
    namespace: str,
) -> Optional[Dict[str, Any]]:
    """Extract the result payload from the completed workflow's event history."""
    result = _run_temporal(
        ["workflow", "show", "--workflow-id", workflow_id],
        temporal_host=temporal_host,
        namespace=namespace,
        timeout=15,
    )
    if result.returncode != 0:
        logger.warning("Could not retrieve workflow result: %s", result.stderr.strip())
        return None

    try:
        history = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    events: List[Dict[str, Any]] = history.get("events", [])
    for event in reversed(events):
        if event.get("eventType") == "EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED":
            payloads = (
                event
                .get("workflowExecutionCompletedEventAttributes", {})
                .get("result", {})
                .get("payloads", [])
            )
            if payloads:
                raw_data: str = payloads[0].get("data", "")
                try:
                    # Temporal base64-encodes payload data
                    decoded = base64.b64decode(raw_data + "==").decode("utf-8", errors="replace")
                    return json.loads(decoded)
                except Exception as exc:
                    logger.warning("Could not decode result payload: %s", exc)
    return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    logs: List[str] = []
    zigflow_proc: Optional[subprocess.Popen] = None  # type: ignore[type-arg]

    def log(msg: str) -> None:
        logger.info(msg)
        logs.append(msg)

    try:
        # 1. Validate workflow
        log(f"Validating workflow: {args.workflow_path}")
        workflow_def = validate_workflow(args.workflow_path)
        doc = workflow_def.get("document", {})
        task_queue: str = doc.get("taskQueue", "zigflow")
        workflow_type: str = doc.get(
            "workflowType",
            os.path.splitext(args.workflow)[0],  # filename without extension
        )
        log(f"Workflow OK — type='{workflow_type}', queue='{task_queue}'")

        # 2. Parse input
        try:
            input_data: Dict[str, Any] = json.loads(args.input)
        except json.JSONDecodeError as exc:
            raise ValueError(f"--input is not valid JSON: {exc}") from exc

        # 3. Start Zigflow worker
        zigflow_proc = start_zigflow_worker(args.workflow_path)
        log(f"Zigflow worker started (PID {zigflow_proc.pid})")

        # 4. Wait for worker to register with Temporal
        log(f"Waiting {args.worker_startup_wait}s for worker registration...")
        time.sleep(args.worker_startup_wait)

        if zigflow_proc.poll() is not None:
            stderr = (zigflow_proc.stderr.read() or b"").decode("utf-8", errors="replace")
            raise RuntimeError(f"Zigflow worker exited prematurely: {stderr}")

        # 5. Trigger Temporal workflow
        workflow_id = f"{args.execution_id}-{workflow_type}"
        log(f"Triggering workflow: {workflow_id}")
        started = trigger_workflow(
            workflow_type=workflow_type,
            task_queue=task_queue,
            workflow_id=workflow_id,
            input_data=input_data,
            temporal_host=args.temporal_host,
            namespace=args.namespace,
        )
        if not started:
            raise RuntimeError("temporal workflow start failed — see stderr for details")

        # 6. Poll until terminal state
        log("Polling for completion...")
        completion = poll_until_done(
            workflow_id=workflow_id,
            temporal_host=args.temporal_host,
            namespace=args.namespace,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
        log(f"Terminal state reached: {completion['status']}")

        # 7. Fetch result payload (only for COMPLETED)
        result_data: Optional[Dict[str, Any]] = None
        if completion["status"] == "completed":
            result_data = fetch_result(
                workflow_id=workflow_id,
                temporal_host=args.temporal_host,
                namespace=args.namespace,
            )

        # 8. Emit structured JSON result to stdout
        output = {
            "status": completion["status"],
            "workflow": args.workflow,
            "workflowId": workflow_id,
            "executionId": args.execution_id,
            "result": result_data,
            "logs": logs,
            "error": completion.get("error"),
        }
        print(json.dumps(output), flush=True)
        return 0

    except TimeoutError as exc:
        error_output = {
            "status": "timeout",
            "workflow": args.workflow,
            "executionId": args.execution_id,
            "result": None,
            "logs": logs,
            "error": str(exc),
        }
        print(json.dumps(error_output), flush=True)
        return 1

    except Exception as exc:
        logger.exception("Runner failed: %s", exc)
        error_output = {
            "status": "failed",
            "workflow": getattr(args, "workflow", "unknown"),
            "executionId": getattr(args, "execution_id", "unknown"),
            "result": None,
            "logs": logs,
            "error": str(exc),
        }
        print(json.dumps(error_output), flush=True)
        return 1

    finally:
        # Always terminate the Zigflow worker subprocess
        if zigflow_proc is not None and zigflow_proc.poll() is None:
            logger.info("Terminating Zigflow worker (PID %d)", zigflow_proc.pid)
            try:
                zigflow_proc.terminate()
                zigflow_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Worker did not terminate; killing")
                zigflow_proc.kill()
            except Exception as exc:
                logger.warning("Error stopping Zigflow worker: %s", exc)


if __name__ == "__main__":
    sys.exit(main())
