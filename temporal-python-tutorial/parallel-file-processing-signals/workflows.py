from datetime import timedelta
from typing import NoReturn
from temporalio import workflow
from temporalio.common import RetryPolicy

from activities import process_file

TASK_QUEUE = "file-task-queue"

@workflow.defn
class FileProcessorWorkflow:

    def __init__(self) -> None:
        self.tasks = []   # To store running tasks

    @workflow.signal
    def process_file_signal(self, file_id: int) -> None:
        # Start activity asynchronously instead of execute activity 
        # for parallel processing or concurrent tasks execution
        handle = workflow.start_activity(
            process_file,
            file_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        self.tasks.append(handle)

    @workflow.run
    async def run(self) -> NoReturn:
        # keep workflow alive forever
        while True:
            await workflow.sleep(timedelta(seconds=10))