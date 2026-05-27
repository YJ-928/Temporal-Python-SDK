from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

from activity import incrementer

TASK_QUEUE = "counter-task"

@workflow.defn
class CounterWorkflow:
    """A simple counter workflow with query and signal functionalities"""

    def __init__(self) -> None:
        self.count = 0
        self.stop_counter = False

    @workflow.query
    def get_current_count(self) -> int:
        workflow.logger.info("Workflow Query recieved")
        return self.count
    
    @workflow.signal
    def stop_counter_func(self) -> None:
        workflow.logger.info("Workflow Signal recieced")
        self.stop_counter = True

    @workflow.run
    async def run_counter(self):# -> Any:
        while not self.stop_counter:
            await workflow.sleep(timedelta(seconds=2))
            result = await workflow.execute_activity(
                incrementer,
                self.count,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(
                    maximum_attempts=5
                )
            )
            self.count = result

        workflow.logger.info(f"Counter Stopped at {self.count}")
        return self.count
