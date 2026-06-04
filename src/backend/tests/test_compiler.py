"""
Compiler snapshot testing suite.

Loads valid workflow fixtures, compiles them, and compares against stored snapshots.
Supports UPDATE_SNAPSHOTS=true environment variable to regenerate snapshots.
"""
import os
import json
import unittest
from app.compiler.workflow_compiler import compile_workflow_to_dsl


class TestCompilerSnapshots(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.fixtures_dir = os.path.join(self.base_dir, "fixtures", "valid")
        self.snapshots_dir = os.path.join(self.base_dir, "snapshots")
        self.update_snapshots = os.environ.get("UPDATE_SNAPSHOTS") == "true"

        # Ensure snapshots directory exists
        os.makedirs(self.snapshots_dir, exist_ok=True)

    def test_golden_snapshots(self):
        self.assertTrue(os.path.isdir(self.fixtures_dir), f"Fixtures directory missing: {self.fixtures_dir}")
        fixture_files = [f for f in os.listdir(self.fixtures_dir) if f.endswith(".json")]
        self.assertGreater(len(fixture_files), 0, "No valid fixtures found")

        for filename in fixture_files:
            fixture_path = os.path.join(self.fixtures_dir, filename)
            with open(fixture_path, "r") as f:
                workflow = json.load(f)

            workflow_type = workflow.get("workflow_type", "test-type")
            task_queue = workflow.get("task_queue", "default")

            # Compile to DSL
            dsl = compile_workflow_to_dsl(
                workflow,
                workflow_type=workflow_type,
                task_queue=task_queue
            )

            # Determine snapshot path
            snapshot_name = f"{os.path.splitext(filename)[0]}_snapshot.json"
            snapshot_path = os.path.join(self.snapshots_dir, snapshot_name)

            if self.update_snapshots:
                # Save the new snapshot
                with open(snapshot_path, "w") as sf:
                    json.dump(dsl, sf, indent=2)
            else:
                # Assert snapshot exists, if not fail
                if not os.path.exists(snapshot_path):
                    self.fail(
                        f"Snapshot {snapshot_name} is missing. "
                        f"Run with UPDATE_SNAPSHOTS=true to generate it."
                    )

                # Load expected snapshot
                with open(snapshot_path, "r") as sf:
                    expected_dsl = json.load(sf)

                # Compare normalized dictionaries
                self.assertEqual(
                    dsl,
                    expected_dsl,
                    f"DSL compilation mismatch for {filename}. "
                    f"Check differences or run with UPDATE_SNAPSHOTS=true to regenerate."
                )


if __name__ == "__main__":
    unittest.main()
