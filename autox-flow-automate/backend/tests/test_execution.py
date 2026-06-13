import json
import unittest
from datetime import timezone
from unittest.mock import patch, MagicMock, AsyncMock
from src.service.execution_service import ExecutionService
from src.service.storage_service import save_dsl


class MockWorkflow:
    def __init__(self, workflow_id, run_id, workflow_type, status, start_time=None, close_time=None):
        self.id = workflow_id
        self.run_id = run_id
        self.workflow_type = workflow_type
        self.status = MagicMock()
        self.status.name = status
        self.start_time = start_time
        self.close_time = close_time


class MockAsyncIterator:
    def __init__(self, items):
        self.items = items
        self.idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.idx >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.idx]
        self.idx += 1
        return item


class TestExecutionServiceHelper:
    def set_up_helper(self):
        self.service = ExecutionService()
        self.workflow_id = "test-flow"
        self.dsl = {
            "document": {
                "dsl": "1.0.0",
                "taskQueue": "default",
                "workflowType": "test-flow-type",
                "version": "1.0.0"
            },
            "do": [{"say_hello": {"set": {"result": "hello"}}}]
        }
        self.saved_path = save_dsl(
            self.dsl,
            workflow_id=self.workflow_id,
            rf_json={
                "nodes": [
                    {"id": "START", "type": "start"},
                    {"id": "say_hello", "type": "activity"},
                    {"id": "END", "type": "end"}
                ],
                "edges": [
                    {"source": "START", "target": "say_hello"},
                    {"source": "say_hello", "target": "END"}
                ]
            }
        )

    def tear_down_helper(self):
        if self.saved_path.exists():
            self.saved_path.unlink()
        rf_path = self.saved_path.with_name(self.saved_path.name.replace(".json", ".rf"))
        if rf_path.exists():
            rf_path.unlink()

    async def run_execute_workflow(self, mock_connect):
        mock_client = MagicMock()
        mock_handle = MagicMock()
        mock_handle.run_id = None
        mock_handle.first_execution_run_id = "run-12345"

        # start_workflow is a coroutine method
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)
        mock_connect.return_value = mock_client

        dsl_hash = self.saved_path.stem.split("-")[-1]
        result = await self.service.execute_workflow(
            workflow_id=self.workflow_id,
            dsl_hash=dsl_hash,
            input_payload={"user_id": "abc"}
        )

        assert result["workflow_id"].startswith(f"rf-{self.workflow_id}-")
        assert result["run_id"] == "run-12345"
        assert result["workflow_type"] == "test-flow-type"
        mock_client.start_workflow.assert_called_once()

    async def run_list_executions(self, mock_connect):
        from datetime import datetime

        mock_client = MagicMock()
        t1 = datetime(2026, 6, 4, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 4, 11, 0, 0, tzinfo=timezone.utc)
        mock_run_1 = MockWorkflow("rf-test-flow-123", "run-1", "test-flow-type", "COMPLETED", t1)
        mock_run_2 = MockWorkflow("rf-test-flow-456", "run-2", "test-flow-type", "RUNNING", t2)

        # list_workflows is a sync method returning an async iterator
        mock_client.list_workflows = MagicMock(return_value=MockAsyncIterator([mock_run_1, mock_run_2]))
        mock_connect.return_value = mock_client

        results = await self.service.list_executions(self.workflow_id)

        assert len(results) == 2
        # Sorted descending by start time: run-2 (11:00) comes first, then run-1 (10:00)
        assert results[0]["run_id"] == "run-2"
        assert results[1]["run_id"] == "run-1"

    async def run_get_execution_trace(self, mock_connect):
        mock_client = MagicMock()
        mock_run = MockWorkflow("rf-test-flow-123", "run-1", "test-flow-type", "COMPLETED")
        mock_client.list_workflows.return_value = MockAsyncIterator([mock_run])

        # Construct mock history events
        mock_handle = MagicMock()

        # 1. Activity Scheduled event
        mock_event_1 = MagicMock()
        mock_event_1.event_id = 5
        mock_event_1.HasField.side_effect = lambda field: field == "activity_task_scheduled_event_attributes"

        mock_payload_input = MagicMock()
        mock_payload_input.data = json.dumps({"test_input": "val"}).encode("utf-8")

        mock_payload_metadata = MagicMock()
        mock_payload_metadata.data = json.dumps({
            "context": None,
            "data": {
                "task": {
                    "name": "N3_get_user"
                }
            }
        }).encode("utf-8")

        mock_attrs_1 = MagicMock()
        mock_attrs_1.input.payloads = [mock_payload_input, None, mock_payload_metadata]
        mock_event_1.activity_task_scheduled_event_attributes = mock_attrs_1

        # 2. Activity Completed event
        mock_event_2 = MagicMock()
        mock_event_2.event_id = 6
        mock_event_2.HasField.side_effect = lambda field: field == "activity_task_completed_event_attributes"

        mock_attrs_2 = MagicMock()
        mock_attrs_2.scheduled_event_id = 5
        mock_payload_output = MagicMock()
        mock_payload_output.data = json.dumps({"user_name": "John Doe"}).encode("utf-8")
        mock_attrs_2.result.payloads = [mock_payload_output]
        mock_event_2.activity_task_completed_event_attributes = mock_attrs_2

        # 3. Workflow Completed event
        mock_event_3 = MagicMock()
        mock_event_3.event_id = 7
        mock_event_3.HasField.side_effect = lambda field: field == "workflow_execution_completed_event_attributes"

        mock_handle.fetch_history_events.return_value = MockAsyncIterator([mock_event_1, mock_event_2, mock_event_3])
        mock_client.get_workflow_handle.return_value = mock_handle
        mock_connect.return_value = mock_client

        # Override DSL to have multiple nodes: N2 (set) -> N3 (call) -> END
        self.dsl = {
            "document": {
                "dsl": "1.0.0",
                "taskQueue": "default",
                "workflowType": "test-flow-type",
                "version": "1.0.0"
            },
            "do": [
                {"N2_capture": {"set": {"id": "123"}}},
                {"N3_get_user": {"call": "http", "with": {"method": "get"}}}
            ]
        }
        # Re-save the DSL and RF json for this run
        if self.saved_path.exists():
            self.saved_path.unlink()
        rf_old_path = self.saved_path.with_name(self.saved_path.name.replace(".json", ".rf"))
        if rf_old_path.exists():
            rf_old_path.unlink()

        self.saved_path = save_dsl(
            self.dsl,
            workflow_id="test-flow",
            rf_json={
                "nodes": [
                    {"id": "START", "type": "start"},
                    {"id": "N2_capture", "type": "input"},
                    {"id": "N3_get_user", "type": "activity"},
                    {"id": "END", "type": "end"}
                ],
                "edges": [
                    {"source": "START", "target": "N2_capture"},
                    {"source": "N2_capture", "target": "N3_get_user"},
                    {"source": "N3_get_user", "target": "END"}
                ]
            }
        )

        dsl_hash = self.saved_path.stem.split("-")[-1]
        mock_desc = MagicMock()
        mock_desc.memo = {
            "dsl_hash": dsl_hash,
            "visual_workflow_id": "test-flow"
        }
        mock_handle.describe = AsyncMock(return_value=mock_desc)

        results = await self.service.get_execution_trace("rf-test-flow-123", "run-1")

        assert results["run_id"] == "run-1"
        steps = results["steps"]
        assert steps["START"]["status"] == "completed"
        assert steps["N2_capture"]["status"] == "completed"  # Propagated!
        assert steps["N3_get_user"]["status"] == "completed"  # From event!
        assert steps["N3_get_user"]["output"] == {"user_name": "John Doe"}
        assert steps["END"]["status"] == "completed"

    async def run_cancel_workflow(self, mock_connect):
        mock_client = MagicMock()
        mock_handle = MagicMock()
        mock_client.get_workflow_handle.return_value = mock_handle
        mock_connect.return_value = mock_client
        mock_handle.cancel = AsyncMock()

        await self.service.cancel_workflow("rf-test-flow-123", "run-1")
        mock_client.get_workflow_handle.assert_called_once_with("rf-test-flow-123", run_id="run-1")
        mock_handle.cancel.assert_called_once()

    async def run_terminate_workflow(self, mock_connect):
        mock_client = MagicMock()
        mock_handle = MagicMock()
        mock_client.get_workflow_handle.return_value = mock_handle
        mock_connect.return_value = mock_client
        mock_handle.terminate = AsyncMock()

        await self.service.terminate_workflow("rf-test-flow-123", "run-1", reason="test")
        mock_client.get_workflow_handle.assert_called_once_with("rf-test-flow-123", run_id="run-1")
        mock_handle.terminate.assert_called_once_with(reason="test")


class TestExecutionService(unittest.TestCase):
    def setUp(self):
        self.helper = TestExecutionServiceHelper()
        self.helper.set_up_helper()

    def tearDown(self):
        self.helper.tear_down_helper()

    @patch("src.service.execution_service.Client.connect")
    def test_execute_workflow(self, mock_connect):
        import asyncio
        asyncio.run(self.helper.run_execute_workflow(mock_connect))

    @patch("src.service.execution_service.Client.connect")
    def test_list_executions(self, mock_connect):
        import asyncio
        asyncio.run(self.helper.run_list_executions(mock_connect))

    @patch("src.service.execution_service.Client.connect")
    def test_get_execution_trace(self, mock_connect):
        import asyncio
        asyncio.run(self.helper.run_get_execution_trace(mock_connect))

    @patch("src.service.execution_service.Client.connect")
    def test_cancel_workflow(self, mock_connect):
        import asyncio
        asyncio.run(self.helper.run_cancel_workflow(mock_connect))

    @patch("src.service.execution_service.Client.connect")
    def test_terminate_workflow(self, mock_connect):
        import asyncio
        asyncio.run(self.helper.run_terminate_workflow(mock_connect))

    def test_get_memo_value(self):
        import asyncio
        from unittest.mock import AsyncMock
        from src.service.execution_service import get_memo_value

        async def run_tests():
            # Test None input
            assert await get_memo_value(None, "key") is None

            # Test memo_value returns value (primary path)
            mock_desc = MagicMock()
            mock_desc.memo_value = AsyncMock(return_value="val")
            assert await get_memo_value(mock_desc, "key") == "val"

            # Test fallback via await desc.memo() dict
            mock_desc2 = MagicMock(spec=[])
            mock_desc2.memo = AsyncMock(return_value={"key": "memo-val"})
            assert await get_memo_value(mock_desc2, "key") == "memo-val"

            # Test missing key via memo() fallback returns None
            mock_desc3 = MagicMock(spec=[])
            mock_desc3.memo = AsyncMock(return_value={"other": "x"})
            assert await get_memo_value(mock_desc3, "key") is None

        asyncio.run(run_tests())

    def test_replay_engine_dag_parallel_join(self):
        from src.service.replay_engine import propagate_dag_states

        # Create a DAG with parallel execution, branch skip, and a join node:
        #           START
        #             │
        #            IF (evaluates to true, true branch is taken)
        #           /  \
        #        True  False
        #         /      \
        #        A        B
        #         \      /
        #          \    /
        #           JOIN (inline node)
        #             │
        #            END
        rf_json = {
            "nodes": [
                {"id": "START", "type": "start"},
                {"id": "IF_NODE", "type": "if"},
                {"id": "A", "type": "activity"},
                {"id": "B", "type": "activity"},
                {"id": "JOIN", "type": "input"}, # inline join node
                {"id": "END", "type": "end"}
            ],
            "edges": [
                {"source": "START", "target": "IF_NODE"},
                {"source": "IF_NODE", "target": "A", "data": {"condition": "true"}},
                {"source": "IF_NODE", "target": "B", "data": {"condition": "false"}},
                {"source": "A", "target": "JOIN"},
                {"source": "B", "target": "JOIN"},
                {"source": "JOIN", "target": "END"}
            ]
        }

        # IF_NODE is completed. A completes. B never runs (skipped).
        event_states = {
            "IF_NODE": {"status": "completed"},
            "A": {"status": "completed", "output": "A_done"}
        }

        results = propagate_dag_states(rf_json, event_states, workflow_completed=True)

        # Assert A is completed
        assert results["A"]["status"] == "completed"
        # Assert B is marked skipped (because IF_NODE was completed, A executed, so False branch was skipped)
        assert results["B"]["status"] == "skipped"
        # Assert JOIN is completed (because A completed, and the only other parent B was skipped)
        assert results["JOIN"]["status"] == "completed"
        # Assert END is completed (since it's a completed workflow and JOIN completed)
        assert results["END"]["status"] == "completed"


if __name__ == "__main__":
    unittest.main()
