"""
run_demo.py — Entry point for the Zigflow DSL Compiler Demo application.

Usage:
    cd /path/to/Temporal-Python-SDK
    python poc-dsl-compiler/run_demo.py

The script inserts poc-dsl-compiler/ at sys.path[0] so that the bare
`from compiler import ...` imports inside the compiler package resolve
correctly (all compiler modules use project-relative imports, not package
imports).
"""

import sys
from pathlib import Path

# Make poc-dsl-compiler/ the first path entry so `import compiler`,
# `import dsl_generator`, `import workflow_generator` all resolve.
_COMPILER_DIR = Path(__file__).parent
sys.path.insert(0, str(_COMPILER_DIR))

import uvicorn  # noqa: E402 — must be after sys.path mutation

if __name__ == "__main__":
    uvicorn.run(
        "demo.app:app",
        host="0.0.0.0",
        port=8888,
        reload=True,
        reload_dirs=[str(_COMPILER_DIR)],
    )
