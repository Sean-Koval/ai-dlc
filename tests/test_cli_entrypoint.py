"""The console entry point reports expected failures in one line (KAN-251)."""

import os
import subprocess
import sys

import pytest
import typer

from ai_dlc import cli
from ai_dlc.errors import RefusedError


def run_module(*args, cwd, env=None):
    environment = dict(os.environ)
    environment.pop(cli.TRACEBACK_ENV, None)
    environment.update(env or {})
    return subprocess.run(
        [sys.executable, "-m", "ai_dlc", *args],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_missing_project_file_names_the_directory_and_the_way_out(tmp_path):
    result = run_module("provider", "list", "--root", str(tmp_path), cwd=tmp_path)

    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert f"Error: no ai-dlc.toml in {tmp_path.resolve()}" in result.stderr
    assert "pass --root PATH" in result.stderr
    assert "AI_DLC_TRACEBACK=1" in result.stderr


def test_traceback_variable_restores_the_traceback(tmp_path):
    result = run_module(
        "provider", "list", "--root", str(tmp_path), cwd=tmp_path, env={cli.TRACEBACK_ENV: "1"}
    )

    assert result.returncode == 1
    assert "FileNotFoundError" in result.stderr


def raising(exc):
    def fake_app():
        raise exc

    return fake_app


@pytest.mark.parametrize(
    ("exc", "message"),
    [
        (ValueError("Work must be reviewed before mutation"), "Work must be reviewed"),
        (RuntimeError("Provider failed: Jira requires an explicit Cloud site URL"), "Jira"),
        (RefusedError("refused before any change"), "refused before any change"),
        (
            subprocess.CalledProcessError(1, ["mise", "install"]),
            "command failed with exit status 1: mise install",
        ),
    ],
)
def test_expected_failures_print_one_line_and_keep_exit_status_one(
    monkeypatch, capsys, exc, message
):
    monkeypatch.delenv(cli.TRACEBACK_ENV, raising=False)
    monkeypatch.setattr(cli, "app", raising(exc))

    with pytest.raises(SystemExit) as exit_info:
        cli.run()

    assert exit_info.value.code == 1
    err = capsys.readouterr().err
    assert err.splitlines()[0].startswith("Error: ")
    assert message in err
    assert "Traceback" not in err


def test_notes_follow_the_error_line(monkeypatch, capsys):
    exc = RuntimeError("setup step failed")
    exc.add_note("hint: rerun to resume")
    monkeypatch.delenv(cli.TRACEBACK_ENV, raising=False)
    monkeypatch.setattr(cli, "app", raising(exc))

    with pytest.raises(SystemExit):
        cli.run()

    assert capsys.readouterr().err.splitlines()[:2] == [
        "Error: setup step failed",
        "hint: rerun to resume",
    ]


def test_bugs_keep_their_traceback(monkeypatch):
    monkeypatch.delenv(cli.TRACEBACK_ENV, raising=False)
    monkeypatch.setattr(cli, "app", raising(KeyError("unexpected")))

    with pytest.raises(KeyError):
        cli.run()


def test_typer_exits_pass_through_unchanged(monkeypatch):
    monkeypatch.setattr(cli, "app", raising(typer.Exit(2)))

    with pytest.raises(typer.Exit) as exit_info:
        cli.run()

    assert exit_info.value.exit_code == 2


def test_console_scripts_use_the_reporting_entry_point():
    import tomllib
    from pathlib import Path

    scripts = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())["project"][
        "scripts"
    ]

    assert scripts["ai-dlc"] == "ai_dlc.cli:run"
    assert scripts["ai-dlc-cli"] == "ai_dlc.cli:run"


def test_failed_mise_install_says_how_to_resume(tmp_path, monkeypatch):
    from ai_dlc.setup.project import setup_project

    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text("schema = 4\n")
    (root / ".mise.toml").write_text("[tools]\n")
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    fake = fakebin / "mise"
    fake.write_text('#!/bin/sh\n[ "$1" = install ] && exit 3\nexit 0\n')
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fakebin}:{os.environ['PATH']}")

    with pytest.raises(RuntimeError, match=r"exit 3\).*rerun `ai-dlc project setup` to resume"):
        setup_project(root, state_path=tmp_path / "state.db", use_mise=True)

    assert not (tmp_path / "state.db").exists()
