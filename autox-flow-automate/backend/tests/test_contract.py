"""
Contract validation tests comparing frontend exported payloads against backend Pydantic schemas.
"""
import json
import unittest
from pathlib import Path
from src.schema.workflow.workflow_sch import CompileRequest
from src.compiler.workflow_compiler import compile_workflow_to_dsl
from pydantic import ValidationError


class TestContracts(unittest.TestCase):
    def test_contracts_validate(self):
        # Determine paths
        base_dir = Path(__file__).resolve().parent
        contracts_dir = base_dir / "contracts"

        # Get list of contract files
        self.assertTrue(contracts_dir.is_dir(), f"Contracts directory missing: {contracts_dir}")
        contract_files = [f for f in contracts_dir.iterdir() if f.suffix == ".json"]
        self.assertGreaterEqual(len(contract_files), 2, "Should have at least 2 contract fixtures")

        for file_path in contract_files:
            with file_path.open("r") as f:
                payload = json.load(f)

            # Assert Pydantic validation succeeds
            try:
                CompileRequest.model_validate(payload)
            except ValidationError as e:
                self.fail(f"Contract payload {file_path.name} failed backend Pydantic validation: {e}")

            # Assert compilation succeeds
            try:
                compile_workflow_to_dsl(
                    payload["workflow"],
                    workflow_type=payload.get("workflow_type", "flowautomate"),
                    task_queue=payload.get("task_queue", "flowautomate")
                )
            except Exception as e:
                self.fail(f"Contract payload {file_path.name} failed compilation: {e}")


if __name__ == "__main__":
    unittest.main()
