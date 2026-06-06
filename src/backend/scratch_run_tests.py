import pytest
import sys

if __name__ == "__main__":
    with open("test_results.txt", "w") as f:
        sys.stdout = f
        sys.stderr = f
        exit_code = pytest.main(["-v"])
        print(f"\nPytest exited with code: {exit_code}", file=f)
