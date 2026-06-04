"""
Contract validation tests comparing frontend exported payloads against backend Pydantic schemas.
"""
import os
import json
import unittest
from app.schemas.workflow_sch import CompileRequest
from app.compiler.workflow_compiler import compile_workflow_to_dsl
from pydantic import ValidationError


class TestContracts(unittest.TestCase):
    def test_contracts_validate(self):
        # Determine paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        contracts_dir = os.path.join(base_dir, "contracts")

        # Get list of contract files
        self.assertTrue(os.path.isdir(contracts_dir), f"Contracts directory missing: {contracts_dir}")
        contract_files = [f for f in os.listdir(contracts_dir) if f.endswith(".json")]
        self.assertGreaterEqual(len(contract_files), 2, "Should have at least 2 contract fixtures")

        for filename in contract_files:
            file_path = os.path.join(contracts_dir, filename)
            with open(file_path, "r") as f:
                payload = json.load(f)

            # Assert Pydantic validation succeeds
            try:
                CompileRequest.model_validate(payload)
            except ValidationError as e:
                self.fail(f"Contract payload {filename} failed backend Pydantic validation: {e}")

            # Assert compilation succeeds
            try:
                compile_workflow_to_dsl(
                    payload["workflow"],
                    workflow_type=payload.get("workflow_type", "workflow-builder"),
                    task_queue=payload.get("task_queue", "workflow-builder")
                )
            except Exception as e:
                self.fail(f"Contract payload {filename} failed compilation: {e}")


if __name__ == "__main__":
    unittest.main()
