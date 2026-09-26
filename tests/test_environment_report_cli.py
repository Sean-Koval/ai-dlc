"""Compatible CLI selection for effective-environment reports."""

import json
import os
import socket
import subprocess
from pathlib import Path

import pytest
from click import unstyle
from test_environment_report import report
from typer.testing import CliRunner

from ai_dlc.environment.report_io import write_report


@pytest.fixture
def project(tmp_path):
    root = Path(os.path.realpath(tmp_path)) / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text('schema = 4\n[roles]\nscm = "github"\n')
    return root


def _forbid(*args, **kwargs):
    raise AssertionError("unexpected local or remote inspection")


def test_status_without_options_preserves_existing_manager_contract(monkeypatch):
    """Would fail if report options changed ordinary machine status selection or bytes."""
    from ai_dlc import cli

    class Manager:
        def status(self):
            return {"enrolled": False, "ready": False, "next": "unchanged"}

    monkeypatch.setattr(cli, "MachineManager", Manager)

    result = CliRunner().invoke(cli.app, ["machine", "status"])

    assert result.exit_code == 0
    assert result.stdout == (
        '{\n  "enrolled": false,\n  "next": "unchanged",\n  "ready": false\n}\n'
    )


def test_status_stdout_export_is_valid_offline_report(project, monkeypatch):
    """Would fail if stdout export constructed a manager or ran a default process/network probe."""
    from ai_dlc import cli

    monkeypatch.setattr(cli, "MachineManager", _forbid)
    monkeypatch.setattr(subprocess, "Popen", _forbid)
    monkeypatch.setattr(socket, "socket", _forbid)
    monkeypatch.setenv("PATH", "")

    result = CliRunner().invoke(
        cli.app, ["machine", "status", "--root", str(project), "--export", "-"]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["schema_version"] == 1


def test_status_file_export_creates_private_new_file(project, tmp_path, monkeypatch):
    """Would fail if CLI publication replaced a file or emitted report JSON to stdout."""
    from ai_dlc import cli

    destination = Path(os.path.realpath(tmp_path)) / "report.json"
    monkeypatch.setenv("PATH", "")

    result = CliRunner().invoke(
        cli.app,
        ["machine", "status", "--root", str(project), "--export", str(destination)],
    )

    assert result.exit_code == 0, result.output
    assert result.stdout == ""
    assert json.loads(destination.read_text())["schema_version"] == 1
    if os.name != "nt":
        assert destination.stat().st_mode & 0o777 == 0o600

    before = destination.read_bytes()
    refused = CliRunner().invoke(
        cli.app,
        ["machine", "status", "--root", str(project), "--export", str(destination)],
    )
    assert refused.exit_code == 2
    assert refused.stdout == ""
    assert str(destination) not in unstyle(refused.stderr)
    assert destination.read_bytes() == before


def test_compare_reads_exactly_two_files_without_local_collection(tmp_path, monkeypatch):
    """Would fail if comparison consulted a manager, collector, process, or network."""
    from ai_dlc import cli
    from ai_dlc.environment import report as report_service

    root = Path(os.path.realpath(tmp_path))
    left, right = root / "left.json", root / "right.json"
    write_report(left, report())
    write_report(right, report(observed_at="2026-09-26T13:00:00Z"))
    monkeypatch.setattr(cli, "MachineManager", _forbid)
    monkeypatch.setattr(report_service, "collect_report", _forbid)
    monkeypatch.setattr(subprocess, "Popen", _forbid)
    monkeypatch.setattr(socket, "socket", _forbid)

    result = CliRunner().invoke(cli.app, ["machine", "status", "--compare", str(left), str(right)])

    assert result.exit_code == 0, result.output
    comparison = json.loads(result.stdout)
    assert comparison["configuration_complete"] is True
    assert comparison["observation_complete"] is True


def test_compare_maps_required_incompleteness_to_one(tmp_path):
    """Would fail if compare treated a valid but incomplete environment as parity."""
    root = Path(os.path.realpath(tmp_path))
    value = report()
    value["engine"]["current_process"]["installation_kind"] = "unknown"
    value["engine"]["current_process"]["source_revision"] = None
    value["engine"]["current_process"]["source_dirty"] = None
    value["engine"]["current_process"]["reasons"].update(
        {
            "source_revision": "provenance-unavailable",
            "source_dirty": "provenance-unavailable",
        }
    )
    value["engine"]["installation_kind"] = "unknown"
    value["engine"]["source_revision"] = None
    value["engine"]["source_dirty"] = None
    from ai_dlc.environment.report_schema import finalize_report

    value["configuration_identity"] = None
    value["observation_identity"] = None
    incomplete = finalize_report(value)
    left, right = root / "left.json", root / "right.json"
    write_report(left, incomplete)
    write_report(right, incomplete)

    from ai_dlc.cli import app

    result = CliRunner().invoke(app, ["machine", "status", "--compare", str(left), str(right)])

    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["observation_complete"] is False


@pytest.mark.parametrize(
    "arguments",
    [
        ["--export", "-"],
        ["--root", "/tmp/project"],
        ["--probe-versions"],
        ["--root", "/tmp/project", "--export", "-", "--probe-versions", "--compare"],
        ["--root", "/tmp/project", "--export", "-", "--compare", "a", "b"],
        ["--root", "/tmp/project", "--compare", "a", "b"],
        ["--compare", "a", "b", "--probe-versions"],
    ],
)
def test_status_rejects_incompatible_options_before_effects(arguments, monkeypatch):
    """Would fail if an invalid status request reached either local-report implementation."""
    from ai_dlc import cli
    from ai_dlc.environment import report as report_service

    monkeypatch.setattr(cli, "MachineManager", _forbid)
    monkeypatch.setattr(report_service, "collect_report", _forbid)

    result = CliRunner().invoke(cli.app, ["machine", "status", *arguments])

    assert result.exit_code == 2
    assert result.stdout == ""


def test_compare_requires_exactly_two_files():
    """Would fail if comparison silently inferred a missing or extra local input."""
    from ai_dlc.cli import app

    one = CliRunner().invoke(app, ["machine", "status", "--compare", "left.json"])
    sentinel = "SECRET-third-path.json"
    three = CliRunner().invoke(
        app, ["machine", "status", "--compare", "left.json", "right.json", sentinel]
    )

    assert one.exit_code == three.exit_code == 2
    assert one.stdout == three.stdout == ""
    assert sentinel not in unstyle(three.stderr)


@pytest.mark.parametrize("command", [["doctor"], ["machine", "doctor"]])
def test_doctor_effective_environment_uses_shared_offline_report(command, project, monkeypatch):
    """Would fail if either doctor report mode delegated to ordinary health inspection."""
    from ai_dlc import cli

    monkeypatch.setattr(cli, "MachineManager", _forbid)
    monkeypatch.setattr(subprocess, "Popen", _forbid)
    monkeypatch.setattr(socket, "socket", _forbid)
    monkeypatch.setenv("PATH", "")

    result = CliRunner().invoke(
        cli.app, [*command, "--root", str(project), "--effective-environment"]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["schema_version"] == 1


@pytest.mark.parametrize(
    "arguments",
    [
        ["doctor", "--probe-versions"],
        ["machine", "doctor", "--probe-versions"],
        ["doctor", "--effective-environment", "--target", "local"],
        ["machine", "doctor", "--effective-environment", "--target", "local"],
        ["doctor", "--effective-environment", "--machine", "machine.toml"],
    ],
)
def test_doctor_rejects_probe_only_and_explicit_overrides_before_effects(arguments, monkeypatch):
    """Would fail if incompatible report options ran ordinary doctor or report collection."""
    from ai_dlc import cli
    from ai_dlc.environment import report as report_service

    monkeypatch.setattr(cli, "MachineManager", _forbid)
    monkeypatch.setattr(report_service, "collect_report", _forbid)

    result = CliRunner().invoke(cli.app, arguments)

    assert result.exit_code == 2
    assert result.stdout == ""


def test_invalid_compare_input_has_no_json_and_no_raw_diagnostics(tmp_path):
    """Would fail if report contents, file paths, or parser diagnostics escaped on exit 2."""
    from ai_dlc.cli import app

    root = Path(os.path.realpath(tmp_path))
    secret_name = root / "SECRET-report.json"
    secret_name.write_text('{"private":"SECRET-input"')
    valid = root / "valid.json"
    write_report(valid, report())

    result = CliRunner().invoke(
        app, ["machine", "status", "--compare", str(secret_name), str(valid)]
    )

    assert result.exit_code == 2
    assert result.stdout == ""
    error = unstyle(result.stderr)
    assert "SECRET" not in error
    assert str(root) not in error
