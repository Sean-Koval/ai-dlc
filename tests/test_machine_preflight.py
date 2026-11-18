"""ai-dlc doctor checks a fresh laptop before any repository is adopted (KAN-363)."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from ai_dlc.environment.preflight import machine_preflight


def tool(directory, name, script="exit 0"):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(f"#!/bin/sh\n{script}\n")
    path.chmod(0o755)
    return path


def laptop(tmp_path, *names, gh_signed_in=True):
    """A PATH holding only the named tools, a bootstrap bin on PATH, and no network settings."""
    bin_dir = tmp_path / "bin"
    for name in names:
        tool(bin_dir, name)
    if "gh" in names:
        tool(bin_dir, "gh", "exit 0" if gh_signed_in else "exit 1")
    bootstrap = tmp_path / "bootstrap"
    (bootstrap / "bin").mkdir(parents=True)
    return {
        "PATH": f"{bin_dir}:{bootstrap / 'bin'}",
        "HOME": str(tmp_path / "home"),
        "AI_DLC_BOOTSTRAP_HOME": str(bootstrap),
    }


def by_id(result):
    return {item["id"]: item for item in result["checks"]}


def test_a_ready_laptop_passes_and_points_at_adoption(tmp_path):
    env = laptop(tmp_path, "git", "gh", "claude", "python3")
    result = machine_preflight(tmp_path, environ=env, system="Linux")
    assert result["ready"] is True, result
    assert result["mode"] == "machine-preflight"
    assert "project adopt" in result["next"]
    checks = by_id(result)
    assert checks["gh-auth"]["status"] == "ready"
    assert checks["client:claude-code"]["status"] == "ready"
    # An unselected client that is absent is reported but does not block.
    assert checks["client:codex"]["status"] == "missing"
    assert checks["client:codex"]["required"] is False
    assert checks["mise"]["required"] is False


@pytest.mark.parametrize(
    ("absent", "item", "action"),
    [
        ("git", "git", "Install git"),
        ("gh", "gh", "cli.github.com"),
        ("python3", "python3", "Install Python 3"),
    ],
)
def test_each_missing_required_tool_fails_with_one_next_action(tmp_path, absent, item, action):
    names = [name for name in ("git", "gh", "claude", "python3") if name != absent]
    result = machine_preflight(tmp_path, environ=laptop(tmp_path, *names), system="Linux")
    assert result["ready"] is False
    failing = by_id(result)[item]
    assert failing["status"] == "missing"
    assert action in failing["next_action"]
    assert result["next"] == failing["next_action"]


def test_gh_not_signed_in_names_the_host(tmp_path):
    env = laptop(tmp_path, "git", "gh", "claude", "python3", gh_signed_in=False)
    env["GH_HOST"] = "github.example.com"
    result = machine_preflight(tmp_path, environ=env, system="Linux")
    assert result["ready"] is False
    assert by_id(result)["gh-auth"]["next_action"] == (
        "Run `gh auth login --hostname github.example.com`."
    )


def test_gh_auth_stays_offline_unless_probing(tmp_path):
    calls = []

    def run(argv, environ):
        calls.append(argv[1:])
        return 0

    env = laptop(tmp_path, "git", "gh", "claude", "python3")
    machine_preflight(tmp_path, environ=env, system="Linux", run=run)
    assert calls == [["auth", "token", "--hostname", "github.com"]]
    calls.clear()
    machine_preflight(tmp_path, environ=env, system="Linux", run=run, probe_versions=True)
    assert calls == [["auth", "status", "--hostname", "github.com"]]


def test_a_selected_client_off_path_blocks(tmp_path):
    env = laptop(tmp_path, "git", "gh", "codex", "python3")
    result = machine_preflight(tmp_path, environ=env, system="Linux", clients=["claude-code"])
    assert result["ready"] is False
    claude = by_id(result)["client:claude-code"]
    assert claude["required"] is True
    assert claude["status"] == "missing"
    assert "client:codex" not in by_id(result)


def test_no_client_at_all_blocks(tmp_path):
    result = machine_preflight(
        tmp_path, environ=laptop(tmp_path, "git", "gh", "python3"), system="Linux"
    )
    assert result["ready"] is False
    assert by_id(result)["client"]["status"] == "missing"


def test_client_versions_are_probed_only_on_request(tmp_path):
    env = laptop(tmp_path, "git", "gh", "python3")
    tool(tmp_path / "bin", "claude", 'echo "2.1.0 (Claude Code)"')
    quiet = machine_preflight(tmp_path, environ=env, system="Linux")
    assert "(version" not in by_id(quiet)["client:claude-code"]["detail"]
    probed = machine_preflight(tmp_path, environ=env, system="Linux", probe_versions=True)
    assert "(version 2.1.0)" in by_id(probed)["client:claude-code"]["detail"]


def test_macos_python_stub_is_flagged_without_running_it(tmp_path, monkeypatch):
    from ai_dlc.environment import preflight

    env = laptop(tmp_path, "git", "gh", "claude")
    calls = []

    def run(argv, environ):
        calls.append(argv)
        return 2 if argv[0] == "xcode-select" else 0

    real_which = preflight.shutil.which
    monkeypatch.setattr(
        preflight.shutil,
        "which",
        lambda name, path=None: (
            "/usr/bin/python3" if name == "python3" else real_which(name, path=path)
        ),
    )
    result = machine_preflight(tmp_path, environ=env, system="Darwin", run=run)
    python = by_id(result)["python3"]
    assert python["status"] == "missing"
    assert "Command Line Tools stub" in python["detail"]
    assert ["xcode-select", "-p"] in calls
    assert not any(argv[0].endswith("python3") for argv in calls)


def test_bootstrap_bin_off_path_names_the_shell_step(tmp_path):
    env = laptop(tmp_path, "git", "gh", "claude", "python3")
    env["PATH"] = str(tmp_path / "bin")
    result = machine_preflight(tmp_path, environ=env, system="Linux")
    item = by_id(result)["bootstrap-path"]
    assert item["status"] == "missing"
    assert "workspace-init --shell --apply" in item["next_action"]


def test_network_settings_are_reported_without_secrets(tmp_path):
    env = laptop(tmp_path, "git", "gh", "claude", "python3", gh_signed_in=False)
    env["HTTPS_PROXY"] = "http://user:hunter2@proxy.corp.example:8080"
    env["SSL_CERT_FILE"] = str(tmp_path / "missing-ca.pem")
    env["UV_NATIVE_TLS"] = "1"
    result = machine_preflight(tmp_path, environ=env, system="Linux")
    checks = by_id(result)
    assert checks["https-proxy"]["detail"] == "proxy http://proxy.corp.example:8080"
    assert "hunter2" not in json.dumps(result)
    assert checks["custom-ca"]["status"] == "missing"
    assert checks["github-token"]["status"] == "warning"
    assert "GITHUB_TOKEN" in checks["github-token"]["next_action"]
    env["GITHUB_TOKEN"] = "ghp_secretvalue"
    (tmp_path / "missing-ca.pem").write_text("ca")
    again = by_id(machine_preflight(tmp_path, environ=env, system="Linux"))
    assert again["github-token"]["detail"] == "GITHUB_TOKEN is set"
    assert again["custom-ca"]["status"] == "info"
    assert "UV_NATIVE_TLS=1" in again["custom-ca"]["detail"]
    assert "ghp_secretvalue" not in json.dumps(again)


def test_doctor_without_ai_dlc_toml_runs_the_preflight(tmp_path):
    env = laptop(tmp_path, "git", "gh", "python3")
    empty = tmp_path / "fresh"
    empty.mkdir()
    result = subprocess.run(
        [sys.executable, "-m", "ai_dlc", "doctor", "--root", str(empty)],
        env={**env, "PATH": env["PATH"] + ":/usr/bin:/bin"},
        text=True,
        capture_output=True,
        check=False,
    )
    report = json.loads(result.stdout)
    assert report["mode"] == "machine-preflight"
    assert "no ai-dlc.toml" not in result.stderr
    # claude is off PATH and so is every other agent client: doctor exits non-zero.
    assert by_id(report)["client:claude-code"]["status"] == "missing"
    assert result.returncode == 1


@pytest.mark.parametrize("command", [["doctor"], ["machine", "doctor"]])
def test_both_doctors_preflight_and_accept_agent_client(tmp_path, monkeypatch, command):
    from ai_dlc import cli

    seen = {}

    def fake(root, *, clients, probe_versions):
        seen.update(root=root, clients=clients, probe=probe_versions)
        return {"ready": True, "mode": "machine-preflight"}

    monkeypatch.setattr("ai_dlc.environment.preflight.machine_preflight", fake)
    result = CliRunner().invoke(
        cli.app,
        [*command, "--root", str(tmp_path), "--agent-client", "codex", "--probe-versions"],
    )
    assert result.exit_code == 0, result.output
    assert seen == {"root": tmp_path, "clients": ["codex"], "probe": True}


def test_agent_client_is_refused_inside_a_project(tmp_path):
    from ai_dlc import cli

    (tmp_path / "ai-dlc.toml").write_text("schema = 4\n")
    result = CliRunner().invoke(
        cli.app, ["doctor", "--root", str(tmp_path), "--agent-client", "codex"]
    )
    assert result.exit_code == 2
    assert "machine preflight" in result.output


def test_readiness_checks_the_client_cli_not_only_its_guidance(tmp_path):
    from ai_dlc.setup.readiness import _client_command_checks

    checks = _client_command_checks(
        ["claude-code", "codex", "antigravity"],
        lambda commands: {"available": commands == ["codex"]},
    )
    assert [(c["component"], c["dimension"], c["status"]) for c in checks] == [
        ("claude-code", "tool", "missing"),
        ("codex", "tool", "ready"),
    ]
    assert "Claude Code" in checks[0]["next_action"]


def test_project_readiness_blocks_on_a_selected_client_off_path(tmp_path):
    from ai_dlc.setup.provision import project_readiness, readiness_config

    root = tmp_path / "repo"
    root.mkdir()
    (root / "ai-dlc.toml").write_text('schema = 4\n[roles]\nagent-client = ["claude-code"]\n')
    result = project_readiness(root, readiness_config(root), {"PATH": str(tmp_path / "bin")})
    assert result["ready"] is False
    tool_rows = [c for c in result["checks"] if c["dimension"] == "tool"]
    assert {"component": "claude-code", "status": "missing"}.items() <= tool_rows[0].items()
