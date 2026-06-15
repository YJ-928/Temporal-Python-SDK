"""
Unit tests for isolated DSL builders.
"""
import unittest
from src.builder.input_builder import build_input
from src.builder.output_builder import build_output
from src.builder.action_builder import build_action
from src.builder.agent_builder import build_agent
from src.builder.if_builder import build_if
from src.builder.terminal_builder import build_terminal
from src.builder.condition_builder import build_condition_expression
from src.config import settings


class TestBuilders(unittest.TestCase):
    def test_build_terminal(self):
        # START node
        node_start = {"id": "N1", "type": "START", "data": {}}
        self.assertIsNone(build_terminal(node_start))

        # END node
        node_end = {"id": "N2", "type": "END", "data": {}}
        self.assertIsNone(build_terminal(node_end))

    def test_build_input(self):
        node = {
            "id": "N_in",
            "type": "INPUT",
            "data": {
                "inputs": [
                    {"field": "username", "store_as": "user_name", "type": "string"},
                    {"field": "age", "store_as": "user_age", "type": "integer"}
                ]
            }
        }
        res = build_input(node)
        task_name = "N_in_capture"
        self.assertIn(task_name, res)
        self.assertEqual(res[task_name]["set"], {
            "user_name": "${ $input.username }",
            "user_age": "${ $input.age }"
        })
        self.assertEqual(
            res[task_name]["export"]["as"],
            "${ $context + {user_name: .user_name, user_age: .user_age} }"
        )
        self.assertNotIn("then", res[task_name])

        # Terminal INPUT node
        res_term = build_input(node, traversal_entry={"is_terminal": True})
        self.assertEqual(res_term[task_name]["then"], "end")

    def test_build_output(self):
        node = {
            "id": "N_out",
            "type": "OUTPUT",
            "data": {
                "outputs": [
                    {"field": "score", "type": "integer"},
                    {"field": "profile", "type": "string"}
                ]
            }
        }
        res = build_output(node)
        task_name = "N_out_expose"
        self.assertIn(task_name, res)
        self.assertEqual(res[task_name]["set"], {
            "score": "${ $context.score }",
            "profile": "${ $context.profile }"
        })
        self.assertNotIn("then", res[task_name])

        # Terminal OUTPUT node
        res_term = build_output(node, traversal_entry={"is_terminal": True})
        self.assertEqual(res_term[task_name]["then"], "end")

    def test_build_action(self):
        # Action with inputs
        node = {
            "id": "N_act",
            "type": "ACTION",
            "data": {
                "operation": "calculate_tax",
                "inputs": {
                    "subtotal": "order_subtotal",
                    "state": "user_state"
                },
                "output": "tax_amount"
            }
        }
        res = build_action(node)
        task_name = "N_act_calculate_tax"
        self.assertIn(task_name, res)
        self.assertEqual(res[task_name]["call"], "http")
        self.assertEqual(res[task_name]["with"]["method"], "post")
        self.assertEqual(
            res[task_name]["with"]["endpoint"],
            f"{settings.ACTIONS_BASE_URL}/api/v1/actions/calculate_tax"
        )
        self.assertEqual(
            res[task_name]["with"]["headers"],
            {"Content-Type": "application/json"}
        )
        # body is now a single JQ expression string (order of keys matches dict iteration order)
        self.assertEqual(
            res[task_name]["with"]["body"],
            "${ {subtotal: $context.order_subtotal, state: $context.user_state} }"
        )
        self.assertEqual(
            res[task_name]["export"]["as"],
            "${ $context + {tax_amount: .} }"
        )
        self.assertNotIn("then", res[task_name])

        # Action without inputs
        node_no_inputs = {
            "id": "N_act",
            "type": "ACTION",
            "data": {
                "operation": "ping",
                "inputs": {},
                "output": "ping_res"
            }
        }
        res_no_inputs = build_action(node_no_inputs)
        self.assertNotIn("body", res_no_inputs["N_act_ping"]["with"])

        # Terminal Action
        res_term = build_action(node, traversal_entry={"is_terminal": True})
        self.assertEqual(res_term[task_name]["then"], "end")

    def test_build_agent(self):
        # Fallback unregistered agent
        node = {
            "id": "N_agt",
            "type": "AGENT",
            "data": {
                "agent": "support-classifier",
                "inputs": {
                    "text": "message"
                },
                "output": "classification",
                "output_path": "label"
            }
        }
        res = build_agent(node)
        task_name = "N_agt_agent"
        self.assertIn(task_name, res)
        self.assertEqual(res[task_name]["call"], "http")
        self.assertEqual(res[task_name]["with"]["method"], "post")
        self.assertEqual(res[task_name]["with"]["endpoint"], "http://localhost:11000/execute")
        self.assertEqual(
            res[task_name]["with"]["headers"],
            {"Content-Type": "application/json"}
        )
        # body is now a single JQ expression string, not a dict with JQ values
        self.assertEqual(res[task_name]["with"]["body"], "${ {text: $context.message} }")
        self.assertEqual(res[task_name]["export"]["as"], "${ $context + {classification: .label} }")
        self.assertNotIn("then", res[task_name])

        # Registered agent (weather-agent)
        node_weather = {
            "id": "N_agt",
            "type": "AGENT",
            "data": {
                "agent": "weather-agent",
                "inputs": {
                    "city": "user_city"
                },
                "output": "weather_result"
            }
        }
        res_weather = build_agent(node_weather)
        self.assertEqual(res_weather[task_name]["with"]["endpoint"], "http://localhost:11000/execute")
        self.assertEqual(res_weather[task_name]["with"]["method"], "post")
        self.assertEqual(
            res_weather[task_name]["with"]["headers"],
            {"Content-Type": "application/json"}
        )
        self.assertEqual(res_weather[task_name]["with"]["body"], "${ {city: $context.user_city} }")
        self.assertEqual(res_weather[task_name]["export"]["as"], "${ $context + {weather_result: .} }")

        # Terminal AGENT
        res_term = build_agent(node, traversal_entry={"is_terminal": True})
        self.assertEqual(res_term[task_name]["then"], "end")

    def test_build_if(self):
        node = {
            "id": "N_if",
            "type": "IF",
            "data": {
                "left": "is_active",
                "operator": "==",
                "right": True
            }
        }
        traversal = {
            "branch_map": {
                "true": {"task_name": "N_true_task"},
                "false": {"task_name": "N_false_task"}
            }
        }
        res = build_if(node, traversal_entry=traversal)
        task_name = "N_if_if"
        self.assertIn(task_name, res)
        self.assertEqual(res[task_name]["switch"][0]["case"]["when"], "${ $context.is_active == true }")
        self.assertEqual(res[task_name]["switch"][0]["case"]["then"], "N_true_task")
        self.assertEqual(res[task_name]["switch"][1]["default"]["then"], "N_false_task")
        self.assertNotIn("then", res[task_name])

        # Terminal IF node
        traversal_term = traversal.copy()
        traversal_term["is_terminal"] = True
        res_term = build_if(node, traversal_entry=traversal_term)
        self.assertEqual(res_term[task_name]["then"], "end")

        # IF node missing branch_map
        with self.assertRaises(ValueError):
            build_if(node)

    def test_build_condition_expression(self):
        # Boolean conditions
        self.assertEqual(build_condition_expression("x", "==", True), "${ $context.x == true }")
        self.assertEqual(build_condition_expression("x", "==", False), "${ $context.x == false }")

        # String conditions
        self.assertEqual(build_condition_expression("x", "!=", "active"), '${ $context.x != "active" }')

        # Numeric conditions
        self.assertEqual(build_condition_expression("x", ">", 10), "${ $context.x > 10 }")
        self.assertEqual(build_condition_expression("x", "<=", 5.5), "${ $context.x <= 5.5 }")

        # None/null conditions
        self.assertEqual(build_condition_expression("x", "==", None), "${ $context.x == null }")

        # Complex types: lists and dicts
        self.assertEqual(build_condition_expression("x", "==", [1, 2]), "${ $context.x == [1, 2] }")
        self.assertEqual(build_condition_expression("x", "==", {"a": 1}), '${ $context.x == {"a": 1} }')

        # Unsupported operator
        with self.assertRaises(ValueError):
            build_condition_expression("x", "IN", 10)


if __name__ == "__main__":
    unittest.main()
