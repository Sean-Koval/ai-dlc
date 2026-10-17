"""The workflow-plugin hook shim degrades cleanly without the CLI and inside hangar."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_hooks import initialize_hook_project

from ai_dlc.harness import hook_shim
from ai_dlc.harness.hooks import classify_command

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "plugins/ai-dlc-workflow/hooks/aidlc_hook.py"
EVENTS = ("session-start", "pre-tool", "stop")
MODES = ("delegate", "no-cli", "not-adopted", "hangar-workspace", "hangar-job")
COMMANDS = [
    "rm -rf build",
    "rm file.txt",
    "git reset --hard HEAD~1",
    "git reset --soft HEAD~1",
    "git clean -fd",
    "git clean -n",
    "git clean --force",
    "git push origin feature/x",
    "git push --force origin main",
    "git push --force-with-lease",
    "git push origin :old-branch",
    "git push -d origin topic",
    "git push --mirror",
    "gh pr create --title 'hi'",
    "git -C elsewhere push",
    "echo 'git push'",
    "ls -la && rm -rf /",
    "cat file | grep x",
    "echo $(whoami)",
    "unterminated 'quote",
    "",
    "pytest -q",
]


def fake_cli(directory: Path, exit_code: int = 0, stdout: str = "", stderr: str = "") -> Path:
    """An ``ai-dlc`` stand-in that records its argv and stdin, then exits as told."""
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / "calls.jsonl"
    script = directory / "ai-dlc"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        f"open({str(log)!r}, 'a').write(json.dumps({{'argv': sys.argv[1:], "
        "'stdin': sys.stdin.read()}) + '\\n')\n"
        f"sys.stdout.write({stdout!r})\n"
        f"sys.stderr.write({stderr!r})\n"
        f"sys.exit({exit_code})\n"
    )
    script.chmod(0o755)
    return log


def project(tmp_path: Path, mode: str) -> tuple[Path, dict[str, str], Path]:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    if mode != "not-adopted":
        (root / "ai-dlc.toml").write_text("schema = 4\n")
    bin_dir = tmp_path / "bin"
    log = fake_cli(bin_dir, exit_code=0, stdout="delegated context\n")
    path = "/usr/bin:/bin" if mode == "no-cli" else f"{bin_dir}{os.pathsep}/usr/bin:/bin"
    env = {"PATH": path}
    if mode == "hangar-workspace":
        env["HANGAR_WORKSPACE"] = "/workspace"
    if mode == "hangar-job":
        env["HANGAR_JOB_ID"] = "job-1"
    return root, env, log


def which_for(env: dict[str, str]):
    import shutil

    return lambda name: shutil.which(name, path=env.get("PATH", ""))


def invoke(event: str, payload: object, env: dict[str, str]) -> tuple[int, str, str]:
    stdin = io.StringIO(payload if isinstance(payload, str) else json.dumps(payload))
    stdout, stderr = io.StringIO(), io.StringIO()
    code = hook_shim.run(["aidlc_hook.py", event], stdin, stdout, stderr, env, which_for(env))
    return code, stdout.getvalue(), stderr.getvalue()


def payload_for(event: str, root: Path, command: str = "git push origin feature/x") -> dict:
    base: dict = {"cwd": str(root), "session_id": "s-1"}
    if event == "pre-tool":
        base |= {"tool_name": "Bash", "tool_input": {"command": command}}
    return base


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("event", EVENTS)
def test_every_event_and_mode_cell(tmp_path, event, mode):
    root, env, log = project(tmp_path, mode)
    code, out, err = invoke(event, payload_for(event, root), env)
    calls = log.read_text().splitlines() if log.exists() else []
    assert code == 0
    if mode == "delegate":
        assert [json.loads(c)["argv"] for c in calls] == [["hook", event, "--root", str(root)]]
        assert json.loads(json.loads(calls[0])["stdin"])["cwd"] == str(root)
        assert out == "delegated context\n"
        return
    assert calls == []
    if event == "session-start":
        expected = {
            "no-cli": hook_shim.NO_CLI_LINE,
            "not-adopted": hook_shim.NOT_ADOPTED_LINE,
            "hangar-workspace": hook_shim.HANGAR_LINE,
            "hangar-job": hook_shim.HANGAR_LINE,
        }[mode]
        assert out == expected + "\n"
    else:
        # pre-tool allows the push without the bound-push policy; stop is a no-op.
        assert out == ""
    assert err == ""
    assert not (root / ".ai-dlc").exists()


@pytest.mark.parametrize("mode", MODES[1:])
def test_destructive_command_denied_without_delegation(tmp_path, mode):
    root, env, log = project(tmp_path, mode)
    code, out, err = invoke("pre-tool", payload_for("pre-tool", root, "rm -rf build"), env)
    assert code == 2
    assert "Destructive operation denied" in err and out == ""
    assert not log.exists()


def test_delegated_destructive_denial_is_passed_through(tmp_path):
    root, env, _ = project(tmp_path, "delegate")
    fake_cli(tmp_path / "bin", exit_code=2, stderr="Destructive operation denied: native\n")
    code, _, err = invoke("pre-tool", payload_for("pre-tool", root, "rm -rf build"), env)
    assert code == 2 and err == "Destructive operation denied: native\n"


@pytest.mark.parametrize("exit_code", [1, 127, 3])
def test_failed_delegate_maps_to_allow_with_a_note(tmp_path, exit_code):
    root, env, _ = project(tmp_path, "delegate")
    fake_cli(tmp_path / "bin", exit_code=exit_code, stdout="ignored", stderr="boom")
    code, out, err = invoke("pre-tool", payload_for("pre-tool", root), env)
    assert code == 0 and out == ""
    assert err == f"ai-dlc workflow plugin: ai-dlc hook pre-tool exited {exit_code}; allowed.\n"


def test_delegate_timeout_maps_to_allow(tmp_path, monkeypatch):
    root, env, _ = project(tmp_path, "delegate")
    script = tmp_path / "bin/ai-dlc"
    script.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(5)\n")
    monkeypatch.setattr(hook_shim, "DELEGATE_TIMEOUT_SECONDS", 0.5)
    code, _, err = invoke("stop", payload_for("stop", root), env)
    assert code == 0 and "did not run" in err


@pytest.mark.parametrize("event", EVENTS)
@pytest.mark.parametrize("mode", MODES)
def test_kill_switch_disables_every_event(tmp_path, event, mode):
    root, env, log = project(tmp_path, mode)
    env["AI_DLC_HOOKS"] = "off"
    payload = payload_for(event, root, "rm -rf build")
    assert invoke(event, payload, env) == (0, "", "")
    assert not log.exists()


def test_quiet_mode_drops_only_the_session_line(tmp_path):
    root, env, _ = project(tmp_path, "not-adopted")
    env["AI_DLC_HOOKS"] = "quiet"
    assert invoke("session-start", payload_for("session-start", root), env) == (0, "", "")
    assert invoke("pre-tool", payload_for("pre-tool", root, "rm -rf build"), env)[0] == 2


@pytest.mark.parametrize("event", EVENTS)
@pytest.mark.parametrize("raw", ["{not json", "[1, 2]", '"text"', "\x00"])
def test_malformed_payload_allows(tmp_path, monkeypatch, event, raw):
    root, env, log = project(tmp_path, "delegate")
    monkeypatch.chdir(root)
    code, _, err = invoke(event, raw, env)
    assert code == 0 and err == ""
    if event == "pre-tool":
        assert not log.exists()


def test_codex_cmd_payload_is_classified(tmp_path):
    root, env, _ = project(tmp_path, "hangar-job")
    payload = {"cwd": str(root), "tool_name": "exec_command", "tool_input": {"cmd": "rm -rf x"}}
    assert invoke("pre-tool", payload, env)[0] == 2


def test_unknown_event_allows(tmp_path):
    _, env, _ = project(tmp_path, "hangar-job")
    code, _, err = invoke("post-tool", {}, env)
    assert code == 0 and "unknown hook event" in err


@pytest.mark.parametrize("command", COMMANDS)
def test_classifier_parity_with_the_generated_shim(command):
    spec = importlib.util.spec_from_file_location("aidlc_hook_generated", GENERATED)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    assert module.classify_command(command) == classify_command(command)


def test_generated_shim_is_the_source_copy():
    assert GENERATED.read_bytes() == (ROOT / "src/ai_dlc/harness/hook_shim.py").read_bytes()


def run_generated(
    tmp_path: Path, event: str, payload: object, extra_env: dict[str, str], path: str
) -> subprocess.CompletedProcess:
    isolated = tmp_path / "isolated"
    isolated.mkdir(exist_ok=True)
    env = {"PATH": path, "HOME": str(tmp_path), **extra_env}
    return subprocess.run(
        [sys.executable, "-I", "-S", str(GENERATED), event],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=isolated,
        env=env,
        timeout=30,
        check=False,
    )


@pytest.mark.parametrize("event", EVENTS)
def test_generated_shim_runs_isolated_without_third_party_imports(tmp_path, event):
    payload = {"cwd": str(tmp_path / "isolated"), "tool_name": "Bash"}
    payload["tool_input"] = {"command": "rm -rf build"}
    result = run_generated(tmp_path, event, payload, {}, "/usr/bin:/bin")
    assert result.returncode == (2 if event == "pre-tool" else 0), result.stderr
    if event == "session-start":
        assert result.stdout.startswith("ai-dlc workflow plugin active")
    assert not (tmp_path / "isolated/.ai-dlc").exists()


def real_cli(directory: Path) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / "ai-dlc"
    script.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m ai_dlc "$@"\n')
    script.chmod(0o755)
    return f"{directory}{os.pathsep}/usr/bin{os.pathsep}/bin"


@pytest.mark.parametrize("hangar", [{"HANGAR_WORKSPACE": "/workspace"}, {"HANGAR_JOB_ID": "job-1"}])
def test_hangar_allows_push_in_adopted_repo_without_work_record(tmp_path, hangar):
    root = tmp_path / "adopted"
    initialize_hook_project(root, None)  # default all-branches policy
    path = real_cli(tmp_path / "bin")
    payload = {"cwd": str(root), "tool_name": "Bash"}
    payload["tool_input"] = {"command": "git push origin feature/x"}
    control = run_generated(tmp_path, "pre-tool", payload, {"PYTHONPATH": str(ROOT / "src")}, path)
    assert control.returncode == 2 and "all-branches" in control.stderr
    result = run_generated(
        tmp_path, "pre-tool", payload, {"PYTHONPATH": str(ROOT / "src"), **hangar}, path
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
