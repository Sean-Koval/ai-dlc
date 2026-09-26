"""Behavior test for the generated application entry point."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class ApplicationTest(unittest.TestCase):
    def test_entry_point_prints_greeting(self) -> None:
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / "src/main.py")],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Hello, world!\n")


if __name__ == "__main__":
    unittest.main()
