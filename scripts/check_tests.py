"""Run repository tests for the supported platform boundary, never install tools."""

import os
import subprocess
import sys

# Native installation is a bounded core/Python offering. Unix-only provider,
# descriptor-inventory and client cases remain in the full Unix matrix. These
# files include real native safety/consumer cases, with no blanket failure skips.
WINDOWS_TESTS = [
    "tests/test_portable_imports.py",
    "tests/test_portable_commands.py",
    "tests/test_windows_storage.py",
    "tests/test_windows_document_dispatch.py",
    "tests/test_windows_core.py",
    "tests/test_windows_render.py",
    "tests/test_template_recovery.py",
    "tests/test_windows_bundle_refusal.py",
    "tests/test_native_repository_checks.py",
    "tests/test_windows_bootstrap.py",
    "tests/test_native_templates.py",
    "tests/test_windows_consumer.py",
    "tests/test_windows_environment.py",
    "tests/test_windows_provision.py",
]

if __name__ == "__main__":
    selected = WINDOWS_TESTS if os.name == "nt" else []
    raise SystemExit(
        subprocess.run([sys.executable, "-m", "pytest", "-q", *selected], check=False).returncode
    )
