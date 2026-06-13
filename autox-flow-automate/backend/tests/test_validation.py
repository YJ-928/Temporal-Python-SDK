"""
Unit tests for schema and graph validation failures.
"""
import json
import unittest
from pathlib import Path
from app.compiler import compile_workflow_to_dsl
from app.compiler.exceptions import (
    WorkflowValidationError,
    GraphValidationError,
    CycleDetectedError,
    MissingBranchError,
)
from app.compiler.graph import resolve_task_name

class TestCompilerValidation(unittest.TestCase):
    def test_missing_start(self):
        workflow = {
            "nodes": [
                {"id": "N2", "type": "END", "data": {}}
            ],
            "edges": []
        }
        with self.assertRaises(GraphValidationError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("exactly one START node", str(ctx.exception))

    def test_missing_end(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}}
            ],
            "edges": []
        }
        with self.assertRaises(GraphValidationError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("at least one END node", str(ctx.exception))

    def test_multiple_starts(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "START", "data": {}},
                {"id": "N3", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N3"}
            ]
        }
        with self.assertRaises(GraphValidationError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("exactly one START node", str(ctx.exception))

    def test_cycle_detection(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "ACTION", "data": {"operation": "op", "inputs": {}, "output": "out"}},
                {"id": "N3", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N2"},
                {"id": "E2", "source": "N2", "target": "N2"},
                {"id": "E3", "source": "N2", "target": "N3"}
            ]
        }
        with self.assertRaises(CycleDetectedError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("contains a cycle", str(ctx.exception))

    def test_missing_if_branch(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "IF", "data": {"left": "x", "operator": "==", "right": True}},
                {"id": "N3", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N2"},
                {"id": "E2", "source": "N2", "target": "N3", "branch": "true"}
            ]
        }
        with self.assertRaises(MissingBranchError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("exactly one 'true' branch and exactly one 'false' branch", str(ctx.exception))

    def test_duplicate_if_branch(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "IF", "data": {"left": "x", "operator": "==", "right": True}},
                {"id": "N3", "type": "END", "data": {}},
                {"id": "N4", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N2"},
                {"id": "E2", "source": "N2", "target": "N3", "branch": "true"},
                {"id": "E3", "source": "N2", "target": "N4", "branch": "true"}
            ]
        }
        with self.assertRaises(MissingBranchError):
            compile_workflow_to_dsl(workflow)

    def test_end_outgoing_edges(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "END", "data": {}},
                {"id": "N3", "type": "ACTION", "data": {"operation": "op", "inputs": {}, "output": "out"}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N2"},
                {"id": "E2", "source": "N2", "target": "N3"}
            ]
        }
        with self.assertRaises(GraphValidationError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("cannot have outgoing edges", str(ctx.exception))

    def test_unreachable_node(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "END", "data": {}},
                {"id": "N3", "type": "ACTION", "data": {"operation": "op", "inputs": {}, "output": "out"}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N2"}
            ]
        }
        with self.assertRaises(GraphValidationError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("Unreachable nodes found", str(ctx.exception))

    def test_action_missing_operation(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "ACTION", "data": {"output": "out", "inputs": {}}}, # missing operation
                {"id": "N3", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N2"},
                {"id": "E2", "source": "N2", "target": "N3"}
            ]
        }
        with self.assertRaises(WorkflowValidationError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("Field required", str(ctx.exception))

    def test_action_missing_output(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "ACTION", "data": {"operation": "op", "inputs": {}}}, # missing output
                {"id": "N3", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N2"},
                {"id": "E2", "source": "N2", "target": "N3"}
            ]
        }
        with self.assertRaises(WorkflowValidationError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("Field required", str(ctx.exception))

    def test_agent_missing_agent(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "AGENT", "data": {}}, # missing agent
                {"id": "N3", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N2"},
                {"id": "E2", "source": "N2", "target": "N3"}
            ]
        }
        with self.assertRaises(WorkflowValidationError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("Field required", str(ctx.exception))

    def test_input_empty_inputs(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "INPUT", "data": {"inputs": []}}, # empty inputs
                {"id": "N3", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N2"},
                {"id": "E2", "source": "N2", "target": "N3"}
            ]
        }
        with self.assertRaises(WorkflowValidationError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("at least 1 item", str(ctx.exception))

    def test_output_empty_outputs(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "OUTPUT", "data": {"outputs": []}}, # empty outputs
                {"id": "N3", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N2"},
                {"id": "E2", "source": "N2", "target": "N3"}
            ]
        }
        with self.assertRaises(WorkflowValidationError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("at least 1 item", str(ctx.exception))

    def test_if_missing_operator(self):
        workflow = {
            "nodes": [
                {"id": "N1", "type": "START", "data": {}},
                {"id": "N2", "type": "IF", "data": {"left": "x", "right": True}}, # missing operator
                {"id": "N3", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "E1", "source": "N1", "target": "N2"}
            ]
        }
        with self.assertRaises(WorkflowValidationError) as ctx:
            compile_workflow_to_dsl(workflow)
        self.assertIn("Field required", str(ctx.exception))

    def test_invalid_golden_fixtures(self):
        """
        Dynamically run tests against all 7 invalid golden workflow fixtures.
        """
        invalid_dir = Path(__file__).resolve().parent / "fixtures" / "invalid"

        self.assertTrue(invalid_dir.is_dir(), f"Invalid fixtures dir missing: {invalid_dir}")

        expected_exceptions = {
            "13_multi_start.json": (GraphValidationError, "exactly one START node"),
            "14_no_start.json": (GraphValidationError, "exactly one START node"),
            "15_cyclic.json": (CycleDetectedError, "contains a cycle"),
            "16_missing_fields.json": (WorkflowValidationError, "Field required"),
            "17_unknown_type.json": (WorkflowValidationError, "does not match any of the expected tags"),
            "18_floating_node.json": (GraphValidationError, "Unreachable nodes found"),
            "19_single_branch_if.json": (
                MissingBranchError, "exactly one 'true' branch and exactly one 'false' branch",
            ),
        }

        for filename, (exc_class, exc_msg) in expected_exceptions.items():
            file_path = invalid_dir / filename
            self.assertTrue(file_path.exists(), f"Required invalid fixture {filename} missing")
            with file_path.open("r") as f:
                workflow = json.load(f)

            with self.assertRaises(exc_class, msg=f"Fixture {filename} failed to raise {exc_class.__name__}") as ctx:
                compile_workflow_to_dsl(workflow)

            self.assertIn(
                exc_msg,
                str(ctx.exception),
                f"Fixture {filename} error message mismatch: expected {exc_msg!r}, got {str(ctx.exception)!r}"
            )

    def test_resolve_task_name_coverage(self):
        """
        Verify every branch of resolve_task_name for 100% coverage.
        """
        # INPUT
        self.assertEqual(resolve_task_name({"id": "N1", "type": "INPUT"}), "N1_capture")
        # OUTPUT
        self.assertEqual(resolve_task_name({"id": "N2", "type": "OUTPUT"}), "N2_expose")
        # AGENT
        self.assertEqual(resolve_task_name({"id": "N3", "type": "AGENT"}), "N3_agent")
        # START
        with self.assertRaises(ValueError) as ctx:
            resolve_task_name({"id": "N4", "type": "START"})
        self.assertIn("produce no DSL task", str(ctx.exception))
        # END
        with self.assertRaises(ValueError) as ctx:
            resolve_task_name({"id": "N5", "type": "END"})
        self.assertIn("produce no DSL task", str(ctx.exception))
        # Unknown
        with self.assertRaises(ValueError) as ctx:
            resolve_task_name({"id": "N6", "type": "FOOBAR"})
        self.assertIn("No task naming rule for node type", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
