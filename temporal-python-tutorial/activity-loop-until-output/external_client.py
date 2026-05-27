"""
External client to interact with a running PasswordCrackingWorkflow.

Usage:
    python external_client.py query
    python external_client.py stop
    python external_client.py override <password>
"""

import asyncio
import sys

from temporalio.client import Client

from workflows import PasswordCrackingWorkflow

TASK_QUEUE = "password-cracking-task-queue"
WORKFLOW_ID = "password-cracking-workflow"


async def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(WORKFLOW_ID)

    if command == "query":
        progress = await handle.query(PasswordCrackingWorkflow.get_progress)
        print(
            f"Attempt : {progress['attempt']}\n"
            f"Last generated : '{progress['current_generated_password']}'"
        )

    elif command == "stop":
        await handle.signal(PasswordCrackingWorkflow.stop)
        print("Stop signal sent.")

    elif command == "override":
        if len(sys.argv) < 3:
            print("Usage: python external_client.py override <password>")
            sys.exit(1)
        password = sys.argv[2].lower()
        result = await handle.execute_update(
            PasswordCrackingWorkflow.set_override_password, password
        )
        print(result)

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
