"""
Builds a Zigflow jq expression string from a condition dict.

A condition dict has three required keys:
  left     — workflow variable name (flat, e.g. "user_email")
  operator — comparison operator string ("==", "!=", ">", "<", ">=", "<=")
  right    — value to compare against (str, int, bool, etc.)

This builder is shared by any node type that needs to emit a condition expression.
Currently consumed by: if_builder.
Future consumers: loop nodes, conditional wait nodes.
"""

SUPPORTED_OPERATORS: frozenset[str] = frozenset({"==", "!=", ">", "<", ">=", "<="})


def build_condition_expression(condition: dict) -> str:
    """
    Format a condition dict into a Zigflow jq expression string.

    Examples:
        {"left": "user_email", "operator": "!=", "right": ""}
            → '${ .user_email != "" }'

        {"left": "country", "operator": "==", "right": "US"}
            → '${ .country == "US" }'

        {"left": "retry_count", "operator": ">", "right": 3}
            → '${ .retry_count > 3 }'

    Raises:
        ValueError: if the operator is not in SUPPORTED_OPERATORS.
        KeyError: if any of left, operator, or right is missing from condition.
    """
    left = condition["left"]
    operator = condition["operator"]
    right = condition["right"]

    if operator not in SUPPORTED_OPERATORS:
        raise ValueError(
            f"Unsupported operator {operator!r} in condition {condition!r}. "
            f"Supported operators: {sorted(SUPPORTED_OPERATORS)}"
        )

    if isinstance(right, bool):
        right_expr = "true" if right else "false"
    elif isinstance(right, str):
        right_expr = f'"{right}"'
    else:
        right_expr = right
    return f"${{ .{left} {operator} {right_expr} }}"
