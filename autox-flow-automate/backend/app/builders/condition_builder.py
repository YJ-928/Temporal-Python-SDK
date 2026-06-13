"""
Condition expression builder for IF nodes.
"""
import json

SUPPORTED_OPERATORS: frozenset[str] = frozenset({"==", "!=", ">", "<", ">=", "<="})


def build_condition_expression(left: str, operator: str, right: any) -> str:
    """
    Format a condition into a Zigflow jq expression string.

    Always reads from $context (not transient data .) for reliability.
    Variables captured by INPUT are always exported to $context via export.as,
    so $context.{field} is always populated.

    Examples:
        build_condition_expression("user_email", "!=", "")
            -> '${ $context.user_email != "" }'

        build_condition_expression("country", "==", "US")
            -> '${ $context.country == "US" }'

        build_condition_expression("retry_count", ">", 3)
            -> '${ $context.retry_count > 3 }'

    Args:
        left: Variable name (read from $context)
        operator: Comparison operator
        right: Right-hand value (bool, str, int, float, list, dict, None)

    Returns:
        jq expression string wrapped in "${ }"

    Raises:
        ValueError: if operator not in SUPPORTED_OPERATORS
    """
    if operator not in SUPPORTED_OPERATORS:
        raise ValueError(
            f"Unsupported operator {operator!r}. "
            f"Supported operators: {sorted(SUPPORTED_OPERATORS)}"
        )

    # Format right-hand side using json.dumps to ensure valid JSON/JQ syntax
    # (None -> null, bool -> true/false, arrays, objects, strings correctly quoted)
    right_expr = json.dumps(right)

    return f"${{ $context.{left} {operator} {right_expr} }}"
