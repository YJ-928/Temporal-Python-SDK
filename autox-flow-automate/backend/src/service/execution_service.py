import asyncio
import contextlib
import json
import uuid
from typing import List, Dict, Optional, Any
from temporalio.client import Client
from temporalio.service import RPCError
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

    if hasattr(desc, "memo_value"):
        with contextlib.suppress(Exception):
            val = await desc.memo_value(key, None)
            if val is not None:
                return val

    if hasattr(desc, "memo"):
        with contextlib.suppress(Exception):
            memo_dict = await desc.memo()
            if memo_dict and hasattr(memo_dict, "get"):
                return memo_dict.get(key)

    return None


def _decode_failure_encoded_attrs(failure) -> str:
    """
    Decode GoSDK/Zigflow encoded_attributes.data (JSON blob) to extract the real error message.
    GoSDK sets failure.message = 'Encoded failure' and puts the real message in encoded_attributes.
    """
    with contextlib.suppress(Exception):
        ea = getattr(failure, 'encoded_attributes', None)
        if not ea:
            return ""
        data = getattr(ea, 'data', b'')
        if not data:
            return ""
        decoded = json.loads(data.decode('utf-8'))
        if isinstance(decoded, dict):
            return decoded.get('message', '')
    return ""


_TRIVIAL_MESSAGES = frozenset({
    "Encoded failure", "Unknown error", "Workflow execution failed",
    "Activity task failed", "activity error", "",
})


def _get_cause_message(failure, depth: int) -> str:
    """Recurse into a Temporal failure's cause and return its unwrapped message, or ''."""
    with contextlib.suppress(Exception):
        if hasattr(failure, "HasField") and failure.HasField("cause"):
            msg = unwrap_temporal_failure(failure.cause, depth + 1)
            return msg if msg not in _TRIVIAL_MESSAGES else ""
    return ""


def unwrap_temporal_failure(failure, _depth: int = 0) -> str:
    """
    Recursively unwrap Temporal failure proto to extract the actual error message.
    Handles GoSDK (Zigflow) encoded failures where the real message is in encoded_attributes.data.
    ApplicationFailureInfo has no .message field — never access it directly.
    """
    if not failure or _depth > 10:
        return "Unknown error"

    ea_msg = _decode_failure_encoded_attrs(failure)
    if ea_msg not in _TRIVIAL_MESSAGES:
        return _get_cause_message(failure, _depth) or ea_msg

    msg = getattr(failure, 'message', '') or ''
    if msg not in _TRIVIAL_MESSAGES:
        return msg

    return _get_cause_message(failure, _depth) or "Workflow execution failed"


def _extract_task_name(payloads) -> Optional[str]:
    """Extract the task name from Temporal activity input payloads."""
    if not payloads:
        return None
    for p in payloads:
        with contextlib.suppress(Exception):
            val = json.loads(p.data.decode("utf-8"))
            if isinstance(val, dict):
                name = val.get("data", {}).get("task", {}).get("name")
                if name:
                    return name
    return None


def _decode_payload(payloads) -> Optional[Any]:
    """Decode the first payload in a list to a Python object."""
    if not payloads:
        return None
    with contextlib.suppress(Exception):
        return json.loads(payloads[0].data.decode("utf-8"))
    return None


def _elapsed(event_time, scheduled_times: dict, schedule_id: int) -> Optional[float]:
    """Compute seconds elapsed since a scheduled event."""
    start_t = scheduled_times.get(schedule_id)
    if start_t:
        return round((event_time.ToDatetime() - start_t).total_seconds(), 2)
    return None


def _handle_activity_scheduled(event, event_states: dict, scheduled_events: dict, scheduled_times: dict) -> None:
    attrs = event.activity_task_scheduled_event_attributes
    task_name = _extract_task_name(attrs.input.payloads)
    if not task_name:
        return
    scheduled_events[event.event_id] = task_name
    scheduled_times[event.event_id] = event.event_time.ToDatetime()
    event_states[task_name] = {
        "status": "running",
        "input": _decode_payload(attrs.input.payloads),
        "output": None,
        "error": None,
        "duration_seconds": None,
    }


def _handle_activity_completed(event, event_states: dict, scheduled_events: dict, scheduled_times: dict) -> None:
    attrs = event.activity_task_completed_event_attributes
    task_name = scheduled_events.get(attrs.scheduled_event_id)
    if not (task_name and task_name in event_states):
        return
    event_states[task_name]["status"] = "completed"
    event_states[task_name]["output"] = _decode_payload(
        attrs.result.payloads if attrs.result else None
    )
    event_states[task_name]["duration_seconds"] = _elapsed(
        event.event_time, scheduled_times, attrs.scheduled_event_id
    )


def _handle_activity_failed(event, event_states: dict, scheduled_events: dict, scheduled_times: dict) -> None:
    attrs = event.activity_task_failed_event_attributes
    task_name = scheduled_events.get(attrs.scheduled_event_id)
    if not (task_name and task_name in event_states):
        return
    error_msg = unwrap_temporal_failure(attrs.failure) if attrs.failure else "Activity failed"
    event_states[task_name]["status"] = "failed"
    event_states[task_name]["error"] = error_msg
    event_states[task_name]["duration_seconds"] = _elapsed(
        event.event_time, scheduled_times, attrs.scheduled_event_id
    )


def _handle_child_initiated(event, event_states: dict, scheduled_events: dict, scheduled_times: dict) -> None:
    attrs = event.start_child_workflow_execution_initiated_event_attributes
    task_name = attrs.workflow_type.name
    if not task_name:
        return
    scheduled_events[event.event_id] = task_name
    scheduled_times[event.event_id] = event.event_time.ToDatetime()
    event_states[task_name] = {
        "status": "running",
        "input": _decode_payload(attrs.input.payloads if attrs.input else None),
        "output": None,
        "error": None,
        "duration_seconds": None,
    }


def _handle_child_completed(event, event_states: dict, scheduled_events: dict, scheduled_times: dict) -> None:
    attrs = event.child_workflow_execution_completed_event_attributes
    task_name = scheduled_events.get(attrs.initiated_event_id)
    if not (task_name and task_name in event_states):
        return
    event_states[task_name]["status"] = "completed"
    event_states[task_name]["output"] = _decode_payload(
        attrs.result.payloads if attrs.result else None
    )
    event_states[task_name]["duration_seconds"] = _elapsed(
        event.event_time, scheduled_times, attrs.initiated_event_id
    )


def _handle_child_failed(event, event_states: dict, scheduled_events: dict, scheduled_times: dict) -> None:
    attrs = event.child_workflow_execution_failed_event_attributes
    task_name = scheduled_events.get(attrs.initiated_event_id)
    if not (task_name and task_name in event_states):
        return
    error_msg = unwrap_temporal_failure(attrs.failure) if attrs.failure else "Child workflow failed"
    event_states[task_name]["status"] = "failed"
    event_states[task_name]["error"] = error_msg
    event_states[task_name]["duration_seconds"] = _elapsed(
        event.event_time, scheduled_times, attrs.initiated_event_id
    )


# Map event field names → handler functions (dispatch table)
_EVENT_HANDLERS = {
    "activity_task_scheduled_event_attributes": _handle_activity_scheduled,
    "activity_task_completed_event_attributes": _handle_activity_completed,
    "activity_task_failed_event_attributes": _handle_activity_failed,
    "start_child_workflow_execution_initiated_event_attributes": _handle_child_initiated,
    "child_workflow_execution_completed_event_attributes": _handle_child_completed,
    "child_workflow_execution_failed_event_attributes": _handle_child_failed,
}


async def _read_rf_file(path) -> Optional[dict]:
    """Read and JSON-parse a single ReactFlow file. Returns None on any error."""
    try:
        text = await asyncio.to_thread(lambda: path.read_text(encoding='utf-8'))
        return json.loads(text)
    except Exception as exc:
        logger.warning(f"Failed to load ReactFlow file {path}: {exc}")
        return None


def _find_fallback_rf_path(visual_workflow_id: str):
    """Locate the best fallback .rf file for a workflow when the versioned one is missing."""
    latest_path = get_latest_workflow(visual_workflow_id)
    if not latest_path:
        return None
    rf_path = latest_path.with_suffix(".rf")
    if rf_path.exists():
        return rf_path
    matches = list(settings.COMPILED_DIR.glob(f"**/*{visual_workflow_id}*.rf"))
    return matches[-1] if matches else None


async def _load_rf_json(visual_workflow_id: str, dsl_hash: Optional[str]) -> dict:
    """Load the ReactFlow canvas JSON for a workflow version, with fallbacks."""
    from .storage_service import find_by_hash

    if dsl_hash:
        rf_path = find_by_hash(visual_workflow_id, dsl_hash, ext=".rf")
        if rf_path and rf_path.exists():
            result = await _read_rf_file(rf_path)
            if result is not None:
                return result

    fallback = _find_fallback_rf_path(visual_workflow_id)
    if fallback:
        result = await _read_rf_file(fallback)
        if result is not None:
            return result

    logger.warning(f"No ReactFlow file found for '{visual_workflow_id}' — returning empty canvas")
    return {"nodes": [], "edges": []}


async def _resolve_visual_id(workflow_id: str, desc) -> str:
    """Resolve the visual workflow ID from memo, falling back to parsing the Temporal workflow ID."""
    visual_id = await get_memo_value(desc, "visual_workflow_id")
    if visual_id:
        return visual_id
    if workflow_id.startswith("rf-"):
        parts = workflow_id.split("-")
        if len(parts) >= 3:
            return "-".join(parts[1:-1])
    return workflow_id


async def _stream_history(handle, workflow_id: str) -> tuple[dict, bool]:
    """Stream Temporal history events and return (event_states, workflow_completed)."""
    event_states: dict = {}
    scheduled_events: dict = {}
    scheduled_times: dict = {}
    workflow_completed = False

    try:
        async for event in handle.fetch_history_events():
            if event.HasField("workflow_execution_completed_event_attributes"):
                workflow_completed = True
                continue
            for field, handler in _EVENT_HANDLERS.items():
                if event.HasField(field):
                    handler(event, event_states, scheduled_events, scheduled_times)
                    break
    except RPCError as exc:
        logger.error(f"Temporal lost connection streaming history for '{workflow_id}': {exc}")
        raise RuntimeError(f"Lost Temporal connection reading workflow history: {exc}") from exc
    except Exception as exc:
        logger.error(f"Unexpected error reading history for '{workflow_id}': {exc}", exc_info=True)
        raise RuntimeError(f"Failed to read workflow history: {exc}") from exc

    return event_states, workflow_completed


def _run_replay(workflow_id: str, rf_json: dict, event_states: dict, workflow_completed: bool) -> list:
    """Run the replay engine with a graceful fallback if it fails."""
    from .replay_engine import propagate_dag_states
    try:
        return propagate_dag_states(rf_json, event_states, workflow_completed)
    except Exception as exc:
        logger.error(f"Replay engine failed for '{workflow_id}': {exc}", exc_info=True)
        return [{"id": name, "name": name, **state} for name, state in event_states.items()]


class ExecutionService:
    """
    Service for managing workflow executions via Temporal.

    Uses a lazy-initialized singleton Temporal client so gRPC channels are
    not leaked per request. Call `shutdown()` on application teardown.
    """

    def __init__(self):
        self._client: Optional[Client] = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> Client:
        """Return the shared Temporal client, creating it lazily on first call."""
        if self._client is not None:
            return self._client
        async with self._client_lock:
            if self._client is None:
                try:
                    self._client = await asyncio.wait_for(
                        Client.connect(settings.TEMPORAL_ADDRESS),
                        timeout=10.0,
                    )
                    logger.info(f"Temporal client connected to {settings.TEMPORAL_ADDRESS}")
                except asyncio.TimeoutError as exc:
                    raise RuntimeError(
                        f"Timed out connecting to Temporal at {settings.TEMPORAL_ADDRESS}"
                    ) from exc
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to connect to Temporal at {settings.TEMPORAL_ADDRESS}: {exc}"
                    ) from exc
        return self._client

    async def shutdown(self) -> None:
        """Close the Temporal client. Call this on application shutdown."""
        if self._client is not None:
            try:
                await self._client.close()
                logger.info("Temporal client closed")
            except Exception as exc:
                logger.warning(f"Error closing Temporal client: {exc}")
            finally:
                self._client = None

    async def execute_workflow(self, workflow_id: str, dsl_hash: str, input_payload: dict) -> Dict:
        """Trigger execution of the compiled DSL matching the given content hash."""
        logger.info(f"Triggering execution for workflow: {workflow_id} (hash: {dsl_hash})")

        from .storage_service import find_by_hash
        dsl_path = find_by_hash(workflow_id, dsl_hash, ext=".json")
        if not dsl_path:
            raise FileNotFoundError(
                f"No compiled DSL found matching hash '{dsl_hash}' for workflow ID: {workflow_id}"
            )

        try:
            dsl = load_dsl(dsl_path)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise ValueError(f"Compiled DSL for '{workflow_id}' is unreadable: {exc}") from exc

        doc = dsl.get("document", {})
        workflow_type = doc.get("workflowType")
        task_queue = doc.get("taskQueue", settings.DEFAULT_TASK_QUEUE)

        if not workflow_type:
            raise ValueError(f"Compiled DSL in {dsl_path} is missing 'document.workflowType'")

        client = await self._get_client()
        temporal_workflow_id = f"rf-{workflow_id}-{uuid.uuid4().hex[:8]}"

        logger.info(
            f"Starting workflow type '{workflow_type}' on queue '{task_queue}' "
            f"with Temporal ID: {temporal_workflow_id} (hash: {dsl_hash})"
        )

        try:
            handle = await client.start_workflow(
                workflow_type,
                input_payload,
                id=temporal_workflow_id,
                task_queue=task_queue,
                memo={"dsl_hash": dsl_hash, "visual_workflow_id": workflow_id},
            )
        except RPCError as exc:
            raise RuntimeError(
                f"Temporal rejected workflow start for '{workflow_type}': {exc}"
            ) from exc

        return {
            "workflow_id": temporal_workflow_id,
            "run_id": handle.first_execution_run_id or handle.run_id,
            "workflow_type": workflow_type,
            "status": "RUNNING",
        }

    async def list_executions(self, workflow_id: str) -> List[Dict]:
        """List all executions of a workflow using Temporal visibility query."""
        logger.info(f"Listing executions for workflow: {workflow_id}")
        client = await self._get_client()
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
        except Exception as exc:
            logger.error(f"Failed to list executions from Temporal: {exc}")
            raise RuntimeError(f"Temporal visibility query failed: {exc}") from exc

        return sorted(executions, key=lambda x: x["start_time"] or "", reverse=True)

    async def get_execution_trace(self, workflow_id: str, run_id: str) -> Dict:
        """Fetch and parse execution event history for a run, mapped back to ReactFlow nodes."""
        logger.info(f"Fetching trace for workflow '{workflow_id}' run: {run_id}")
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id, run_id=run_id)

        # Let RPCError (including NOT_FOUND) propagate — the router maps status codes to HTTP
        desc = await handle.describe()

        workflow_status = desc.status.name if hasattr(desc.status, "name") else str(desc.status)
        dsl_hash = await get_memo_value(desc, "dsl_hash")
        visual_workflow_id = await _resolve_visual_id(workflow_id, desc)

        event_states, workflow_completed = await _stream_history(handle, workflow_id)
        rf_json = await _load_rf_json(visual_workflow_id, dsl_hash)
        final_steps = _run_replay(workflow_id, rf_json, event_states, workflow_completed)

        return {"run_id": run_id, "status": workflow_status, "steps": final_steps}

    async def cancel_workflow(self, workflow_id: str, run_id: str) -> None:
        """Cancel a running workflow execution."""
        logger.info(f"Cancelling workflow: {workflow_id} (run: {run_id})")
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id, run_id=run_id)
        try:
            await handle.cancel()
        except RPCError as exc:
            raise RuntimeError(f"Failed to cancel workflow '{workflow_id}': {exc}") from exc

    async def terminate_workflow(self, workflow_id: str, run_id: str, reason: str = "Terminated by user") -> None:
        """Forcefully terminate a running workflow execution."""
        logger.info(f"Terminating workflow: {workflow_id} (run: {run_id})")
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id, run_id=run_id)
        try:
            await handle.terminate(reason=reason)
        except RPCError as exc:
            raise RuntimeError(f"Failed to terminate workflow '{workflow_id}': {exc}") from exc


execution_service = ExecutionService()
