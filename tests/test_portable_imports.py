"""Core surfaces remain importable when Unix-only modules are unavailable."""

import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "ai_dlc.cli",
        "ai_dlc.mcp_server",
        "ai_dlc.documentation.knowledge",
        "ai_dlc.harness.friction",
        "ai_dlc.providers.plane_attempts",
    ],
)
def test_core_import_does_not_require_unix_modules(module):
    code = """
import importlib.abc
import sys
class NoUnix(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {"fcntl", "pwd"}:
            raise ModuleNotFoundError("Unix-only module: " + fullname)
sys.meta_path.insert(0, NoUnix())
__import__(sys.argv[1])
"""
    result = subprocess.run(
        [sys.executable, "-c", code, module], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
