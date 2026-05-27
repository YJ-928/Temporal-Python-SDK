"""
Demo POC — External Clients
============================
Command-line driver for every signal, query, and update exposed by
TemporalShowcaseWorkflow.  Run commands in any order from a separate terminal
while the worker is running.

Usage:
    python Demo/clients.py <workflow_id> <action> [options]

Actions & options
─
Signals:
    start           --pin PIN          kick off showcase with target PIN
    pause                              pause the workflow
    resume                             resume a paused workflow
    stop                               gracefully stop the workflow
    advance_phase                      end current phase, move forward
    stop_counter                       end counter phase
    queue_file      --file-id INT      add a file ID to parallel processing queue
    override_pin    --pin PIN          inject PIN guess for cracker phase

Queries:
    query_status                       overall workflow state
    query_progress                     current phase + live metrics
    query_results                      all completed phase results

Updates (synchronous — waits for the activity to finish):
    update_calc     --a INT --b INT --op OP    run one calculator operation
                                               OP: add / subtract / multiply / divide
    update_pin      --guess STR --target STR   test a PIN guess against a target

Examples:
    python Demo/clients.py showcase-abc123 start --pin 742
    python Demo/clients.py showcase-abc123 query_status
    python Demo/clients.py showcase-abc123 stop_counter
    python Demo/clients.py showcase-abc123 override_pin --pin 742
    python Demo/clients.py showcase-abc123 queue_file --file-id 101
    python Demo/clients.py showcase-abc123 advance_phase
    python Demo/clients.py showcase-abc123 update_calc --a 9 --b 3 --op divide
    python Demo/clients.py showcase-abc123 update_pin --guess 742 --target 742
    python Demo/clients.py showcase-abc123 query_results
"""

import asyncio
import argparse
import dataclasses
import json
import logging
import sys

from temporalio.client import Client

from shared import StartInput, CalculatorInput, PinMatchInput
from workflows import TemporalShowcaseWorkflow


async def main(workflow_id: str, action: str, opts: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.WARNING)  # keep output clean

    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id)

    # Signals 
    if action == "start":
        pin = _require(opts, "pin", action)
        await handle.signal(TemporalShowcaseWorkflow.start, StartInput(target_pin=pin))
        print(f"[signal] start sent — target PIN: {pin!r}")

    elif action == "pause":
        await handle.signal(TemporalShowcaseWorkflow.pause)
        print("[signal] pause sent")

    elif action == "resume":
        await handle.signal(TemporalShowcaseWorkflow.resume)
        print("[signal] resume sent")

    elif action == "stop":
        await handle.signal(TemporalShowcaseWorkflow.stop)
        print("[signal] stop sent")

    elif action == "advance_phase":
        await handle.signal(TemporalShowcaseWorkflow.advance_phase)
        print("[signal] advance_phase sent")

    elif action == "stop_counter":
        await handle.signal(TemporalShowcaseWorkflow.stop_counter)
        print("[signal] stop_counter sent")

    elif action == "queue_file":
        file_id = int(_require(opts, "file_id", action))
        await handle.signal(TemporalShowcaseWorkflow.queue_file, file_id)
        print(f"[signal] queue_file sent — file_id={file_id}")

    elif action == "override_pin":
        pin = _require(opts, "pin", action)
        await handle.signal(TemporalShowcaseWorkflow.override_pin, pin)
        print(f"[signal] override_pin sent — pin={pin!r}")

    # Queries 
    elif action == "query_status":
        result = await handle.query(TemporalShowcaseWorkflow.get_status)
        _pretty("Status", result)

    elif action == "query_progress":
        result = await handle.query(TemporalShowcaseWorkflow.get_phase_progress)
        _pretty("Phase progress", result)

    elif action == "query_results":
        result = await handle.query(TemporalShowcaseWorkflow.get_results)
        _pretty("Phase results", result)

    # Updates 
    elif action == "update_calc":
        a = int(_require(opts, "a", action))
        b = int(_require(opts, "b", action))
        op = _require(opts, "op", action)
        print(f"[update] run_calculator({a}, {b}, {op!r}) — waiting …")
        result = await handle.execute_update(
            TemporalShowcaseWorkflow.run_calculator,
            args=[CalculatorInput(a=a, b=b, op=op)],
        )
        print(f"[update] result: {result}")

    elif action == "update_pin":
        guess = _require(opts, "guess", action)
        target = _require(opts, "target", action)
        print(f"[update] test_pin_match({guess!r}, {target!r}) — waiting …")
        result = await handle.execute_update(
            TemporalShowcaseWorkflow.test_pin_match,
            args=[PinMatchInput(guess=guess, target=target)],
        )
        print(f"[update] matched: {result}")

    else:
        print(f"Unknown action: {action!r}")
        print("Run 'python Demo/clients.py --help' for usage.")
        sys.exit(1)


def _require(opts: argparse.Namespace, attr: str, action: str) -> str:
    value = getattr(opts, attr, None)
    if value is None:
        print(f"Action '{action}' requires --{attr.replace('_', '-')}.")
        sys.exit(1)
    return str(value)


def _pretty(label: str, data: object) -> None:
    # Temporal returns dataclasses for typed query results; fall back to dict display
    if dataclasses.is_dataclass(data) and not isinstance(data, type):
        payload = dataclasses.asdict(data)  # type: ignore[arg-type]
    elif isinstance(data, dict):
        payload = data
    else:
        print(f"\n{label}: {data}\n")
        return
    print(f"\n{label}:")
    print(json.dumps(payload, indent=2, default=str))
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="External client for TemporalShowcaseWorkflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("workflow_id", help="Target workflow ID")
    parser.add_argument("action", help="Action to perform (see list above)")
    parser.add_argument("--pin", help="PIN value (start / override_pin)")
    parser.add_argument("--guess", help="PIN guess (update_pin)")
    parser.add_argument("--target", help="PIN target (update_pin)")
    parser.add_argument("--file-id", dest="file_id", help="File ID (queue_file)")
    parser.add_argument("--a", type=int, help="First operand (update_calc)")
    parser.add_argument("--b", type=int, help="Second operand (update_calc)")
    parser.add_argument("--op", help="Operation: add/subtract/multiply/divide (update_calc)")
    args = parser.parse_args()

    asyncio.run(main(args.workflow_id, args.action, args))
