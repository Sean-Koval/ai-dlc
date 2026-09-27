"""Thin CLI coverage for bounded offline native verification."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from click import unstyle
from test_native_verification import (
    historical_removed_scope,
    imported_report,
    isolated_environment,
)
from typer.testing import CliRunner

from ai_dlc.environment.report_io import write_report


@pytest.fixture
def verification_cli(tmp_path, monkeypatch):
    root, home, environment = isolated_environment(tmp_path)
    report_path = tmp_path / "environment.json"
    write_report(report_path, imported_report(root, home, environment))
    monkeypatch.setattr(Path, "home", lambda: home)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    return root, report_path


def test_valid_pending_cli_emits_json_and_exits_one_without_process_probe(
    verification_cli, monkeypatch
):
    """Would fail if valid incomplete scope were malformed, green or effectful."""
    from ai_dlc.cli import app

    root, report_path = verification_cli

    def forbidden(*args, **kwargs):
        raise AssertionError("native verification launched a process")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = CliRunner().invoke(
        app,
        [
            "agents",
            "verify",
            "--root",
            str(root),
            "--client",
            "codex",
            "--environment",
            str(report_path),
        ],
    )

    assert result.exit_code == 1, result.output
    output = json.loads(result.stdout)
    assert output["result"]["state"] == "pending"
    assert output["result"]["recognized"] == "pending"
    assert output["result"]["authenticated"] == "not-assessed"
    assert output["exit_code"] == 1


def test_malformed_evidence_cli_exits_two_without_private_input_or_path(verification_cli, tmp_path):
    """Would fail if malformed evidence content or its selected path reached diagnostics."""
    from ai_dlc.cli import app

    root, report_path = verification_cli
    evidence = tmp_path / "SECRET-evidence.json"
    evidence.write_text('{"PRIVATE_SENTINEL":"secret"}')

    result = CliRunner().invoke(
        app,
        [
            "agents",
            "verify",
            "--root",
            str(root),
            "--client",
            "codex",
            "--environment",
            str(report_path),
            "--evidence",
            str(evidence),
        ],
        color=True,
    )

    assert result.exit_code == 2
    assert result.stdout == ""
    error = unstyle(result.stderr)
    assert "Native verification input could not be read safely" in error
    assert "SECRET" not in error
    assert "PRIVATE" not in error
    assert str(tmp_path) not in error


def test_historical_removed_skill_and_server_cli_emits_stale_result(tmp_path, monkeypatch):
    """Would fail if the CLI treated valid historical scope as malformed current scope."""
    from ai_dlc.cli import app
    from ai_dlc.environment import report as report_service

    root, home, report_path, evidence_path, environment, changed = historical_removed_scope(
        tmp_path
    )
    monkeypatch.setattr(Path, "home", lambda: home)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(report_service, "collect_report", lambda *args, **kwargs: changed)

    result = CliRunner().invoke(
        app,
        [
            "agents",
            "verify",
            "--root",
            str(root),
            "--client",
            "codex",
            "--environment",
            str(report_path),
            "--evidence",
            str(evidence_path),
        ],
    )

    assert result.exit_code == 1, result.output
    output = json.loads(result.stdout)
    assert output["result"]["state"] == "stale"
    assert [step["result"] for step in output["result"]["steps"]] == ["passed"] * 3
    selected = {step["id"]: step for step in output["procedure"]["steps"]}
    assert selected["skill"]["artifact_id"] is None
    assert selected["mcp"]["artifact_id"] is None
    assert selected["mcp"]["tool_id"] is None


def test_unknown_cli_arguments_are_rejected_before_any_file_read(verification_cli, monkeypatch):
    """Would fail if Click disclosed an extra token or verification opened inputs first."""
    from ai_dlc import cli
    from ai_dlc.environment import report_io

    root, report_path = verification_cli

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid CLI selection reached file IO")

    monkeypatch.setattr(report_io, "read_report", forbidden)
    sentinel = "SECRET-extra-path"
    result = CliRunner().invoke(
        cli.app,
        [
            "agents",
            "verify",
            "--root",
            str(root),
            "--client",
            "codex",
            "--environment",
            str(report_path),
            sentinel,
        ],
        color=True,
    )

    assert result.exit_code == 2
    assert result.stdout == ""
    error = unstyle(result.stderr)
    assert "Unexpected extra arguments" in error
    assert sentinel not in error
