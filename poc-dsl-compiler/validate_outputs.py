"""
validate_outputs.py

Runs `zigflow validate` against every JSON file in the output/ directory
and prints a consolidated pass/fail summary.

Usage:
    python validate_outputs.py
"""

import os
import subprocess
import sys

BASE = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE, "output")


def main() -> None:
    files = sorted(
        f for f in os.listdir(OUTPUT_DIR) if f.endswith(".json")
    )

    if not files:
        print(f"No JSON files found in {OUTPUT_DIR}")
        sys.exit(0)

    passed = []
    failed = []

    for filename in files:
        filepath = os.path.join(OUTPUT_DIR, filename)
        print(f"── {filename}")

        result = subprocess.run(
            ["zigflow", "validate", filepath],
            capture_output=True,
            text=True,
        )

        # Filter out the update-available banner (cosmetic noise)
        output = "\n".join(
            line for line in result.stdout.splitlines()
            if not any(
                token in line
                for token in ["Update available", "zigflow/releases", "╭", "╰", "│"]
            )
        ).strip()

        if output:
            print(output)

        if result.returncode == 0:
            passed.append(filename)
        else:
            failed.append(filename)
            if result.stderr.strip():
                print(result.stderr.strip())

        print()

    # Summary
    total = len(files)
    print("=" * 50)
    print(f"Results: {len(passed)}/{total} passed")
    if failed:
        print("\nFailed:")
        for f in failed:
            print(f"  ✗ {f}")
        sys.exit(1)
    else:
        print("All files are valid")


if __name__ == "__main__":
    main()
