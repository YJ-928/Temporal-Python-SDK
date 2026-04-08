from datetime import timedelta
import time
from typing import Literal
from temporalio import workflow
from temporalio.common import RetryPolicy

from activity import file_processor

TASK_QUEUE = "signals-and-heartbeats"

@workflow.defn
class SignalWorkflow:
    """A simple workflow which accepts a signal from external client"""

    def __init__(self) -> None:
            self.result_requested = False

    @workflow.signal
    def request_result(self) -> None:
         self.result_requested = True

    @workflow.run
    async def run_activity(self) -> Literal['File processed successfully']:
        """Workflow method to start and execute the activity"""

        while not self.result_requested:
            result = await workflow.execute_activity(
                file_processor,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    maximum_attempts=99
                )
            )

        return result