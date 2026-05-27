from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

from activities import UserActivities

GREET_TASK_QUEUE = "infinite-greetings"
FAREWELL_TASK_QUEUE = "finite-farewells"

@workflow.defn
class InfiniteRetryWorkflow:
    @workflow.run
    async def welcome(self) -> str:
        result = await workflow.execute_activity_method(
            UserActivities.greet_user,
            "Yash",
            start_to_close_timeout=timedelta(seconds=10),
            # Infinite retry policy
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=1,
                maximum_attempts=99,
                maximum_interval=timedelta(seconds=9999)
            )
        )
        return result
    
@workflow.defn
class FiniteRetryWorkflow:
    @workflow.run
    async def farewell(self) -> str:
        result = await workflow.execute_activity_method(
            UserActivities.farewell_user,
            "Joshi",
            start_to_close_timeout=timedelta(seconds=10),
            # Finite retry policy
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=1,
                maximum_attempts=9,
                maximum_interval=timedelta(seconds=20)
            )
        )
        return result
