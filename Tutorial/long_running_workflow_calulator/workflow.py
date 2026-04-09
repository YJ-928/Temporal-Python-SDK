from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activity import Calculator

TASK_QUEUE = "long-running-taskqueue"
OPERATIONS = ["addition", "subtraction", "multiplication", "integer_division"]

@workflow.defn
class LongRunningWorkflow:
    """Workflow class which performs calculator operations and returns output until cancelled"""

    def __init__(self) -> None:
        self.cancel_workflow = False

    @workflow.signal
    def cancel_longrunning_workflow(self) -> None:
        self.cancel_workflow = True
    
    @workflow.run
    async def calculate(self) -> str:
        while not self.cancel_workflow:
            await workflow.sleep(timedelta(seconds=1))
            value1 = await workflow.execute_activity_method(
                Calculator.generate_value,
                start_to_close_timeout=timedelta(seconds=10)
            )
            value2 = await workflow.execute_activity_method(
                Calculator.generate_value,
                start_to_close_timeout=timedelta(seconds=10)
            )

            for op in OPERATIONS:
                await workflow.sleep(timedelta(seconds=1))
                result = await workflow.execute_activity_method(
                    getattr(Calculator, op),
                    args=[value1, value2],
                    start_to_close_timeout=timedelta(seconds=10)
                )
                workflow.logger.info(f"Result: {result}")

        workflow.logger.info("Signal received, stopping workflow...")
        return "LONG RUNNING WORKFLOW COMPLETED !!"
