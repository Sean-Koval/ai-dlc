"""Run the project's standard-library tests and reject vacuous success."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tests = root / "tests"
    if not tests.is_dir():
        print(
            "No tests were discovered because the tests directory is missing; "
            "add a test*.py file under tests/.",
            file=sys.stderr,
        )
        return 1
    suite = unittest.defaultTestLoader.discover(str(tests), pattern="test*.py")
    if suite.countTestCases() == 0:
        print(
            "No tests were discovered; add a test*.py file under tests/.",
            file=sys.stderr,
        )
        return 1
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.testsRun == len(result.skipped):
        print(
            "Every discovered test was skipped; add at least one runnable test.",
            file=sys.stderr,
        )
        return 1
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
