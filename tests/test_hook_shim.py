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
from ai_dlc.harness.hook_shim import classify_command

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
    "git -C elsewhere reset --hard",
    "git --git-dir=.git clean -fdx",
    "cmd /c del /q build",
    "cmd.exe /c dir",
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


def test_delegated_denial_is_passed_through(tmp_path):
    root, env, _ = project(tmp_path, "delegate")
    fake_cli(tmp_path / "bin", exit_code=2, stderr="Push denied: native\n")
    code, _, err = invoke("pre-tool", payload_for("pre-tool", root), env)
    assert code == 2 and err == "Push denied: native\n"


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_destructive_check_runs_before_delegating(tmp_path, tool):
    """KAN-487: a CLI older than the plugin exits 0 for a tool it doesn't know."""
    root, env, log = project(tmp_path, "delegate")
    payload = {"cwd": str(root), "tool_name": tool, "tool_input": {"command": "rm -rf build"}}
    assert invoke("pre-tool", payload, env) == (2, "", hook_shim.DESTRUCTIVE_REASON + "\n")
    assert not log.exists()


@pytest.mark.parametrize("exit_code", [1, 127, 3])
def test_failed_delegate_falls_back_to_the_plugin_check(tmp_path, exit_code):
    root, env, _ = project(tmp_path, "delegate")
    fake_cli(tmp_path / "bin", exit_code=exit_code, stdout="ignored", stderr="boom")
    note = f"ai-dlc workflow plugin: ai-dlc hook pre-tool exited {exit_code}; "
    note += "allowed after the plugin's own check.\n"
    code, out, err = invoke("pre-tool", payload_for("pre-tool", root), env)
    assert code == 0 and out == "" and err == note
    # KAN-487: a broken CLI no longer turns the destructive check off.
    code, out, err = invoke("pre-tool", payload_for("pre-tool", root, "rm -rf build"), env)
    assert (code, out, err) == (2, "", hook_shim.DESTRUCTIVE_REASON + "\n")


@pytest.mark.parametrize("event", ["session-start", "stop"])
def test_failed_delegate_allows_other_events(tmp_path, event):
    root, env, _ = project(tmp_path, "delegate")
    fake_cli(tmp_path / "bin", exit_code=1, stdout="ignored")
    code, out, err = invoke(event, payload_for(event, root), env)
    assert (code, out) == (0, "")
    assert err == f"ai-dlc workflow plugin: ai-dlc hook {event} exited 1; allowed.\n"


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


MALFORMED = ["{not json", "[1, 2]", '"text"', "\x00", "null", ""]


@pytest.mark.parametrize("event", ["session-start", "stop"])
@pytest.mark.parametrize("raw", MALFORMED)
def test_malformed_payload_never_blocks_session_start_or_stop(tmp_path, monkeypatch, event, raw):
    root, env, _ = project(tmp_path, "delegate")
    monkeypatch.chdir(root)
    code, _, err = invoke(event, raw, env)
    assert code == 0 and err == ""


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("raw", MALFORMED)
def test_malformed_pre_tool_payload_fails_closed(tmp_path, monkeypatch, mode, raw):
    """KAN-487: a payload the shim cannot read may still be a shell call, so it blocks."""
    root, env, log = project(tmp_path, mode)
    monkeypatch.chdir(root)
    code, out, err = invoke("pre-tool", raw, env)
    assert (code, out, err) == (2, "", hook_shim.UNJUDGED_REASON + "\n")
    assert not log.exists()


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "tool_input",
    [None, "rm -rf build", {}, {"command": None}, {"command": ["rm", "-rf", "build"]}],
)
@pytest.mark.parametrize("tool", ["Bash", "PowerShell", "exec_command"])
def test_shell_call_without_a_command_string_fails_closed(tmp_path, mode, tool, tool_input):
    root, env, _ = project(tmp_path, mode)
    payload = {"cwd": str(root), "tool_name": tool, "tool_input": tool_input}
    code, _, err = invoke("pre-tool", payload, env)
    assert (code, err) == (2, hook_shim.UNJUDGED_REASON + "\n")


POWERSHELL_DESTRUCTIVE = [
    "rm -rf build",
    "rm -r -fo build",
    "git reset --hard HEAD~1",
    "git clean -fdx",
    "git push --force origin main",
    "Set-Location src; rm notes.txt",
    # PowerShell is case-insensitive, and its backtick escapes and continues lines.
    "RM -r build",
    "Git Reset --hard",
    "git reset `--hard",
    "git reset `\n  --hard HEAD",
    "git clean `-fdx",
    "git push `--force origin main",
    'rm -rf y; Write-Host "a`"b"',
    # KAN-493: PowerShell's own deletes, and git named as git.exe or by its full path.
    "Remove-Item -Recurse -Force src",
    "ri -r -fo src",
    "rd -r src",
    "rmdir src",
    "del /s /q src",
    "erase notes.txt",
    "Remove-Item notes.txt",
    "Get-ChildItem *.log | Remove-Item",
    "Microsoft.PowerShell.Management\\Remove-Item src -Recurse",
    "git.exe reset --hard",
    "GIT.EXE push -f origin main",
    '& "C:\\Program Files\\Git\\cmd\\git.exe" push --force origin main',
    "C:\\Git\\cmd\\git.exe clean -fdx",
    "C:\\Program` Files\\Git\\cmd\\git.exe push --force",
    ". git.exe push --force",
    "git.cmd push --force",
    # The usual recursive delete is inside a script block.
    "Get-ChildItem build | ForEach-Object { Remove-Item $_ -Recurse -Force }",
    "gci build | % {ri $_ -r -fo}",
    "try { Remove-Item src -Recurse } catch {}",
    # KAN-493 review: cmd.exe's line is judged with its own deletes, and git's global
    # options don't hide the subcommand.
    "cmd /c del /s /q src",
    "& cmd.exe /C RD /S /Q build",
    "C:\\Windows\\System32\\cmd.exe /c erase notes.txt",
    "git -C repo reset --hard",
]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("command", POWERSHELL_DESTRUCTIVE)
def test_powershell_destructive_command_is_denied(tmp_path, mode, command):
    """KAN-487: Claude Code on native Windows runs shell commands as the PowerShell tool."""
    root, env, log = project(tmp_path, mode)
    payload = {"cwd": str(root), "tool_name": "PowerShell", "tool_input": {"command": command}}
    code, out, err = invoke("pre-tool", payload, env)
    assert (code, out, err) == (2, "", hook_shim.DESTRUCTIVE_REASON + "\n")
    assert not log.exists()


@pytest.mark.parametrize(
    "command",
    [
        "Get-ChildItem",
        "git status",
        "git push origin feature/x",
        'Write-Host "a`tb"',
        "Get-Content C:\\work\\notes.txt",
        "git.exe status",
        '& "C:\\Program Files\\Git\\cmd\\git.exe" log -1',
        "Get-Item src | Select-Object FullName",
        "Get-ChildItem | Where-Object { $_.Length -gt 1kb }",
        "$h = @{a = 1}; Write-Host ${env:PATH}",
        "Write-Host 'Remove-Item { x }'",
        "cmd /c dir",
        'cmd /c echo "don\'t"',
        "git -C repo status",
    ],
)
def test_ordinary_powershell_command_is_allowed(tmp_path, command):
    root, env, _ = project(tmp_path, "no-cli")
    payload = {"cwd": str(root), "tool_name": "PowerShell", "tool_input": {"command": command}}
    assert invoke("pre-tool", payload, env) == (0, "", "")


@pytest.mark.parametrize(
    "command, category",
    [
        # KAN-493: a program is known by its name, wherever it lives.
        ("/usr/bin/git reset --hard", "destructive"),
        ("/bin/rm -rf build", "destructive"),
        ("git.exe push --force origin main", "destructive"),
        ("./tools/git.exe clean -fd", "destructive"),
        # PowerShell's delete aliases are other programs, or none, in a POSIX shell.
        ("del notes.txt", "ordinary"),
        ("rd build", "ordinary"),
        ("Remove-Item build", "ordinary"),
        ("/usr/bin/git status", "ordinary"),
    ],
)
def test_bash_names_programs_by_their_name(command, category):
    assert hook_shim.classify_shell("Bash", command) == category


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
@pytest.mark.parametrize(
    "command, category",
    [
        # KAN-493 review: the line cmd /c runs is judged as cmd.exe reads it.
        ("cmd /c del foo", "destructive"),
        ("cmd.exe /c rd /s /q build", "destructive"),
        ("cmd /c erase notes.txt", "destructive"),
        ("cmd /c rmdir build", "destructive"),
        ("cmd /c rm -rf build", "destructive"),
        ("CMD /C DEL foo", "destructive"),
        ('cmd /c "del /q foo"', "destructive"),
        ('cmd /c"del foo"', "destructive"),
        ("cmd /s /q /c del foo", "destructive"),
        ("cmd /k del foo", "destructive"),
        ("cmd //c del foo", "destructive"),
        ("cmd /c d^el foo", "destructive"),
        # cmd.exe takes a switch glued straight onto the command name.
        ("cmd /c rd/s/q build", "destructive"),
        ("cmd /c del/q foo", "destructive"),
        ("cmd /c erase/f notes.txt", "destructive"),
        ("cmd /c rmdir/s build", "destructive"),
        ('cmd /c "dir & rd/s/q build"', "destructive"),
        ("cmd /c cmd/c del foo", "destructive"),
        ("cmd /c dir/s", "ordinary"),
        ("cmd /c c:/tools/report.exe /q", "ordinary"),
        ('cmd /c "dir && del foo"', "destructive"),
        ('cmd /c "echo a & git reset --hard"', "destructive"),
        ("cmd /c cmd /c del foo", "destructive"),
        ("cmd /c git push --force", "destructive"),
        ("cmd /c git push origin main", "bound-operation"),
        ("cmd /c dir", "ordinary"),
        ('cmd /c echo "don\'t"', "ordinary"),
        ("cmd /c type notes.txt", "ordinary"),
        ("cmd", "ordinary"),
        ("cmd del foo", "ordinary"),
        # git's global options come before its subcommand; skipping them finds it.
        ("git -C repo reset --hard", "destructive"),
        ("git -c core.pager=less reset --hard", "destructive"),
        ("git --git-dir=.git reset --hard", "destructive"),
        ("git --git-dir .git --work-tree . clean -fd", "destructive"),
        ("git --no-pager -P -C repo push --force origin main", "destructive"),
        ("git -C repo push --delete origin x", "destructive"),
        ("git --no-pager push origin main", "bound-operation"),
        ("git -c push.default=current push", "bound-operation"),
        # A push in another repository keeps the unsupported verdict it had.
        ("git -C repo push origin main", "unsupported"),
        ("git --git-dir=other/.git push", "unsupported"),
        ("git -C repo status", "ordinary"),
        ("git -c color.ui=never log -1", "ordinary"),
        ("git -C repo", "ordinary"),
    ],
)
def test_cmd_lines_and_git_global_options_are_judged(tool, command, category):
    assert hook_shim.classify_shell(tool, command) == category


@pytest.mark.parametrize("mode", MODES)
def test_other_tools_are_allowed_but_an_unnamed_call_needs_a_command(tmp_path, mode):
    root, env, log = project(tmp_path, mode)
    other = {"cwd": str(root), "tool_name": "MultiEdit", "tool_input": {"file_path": "a"}}
    assert invoke("pre-tool", other, env) == (0, "", "")
    unnamed = {"cwd": str(root), "tool_input": {"file_path": "a"}}
    assert invoke("pre-tool", unnamed, env)[0] == 2
    assert not log.exists()


@pytest.mark.parametrize("event, code", [("pre-tool", 2), ("stop", 0), ("session-start", 0)])
def test_an_error_inside_the_shim_blocks_only_pre_tool(monkeypatch, capsys, event, code):
    """A closed stdin (sys.stdin is None) raises inside run(); only pre-tool may block."""
    monkeypatch.setattr(sys, "argv", ["aidlc_hook.py", event])
    monkeypatch.setattr(sys, "stdin", None)
    monkeypatch.delenv("AI_DLC_HOOKS", raising=False)
    assert hook_shim.main() == code
    assert ("blocked" if code else "allowed") in capsys.readouterr().err


def test_an_error_inside_the_shim_allows_when_hooks_are_off(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["aidlc_hook.py", "pre-tool"])
    monkeypatch.setattr(sys, "stdin", None)
    monkeypatch.setenv("AI_DLC_HOOKS", "off")
    assert hook_shim.main() == 0


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
    for tool in hook_shim.SHELL_TOOLS:
        assert module.classify_shell(tool, command) == hook_shim.classify_shell(tool, command)


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


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_generated_shim_fails_closed_on_empty_stdin(tmp_path, tool):
    result = run_generated(tmp_path, "pre-tool", "", {}, "/usr/bin:/bin")
    assert result.returncode == 2 and "could not read a command" in result.stderr
    payload = {"cwd": str(tmp_path / "isolated"), "tool_name": tool}
    payload["tool_input"] = {"command": "git reset --hard"}
    assert run_generated(tmp_path, "pre-tool", payload, {}, "/usr/bin:/bin").returncode == 2


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


@pytest.mark.parametrize("command", ["rm -rf build", "git reset --hard HEAD~1"])
def test_delegated_cli_denies_a_powershell_destructive_command(tmp_path, command):
    root = tmp_path / "adopted"
    initialize_hook_project(root, None)
    path = real_cli(tmp_path / "bin")
    payload = {"cwd": str(root), "tool_name": "PowerShell", "tool_input": {"command": command}}
    result = run_generated(tmp_path, "pre-tool", payload, {"PYTHONPATH": str(ROOT / "src")}, path)
    assert result.returncode == 2 and "Destructive operation denied" in result.stderr
    assert "using the plugin's own check" not in result.stderr


@pytest.mark.parametrize(
    "file_path, delegated",
    [
        ("docs/specs/feature.md", True),
        ("src/module.py", False),
        ("../outside/docs/specs/x.md", False),
    ],
)
@pytest.mark.parametrize("tool", ["Edit", "Write"])
def test_edit_payloads_reach_the_cli_only_for_specification_files(
    tmp_path, tool, file_path, delegated
):
    """KAN-318: the matcher routes Edit and Write here; only docs/specs edits start the CLI."""
    root, env, log = project(tmp_path, "delegate")
    payload = {
        "cwd": str(root),
        "session_id": "s-1",
        "tool_name": tool,
        "tool_input": {"file_path": str(root / file_path)},
    }
    code, out, err = invoke("pre-tool", payload, env)
    calls = log.read_text().splitlines() if log.exists() else []
    assert code == 0 and err == ""
    assert len(calls) == (1 if delegated else 0)
    assert out == ("delegated context\n" if delegated else "")


def test_cli_warns_on_a_specification_edit_routed_by_the_plugin(tmp_path):
    from typer.testing import CliRunner

    from ai_dlc.cli import app

    payload = {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(tmp_path / "docs/specs/feature.md")},
    }
    result = CliRunner().invoke(
        app, ["hook", "pre-tool", "--root", str(tmp_path)], input=json.dumps(payload)
    )
    assert result.exit_code == 0
    assert "Specification edit" in result.stdout
