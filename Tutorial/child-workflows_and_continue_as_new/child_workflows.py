from datetime import timedelta
from temporalio import workflow

from activities import ActivityClass

@workflow.defn
class FileProceesingWorkflow:
    
    @workflow.run
    async def run_file_activity(self):
        result = await workflow.execute_activity(
            
        )

@workflow.defn
class VideoProcessingWorkflow:
    pass