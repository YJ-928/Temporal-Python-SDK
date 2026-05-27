import asyncio

from temporalio.client import Client

from workflow import CounterWorkflow, TASK_QUEUE

WORKFLOW_ID = "counter-workflow"

async def main():# -> Any:
    """Client or starter which executes the workflow"""

    # Create and connect client to temporal server
    client = await Client.connect("localhost:7233")

    print(f"Client started {WORKFLOW_ID} workflow execution")

    # Use created client to execute workflow using worker
    result = await client.execute_workflow(
        CounterWorkflow.run_counter,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE
    )

    return result

if __name__ == "__main__":
    asyncio.run(main())
