from typer.testing import CliRunner


def test_command_help_exposes_public_groups():
    from ai_dlc.cli import app

    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in ["project", "work", "setup", "profile", "knowledge", "mcp", "scaffold"]:
        assert name in result.stdout


def test_scaffold_matches_legacy_assets_and_preserves_conflicts(tmp_path, monkeypatch):
    from ai_dlc.cli import app
    from ai_dlc.files import assets

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["scaffold", "--provider", "gemini"])
    assert result.exit_code == 0, result.output
    source = assets("legacy") / "gemini"
    files = [p for p in source.rglob("*") if p.is_file()]
    assert files
    for file in files:
        assert (tmp_path / ".gemini" / file.relative_to(source)).read_bytes() == file.read_bytes()
    modified = tmp_path / ".gemini" / files[0].relative_to(source)
    modified.write_text("custom")
    result = runner.invoke(app, ["scaffold", "--provider", "gemini"])
    assert result.exit_code != 0
    assert modified.read_text() == "custom"


def test_provider_conformance_failure_is_nonzero(tmp_path, monkeypatch):
    import ai_dlc.sandbox
    from ai_dlc.cli import app

    manifest = tmp_path / "test.toml"
    manifest.write_text("")
    monkeypatch.setattr(ai_dlc.sandbox, "test_provider", lambda *args, **kwargs: {"passed": False})
    result = CliRunner().invoke(app, ["provider", "test", "linear", str(manifest)])
    assert result.exit_code == 1


def test_personal_agent_render_is_explicit_and_project_independent(tmp_path, monkeypatch):
    import json

    from ai_dlc.cli import app

    personal = tmp_path / "personal.toml"
    personal.write_text('schema=4\n[[agents.servers]]\nid="notes"\ncommand="notes-mcp"\n')
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    runner = CliRunner()
    arguments = ["agents", "render", "--personal", str(personal), "--home", str(home)]
    preview = runner.invoke(app, [*arguments, "--check"])
    assert preview.exit_code == 1, preview.output
    assert not list(home.iterdir())
    applied = runner.invoke(app, [*arguments, "--apply"])
    assert applied.exit_code == 0, applied.output
    assert json.loads((home / ".claude.json").read_text())["mcpServers"]["notes"] == {
        "command": "notes-mcp"
    }
    assert runner.invoke(app, [*arguments, "--check"]).exit_code == 0
    assert not list(project.iterdir())


def test_setup_commands_accept_documented_profile_option(tmp_path, monkeypatch):
    import ai_dlc.provision
    from ai_dlc.cli import app

    profile = tmp_path / "profile.toml"
    profile.write_text("schema=4\n")
    monkeypatch.setattr(
        ai_dlc.provision,
        "machine_plan",
        lambda profile, headless=False, home=None: {"profile": str(profile)},
    )
    monkeypatch.setattr(
        ai_dlc.provision,
        "machine_apply",
        lambda profile, headless=False, home=None: {"profile": str(profile)},
    )
    runner = CliRunner()
    for action in ["plan", "apply"]:
        result = runner.invoke(app, ["setup", action, "--profile", str(profile)])
        assert result.exit_code == 0, result.output
