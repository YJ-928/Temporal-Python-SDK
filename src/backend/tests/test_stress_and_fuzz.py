"""
Stress and Fuzz Testing Suite for Workflow Builder Compiler and Validator.
"""
import json
import time
import random
import unittest
from pathlib import Path
from app.compiler import compile_workflow_to_dsl
from app.compiler.exceptions import (
    WorkflowValidationError,
    GraphValidationError,
    CycleDetectedError,
    MissingBranchError,
)


class TestStressAndFuzz(unittest.TestCase):
    def setUp(self):
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "valid"

    def test_phase_8_0_example_workflow_certification(self):
        """
        Phase 8.0: Verify and compile the 3 main example workflows.
        """
        examples = [
            "13_weather_assistant.json",
            "15_email_validation_sender.json",
            "16_account_routing.json"
        ]
        for example in examples:
            path = self.fixtures_dir / example
            self.assertTrue(path.exists(), f"Example workflow fixture {example} missing")
            with path.open("r") as f:
                workflow = json.load(f)

            try:
                dsl = compile_workflow_to_dsl(
                    workflow,
                    workflow_type="test-cert",
                    task_queue="default"
                )
                self.assertIsNotNone(dsl)
                self.assertEqual(dsl["document"]["workflowType"], "test-cert")
            except Exception as e:
                self.fail(f"Certification failed for example {example} with: {e}")

    def test_phase_8_1_validation_matrix_schemas(self):
        """
        Phase 8.1: Test explicit Pydantic schema validation failures.
        """
        # 1. Missing operation in ACTION node
        wf_missing_op = {
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "ACT", "type": "ACTION", "data": {"inputs": {}, "output": "out"}},
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "ACT"},
                {"id": "e2", "source": "ACT", "target": "END"}
            ]
        }
        with self.assertRaises(WorkflowValidationError) as ctx:
            compile_workflow_to_dsl(wf_missing_op)
        self.assertIn("Field required", str(ctx.exception))

        # 2. Duplicate Input fields
        wf_dup_input = {
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {
                    "id": "INP",
                    "type": "INPUT",
                    "data": {
                        "inputs": [
                            {"field": "email", "store_as": "email", "type": "string"},
                            {"field": "email", "store_as": "email2", "type": "string"}
                        ]
                    }
                },
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "INP"},
                {"id": "e2", "source": "INP", "target": "END"}
            ]
        }
        with self.assertRaises(WorkflowValidationError) as ctx:
            compile_workflow_to_dsl(wf_dup_input)
        self.assertIn("Duplicate input field names are not allowed", str(ctx.exception))

        # 3. Duplicate Input store_as variables
        wf_dup_store = {
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {
                    "id": "INP",
                    "type": "INPUT",
                    "data": {
                        "inputs": [
                            {"field": "email1", "store_as": "email", "type": "string"},
                            {"field": "email2", "store_as": "email", "type": "string"}
                        ]
                    }
                },
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "INP"},
                {"id": "e2", "source": "INP", "target": "END"}
            ]
        }
        with self.assertRaises(WorkflowValidationError) as ctx:
            compile_workflow_to_dsl(wf_dup_store)
        self.assertIn("Duplicate 'store_as' variable names are not allowed", str(ctx.exception))

        # 4. Duplicate Output fields
        wf_dup_output = {
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {
                    "id": "OUT",
                    "type": "OUTPUT",
                    "data": {
                        "outputs": [
                            {"field": "result", "type": "string"},
                            {"field": "result", "type": "string"}
                        ]
                    }
                },
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "OUT"},
                {"id": "e2", "source": "OUT", "target": "END"}
            ]
        }
        with self.assertRaises(WorkflowValidationError) as ctx:
            compile_workflow_to_dsl(wf_dup_output)
        self.assertIn("Duplicate output field names are not allowed", str(ctx.exception))

        # 5. Unregistered Agent ID
        wf_invalid_agent = {
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "AG", "type": "AGENT", "data": {"agent": "unregistered-id"}},
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "AG"},
                {"id": "e2", "source": "AG", "target": "END"}
            ]
        }
        with self.assertRaises(WorkflowValidationError) as ctx:
            compile_workflow_to_dsl(wf_invalid_agent)
        self.assertIn("is not registered in the system", str(ctx.exception))

    def test_phase_8_1_validation_matrix_topology(self):
        """
        Phase 8.1: Test explicit graph topology validation failures.
        """
        # 1. START node incoming edges
        wf_start_incoming = {
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "ACT", "type": "ACTION", "data": {"operation": "op", "inputs": {}, "output": "out"}},
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "ACT"},
                {"id": "e2", "source": "ACT", "target": "END"},
                {"id": "e3", "source": "ACT", "target": "START"}
            ]
        }
        with self.assertRaises(GraphValidationError) as ctx:
            compile_workflow_to_dsl(wf_start_incoming)
        self.assertIn("cannot have incoming edges", str(ctx.exception))

        # 2. Duplicate edges
        wf_dup_edge = {
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "END"},
                {"id": "e2", "source": "START", "target": "END"}
            ]
        }
        with self.assertRaises(GraphValidationError) as ctx:
            compile_workflow_to_dsl(wf_dup_edge)
        self.assertIn("Duplicate edge detected", str(ctx.exception))

        # 3. Dead ends (non-END node with no outgoing edges, but all reachable)
        wf_dead_end = {
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "IF", "type": "IF", "data": {"left": "x", "operator": "==", "right": True}},
                {"id": "ACT", "type": "ACTION", "data": {"operation": "op", "inputs": {}, "output": "out"}},
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "IF"},
                {"id": "e2", "source": "IF", "target": "ACT", "branch": "true"},
                {"id": "e3", "source": "IF", "target": "END", "branch": "false"}
            ]
        }
        with self.assertRaises(GraphValidationError) as ctx:
            compile_workflow_to_dsl(wf_dead_end)
        self.assertIn("must have at least one outgoing edge (dead end)", str(ctx.exception))

        # 4. Multiple outgoing edges for non-IF nodes
        wf_multi_out = {
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "ACT", "type": "ACTION", "data": {"operation": "op", "inputs": {}, "output": "out"}},
                {"id": "END1", "type": "END", "data": {}},
                {"id": "END2", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "ACT"},
                {"id": "e2", "source": "ACT", "target": "END1"},
                {"id": "e3", "source": "ACT", "target": "END2"}
            ]
        }
        with self.assertRaises(GraphValidationError) as ctx:
            compile_workflow_to_dsl(wf_multi_out)
        self.assertIn("cannot have multiple outgoing edges", str(ctx.exception))

        # 5. IF node outgoing edges count != 2
        wf_if_one_out = {
            "nodes": [
                {"id": "START", "type": "START", "data": {}},
                {"id": "IF", "type": "IF", "data": {"left": "x", "operator": "==", "right": True}},
                {"id": "END", "type": "END", "data": {}}
            ],
            "edges": [
                {"id": "e1", "source": "START", "target": "IF"},
                {"id": "e2", "source": "IF", "target": "END", "branch": "true"}
            ]
        }
        with self.assertRaises(GraphValidationError) as ctx:
            compile_workflow_to_dsl(wf_if_one_out)
        self.assertIn("must have exactly 2 outgoing edges", str(ctx.exception))

    def test_phase_8_2_scale_and_stress_testing(self):
        """
        Phase 8.2: Verify compiler scalability with up to 250 nodes.
        """
        sizes = [10, 25, 50, 100, 250]
        for size in sizes:
            workflow = self._build_scale_workflow(size)

            start_time = time.perf_counter()
            dsl = compile_workflow_to_dsl(workflow)
            end_time = time.perf_counter()

            duration = end_time - start_time
            self.assertIsNotNone(dsl)
            # Compilation must be fast (under 5.0 seconds even for 250 nodes)
            self.assertLess(duration, 5.0, f"Compilation of size {size} took too long: {duration:.4f}s")

            # Verify traversal size matches: size ACTION nodes
            self.assertEqual(len(dsl["do"]), size)

    def test_phase_8_3_fuzz_testing_1000_graphs(self):
        """
        Phase 8.3: Run 1,000 unique randomized graphs through the compiler.
        Ensure compiler never panics with KeyError, AttributeError, etc.
        """
        random.seed(42)  # Deterministic seed for fuzz tests

        expected_exceptions = (
            WorkflowValidationError,
            GraphValidationError,
            CycleDetectedError,
            MissingBranchError,
        )

        successes = 0
        failures = 0

        # 500 valid sequential random graphs
        for _ in range(500):
            wf = self._generate_valid_random_workflow()
            try:
                dsl = compile_workflow_to_dsl(wf)
                self.assertIsNotNone(dsl)
                successes += 1
            except Exception as e:
                self.fail(f"Compiler crashed on valid random graph with unexpected exception {type(e).__name__}: {e}")

        # 500 completely random graphs (mostly invalid)
        for _ in range(500):
            wf = self._generate_random_workflow()
            try:
                dsl = compile_workflow_to_dsl(wf)
                self.assertIsNotNone(dsl)
                successes += 1
            except expected_exceptions:
                # Expected validation failure
                failures += 1
            except Exception as e:
                # Unexpected crash!
                self.fail(f"Compiler crashed on random graph with unexpected exception {type(e).__name__}: {e}")

        # Make sure we got a mix of successes and validation failures
        self.assertGreater(successes, 0)
        self.assertGreater(failures, 0)

    def _build_scale_workflow(self, size: int) -> dict:
        nodes = [{"id": "START", "type": "START", "data": {}}]
        edges = []

        for i in range(size):
            node_id = f"N_{i}"
            nodes.append({
                "id": node_id,
                "type": "ACTION",
                "data": {
                    "operation": "add",
                    "inputs": {"x": "y"},
                    "output": f"out_{i}"
                }
            })
            if i == 0:
                edges.append({"id": f"E_{i}", "source": "START", "target": node_id})
            else:
                edges.append({"id": f"E_{i}", "source": f"N_{i-1}", "target": node_id})

        nodes.append({"id": "END", "type": "END", "data": {}})
        edges.append({"id": "E_end", "source": f"N_{size-1}", "target": "END"})

        return {"nodes": nodes, "edges": edges}

    def _generate_random_workflow(self) -> dict:
        num_nodes = random.randint(3, 20)
        nodes = []

        # Always have START and END
        nodes.append({"id": "START", "type": "START", "data": {}})
        nodes.append({"id": "END", "type": "END", "data": {}})

        node_types = ["INPUT", "ACTION", "AGENT", "IF", "OUTPUT"]
        for i in range(num_nodes - 2):
            node_id = f"Node_{i}"
            ntype = random.choice(node_types)
            data = {}
            if ntype == "INPUT":
                num_fields = random.randint(1, 3)
                inputs = []
                for j in range(num_fields):
                    inputs.append({
                        "field": f"field_{j}",
                        "store_as": f"store_{j}",
                        "type": random.choice(["string", "number", "boolean"])
                    })
                # Inject duplicates occasionally
                if random.random() < 0.1:
                    inputs.append({
                        "field": "field_0",
                        "store_as": "store_dup",
                        "type": "string"
                    })
                data = {"inputs": inputs}
            elif ntype == "OUTPUT":
                num_fields = random.randint(1, 3)
                outputs = []
                for j in range(num_fields):
                    outputs.append({
                        "field": f"out_{j}",
                        "type": random.choice(["string", "number", "boolean"])
                    })
                if random.random() < 0.1:
                    outputs.append({
                        "field": "out_0",
                        "type": "string"
                    })
                data = {"outputs": outputs}
            elif ntype == "ACTION":
                data = {
                    "operation": random.choice(["add", "subtract", "format_string", ""]),
                    "inputs": {"x": "y"},
                    "output": "action_out"
                }
            elif ntype == "AGENT":
                data = {
                    "agent": random.choice(["weather-agent", "email-validator-agent", "invalid-agent"]),
                    "inputs": {"a": "b"},
                    "output": "agent_out"
                }
            elif ntype == "IF":
                data = {
                    "left": "value",
                    "operator": random.choice(["==", "!=", ">", "<", ">=", "<=", "INVALID"]),
                    "right": 42
                }

            nodes.append({"id": node_id, "type": ntype, "data": data})

        edges = []
        node_ids = [n["id"] for n in nodes]

        num_edges = random.randint(num_nodes - 1, num_nodes * 2)
        for i in range(num_edges):
            source = random.choice(node_ids)
            target = random.choice(node_ids)

            edge_data = {"id": f"E_{i}", "source": source, "target": target}

            source_node = next(n for n in nodes if n["id"] == source)
            if source_node["type"] == "IF":
                edge_data["branch"] = random.choice(["true", "false", "invalid_branch"])

            edges.append(edge_data)

        return {"nodes": nodes, "edges": edges}

    def _generate_valid_random_workflow(self) -> dict:
        num_nodes = random.randint(1, 10)
        nodes = [{"id": "START", "type": "START", "data": {}}]
        edges = []

        node_types = ["INPUT", "ACTION", "AGENT", "OUTPUT"]
        prev_id = "START"
        for i in range(num_nodes):
            node_id = f"Node_valid_{i}"
            ntype = random.choice(node_types)
            data = {}
            if ntype == "INPUT":
                data = {"inputs": [{"field": f"f_{i}", "store_as": f"s_{i}", "type": "string"}]}
            elif ntype == "OUTPUT":
                data = {"outputs": [{"field": f"o_{i}", "type": "string"}]}
            elif ntype == "ACTION":
                data = {"operation": "add", "inputs": {}, "output": f"out_{i}"}
            elif ntype == "AGENT":
                data = {"agent": "weather-agent", "output": f"out_{i}"}

            nodes.append({"id": node_id, "type": ntype, "data": data})
            edges.append({"id": f"E_valid_{i}", "source": prev_id, "target": node_id})
            prev_id = node_id

        nodes.append({"id": "END", "type": "END", "data": {}})
        edges.append({"id": "E_valid_end", "source": prev_id, "target": "END"})
        return {"nodes": nodes, "edges": edges}
