"""
Demo POC — Starter
==================
Starts a single TemporalShowcaseWorkflow instance and prints the workflow ID
together with ready-to-run client.py commands so you can drive it step by step.

Usage:
    python Demo/starter.py
    python Demo/starter.py --pin 742   # custom target PIN (default: 742)
    python Demo/starter.py --wait      # block until the workflow completes
"""

import asyncio
import argparse
import logging
import uuid

from temporalio.client import Client

from workflows import TemporalShowcaseWorkflow, TASK_QUEUE


async def main(target_pin: str, wait: bool) -> None:
    logging.basicConfig(level=logging.INFO)

    client = await Client.connect("localhost:7233")

    workflow_id = f"temporal-showcase-{uuid.uuid4().hex[:8]}"

    handle = await client.start_workflow(
        TemporalShowcaseWorkflow.run,
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    print(f"\n{'='*60}")
    print(f"  Workflow started:  {workflow_id}")
    print(f"  Task queue:        {TASK_QUEUE}")
    print(f"  Target PIN:        {target_pin}")
    print(f"{'='*60}\n")
    print("Step-by-step driver commands (run in a separate terminal):\n")
    print("  # 1. Send the start signal (required to begin Phase 1)")
    print(f"  python Demo/clients.py {workflow_id} start --pin {target_pin}\n")
    print("  # 2. Query live status at any time")
    print(f"  python Demo/clients.py {workflow_id} query_status\n")
    print("  # 3. Stop the counter and advance to Phase 2")
    print(f"  python Demo/clients.py {workflow_id} stop_counter\n")
    print("  # 4. Inject an override PIN to cheat the cracker")
    print(f"  python Demo/clients.py {workflow_id} override_pin --pin {target_pin}\n")
    print("  # 5. Queue files for parallel processing (Phase 3)")
    print(f"  python Demo/clients.py {workflow_id} queue_file --file-id 101")
    print(f"  python Demo/clients.py {workflow_id} queue_file --file-id 202")
    print(f"  python Demo/clients.py {workflow_id} advance_phase\n")
    print("  # 6. Run an on-demand update (any phase)")
    print(f"  python Demo/clients.py {workflow_id} update_calc --a 12 --b 5 --op multiply\n")
    print("  # 7. Advance through calculator phase (Phase 4)")
    print(f"  python Demo/clients.py {workflow_id} advance_phase\n")
    print("  # 8. Pause / resume the workflow")
    print(f"  python Demo/clients.py {workflow_id} pause")
    print(f"  python Demo/clients.py {workflow_id} resume\n")
    print("  # 9. Stop the workflow early (optional)")
    print(f"  python Demo/clients.py {workflow_id} stop\n")

    if wait:
        print("Waiting for workflow to complete …\n")
        result = await handle.result()
        print(f"Final result:\n{result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Temporal Showcase workflow")
    parser.add_argument("--pin", default="742", help="3-digit target PIN for the cracker phase")
    parser.add_argument("--wait", action="store_true", help="Block until workflow completes")
    args = parser.parse_args()
    asyncio.run(main(args.pin, args.wait))
