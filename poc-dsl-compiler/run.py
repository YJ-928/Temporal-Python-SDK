# run.py
#
# Engine: generate all workflow levels -> compile to DSL schemas -> validate.
#
# This script automates the full pipeline that previously required running
# workflow_generator.py, main.py, and validate_outputs.py manually for every
# difficulty level.
#
# Steps:
#   1. Clean all input/output directories (fresh state every run)
#   2. Generate one workflow JSON + markdown for each difficulty level (1–N)
#   3. Compile each generated JSON to a DSL schema in output/
#   4. Validate all DSL schemas in output/ with `zigflow validate`
#
# Usage:
#   python run.py

import json
import os
import subprocess
import sys
from pathlib import Path

# Package root on path so sibling modules resolve without install
sys.path.insert(0, os.path.dirname(__file__))

from workflow_generator import (
    GENERATORS,
    DESCRIPTIONS,
    WORKFLOWS_DIR,
    OUTPUTS_DIR,
    generate_mermaid,
    get_next_index,
    save_workflow,
    shuffle_nodes,
)
from compiler import run_compiler
from dsl_generator import generate_dsl, save_dsl

BASE = Path(__file__).parent
OUTPUT_DIR = BASE / "output"


# Helpers
def _section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}\n")

def _clean_dir(directory: Path, extensions: tuple[str, ...]) -> int:
    """Delete all files with the given extensions in directory. Returns count removed."""
    removed = 0
    if directory.exists():
        for ext in extensions:
            for f in directory.glob(f"*{ext}"):
                f.unlink()
                removed += 1
    return removed


# Step 0 - Clean
def clean_all() -> None:
    _section("STEP 0 - CLEANING DIRECTORIES")
    targets = [
        (WORKFLOWS_DIR, (".md",)),
        (OUTPUTS_DIR,   (".json",)),
        (OUTPUT_DIR,    (".json",)),
    ]
    for directory, exts in targets:
        count = _clean_dir(directory, exts)
        label = str(directory.relative_to(BASE))
        print(f"  Cleaned  {label}/  ({count} file{'s' if count != 1 else ''} removed)")


# Step 1 - Generate
def generate_all_levels() -> list[Path]:
    """
    Generate one workflow JSON + markdown for every level in GENERATORS.
    Returns a sorted list of the generated JSON file paths.
    """
    levels = sorted(GENERATORS.keys())
    _section(f"STEP 1 - GENERATING WORKFLOWS  ({len(levels)} levels)")

    generated: list[Path] = []
    for level in levels:
        workflow = GENERATORS[level]()
        shuffle_nodes(workflow)
        index = get_next_index()
        mermaid = generate_mermaid(workflow)
        save_workflow(workflow, mermaid, index)
        json_path = OUTPUTS_DIR / f"workflow_{index}_output.json"
        generated.append(json_path)
        print(f"  Level {level:2d}  ✓  workflow_{index}_output.json  -  {DESCRIPTIONS[level]}")

    return sorted(generated)


# Step 2 - Compile
def _resolve_output_path(input_path: Path) -> Path:
    stem = input_path.stem  # e.g. "workflow_3_output"
    if stem.endswith("_output"):
        stem = stem[: -len("_output")]  # e.g. "workflow_3"
    return OUTPUT_DIR / f"{stem}_dsl_schema.json"

def compile_all(json_paths: list[Path]) -> tuple[int, int]:
    """
    Compile every workflow JSON to a DSL schema in output/.
    Returns (passed_count, failed_count).
    """
    _section(f"STEP 2 - COMPILING DSL SCHEMAS  ({len(json_paths)} files)")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    passed = failed = 0
    for path in json_paths:
        out_path = _resolve_output_path(path)
        try:
            with open(path, encoding="utf-8") as f:
                workflow = json.load(f)

            compiler_output = run_compiler(workflow)
            dsl = generate_dsl(
                compiler_output["traversal"],
                compiler_context=compiler_output["builder_context"],
            )
            save_dsl(dsl, str(out_path))
            print(f"  OK    {path.name}  ->  {out_path.name}")
            passed += 1
        except Exception as exc:
            print(f"  FAIL  {path.name}  -  {exc}")
            failed += 1

    print(f"\n  Compiled: {passed} succeeded, {failed} failed")
    return passed, failed


# Step 3 - Validate
def validate_all() -> int:
    """
    Run validate_outputs.py as a subprocess.
    Returns the process exit code (0 = all valid, 1 = failures found).
    """
    _section("STEP 3 - VALIDATING DSL SCHEMAS")
    result = subprocess.run(
        [sys.executable, str(BASE / "validate_outputs.py")],
        cwd=str(BASE),
    )
    return result.returncode


# Engine
def main() -> None:
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║           DSL Compiler - Full Pipeline Run               ║")
    print("╚══════════════════════════════════════════════════════════╝")

    clean_all()
    generated = generate_all_levels()
    _compile_passed, compile_failed = compile_all(generated)
    validate_exit = validate_all()

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║                     Pipeline Summary                     ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Levels generated : {len(generated):<37}║")
    print(f"║  Compile failures : {compile_failed:<37}║")
    print(f"║  Validate result  : {'PASS' if validate_exit == 0 else 'FAIL':<37}║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    if compile_failed > 0 or validate_exit != 0:
        sys.exit(1)


# Starter
if __name__ == "__main__":
    main()
