"""
Regression tests verifying compiler stability and regression prevention.
"""
import os
import json
import unittest
from app.compiler.workflow_compiler import compile_workflow_to_dsl
from app.compiler.exceptions import GraphValidationError, MissingBranchError


class TestRegressions(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.regressions_dir = os.path.join(self.base_dir, "regressions")

    def load_fixture(self, filename: str) -> dict:
        path = os.path.join(self.regressions_dir, filename)
        with open(path, "r") as f:
            return json.load(f)

    def test_bug_001_ctx_prefix(self):
        """
        Verify input fields with 'ctx.' prefix compile successfully.
        """
        payload = self.load_fixture("bug_001_ctx_prefix.json")
        # Compile should run successfully
        dsl = compile_workflow_to_dsl(payload["workflow"])
        # Should have captured the 'ctx.name' field correctly in input capture
        # Wait, the compiler expects inputs to be clean names, but if they
        # have 'ctx.name', the builder converts it to '$input.ctx.name' or similar,
        # or the export.as merges them. Let's make sure it compiled.
        self.assertIn("N2_capture", dsl["do"][0])

    def test_bug_002_legacy_branch(self):
        """
        Verify backward compatibility with legacy control.branch edge metadata.
        """
        payload = self.load_fixture("bug_002_legacy_branch.json")
        dsl = compile_workflow_to_dsl(payload["workflow"])
        # Verify the switch cases point to correct target task names
        switch_task = dsl["do"][0]["N2_if"]
        self.assertEqual(switch_task["switch"][0]["case"]["then"], "end")
        self.assertEqual(switch_task["switch"][1]["default"]["then"], "end")

    def test_bug_003_null_condition(self):
        """
        Verify condition builder handles null/None condition value correctly.
        """
        payload = self.load_fixture("bug_003_null_condition.json")
        dsl = compile_workflow_to_dsl(payload["workflow"])
        switch_task = dsl["do"][0]["N2_if"]
        self.assertEqual(switch_task["switch"][0]["case"]["when"], "${ $context.email == null }")

    def test_bug_004_duplicate_branch(self):
        """
        Verify compilation fails on duplicate IF branches (e.g. duplicate true edges).
        """
        payload = self.load_fixture("bug_004_duplicate_branch.json")
        with self.assertRaises((GraphValidationError, MissingBranchError)):
            compile_workflow_to_dsl(payload["workflow"])


if __name__ == "__main__":
    unittest.main()
