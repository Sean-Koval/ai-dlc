"""The contributor journey must not secretly require a POSIX shell on Windows."""

import tomllib
from pathlib import Path

from ai_dlc.setup.commands import parse_command

ROOT = Path(__file__).resolve().parents[1]


def test_contributor_setup_and_required_checks_have_native_command_records():
    config = tomllib.loads((ROOT / "ai-dlc.toml").read_text())
    commands = [config["checks"]["commands"][name] for name in config["checks"]["required"]]
    for step in config["setup"]["steps"]:
        commands.extend([step["command"], step["verify"]])
    for command in commands:
        assert parse_command(command).shell is None, command


def test_native_bootstrap_assets_are_packaged_byte_for_byte():
    for name in (
        "scripts/bootstrap.ps1",
        "bootstrap/windows.json",
        "bootstrap/windows.ps1",
        "bootstrap/windows-native.cs",
        "bootstrap/windows-select.py",
    ):
        assert (ROOT / name).read_bytes() == (
            ROOT / "project-templates/project" / name
        ).read_bytes()


def _force_legacy_text_default(monkeypatch):
    original = Path.read_text

    def read_text(path, encoding=None, errors=None):
        return original(path, encoding=encoding or "cp1252", errors=errors)

    monkeypatch.setattr(Path, "read_text", read_text)


def test_project_configuration_is_utf8_with_legacy_platform_default(tmp_path, monkeypatch):
    from ai_dlc.config import read_toml

    config = tmp_path / "ai-dlc.toml"
    config.write_bytes('schema = 4\n[project]\nname = "équipe’s project"\n'.encode())
    _force_legacy_text_default(monkeypatch)
    assert read_toml(config)["project"]["name"] == "équipe’s project"


def test_rendered_utf8_provider_guidance_stays_clean_with_legacy_default(tmp_path, monkeypatch):
    from ai_dlc.harness.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_bytes(
        b'schema = 4\n[roles]\ntracker = "github-issues"\nspecs = "openspec"\n'
    )
    render_agents(tmp_path, apply=True)
    provider = tmp_path / ".ai-dlc/providers/github-issues.md"
    original = provider.read_bytes()
    assert "’" in original.decode("utf-8")
    _force_legacy_text_default(monkeypatch)
    checked = render_agents(tmp_path)
    assert checked["clean"], checked["changed"]
    render_agents(tmp_path, apply=True)
    assert provider.read_bytes() == original


def test_ci_stale_generated_error_identifies_changed_paths(tmp_path):
    import pytest

    from ai_dlc.setup.project import setup_project

    (tmp_path / "ai-dlc.toml").write_bytes(b"schema = 4\n")
    with pytest.raises(ValueError, match=r"generated project files are stale.*AGENTS\.md"):
        setup_project(
            tmp_path, target="github-actions", state_path=tmp_path / "state.db", use_mise=False
        )
