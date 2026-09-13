"""The shared git runner is the only way source code invokes git."""

import re
import subprocess
from pathlib import Path

import pytest

from ai_dlc.files import GIT_TIMEOUT_SECONDS, GitError, run_git

SOURCE = Path(__file__).resolve().parents[1] / "src/ai_dlc"


def test_only_the_shared_runner_spawns_git():
    """Would fail if a module reintroduced its own subprocess call with a git argv."""
    offenders = []
    for path in SOURCE.rglob("*.py"):
        if path == SOURCE / "files.py":
            continue
        text = path.read_text()
        if re.search(r'subprocess\.\w+\(\s*\[\s*"git"', text) or re.search(
            r"subprocess\.\w+\(\s*\[\s*command,", text
        ):
            offenders.append(str(path.relative_to(SOURCE)))
    assert offenders == []


def test_failure_carries_context_and_stderr_and_is_catchable_by_existing_handlers(tmp_path):
    with pytest.raises(GitError, match="Probe failed: fatal") as caught:
        run_git(tmp_path, "rev-parse", "HEAD", context="Probe failed")
    assert caught.value.returncode not in (None, 0)
    assert "fatal" in caught.value.stderr
    assert isinstance(caught.value, ValueError)
    assert isinstance(caught.value, RuntimeError)


def test_check_false_returns_the_completed_process(tmp_path):
    result = run_git(tmp_path, "rev-parse", "HEAD", check=False)
    assert result.returncode != 0
    assert result.stdout == ""


def test_bytes_mode_and_success(tmp_path):
    run_git(tmp_path, "init", "--quiet")
    assert run_git(tmp_path, "rev-parse", "--is-inside-work-tree").stdout.strip() == "true"
    assert run_git(tmp_path, "rev-parse", "--is-inside-work-tree", text=False).stdout == b"true\n"


def test_timeout_is_explicit_and_surfaces_as_git_error(monkeypatch, tmp_path):
    seen = {}

    def slow(argv, **kwargs):
        seen.update(kwargs)
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", slow)
    with pytest.raises(GitError, match="timed out after 30s"):
        run_git(tmp_path, "fetch")
    assert seen["timeout"] == GIT_TIMEOUT_SECONDS == 30


def test_environ_scopes_executable_lookup(tmp_path):
    with pytest.raises(GitError, match="not available on the configured PATH"):
        run_git(tmp_path, "status", environ={"PATH": str(tmp_path)})
