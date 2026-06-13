import json
import unittest
from pathlib import Path
from unittest.mock import patch
from app.services.compiler_service import CompilerService


class TestCompilerService(unittest.TestCase):
    def setUp(self):
        self.service = CompilerService()
        self.base_dir = Path(__file__).resolve().parent
        self.fixtures_dir = self.base_dir / "fixtures" / "valid"

    def test_compile_valid_workflow(self):
        # Load single action valid fixture (contains actual tasks)
        fixture_path = self.fixtures_dir / "03_single_action.json"
        with fixture_path.open("r") as f:
            workflow = json.load(f)

        # It should compile and validate successfully
        dsl = self.service.compile(
            workflow=workflow,
            workflow_type="action-pipeline",
            task_queue="default"
        )
        self.assertIn("document", dsl)
        self.assertIn("do", dsl)
        self.assertGreater(len(dsl["do"]), 0)

    def test_compile_validation_failure(self):
        # Load single action valid fixture
        fixture_path = self.fixtures_dir / "03_single_action.json"
        with fixture_path.open("r") as f:
            workflow = json.load(f)

        # Mock compile_workflow_to_dsl to return an invalid schema structure
        # (e.g. missing required "document" property)
        with patch("app.services.compiler_service.compile_workflow_to_dsl") as mock_compile:
            mock_compile.return_value = {
                "invalid_dsl": True
            }

            with self.assertRaises(ValueError) as ctx:
                self.service.compile(
                    workflow=workflow,
                    workflow_type="invalid-test",
                    task_queue="default"
                )

            self.assertIn("Zigflow validation failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
