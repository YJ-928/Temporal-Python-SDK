"""
Compiler snapshot testing suite.

Loads valid workflow fixtures, compiles them, and compares against stored snapshots.
Supports UPDATE_SNAPSHOTS=true environment variable to regenerate snapshots.
"""
import os
import json
import unittest
from pathlib import Path
from app.compiler.workflow_compiler import compile_workflow_to_dsl


class TestCompilerSnapshots(unittest.TestCase):
    def setUp(self):
        self.base_dir = Path(__file__).resolve().parent
        self.fixtures_dir = self.base_dir / "fixtures" / "valid"
        self.snapshots_dir = self.base_dir / "snapshots"
        self.update_snapshots = os.environ.get("UPDATE_SNAPSHOTS") == "true"

        # Ensure snapshots directory exists
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def test_golden_snapshots(self):
        self.assertTrue(self.fixtures_dir.is_dir(), f"Fixtures directory missing: {self.fixtures_dir}")
        fixture_files = [f for f in self.fixtures_dir.iterdir() if f.suffix == ".json"]
        self.assertGreater(len(fixture_files), 0, "No valid fixtures found")

        for fixture_path in fixture_files:
            with fixture_path.open("r") as f:
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
            snapshot_name = f"{fixture_path.stem}_snapshot.json"
            snapshot_path = self.snapshots_dir / snapshot_name

            if self.update_snapshots:
                # Save the new snapshot
                with snapshot_path.open("w") as sf:
                    json.dump(dsl, sf, indent=2)
            else:
                # Assert snapshot exists, if not fail
                if not snapshot_path.exists():
                    self.fail(
                        f"Snapshot {snapshot_name} is missing. "
                        f"Run with UPDATE_SNAPSHOTS=true to generate it."
                    )

                # Load expected snapshot
                with snapshot_path.open("r") as sf:
                    expected_dsl = json.load(sf)

                # Compare normalized dictionaries
                self.assertEqual(
                    dsl,
                    expected_dsl,
                    f"DSL compilation mismatch for {fixture_path.name}. "
                    f"Check differences or run with UPDATE_SNAPSHOTS=true to regenerate."
                )
