from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

from activities import ActivityClass

FILE_PROCESSOR_TASK_QUEUE = "child-file-processor-queue"
VIDEO_PROCESSOR_TASK_QUEUE = "child-video-processor-queue"

@workflow.defn
class FileProceesingWorkflow:
    
    @workflow.run
    async def run_file_activity(self) -> str:
        await workflow.execute_activity_method(
            ActivityClass.file_processor,
            task_queue=FILE_PROCESSOR_TASK_QUEUE,
            schedule_to_start_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=2)
        )
        return "File processing child workflow completed"

@workflow.defn
class VideoProcessingWorkflow:
    
    @workflow.run
    async def run_video_activity(self) -> str:
        await workflow.execute_activity_method(
            ActivityClass.video_processor,
            task_queue=VIDEO_PROCESSOR_TASK_QUEUE,
            start_to_close_timeout=timedelta(seconds=20),
            retry_policy=RetryPolicy(maximum_attempts=2)
        )
        return "Video processing child workflow completed"
