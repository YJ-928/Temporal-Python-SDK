"""
Runtime Failure Unwrapping and Registration Lifecycle Tests.
"""
import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.execution_service import unwrap_temporal_failure
from app.services.registration_service import RegistrationService, REGISTRATIONS_FILE


class MockFailureInfo:
    def __init__(self, message):
        self.message = message


class MockFailure:
    def __init__(self, message=None, cause=None, application_failure_info=None, activity_failure_info=None):
        self.message = message
        self.cause = cause
        self.application_failure_info = application_failure_info
        self.activity_failure_info = activity_failure_info

    def HasField(self, field_name):
        if field_name == "cause":
            return self.cause is not None
        if field_name == "application_failure_info":
            return self.application_failure_info is not None
        if field_name == "activity_failure_info":
            return self.activity_failure_info is not None
        return False


class TestRuntimeFailures(unittest.TestCase):
    def test_unwrap_temporal_failure_scenarios(self):
        """Verify that various agent/runtime failures unwrap to human-readable error messages."""

        # 1. 400 Bad Request / Validation Failure
        # Temporal wraps real error in cause: outer message is generic, inner cause has the real error
        inner_400 = MockFailure(message="HTTP status code 400: Detail: Invalid email format")
        fail_400 = MockFailure(message="Activity task failed", cause=inner_400)
        msg_400 = unwrap_temporal_failure(fail_400)
        self.assertEqual(msg_400, "HTTP status code 400: Detail: Invalid email format")

        # 2. Timeout Failure — message is the real error directly (no wrapper)
        timeout_fail = MockFailure(message="Activity timeout: StartToClose")
        msg_timeout = unwrap_temporal_failure(timeout_fail)
        self.assertEqual(msg_timeout, "Activity timeout: StartToClose")

        # 3. Connection Refused — real error in cause
        inner_conn = MockFailure(message="ConnectError: [Errno 111] Connection refused")
        fail_conn = MockFailure(message="Activity task failed", cause=inner_conn)
        msg_conn = unwrap_temporal_failure(fail_conn)
        self.assertEqual(msg_conn, "ConnectError: [Errno 111] Connection refused")

        # 4. Malformed JSON — real error in cause
        inner_json = MockFailure(message="JSONDecodeError: Expecting value: line 1 column 1 (char 0)")
        fail_json = MockFailure(message="Activity task failed", cause=inner_json)
        msg_json = unwrap_temporal_failure(fail_json)
        self.assertEqual(msg_json, "JSONDecodeError: Expecting value: line 1 column 1 (char 0)")

        # 5. Nested cause unwrap: workflow failure -> activity failure -> real error
        inner_cause = MockFailure(message="Root cause error")
        nested_cause = MockFailure(message="Activity task failed", cause=inner_cause)
        top_failure = MockFailure(message="Workflow execution failed", cause=nested_cause)
        msg_nested = unwrap_temporal_failure(top_failure)
        self.assertEqual(msg_nested, "Root cause error")


class TestRegistrationLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp_reg_file = Path(str(REGISTRATIONS_FILE) + ".test")
        self.patcher = patch("app.services.registration_service.REGISTRATIONS_FILE", self.temp_reg_file)
        self.patcher.start()
        # Clean up any residual test file
        if self.temp_reg_file.exists():
            self.temp_reg_file.unlink()

    def tearDown(self):
        self.patcher.stop()
        if self.temp_reg_file.exists():
            self.temp_reg_file.unlink()

    def test_persistence_across_restart(self):
        """Verify workflow registration persists to storage and survives service restart (instance recreation)."""
        service_instance_1 = RegistrationService()

        # Verify initial state
        self.assertFalse(service_instance_1.is_registered("hash-123"))

        # Register a workflow
        with patch.object(service_instance_1, "_validate_dsl_file", return_value=True), \
             patch.object(service_instance_1, "trigger_reload", return_value=AsyncMock()), \
             patch("asyncio.create_task"):
            entry = service_instance_1.register_workflow(
                dsl_hash="hash-123",
                workflow_id="wf-test",
                workflow_type="test-type",
                file_path=Path("dummy_path")
            )
            self.assertTrue(entry["registered"])

        self.assertTrue(service_instance_1.is_registered("hash-123"))

        # Recreate service instance (simulating restart)
        service_instance_2 = RegistrationService()
        self.assertTrue(service_instance_2.is_registered("hash-123"))

        # Check details
        regs = service_instance_2.get_all_registrations()
        self.assertEqual(regs["hash-123"]["workflow_id"], "wf-test")
        self.assertEqual(regs["hash-123"]["workflow_type"], "test-type")

    def test_validation_failure_prevents_registration(self):
        """Verify that invalid workflows fail registration validation and are not marked as registered."""
        service = RegistrationService()

        with patch.object(service, "_validate_dsl_file", return_value=False):
            entry = service.register_workflow(
                dsl_hash="hash-bad",
                workflow_id="wf-bad",
                workflow_type="bad-type",
                file_path=Path("dummy_bad_path")
            )
            self.assertFalse(entry["registered"])
            self.assertFalse(entry["validated"])

        self.assertFalse(service.is_registered("hash-bad"))

    def test_reload_concurrency_locking(self):
        """Verify reload scheduling utilizes lock batching and concurrency protection."""
        service = RegistrationService()

        # Mock background daemon stop/start scripts to prevent actual process execution
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()

            # Use a side_effect that yields control to other async tasks
            async def mock_wait():
                await asyncio.sleep(0.01)

            mock_process.wait = mock_wait
            mock_exec.return_value = mock_process

            # Call reload multiple times concurrently
            async def run_concurrent_reloads():
                tasks = [
                    asyncio.create_task(service.trigger_reload()),
                    asyncio.create_task(service.trigger_reload()),
                    asyncio.create_task(service.trigger_reload())
                ]
                await asyncio.gather(*tasks)

            asyncio.run(run_concurrent_reloads())

            # Since trigger_reload runs sequentially by utilizing self.reload_pending and lock,
            # it should run exactly twice: the first active reload, and one queued reload covering subsequent requests.
            # Each reload calls create_subprocess_exec twice (once stop, once start).
            # So 2 runs * 2 calls = 4 calls.
            self.assertEqual(mock_exec.call_count, 4)
