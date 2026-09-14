"""Run git against a fixture repository with an explicit or inherited environment."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def git(repository: Path, *arguments: str, environment: dict[str, str] | None = None) -> str:
    executable = "git"
    if environment is not None:
        located = shutil.which("git", path=environment["PATH"])
        assert located is not None
        executable = located
    result = subprocess.run(
        [executable, "-C", str(repository), *arguments],
        capture_output=True,
        check=True,
        env=environment,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()
