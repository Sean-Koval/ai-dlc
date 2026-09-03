import pytest


def test_headless_plan_omits_desktop_and_does_not_upgrade(tmp_path):
    from ai_dlc.provision import machine_plan

    profile = tmp_path / "profile.toml"
    profile.write_text('schema=4\n[modules]\ninclude=["core","vscode","obsidian"]\n')
    result = machine_plan(profile, headless=True, system="Darwin", architecture="arm64")
    assert [x["id"] for x in result["omitted"]] == ["vscode", "obsidian"]
    assert not any(x == "upgrade" for step in result["commands"] for x in step["argv"])
    assert "--no-upgrade" in result["commands"][0]["argv"]


def test_unsupported_os_fails_before_install(tmp_path):
    from ai_dlc.provision import machine_plan

    profile = tmp_path / "p.toml"
    profile.write_text("schema=4\n")
    with pytest.raises(ValueError, match="unsupported"):
        machine_plan(profile, system="Windows", architecture="x86_64")


def test_migration_refuses_unknown_future_version_without_writing(tmp_path):
    from ai_dlc.provision import migrate

    profile = tmp_path / "p.toml"
    profile.write_text("schema=99\n")
    before = profile.read_bytes()
    with pytest.raises(ValueError, match="schema"):
        migrate(profile, apply=True)
    assert profile.read_bytes() == before


def test_doctor_checks_alias_provider_requirements(tmp_path, monkeypatch):
    from ai_dlc import agents, provision

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\ntracker="team-tracker"\n[providers.team-tracker]\nkind="linear"\ntoken_env="AI_DLC_TEST_MISSING_TOKEN"\n'
    )
    monkeypatch.delenv("AI_DLC_TEST_MISSING_TOKEN", raising=False)
    monkeypatch.setattr(provision.shutil, "which", lambda name: None)
    monkeypatch.setattr(agents, "render_agents", lambda root: {"changed": []})
    result = provision.doctor(tmp_path)
    assert not result["ready"]
    assert any("AI_DLC_TEST_MISSING_TOKEN" in s for s in result["signins"])
    assert any("team_id" in s for s in result["configuration"])
    assert any("closed" in s for s in result["configuration"])


def test_machine_apply_activates_runtimes_and_personal_agents(tmp_path, monkeypatch):
    import json
    import tomllib

    from ai_dlc.provision import machine_apply

    binaries = tmp_path / "bin"
    binaries.mkdir()
    for name in ["brew", "mise"]:
        executable = binaries / name
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    bootstrap = tmp_path / "bootstrap"
    profile = tmp_path / "profile.toml"
    profile.write_text(
        """schema=4
[modules]
include=["core", "python"]
[[agents.servers]]
id="notes"
command="notes-mcp"
env=["NOTES_TOKEN"]
"""
    )
    monkeypatch.setenv("PATH", f"{binaries}:/usr/bin:/bin")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("AI_DLC_BOOTSTRAP_HOME", str(bootstrap))
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr("ai_dlc.provision.platform.system", lambda: "Darwin")
    monkeypatch.setattr("ai_dlc.provision.platform.machine", lambda: "arm64")

    result = machine_apply(profile, home=home)

    assert result["ready"] is True
    assert result["workstation"]["ready"] is True
    assert result["agent_configuration"]["applied"] is True
    assert tomllib.loads((home / ".config/mise/config.toml").read_text())["tools"] == {
        "python": "3.12.11",
        "uv": "0.9.11",
    }
    assert str(bootstrap / "bin") in (home / ".zshrc").read_text()
    assert json.loads((home / ".claude.json").read_text())["mcpServers"]["notes"] == {
        "command": "notes-mcp",
        "env": {"NOTES_TOKEN": "${NOTES_TOKEN}"},
    }


def test_machine_plan_previews_personal_agents_without_writing(tmp_path):
    from ai_dlc.provision import machine_plan

    profile = tmp_path / "profile.toml"
    profile.write_text('schema=4\n[[agents.servers]]\nid="notes"\ncommand="notes-mcp"\n')
    home = tmp_path / "home"
    home.mkdir()
    result = machine_plan(profile, system="Darwin", architecture="arm64", home=home)
    assert result["agent_configuration"]["clean"] is False
    assert result["agent_configuration"]["applied"] is False
    assert not list(home.iterdir())


def test_machine_apply_scopes_default_workstation_state_to_explicit_home(tmp_path, monkeypatch):
    from ai_dlc.provision import machine_apply

    binaries = tmp_path / "bin"
    binaries.mkdir()
    for name in ["brew", "mise"]:
        executable = binaries / name
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
    profile = tmp_path / "profile.toml"
    profile.write_text("schema=4\n[modules]\ninclude=[]\n")
    home = tmp_path / "selected-home"
    home.mkdir()
    monkeypatch.setenv("PATH", f"{binaries}:/usr/bin:/bin")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("AI_DLC_BOOTSTRAP_HOME", raising=False)
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr("ai_dlc.provision.platform.system", lambda: "Darwin")
    monkeypatch.setattr("ai_dlc.provision.platform.machine", lambda: "arm64")

    machine_apply(profile, home=home)

    assert (home / ".local/share/ai-dlc/workstation").is_dir()
