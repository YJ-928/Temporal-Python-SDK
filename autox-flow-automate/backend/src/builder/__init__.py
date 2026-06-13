"""
Builder registry for node-specific DSL builders.
"""
from .terminal_builder import build_terminal
from .input_builder import build_input
from .output_builder import build_output
from .action_builder import build_action
from .agent_builder import build_agent
from .if_builder import build_if


# Register all builders
BUILDERS = {
    "START": build_terminal,
    "END": build_terminal,
    "INPUT": build_input,
    "OUTPUT": build_output,
    "ACTION": build_action,
    "AGENT": build_agent,
    "IF": build_if,
}


__all__ = [
    "BUILDERS",
    "build_terminal",
    "build_input",
    "build_output",
    "build_action",
    "build_agent",
    "build_if",
]
