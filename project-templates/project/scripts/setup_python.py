"""Prepare locked dependencies or run checks with the already prepared Python."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--initialize", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--run", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    environment = Path(os.environ.get("UV_PROJECT_ENVIRONMENT", ".venv"))
    if not environment.is_absolute():
        environment = root / environment
    interpreter = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if options.verify or options.run is not None:
        if (
            not (root / "uv.lock").is_file()
            or not (environment / "pyvenv.cfg").is_file()
            or not interpreter.is_file()
        ):
            print(
                "Prepared Python environment and uv.lock are required; rerun project setup.",
                file=sys.stderr,
            )
            return 2
        if options.run is not None:
            if not options.run:
                parser.error("--run requires Python arguments")
            return subprocess.run(
                [str(interpreter), *options.run], cwd=root, check=False
            ).returncode
        return subprocess.run(
            ["uv", "sync", "--locked", "--check"], cwd=root, check=False
        ).returncode
    if not (root / "uv.lock").is_file() and not options.initialize:
        print(
            "uv.lock is required for adopted Python projects; restore the team's reviewed "
            "lockfile before rerunning setup. Dependencies were not resolved.",
            file=sys.stderr,
        )
        return 2
    try:
        if not (root / "uv.lock").is_file():
            result = subprocess.run(["uv", "lock"], cwd=root, check=False)
            if result.returncode:
                return result.returncode
        return subprocess.run(["uv", "sync", "--locked"], cwd=root, check=False).returncode
    except FileNotFoundError:
        print(
            "uv is required; prepare the project's declared Python tools and retry.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
