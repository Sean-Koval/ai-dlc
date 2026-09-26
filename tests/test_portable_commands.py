"""Observable portable setup/check execution; native host cases run without a POSIX shell."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import tomli_w

from ai_dlc.config import digest
from ai_dlc.setup import project


def configure(root, *, commands=None, required=None, steps=None):
    config = {"schema": 4}
    if commands is not None:
        config["checks"] = {"required": required or [], "commands": commands}
    if steps is not None:
        config["setup"] = {"steps": steps}
    (root / "ai-dlc.toml").write_text(tomli_w.dumps(config), encoding="utf-8", newline="\n")
    (root / ".mise.toml").write_text("[tools]\n", encoding="utf-8", newline="\n")
    return config


def test_configuration_fixture_uses_utf8_even_with_legacy_platform_defaults(tmp_path, monkeypatch):
    original = Path.write_text

    def write_text(path, data, encoding=None, errors=None, newline=None):
        return original(
            path,
            data,
            encoding=encoding or "cp1252",
            errors=errors,
            newline="\r\n" if newline is None else newline,
        )

    monkeypatch.setattr(Path, "write_text", write_text)
    command = {"argv": ["C:/source é/python.exe", "--version"]}
    configure(tmp_path, commands={"behavior": command}, required=["behavior"])
    assert project.load_project(tmp_path)["checks"]["commands"]["behavior"] == command
    assert b"\r\n" not in (tmp_path / "ai-dlc.toml").read_bytes()


def repository(root, commands, required):
    config = configure(root, commands=commands, required=required)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.test",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    return config


def python(code, *args):
    return {"argv": [sys.executable, "-c", code, *args]}


def test_native_argv_passes_literal_arguments_without_a_shell(tmp_path, monkeypatch):
    arguments = [
        "",
        "two words",
        "héllo 世界",
        "$HOME",
        "&",
        'a"b',
        "line\nnext",
        "; touch injected",
    ]
    monkeypatch.setenv("PATH", "")
    result = project.run_command(
        tmp_path,
        python(
            "import json,sys; from pathlib import Path; Path('args.json').write_text(json.dumps(sys.argv[1:])); assert Path.cwd().name == sys.argv[1]",
            tmp_path.name,
            *arguments,
        ),
        use_mise=False,
    )
    assert result.returncode == 0
    assert json.loads((tmp_path / "args.json").read_text(encoding="utf-8")) == [
        tmp_path.name,
        *arguments,
    ]
    assert not (tmp_path / "injected").exists()


def test_native_focused_checks_preserve_failure_order_and_configuration_digest(tmp_path):
    commands = {
        "required": python("raise SystemExit(0)"),
        "bad": python("raise SystemExit(7)"),
        "other": python("raise SystemExit(99)"),
    }
    config = repository(tmp_path, commands, ["required", "other"])
    receipt = project.check_project(tmp_path, use_mise=False, selected_checks=["bad", "required"])
    assert [(row["id"], row["status"], row["exit_code"]) for row in receipt["outcomes"]] == [
        ("bad", "failed", 7),
        ("required", "passed", 0),
    ]
    assert receipt["required"] == ["required", "other"]
    assert receipt["checks_digest"] == digest(config["checks"])
    assert receipt["dirty"] is False


INVALID_COMMANDS = [
    "",
    " \n",
    "bad\x00script",
    7,
    [],
    {},
    {"argv": []},
    {"argv": [""]},
    {"argv": [" "]},
    {"argv": [7]},
    {"argv": ["python", 7]},
    {"argv": ["python", "\x00"]},
    {"argv": ["python"], "script": "exit 0"},
    {"argv": ["python"], "extra": True},
    {"shell": "bash", "script": "exit 0"},
    {"shell": "posix", "script": ""},
    {"shell": "posix", "script": "\x00"},
    {"shell": "posix"},
    {"shell": "powershell", "script": 7},
    {"shell": "posix", "script": "exit 0", "args": []},
]


@pytest.mark.parametrize("command", INVALID_COMMANDS)
def test_malformed_selected_commands_fail_before_runtime(tmp_path, monkeypatch, command):
    config = {"checks": {"required": [], "commands": {"bad": command}}}
    monkeypatch.setattr(project, "load_project", lambda root: config)
    monkeypatch.setattr(project, "runtime_env", lambda *a, **k: pytest.fail("runtime was resolved"))
    with pytest.raises(ValueError, match="selected check.*bad"):
        project.check_project(tmp_path, selected_checks=["bad"])


@pytest.mark.parametrize("field", ["command", "verify"])
def test_all_setup_commands_are_validated_before_any_mutation(tmp_path, monkeypatch, field):
    steps = [
        {"id": "first", "command": python("from pathlib import Path; Path('changed').touch()")},
        {"id": "later", "command": python("pass"), field: {"argv": []}},
    ]
    configure(tmp_path, steps=steps)
    (tmp_path / ".mise.toml").write_text("[tools]\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(
        project.subprocess, "run", lambda *a, **k: pytest.fail("child launched before validation")
    )
    with pytest.raises(ValueError, match="later"):
        project.setup_project(tmp_path, state_path=tmp_path / "journal.db", use_mise=True)
    assert not (tmp_path / "journal.db").exists()
    assert not (tmp_path / "changed").exists()


def test_invalid_required_command_blocks_an_optional_selection(tmp_path, monkeypatch):
    config = {
        "checks": {
            "required": ["required"],
            "commands": {
                "required": {"argv": ["python"], "shell": "posix"},
                "optional": python("pass"),
            },
        }
    }
    monkeypatch.setattr(project, "load_project", lambda root: config)
    monkeypatch.setattr(project, "runtime_env", lambda *a, **k: pytest.fail("runtime was resolved"))
    with pytest.raises(ValueError, match="required check.*required"):
        project.check_project(tmp_path, selected_checks=["optional"])


@pytest.mark.parametrize("command", ["exit 0", {"shell": "posix", "script": "exit 0"}])
def test_missing_selected_shell_is_a_failed_check_with_remedy(tmp_path, monkeypatch, command):
    repository(tmp_path, {"shell-check": command}, ["shell-check"])
    original_environment = project.runtime_env

    def without_shell(*args, **kwargs):
        environment = original_environment(*args, **kwargs)
        # Keep Git available for receipt metadata, but give the actual command
        # resolver an empty tool directory on every host, including Git-for-Windows.
        environment["PATH"] = str(tmp_path / "empty-tools")
        return environment

    (tmp_path / "empty-tools").mkdir()
    monkeypatch.setattr(project, "runtime_env", without_shell)
    receipt = project.check_project(tmp_path, use_mise=False)
    row = receipt["outcomes"][0]
    assert row["id"] == "shell-check"
    assert row["status"] == "failed"
    assert row["exit_code"] != 0
    assert "POSIX" in row["reason"]
    assert "argv" in row["reason"]


def test_native_missing_executable_is_never_recorded_passed(tmp_path):
    repository(tmp_path, {"missing": {"argv": ["ai-dlc-absent-runtime-12345"]}}, ["missing"])
    receipt = project.check_project(tmp_path, use_mise=False)
    assert receipt["outcomes"][0]["status"] == "failed"
    assert "ai-dlc-absent-runtime-12345" in receipt["outcomes"][0]["reason"]


@pytest.mark.parametrize(
    "failure,code", [(subprocess.TimeoutExpired("native", 1), 124), (KeyboardInterrupt(), 130)]
)
def test_native_cancellation_stops_subsequent_checks(tmp_path, monkeypatch, failure, code):
    repository(
        tmp_path,
        {
            "first": python("pass"),
            "after": python("from pathlib import Path; Path('after').touch()"),
        },
        ["first", "after"],
    )
    monkeypatch.setattr(project, "run_command", lambda *a, **k: (_ for _ in ()).throw(failure))
    receipt = project.check_project(tmp_path, use_mise=False)
    assert [(row["id"], row["status"], row["exit_code"]) for row in receipt["outcomes"]] == [
        ("first", "cancelled", code)
    ]
    assert not (tmp_path / "after").exists()


def test_native_setup_resumes_and_rechecks_dependencies(tmp_path):
    first = python(
        "from pathlib import Path; p=Path('count'); p.write_text(p.read_text()+'x' if p.exists() else 'x')"
    )
    steps = [
        {
            "id": "first",
            "command": first,
            "verify": python("from pathlib import Path; assert Path('count').exists()"),
        },
        {
            "id": "second",
            "command": python("from pathlib import Path; assert Path('ready').exists()"),
        },
    ]
    configure(tmp_path, steps=steps)
    journal = tmp_path / "journal.db"
    with pytest.raises(RuntimeError, match="second"):
        project.setup_project(tmp_path, state_path=journal, use_mise=False)
    (tmp_path / "ready").touch()
    result = project.setup_project(tmp_path, state_path=journal, use_mise=False)
    assert result["steps"] == [
        {"id": "first", "status": "unchanged"},
        {"id": "second", "status": "completed"},
    ]
    assert (tmp_path / "count").read_text(encoding="utf-8") == "x"
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='changed'\n", encoding="utf-8", newline="\n"
    )
    project.setup_project(tmp_path, state_path=journal, use_mise=False)
    assert (tmp_path / "count").read_text(encoding="utf-8") == "xx"


def test_native_setup_command_change_invalidates_completed_state(tmp_path):
    configure(
        tmp_path,
        steps=[
            {
                "id": "one",
                "command": python("from pathlib import Path; Path('value').write_text('old')"),
            }
        ],
    )
    journal = tmp_path / "journal.db"
    project.setup_project(tmp_path, state_path=journal, use_mise=False)
    configure(
        tmp_path,
        steps=[
            {
                "id": "one",
                "command": python("from pathlib import Path; Path('value').write_text('new')"),
            }
        ],
    )
    result = project.setup_project(tmp_path, state_path=journal, use_mise=False)
    assert result["steps"][0]["status"] == "completed"
    assert (tmp_path / "value").read_text(encoding="utf-8") == "new"


@pytest.mark.skipif(
    os.name != "nt", reason="requires native Windows executable and PowerShell semantics"
)
def test_windows_batch_argv_is_refused_and_explicit_powershell_returns_failure(tmp_path):
    batch = tmp_path / "test.cmd"
    batch.write_text("@echo off\necho unsafe > invoked\n", encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="explicit.shell"):
        project.run_command(tmp_path, {"argv": [str(batch)]}, use_mise=False)
    assert not (tmp_path / "invoked").exists()
    result = project.run_command(
        tmp_path,
        {"shell": "powershell", "script": "& $env:COMSPEC /c exit 7; exit $LASTEXITCODE"},
        use_mise=False,
    )
    assert result.returncode == 7


def test_all_command_mode_validates_optional_definitions_before_runtime(tmp_path, monkeypatch):
    configure(tmp_path, commands={"ok": python("pass"), "bad": {"argv": []}}, required=["ok"])
    monkeypatch.setattr(project, "runtime_env", lambda *a, **k: pytest.fail("runtime was resolved"))
    with pytest.raises(ValueError, match="selected check.*bad"):
        project.check_project(tmp_path, required_only=False)


@pytest.mark.parametrize("bad_verify", ["", False, [], {"shell": ["posix"], "script": "exit 0"}])
def test_invalid_optional_verification_is_not_silently_ignored(tmp_path, bad_verify):
    configure(tmp_path, steps=[{"id": "one", "command": python("pass"), "verify": bad_verify}])
    with pytest.raises(ValueError, match="one.*verify"):
        project.setup_project(tmp_path, state_path=tmp_path / "journal.db", use_mise=False)
    assert not (tmp_path / "journal.db").exists()


def test_structured_setup_retries_when_platform_python_marker_disappears(tmp_path, monkeypatch):
    configure(
        tmp_path,
        steps=[
            {
                "id": "deps",
                "command": {"argv": ["uv.exe" if os.name == "nt" else "uv", "sync", "--locked"]},
                "verify": python("pass"),
            }
        ],
    )
    actual_runner = project.run_command
    interpreter = tmp_path / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    def install_environment(root, command, **kwargs):
        if command["argv"][0] in {"uv", "uv.exe"}:
            interpreter.parent.mkdir(parents=True, exist_ok=True)
            interpreter.write_bytes(b"installed fixture")
            (root / ".venv/pyvenv.cfg").write_text("version=3.12", encoding="utf-8", newline="\n")
            return subprocess.CompletedProcess(command, 0)
        return actual_runner(root, command, **kwargs)

    monkeypatch.setattr(project, "run_command", install_environment)
    journal = tmp_path / "journal.db"
    assert (
        project.setup_project(tmp_path, state_path=journal, use_mise=False)["steps"][0]["status"]
        == "completed"
    )
    assert (
        project.setup_project(tmp_path, state_path=journal, use_mise=False)["steps"][0]["status"]
        == "unchanged"
    )
    interpreter.unlink()
    assert (
        project.setup_project(tmp_path, state_path=journal, use_mise=False)["steps"][0]["status"]
        == "completed"
    )
    assert interpreter.read_bytes() == b"installed fixture"


def test_native_command_timeout_does_not_lose_cancel_classification(tmp_path):
    with pytest.raises(subprocess.TimeoutExpired):
        project.run_command(
            tmp_path, python("import time; time.sleep(30)"), use_mise=False, timeout=0.05
        )


def test_relative_native_executable_uses_project_root_not_parent_cwd(tmp_path, monkeypatch):
    executable = Path(sys.executable)
    root = executable.parent.parent
    relative = "./" + executable.relative_to(root).as_posix()
    # CI can place Python on D: and pytest's temporary directory on C:. The
    # executable remains relative to its root; the caller can be on either drive.
    monkeypatch.chdir(tmp_path)
    result = project.run_command(
        root,
        {
            "argv": [
                relative,
                "-c",
                "import sys; from pathlib import Path; assert Path.cwd().samefile(sys.argv[1]); raise SystemExit(9)",
                str(root),
            ]
        },
        use_mise=False,
    )
    assert result.returncode == 9


@pytest.mark.skipif(os.name == "nt", reason="Unix compatibility exercise uses POSIX shell")
def test_legacy_and_explicit_posix_commands_keep_their_meaning(tmp_path):
    for command in ["exit 8", {"shell": "posix", "script": "exit 8"}]:
        assert project.run_command(tmp_path, command, use_mise=False).returncode == 8


def test_native_partial_receipt_cannot_complete_required_checks(tmp_path):
    from ai_dlc.config import load_project, read_toml
    from ai_dlc.providers.scm import validate_receipt

    repository(tmp_path, {"first": python("pass"), "second": python("pass")}, ["first", "second"])
    receipt = project.check_project(
        tmp_path, target="github-actions", use_mise=False, selected_checks=["first"]
    )
    with pytest.raises(ValueError, match="outcomes must exactly match required checks"):
        validate_receipt(
            receipt, receipt["commit"], load_project(tmp_path), read_toml(tmp_path / ".mise.toml")
        )


def test_checks_disable_python_downloads_even_without_mise(tmp_path, monkeypatch):
    monkeypatch.delenv("UV_PYTHON_DOWNLOADS", raising=False)
    result = project.run_command(
        tmp_path,
        python("import os; assert os.environ['UV_PYTHON_DOWNLOADS']=='never'"),
        use_mise=False,
    )
    assert result.returncode == 0


@pytest.mark.skipif(
    os.name == "nt", reason="Unix fake executable; native Windows uses real executable fixtures"
)
def test_mise_resolves_native_tool_and_never_installs_during_checks(tmp_path, monkeypatch):
    directory = tmp_path / "bin"
    directory.mkdir()
    mise = directory / "mise"
    mise.write_text(
        f"#!{sys.executable}\n"
        "import os,sys,subprocess\n"
        "assert os.environ['MISE_AUTO_INSTALL'] == '0'\n"
        "assert os.environ['UV_PYTHON_DOWNLOADS'] == 'never'\n"
        f"program = {sys.executable!r}\n"
        "if sys.argv[1:] == ['which', 'managed-python']:\n"
        "    print(program)\n"
        "elif sys.argv[1:3] == ['exec', '--']:\n"
        "    assert sys.argv[3] == program\n"
        "    raise SystemExit(subprocess.call(sys.argv[3:]))\n"
        "else:\n"
        "    raise SystemExit(99)\n",
        encoding="utf-8",
        newline="\n",
    )
    mise.chmod(0o755)
    monkeypatch.setenv("PATH", str(directory))
    (tmp_path / ".mise.toml").write_text("[tools]\n", encoding="utf-8", newline="\n")
    result = project.run_command(
        tmp_path, {"argv": ["managed-python", "-c", "raise SystemExit(11)"]}, use_mise=True
    )
    assert result.returncode == 11


def test_native_setup_checks_lexical_root_before_loading_configuration(tmp_path, monkeypatch):
    """Exercise the entry boundary on every host; native junction proof is separate."""
    from contextlib import contextmanager
    from types import SimpleNamespace

    from ai_dlc import _windows_storage

    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    # Unix symlinks reproduce resolve() losing the supplied path; Windows uses
    # the actual junction regression below without requiring symlink privilege.
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(alias), str(target)],
            check=True,
            capture_output=True,
        )
    else:
        alias.symlink_to(target, target_is_directory=True)

    @contextmanager
    def refuse_alias(path):
        if path == alias:
            raise ValueError("native root reparse refusal")
        yield

    monkeypatch.setattr(project, "os", SimpleNamespace(name="nt", path=os.path))
    monkeypatch.setattr(_windows_storage, "guarded_path", refuse_alias)
    monkeypatch.setattr(
        project,
        "load_project",
        lambda root: pytest.fail("configuration read before native root guard"),
    )
    with pytest.raises(ValueError, match="root reparse"):
        project.setup_project(alias, state_path=tmp_path / "journal.db", use_mise=False)
    assert not (tmp_path / "journal.db").exists()


@pytest.mark.skipif(os.name != "nt", reason="requires actual Windows NTFS junction semantics")
@pytest.mark.parametrize("junction_at_root", [True, False])
def test_native_setup_refuses_junction_before_setup_side_effects(tmp_path, junction_at_root):
    target = tmp_path / "target"
    root = target if junction_at_root else target / "project"
    root.mkdir(parents=True)
    configure(
        root,
        steps=[
            {"id": "effect", "command": python("from pathlib import Path; Path('changed').touch()")}
        ],
    )
    alias = tmp_path / "alias"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(alias), str(target)],
        check=True,
        capture_output=True,
    )
    selected = alias if junction_at_root else alias / "project"
    before = {
        path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }
    with pytest.raises(ValueError, match="reparse"):
        project.setup_project(selected, state_path=tmp_path / "journal.db", use_mise=False)
    assert not (tmp_path / "journal.db").exists()
    assert {
        path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()
    } == before
