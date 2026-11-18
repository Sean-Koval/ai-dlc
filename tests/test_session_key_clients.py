"""KAN-285: the workflow plugin gives each client session the join key, end to end.

These drive the generated plugin hook with the real CLI, as a client would run it.
Claude Code and Codex run the same hook file; they differ in that Claude Code names
an environment file in ``CLAUDE_ENV_FILE`` and Codex does not. Inside hangar the
plugin never starts the CLI, so hangar's own fields are kept.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_hook_shim import ROOT, real_cli, run_generated
from test_hooks import initialize_hook_project, write_work_record

from ai_dlc.harness import hook_shim
from ai_dlc.work.session_key import ENV_NAMES, SessionKey, local_session_keys, read_session_keys

JIRA_URL = "https://example.atlassian.net/browse/KAN-7"
CODEX_HOOK = ROOT / "plugins/ai-dlc-workflow/native/codex/hooks/aidlc_hook.py"


def adopted(tmp_path: Path, *, record: bool = True) -> Path:
    root = tmp_path / "adopted"
    initialize_hook_project(root, None)  # on branch "topic"
    if record:
        write_work_record(root, "kan-7-join", artifacts={"branch": "topic", "tracker": JIRA_URL})
    return root


def start(tmp_path: Path, root: Path, extra_env: dict[str, str]):
    path = real_cli(tmp_path / "bin")
    payload = {"cwd": str(root), "session_id": "sess-1"}
    env = {"PYTHONPATH": str(ROOT / "src"), **extra_env}
    return run_generated(tmp_path, "session-start", payload, env, path)


def test_codex_runs_the_same_hook_file_as_claude_code():
    generated = ROOT / "plugins/ai-dlc-workflow/hooks/aidlc_hook.py"
    assert CODEX_HOOK.read_bytes() == generated.read_bytes()


def test_claude_code_session_gets_the_key_in_its_environment_file(tmp_path):
    root = adopted(tmp_path)
    env_file = tmp_path / "claude.env"

    result = start(tmp_path, root, {"CLAUDE_ENV_FILE": str(env_file)})

    expected = "aidlc1:KAN-7:kan-7-join:sess-1"
    assert result.returncode == 0, result.stderr
    assert read_session_keys(result.stdout) == [SessionKey.parse(expected)]
    exported = env_file.read_text()
    assert f"export AI_DLC_SESSION_KEY={expected}\n" in exported
    assert "export AI_DLC_TRACKER_KEY=KAN-7\n" in exported
    assert "export AI_DLC_WORK_ID=kan-7-join\n" in exported
    assert "export AI_DLC_SESSION_ID=sess-1\n" in exported
    assert local_session_keys(root, "kan-7-join") == [expected]


def test_codex_session_gets_the_key_in_its_context_only(tmp_path):
    root = adopted(tmp_path)

    result = start(tmp_path, root, {})  # Codex names no environment file

    expected = "aidlc1:KAN-7:kan-7-join:sess-1"
    assert result.returncode == 0, result.stderr
    assert f"Work-Session: {expected}" in result.stdout.splitlines()
    assert local_session_keys(root, "kan-7-join") == [expected]
    assert not list(tmp_path.glob("*.env"))


@pytest.mark.parametrize("hangar", [{"HANGAR_WORKSPACE": "/workspace"}, {"HANGAR_JOB_ID": "job-1"}])
def test_hangar_session_keeps_hangars_keys_and_never_starts_the_cli(tmp_path, hangar):
    root = adopted(tmp_path)
    env_file = tmp_path / "claude.env"
    preset = {name: "set-by-hangar" for name in ENV_NAMES}
    preset["AI_DLC_SESSION_KEY"] = "aidlc1:KAN-9:hangar-job:job-1"

    result = start(tmp_path, root, {"CLAUDE_ENV_FILE": str(env_file), **hangar, **preset})

    assert result.returncode == 0, result.stderr
    assert result.stdout == hook_shim.HANGAR_LINE + "\n"
    assert not env_file.exists()
    assert not (root / ".ai-dlc/local/sessions").exists()


def test_session_without_a_record_or_ticket_still_starts(tmp_path):
    """No bound record: the key has empty ticket and work parts, and nothing fails."""
    root = adopted(tmp_path, record=False)
    env_file = tmp_path / "claude.env"

    result = start(tmp_path, root, {"CLAUDE_ENV_FILE": str(env_file)})

    assert result.returncode == 0, result.stderr
    assert read_session_keys(result.stdout) == [SessionKey.parse("aidlc1:::sess-1")]
    assert "export AI_DLC_WORK_ID=''\n" in env_file.read_text()
    assert not (root / ".ai-dlc/work").exists()
