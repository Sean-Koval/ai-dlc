"""The consumer onboarding CLI is a thin, read-only plan boundary."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app


@pytest.fixture
def supported_environment(tmp_path, monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr("platform.machine", lambda: "arm64")
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("ai-dlc", "sh", "python"):
        executable = bin_dir / name
        executable.write_text("#!/bin/sh\nexit 99\n")
        executable.chmod(0o755)
    return {
        "HOME": str(home),
        "PATH": str(bin_dir),
        "SHELL": "/bin/zsh",
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_STATE_HOME": str(home / "state"),
    }


def test_onboard_requires_an_explicit_root_and_has_no_apply_option(tmp_path):
    runner = CliRunner()

    missing = runner.invoke(app, ["project", "onboard"])
    applying = runner.invoke(
        app,
        ["project", "onboard", "--root", str(tmp_path), "--apply"],
    )

    assert missing.exit_code == 2
    assert "--root" in missing.stderr
    assert applying.exit_code == 2
    assert "No such option: --apply" in applying.stderr


def test_onboard_reports_a_nonexistent_target_as_input_required(tmp_path, supported_environment):
    missing = tmp_path / "does-not-exist"

    result = CliRunner().invoke(
        app,
        ["project", "onboard", "--root", str(missing), "--agent-client", "codex"],
        env=supported_environment,
    )

    assert result.exit_code == 1, result.output
    report = json.loads(result.stdout)
    assert report["schema"] == 1
    assert report["state"] == "input-required"
    assert report["target"] == str(missing)
    assert {finding["code"] for finding in report["findings"]} == {"target-required"}
    assert not missing.exists()


def test_onboard_forwards_repeated_clients_to_the_read_only_service(
    tmp_path, supported_environment
):
    target = tmp_path / "target"
    target.mkdir()
    authored = target / "README.md"
    authored.write_text("owned by the target\n")

    result = CliRunner().invoke(
        app,
        [
            "project",
            "onboard",
            "--root",
            str(target),
            "--agent-client",
            "codex",
            "--agent-client",
            "claude-code",
            "--preset",
            "generic",
            "--source",
            "https://example.test/profiles.git",
            "--ref",
            "reviewed-v1",
            "--profile-id",
            "work",
            "--machine-id",
            "laptop",
        ],
        env=supported_environment,
    )

    assert result.exit_code == 1, result.output
    report = json.loads(result.stdout)
    assert report["clients"] == ["codex", "claude-code"]
    preview = next(action for action in report["actions"] if action["id"] == "adopt-preview")
    assert preview["argv"] == [
        "ai-dlc",
        "project",
        "adopt",
        "--root",
        str(target),
        "--preset",
        "generic",
        "--capability",
        "agent-client",
        "--agent-client",
        "codex",
        "--agent-client",
        "claude-code",
    ]
    enrollment = next(action for action in report["actions"] if action["id"] == "enroll-preview")
    assert enrollment["argv"] == [
        "ai-dlc",
        "machine",
        "enroll",
        "https://example.test/profiles.git",
        "--ref",
        "reviewed-v1",
        "--profile-id",
        "work",
        "--machine-id",
        "laptop",
    ]
    assert authored.read_text() == "owned by the target\n"
    assert sorted(path.name for path in target.iterdir()) == ["README.md"]


@pytest.mark.parametrize(
    ("state", "exit_code"),
    [
        ("actionable", 0),
        ("input-required", 1),
        ("blocked", 1),
        ("unsupported", 1),
    ],
)
def test_onboard_maps_service_state_to_exit_status(tmp_path, monkeypatch, state, exit_code):
    from ai_dlc.setup import onboarding

    monkeypatch.setattr(
        onboarding,
        "plan_onboarding",
        lambda root, **selection: {"schema": 1, "state": state, "target": str(root)},
    )

    result = CliRunner().invoke(app, ["project", "onboard", "--root", str(tmp_path)])

    assert result.exit_code == exit_code, result.output
    assert json.loads(result.stdout)["state"] == state


def test_onboard_reports_malformed_configuration_without_echoing_sensitive_input(
    tmp_path, supported_environment
):
    target = tmp_path / "target"
    target.mkdir()
    secret = "do-not-echo-this-value"
    (target / "ai-dlc.toml").write_text(f'roles = "{secret}"\n')

    result = CliRunner().invoke(
        app,
        ["project", "onboard", "--root", str(target)],
        env=supported_environment,
    )

    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == "Error: onboarding input or target configuration is invalid\n"
    assert secret not in result.output
