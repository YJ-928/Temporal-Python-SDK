import json
import uuid
from typing import List, Dict, Optional, Any
from temporalio.client import Client
from ..config import settings, get_logger
from .storage_service import get_latest_workflow, load_dsl

logger = get_logger(__name__)


async def get_memo_value(desc, key: str) -> Optional[Any]:
    """
    Retrieve and safely decode a value from a workflow description's memo.

    desc.memo and desc.memo_value are both async coroutines in the
    Temporal Python SDK (WorkflowExecutionDescription).
    """
    if not desc:
        return None

    # Primary: memo_value is the typed accessor (async)
    if hasattr(desc, "memo_value"):
        try:
            val = await desc.memo_value(key, None)
            if val is not None:
                return val
        except Exception:
            pass

    # Fallback: await desc.memo() to get the full dict
    if hasattr(desc, "memo"):
        try:
            memo_dict = await desc.memo()
            if memo_dict and hasattr(memo_dict, "get"):
                return memo_dict.get(key)
        except Exception:
            pass

    return None


class ExecutionService:
    """
    Service for managing workflow executions via Temporal.
    """

    async def _get_client(self) -> Client:
        """Connect to the Temporal server."""
        return await Client.connect(settings.TEMPORAL_ADDRESS)

    async def execute_workflow(self, workflow_id: str, dsl_hash: str, input_payload: dict) -> Dict:
        """
        Trigger execution of the compiled DSL matching the given content hash.

        Args:
            workflow_id: Visual design ID of the workflow
            dsl_hash: SHA-256 hash of compiled DSL to execute
            input_payload: Dict payload passed to workflow execution

        Returns:
            Dict containing execution identifiers: workflow_id, run_id, type
        """
        logger.info(f"Triggering execution for workflow: {workflow_id} (hash: {dsl_hash})")

        # 1. Fetch compiled DSL matching the hash (scoped by workflow_id)
        from .storage_service import find_by_hash
        dsl_path = find_by_hash(workflow_id, dsl_hash, ext=".json")
        if not dsl_path:
            raise FileNotFoundError(
                f"No compiled DSL found matching hash '{dsl_hash}' for workflow ID: {workflow_id}"
            )

        # 2. Load DSL to retrieve type and task queue configurations
        dsl = load_dsl(dsl_path)
        doc = dsl.get("document", {})
        workflow_type = doc.get("workflowType")
        task_queue = doc.get("taskQueue", settings.DEFAULT_TASK_QUEUE)

        if not workflow_type:
            raise ValueError(
                f"Compiled DSL in {dsl_path} is missing 'document.workflowType'"
            )

        # 3. Connect to Temporal and trigger execution
        client = await self._get_client()
        
        # Format Temporal workflow ID: rf-{visual_id}-{short_uuid}
        temporal_workflow_id = f"rf-{workflow_id}-{uuid.uuid4().hex[:8]}"

        logger.info(
            f"Starting workflow type '{workflow_type}' on queue '{task_queue}' "
            f"with Temporal ID: {temporal_workflow_id} (hash: {dsl_hash})"
        )

        handle = await client.start_workflow(
            workflow_type,
            input_payload,
            id=temporal_workflow_id,
            task_queue=task_queue,
            memo={
                "dsl_hash": dsl_hash,
                "visual_workflow_id": workflow_id
            },
        )

        return {
            "workflow_id": temporal_workflow_id,
            "run_id": handle.first_execution_run_id or handle.run_id,
            "workflow_type": workflow_type,
            "status": "RUNNING",
        }

    async def list_executions(self, workflow_id: str) -> List[Dict]:
        """
        List all executions of a workflow using Temporal visibility query.

        Args:
            workflow_id: Visual design ID of the workflow

        Returns:
            List of executions with their status and times
        """
        logger.info(f"Listing executions for workflow: {workflow_id}")
        client = await self._get_client()

        # Query all executions matching our ID prefix pattern
        query = f"WorkflowId STARTS_WITH 'rf-{workflow_id}-'"
        executions = []

        try:
            async for workflow in client.list_workflows(query=query):
                executions.append({
                    "workflow_id": workflow.id,
                    "run_id": workflow.run_id,
                    "workflow_type": workflow.workflow_type,
                    "status": workflow.status.name if hasattr(workflow.status, "name") else str(workflow.status),
                    "start_time": workflow.start_time.isoformat() if workflow.start_time else None,
                    "close_time": workflow.close_time.isoformat() if workflow.close_time else None,
                })
        except Exception as e:
            logger.error(f"Failed to list executions from Temporal: {e}")
            raise RuntimeError(f"Temporal visibility query failed: {e}")

        # Return sorted by start time descending
        return sorted(
            executions,
            key=lambda x: x["start_time"] or "",
            reverse=True
        )

    async def get_execution_trace(self, workflow_id: str, run_id: str) -> Dict:
        """
        Fetch and parse execution event history for a run and map states back to ReactFlow nodes.

        Args:
            workflow_id: Temporal ID of the executing workflow (e.g. rf-greeting-flow-a1b2c3d4)
            run_id: Temporal run ID

        Returns:
            Dict containing step execution traces
        """
        logger.info(f"Fetching trace for workflow '{workflow_id}' run: {run_id}")
        client = await self._get_client()

        # Connect to Temporal workflow handle directly without visibility search lookup
        handle = client.get_workflow_handle(workflow_id, run_id=run_id)
        
        # Describe workflow to fetch dsl_hash and visual_workflow_id from memo
        desc = await handle.describe()
        workflow_status = desc.status.name if hasattr(desc.status, "name") else str(desc.status)
        dsl_hash = await get_memo_value(desc, "dsl_hash")
        visual_workflow_id = await get_memo_value(desc, "visual_workflow_id")

        # Fallback parsing for legacy/older executions without visual_workflow_id in memo
        if not visual_workflow_id:
            if workflow_id.startswith("rf-"):
                parts = workflow_id.split("-")
                if len(parts) >= 3:
                    visual_workflow_id = "-".join(parts[1:-1])
            if not visual_workflow_id:
                visual_workflow_id = workflow_id

        # 1. Fetch history events
        event_states = {}
        scheduled_events = {}
        workflow_completed = False

        def _extract_task_name(payloads) -> Optional[str]:
            if not payloads:
                return None
            for p in payloads:
                try:
                    val = json.loads(p.data.decode("utf-8"))
                    if isinstance(val, dict):
                        name = val.get("data", {}).get("task", {}).get("name")
                        if name:
                            return name
                except Exception:
                    continue
            return None

        async for event in handle.fetch_history_events():
            # External Activity Scheduled
            if event.HasField("activity_task_scheduled_event_attributes"):
                attrs = event.activity_task_scheduled_event_attributes
                task_name = _extract_task_name(attrs.input.payloads)
                if task_name:
                    scheduled_events[event.event_id] = task_name
                    input_data = None
                    if attrs.input.payloads:
                        try:
                            input_data = json.loads(attrs.input.payloads[0].data.decode("utf-8"))
                        except Exception:
                            pass
                    event_states[task_name] = {
                        "status": "running",
                        "input": input_data,
                        "output": None,
                        "error": None
                    }

            # External Activity Completed
            elif event.HasField("activity_task_completed_event_attributes"):
                attrs = event.activity_task_completed_event_attributes
                task_name = scheduled_events.get(attrs.scheduled_event_id)
                if task_name and task_name in event_states:
                    output_data = None
                    if attrs.result and attrs.result.payloads:
                        try:
                            output_data = json.loads(attrs.result.payloads[0].data.decode("utf-8"))
                        except Exception:
                            pass
                    event_states[task_name]["status"] = "completed"
                    event_states[task_name]["output"] = output_data

            # External Activity Failed
            elif event.HasField("activity_task_failed_event_attributes"):
                attrs = event.activity_task_failed_event_attributes
                task_name = scheduled_events.get(attrs.scheduled_event_id)
                if task_name and task_name in event_states:
                    error_msg = "Activity failed"
                    if attrs.failure:
                        error_msg = attrs.failure.message
                    event_states[task_name]["status"] = "failed"
                    event_states[task_name]["error"] = error_msg

            # Child Workflow Initiated
            elif event.HasField("start_child_workflow_execution_initiated_event_attributes"):
                attrs = event.start_child_workflow_execution_initiated_event_attributes
                task_name = attrs.workflow_type.name
                if task_name:
                    scheduled_events[event.event_id] = task_name
                    input_data = None
                    if attrs.input.payloads:
                        try:
                            input_data = json.loads(attrs.input.payloads[0].data.decode("utf-8"))
                        except Exception:
                            pass
                    event_states[task_name] = {
                        "status": "running",
                        "input": input_data,
                        "output": None,
                        "error": None
                    }

            # Child Workflow Completed
            elif event.HasField("child_workflow_execution_completed_event_attributes"):
                attrs = event.child_workflow_execution_completed_event_attributes
                task_name = scheduled_events.get(attrs.initiated_event_id)
                if task_name and task_name in event_states:
                    output_data = None
                    if attrs.result and attrs.result.payloads:
                        try:
                            output_data = json.loads(attrs.result.payloads[0].data.decode("utf-8"))
                        except Exception:
                            pass
                    event_states[task_name]["status"] = "completed"
                    event_states[task_name]["output"] = output_data

            # Child Workflow Failed
            elif event.HasField("child_workflow_execution_failed_event_attributes"):
                attrs = event.child_workflow_execution_failed_event_attributes
                task_name = scheduled_events.get(attrs.initiated_event_id)
                if task_name and task_name in event_states:
                    error_msg = "Child workflow failed"
                    if attrs.failure:
                        error_msg = attrs.failure.message
                    event_states[task_name]["status"] = "failed"
                    event_states[task_name]["error"] = error_msg

            # Workflow Completed
            elif event.HasField("workflow_execution_completed_event_attributes"):
                workflow_completed = True

        # 2. Load ReactFlow JSON representing the layout of the executed workflow
        from .storage_service import find_by_hash
        rf_json = None
        if dsl_hash:
            rf_path = find_by_hash(visual_workflow_id, dsl_hash, ext=".rf")
            if rf_path and rf_path.exists():
                try:
                    with open(rf_path, 'r', encoding='utf-8') as f:
                        rf_json = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load versioned ReactFlow file {rf_path}: {e}")

        # Fallback to latest visual workflow layout if hash-file is missing (e.g. backward compatibility)
        if not rf_json:
            latest_path = get_latest_workflow(visual_workflow_id)
            if latest_path:
                # Primary fallback: look for .rf alongside the DSL file
                rf_path = latest_path.with_suffix(".rf")
                # Secondary fallback: glob for any .rf file matching the visual_workflow_id
                if not rf_path.exists():
                    latest_glob = list(settings.COMPILED_DIR.glob(f"**/*{visual_workflow_id}*.rf"))
                    if latest_glob:
                        rf_path = latest_glob[-1]

                if rf_path.exists():
                    try:
                        with open(rf_path, 'r', encoding='utf-8') as f:
                            rf_json = json.load(f)
                    except Exception as e:
                        logger.warning(f"Failed to load fallback ReactFlow file {rf_path}: {e}")

        if not rf_json:
            # Reconstruct dummy ReactFlow format if totally unavailable
            rf_json = {"nodes": [], "edges": []}

        # 3. Propagate states topologically using our decoupled Replay Engine
        from .replay_engine import propagate_dag_states
        final_steps = propagate_dag_states(rf_json, event_states, workflow_completed)

        return {
            "run_id": run_id,
            "status": workflow_status,
            "steps": final_steps
        }

    async def cancel_workflow(self, workflow_id: str, run_id: str) -> None:
        """Cancel a running workflow execution."""
        logger.info(f"Cancelling workflow: {workflow_id} (run: {run_id})")
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id, run_id=run_id)
        await handle.cancel()

    async def terminate_workflow(self, workflow_id: str, run_id: str, reason: str = "Terminated by user") -> None:
        """Forcefully terminate a running workflow execution."""
        logger.info(f"Terminating workflow: {workflow_id} (run: {run_id})")
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id, run_id=run_id)
        await handle.terminate(reason=reason)


execution_service = ExecutionService()
