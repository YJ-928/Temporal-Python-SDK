"""
Dedicated test suite verifying compiler convergence (join node) behaviors.
"""
import unittest
from src.compiler.workflow_compiler import compile_workflow_to_dsl


class TestCompilerConvergence(unittest.TestCase):
    def test_single_convergence(self):
        """
        Scenario:
        START -> INPUT -> IF -> A (ACTION) -> C (ACTION) -> END
                             -> B (ACTION) -> C (ACTION) -> END
        """
        workflow = {
            "workflow_id": "single-conv",
            "workflow_type": "single-conv-type",
            "task_queue": "default",
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "INP", "type": "INPUT", "data": {"inputs": [{"field": "x", "store_as": "x", "type": "string"}]}},
                {"id": "IF", "type": "IF", "data": {"left": "x", "operator": "==", "right": "yes"}},
                {"id": "A", "type": "ACTION", "data": {"operation": "op_a", "inputs": {}, "output": "a_out"}},
                {"id": "B", "type": "ACTION", "data": {"operation": "op_b", "inputs": {}, "output": "b_out"}},
                {"id": "C", "type": "ACTION", "data": {"operation": "op_c", "inputs": {}, "output": "c_out"}},
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "INP"},
                {"id": "e2", "source": "INP", "target": "IF"},
                {"id": "e3", "source": "IF", "target": "A", "branch": "true"},
                {"id": "e4", "source": "IF", "target": "B", "branch": "false"},
                {"id": "e5", "source": "A", "target": "C"},
                {"id": "e6", "source": "B", "target": "C"},
                {"id": "e7", "source": "C", "target": "END"}
            ]
        }

        dsl = compile_workflow_to_dsl(workflow)

        # Locate tasks
        tasks = {list(t.keys())[0]: list(t.values())[0] for t in dsl["do"]}

        # Verify transition links
        self.assertIn("A_op_a", tasks)
        self.assertIn("B_op_b", tasks)
        self.assertIn("C_op_c", tasks)

        # In branch wrapping, tasks might have 'inner' blocks, let's verify outer transitions
        self.assertEqual(tasks["A_op_a"].get("then"), "C_op_c", "A must transition explicitly to C")
        self.assertEqual(tasks["B_op_b"].get("then"), "C_op_c", "B must transition explicitly to C")
        self.assertEqual(tasks["C_op_c"].get("then"), "end", "C must transition to end")

    def test_double_convergence(self):
        """
        Scenario:
        START -> INPUT -> IF -> A (ACTION) -> C (ACTION) -> D (ACTION) -> END
                             -> B (ACTION) -> C (ACTION) -> D (ACTION) -> END
        """
        workflow = {
            "workflow_id": "double-conv",
            "workflow_type": "double-conv-type",
            "task_queue": "default",
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "INP", "type": "INPUT", "data": {"inputs": [{"field": "x", "store_as": "x", "type": "string"}]}},
                {"id": "IF", "type": "IF", "data": {"left": "x", "operator": "==", "right": "yes"}},
                {"id": "A", "type": "ACTION", "data": {"operation": "op_a", "inputs": {}, "output": "a_out"}},
                {"id": "B", "type": "ACTION", "data": {"operation": "op_b", "inputs": {}, "output": "b_out"}},
                {"id": "C", "type": "ACTION", "data": {"operation": "op_c", "inputs": {}, "output": "c_out"}},
                {"id": "D", "type": "ACTION", "data": {"operation": "op_d", "inputs": {}, "output": "d_out"}},
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "INP"},
                {"id": "e2", "source": "INP", "target": "IF"},
                {"id": "e3", "source": "IF", "target": "A", "branch": "true"},
                {"id": "e4", "source": "IF", "target": "B", "branch": "false"},
                {"id": "e5", "source": "A", "target": "C"},
                {"id": "e6", "source": "B", "target": "C"},
                {"id": "e7", "source": "C", "target": "D"},
                {"id": "e8", "source": "D", "target": "END"}
            ]
        }

        dsl = compile_workflow_to_dsl(workflow)
        tasks = {list(t.keys())[0]: list(t.values())[0] for t in dsl["do"]}

        self.assertEqual(tasks["A_op_a"].get("then"), "C_op_c")
        self.assertEqual(tasks["B_op_b"].get("then"), "C_op_c")
        self.assertEqual(tasks["C_op_c"].get("then"), "D_op_d")
        self.assertEqual(tasks["D_op_d"].get("then"), "end")

    def test_nested_convergence(self):
        """
        Scenario:
        START -> INPUT -> IF1 -> A (ACTION) -> IF2 -> X (ACTION) -> Z (ACTION) -> END
                                                   -> Y (ACTION) -> Z (ACTION) -> END
                              -> B (ACTION) ----------------------> Z (ACTION) -> END
        """
        workflow = {
            "workflow_id": "nested-conv",
            "workflow_type": "nested-conv-type",
            "task_queue": "default",
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "INP", "type": "INPUT", "data": {"inputs": [{"field": "x", "store_as": "x", "type": "string"}]}},
                {"id": "IF1", "type": "IF", "data": {"left": "x", "operator": "==", "right": "yes"}},
                {"id": "A", "type": "ACTION", "data": {"operation": "op_a", "inputs": {}, "output": "a_out"}},
                {"id": "B", "type": "ACTION", "data": {"operation": "op_b", "inputs": {}, "output": "b_out"}},
                {"id": "IF2", "type": "IF", "data": {"left": "x", "operator": "==", "right": "nested"}},
                {"id": "X", "type": "ACTION", "data": {"operation": "op_x", "inputs": {}, "output": "x_out"}},
                {"id": "Y", "type": "ACTION", "data": {"operation": "op_y", "inputs": {}, "output": "y_out"}},
                {"id": "Z", "type": "ACTION", "data": {"operation": "op_z", "inputs": {}, "output": "z_out"}},
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "INP"},
                {"id": "e2", "source": "INP", "target": "IF1"},
                {"id": "e3", "source": "IF1", "target": "A", "branch": "true"},
                {"id": "e4", "source": "IF1", "target": "B", "branch": "false"},
                {"id": "e5", "source": "A", "target": "IF2"},
                {"id": "e6", "source": "IF2", "target": "X", "branch": "true"},
                {"id": "e7", "source": "IF2", "target": "Y", "branch": "false"},
                {"id": "e8", "source": "X", "target": "Z"},
                {"id": "e9", "source": "Y", "target": "Z"},
                {"id": "e10", "source": "B", "target": "Z"},
                {"id": "e11", "source": "Z", "target": "END"}
            ]
        }

        dsl = compile_workflow_to_dsl(workflow)
        tasks = {list(t.keys())[0]: list(t.values())[0] for t in dsl["do"]}

        self.assertEqual(tasks["X_op_x"].get("then"), "Z_op_z")
        self.assertEqual(tasks["Y_op_y"].get("then"), "Z_op_z")
        self.assertEqual(tasks["B_op_b"].get("then"), "Z_op_z")
        self.assertEqual(tasks["A_op_a"].get("then"), "IF2_if")
        self.assertEqual(tasks["Z_op_z"].get("then"), "end")

    def test_output_convergence(self):
        """
        Scenario:
        START -> INPUT -> IF -> APPROVE (ACTION) -> OUT (OUTPUT) -> END
                             -> REJECT (ACTION)  -> OUT (OUTPUT) -> END
        """
        workflow = {
            "workflow_id": "output-conv",
            "workflow_type": "output-conv-type",
            "task_queue": "default",
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "INP", "type": "INPUT", "data": {"inputs": [{"field": "x", "store_as": "x", "type": "string"}]}},
                {"id": "IF", "type": "IF", "data": {"left": "x", "operator": "==", "right": "yes"}},
                {"id": "APPROVE", "type": "ACTION", "data": {"operation": "approve", "inputs": {}, "output": "status"}},
                {"id": "REJECT", "type": "ACTION", "data": {"operation": "reject", "inputs": {}, "output": "status"}},
                {"id": "OUT", "type": "OUTPUT", "data": {"outputs": [{"field": "status", "type": "string"}]}},
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "INP"},
                {"id": "e2", "source": "INP", "target": "IF"},
                {"id": "e3", "source": "IF", "target": "APPROVE", "branch": "true"},
                {"id": "e4", "source": "IF", "target": "REJECT", "branch": "false"},
                {"id": "e5", "source": "APPROVE", "target": "OUT"},
                {"id": "e6", "source": "REJECT", "target": "OUT"},
                {"id": "e7", "source": "OUT", "target": "END"}
            ]
        }

        dsl = compile_workflow_to_dsl(workflow)
        tasks = {list(t.keys())[0]: list(t.values())[0] for t in dsl["do"]}

        self.assertEqual(tasks["APPROVE_approve"].get("then"), "OUT_expose")
        self.assertEqual(tasks["REJECT_reject"].get("then"), "OUT_expose")
        self.assertEqual(tasks["OUT_expose"].get("then"), "end")

    def test_agent_convergence(self):
        """
        Scenario:
        START -> INPUT -> IF -> W_AGENT (AGENT) -> OUT (OUTPUT) -> END
                             -> E_AGENT (AGENT) -> OUT (OUTPUT) -> END
        """
        workflow = {
            "workflow_id": "agent-conv",
            "workflow_type": "agent-conv-type",
            "task_queue": "default",
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "INP", "type": "INPUT", "data": {
                    "inputs": [{"field": "city", "store_as": "city", "type": "string"}],
                }},
                {"id": "IF", "type": "IF", "data": {"left": "city", "operator": "==", "right": "London"}},
                {"id": "W_AGENT", "type": "AGENT", "data": {
                    "agent": "weather-agent", "inputs": {"city": "city"}, "output": "res",
                }},
                {"id": "E_AGENT", "type": "AGENT", "data": {
                    "agent": "email-validator-agent", "inputs": {"email": "city"}, "output": "res",
                }},
                {"id": "OUT", "type": "OUTPUT", "data": {"outputs": [{"field": "res", "type": "string"}]}},
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "INP"},
                {"id": "e2", "source": "INP", "target": "IF"},
                {"id": "e3", "source": "IF", "target": "W_AGENT", "branch": "true"},
                {"id": "e4", "source": "IF", "target": "E_AGENT", "branch": "false"},
                {"id": "e5", "source": "W_AGENT", "target": "OUT"},
                {"id": "e6", "source": "E_AGENT", "target": "OUT"},
                {"id": "e7", "source": "OUT", "target": "END"}
            ]
        }

        dsl = compile_workflow_to_dsl(workflow)
        tasks = {list(t.keys())[0]: list(t.values())[0] for t in dsl["do"]}

        self.assertEqual(tasks["W_AGENT_agent"].get("then"), "OUT_expose")
        self.assertEqual(tasks["E_AGENT_agent"].get("then"), "OUT_expose")
        self.assertEqual(tasks["OUT_expose"].get("then"), "end")


if __name__ == "__main__":
    unittest.main()
