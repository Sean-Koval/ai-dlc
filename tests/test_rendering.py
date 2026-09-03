import pytest


def test_render_preserves_authored_text_and_detects_stale_generated_section(tmp_path):
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[checks]\nrequired=["test"]\n[checks.commands]\ntest="pytest"\n[roles]\ntracker="linear"\n'
    )
    (tmp_path / "AGENTS.md").write_text("# My instructions\nKeep this.\n")
    render_agents(tmp_path, apply=True)
    first = (tmp_path / "AGENTS.md").read_bytes()
    render_agents(tmp_path, apply=True)
    assert (tmp_path / "AGENTS.md").read_bytes() == first
    assert first.startswith(b"# My instructions\nKeep this.\n")
    assert render_agents(tmp_path)["clean"] is True
    config = tmp_path / "ai-dlc.toml"
    config.write_text(config.read_text().replace("pytest", "pytest -q"))
    assert render_agents(tmp_path)["clean"] is False


def test_edits_inside_managed_section_are_not_overwritten(tmp_path):
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    render_agents(tmp_path, apply=True)
    agents = tmp_path / "AGENTS.md"
    agents.write_text(agents.read_text().replace("Shared project guidance", "User changed title"))
    before = agents.read_bytes()
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    assert agents.read_bytes() == before


def test_mcp_conflicting_server_preserved(tmp_path):
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[[agents.servers]]\nid="docs"\ncommand="server"\nargs=["run"]\n'
    )
    (tmp_path / ".mcp.json").write_text('{"mcpServers":{"docs":{"command":"mine"}}}')
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    assert "mine" in (tmp_path / ".mcp.json").read_text()


def test_unsupported_required_hook_fails_readiness():
    from ai_dlc.agents import hook_readiness

    result = hook_readiness("codex", "0.151.0", "local", ["request-approval"])
    assert result["ready"] is False
    assert "request-approval" in result["unavailable"]


def test_skills_selection_partial_ownership_and_removal(tmp_path):
    import json

    from ai_dlc.agents import render_agents
    from ai_dlc.files import assets

    config = tmp_path / "ai-dlc.toml"
    config.write_text('schema=4\n[agents]\nskills=["day-start"]\n')
    render_agents(tmp_path, apply=True)
    for directory in [".agents", ".claude"]:
        assert (tmp_path / directory / "skills/day-start/SKILL.md").read_bytes() == (
            assets("agents") / "skills/day-start/SKILL.md"
        ).read_bytes()
    config.write_text("schema=4\n[agents]\nskills=[]\n")
    render_agents(tmp_path, apply=True, client="codex")
    assert not (tmp_path / ".agents/skills/day-start/SKILL.md").exists()
    assert (tmp_path / ".claude/skills/day-start/SKILL.md").exists()
    manifest = json.loads((tmp_path / ".ai-dlc/agent-ownership.json").read_text())
    assert ".claude/skills/day-start/SKILL.md" in manifest["files"]
    render_agents(tmp_path, apply=True, client="claude-code")
    assert not (tmp_path / ".claude/skills/day-start/SKILL.md").exists()


def test_skill_conflict_has_no_partial_writes(tmp_path):
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    skill = tmp_path / ".agents/skills/day-start/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("authored")
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    assert not (tmp_path / "AGENTS.md").exists()
    assert skill.read_text() == "authored"


def test_required_hooks_preserve_unmanaged_and_target_independent(tmp_path):
    import json

    from ai_dlc.agents import render_agents, target_hooks
    from ai_dlc.config import load_project

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents.clients.codex]\nversion="0.151.0"\nrequired_hooks=["bound-push","session-context","stop-reminder"]\n'
    )
    path = tmp_path / ".codex/hooks.json"
    path.parent.mkdir()
    path.write_text(
        '{"custom":true,"hooks":{"Stop":[{"hooks":[{"type":"command","command":"user-hook"}]}]}}'
    )
    render_agents(tmp_path, apply=True)
    content = path.read_text()
    assert "git rev-parse --show-toplevel" in content
    assert "user-hook" in content and json.loads(content)["custom"]
    assert render_agents(tmp_path, target="ci")["clean"]
    assert not target_hooks(load_project(tmp_path), "ci")["ready"]


def test_unsupported_required_hooks_fail_before_writes(tmp_path):
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents.clients.codex]\nversion="0.151.0"\nrequired_hooks=["request-approval"]\n'
    )
    with pytest.raises(ValueError, match="hook"):
        render_agents(tmp_path, apply=True)
    assert not (tmp_path / "AGENTS.md").exists()


def test_digest_mismatch_prevents_all_writes(tmp_path, monkeypatch):
    import shutil

    from ai_dlc import agents
    from ai_dlc.files import assets

    package = tmp_path / "package"
    shutil.copytree(assets("agents"), package)
    (package / "skills/day-start/SKILL.md").write_text("tampered")
    monkeypatch.setattr(agents, "assets", lambda name: package)
    project = tmp_path / "project"
    project.mkdir()
    (project / "ai-dlc.toml").write_text("schema=4\n")
    with pytest.raises(ValueError, match="digest"):
        agents.render_agents(project, apply=True)
    assert not (project / "AGENTS.md").exists()


def test_unchanged_owned_skill_updates_and_edited_removal_conflicts(tmp_path, monkeypatch):
    import hashlib
    import json
    import shutil

    from ai_dlc import agents
    from ai_dlc.files import assets

    package = tmp_path / "package"
    shutil.copytree(assets("agents"), package)
    monkeypatch.setattr(agents, "assets", lambda name: package)
    project = tmp_path / "project"
    project.mkdir()
    config = project / "ai-dlc.toml"
    config.write_text('schema=4\n[agents]\nskills=["day-start"]\n')
    agents.render_agents(project, apply=True)
    source = package / "skills/day-start/SKILL.md"
    source.write_text(source.read_text() + "\nNew package guidance\n")
    lock_path = package / "skills.lock.json"
    lock = json.loads(lock_path.read_text())
    lock["skills"]["day-start"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    lock_path.write_text(json.dumps(lock))
    agents.render_agents(project, apply=True)
    destination = project / ".agents/skills/day-start/SKILL.md"
    assert destination.read_bytes() == source.read_bytes()
    destination.write_text("user edit")
    config.write_text("schema=4\n[agents]\nskills=[]\n")
    with pytest.raises(ValueError, match="conflict"):
        agents.render_agents(project, apply=True)
    assert destination.read_text() == "user edit"
    assert (project / ".claude/skills/day-start/SKILL.md").exists()


def test_codex_partial_keeps_claude_mcp_ownership_for_later_removal(tmp_path):
    import json

    from ai_dlc.agents import render_agents

    config = tmp_path / "ai-dlc.toml"
    config.write_text('schema=4\n[[agents.servers]]\nid="docs"\ncommand="server"\n')
    render_agents(tmp_path, apply=True)
    config.write_text("schema=4\n")
    render_agents(tmp_path, apply=True, client="codex")
    assert "docs" in json.loads((tmp_path / ".ai-dlc/agent-ownership.json").read_text())["mcp"]
    render_agents(tmp_path, apply=True, client="claude-code")
    assert not json.loads((tmp_path / ".mcp.json").read_text())["mcpServers"]


def test_hook_edit_conflict_and_removal_preserve_user_hook(tmp_path):
    import json

    from ai_dlc.agents import render_agents

    config = tmp_path / "ai-dlc.toml"
    config.write_text(
        'schema=4\n[agents.clients.claude-code]\nversion="2.1.0"\nrequired_hooks=["stop-reminder"]\n'
    )
    render_agents(tmp_path, apply=True)
    path = tmp_path / ".claude/settings.json"
    original = path.read_text()
    path.write_text(original.replace("ai-dlc hook stop", "edited hook"))
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    document = json.loads(original)
    user_hook = {"hooks": [{"type": "command", "command": "user-hook"}]}
    document["hooks"]["Stop"].append(user_hook)
    path.write_text(json.dumps(document))
    config.write_text("schema=4\n")
    render_agents(tmp_path, apply=True)
    assert json.loads(path.read_text())["hooks"]["Stop"] == [user_hook]


def test_unknown_client_version_has_no_claimed_hook_support():
    from ai_dlc.agents import hook_readiness

    result = hook_readiness("codex", "999.0.0", "local", ["bound-push"])
    assert not result["ready"]
    assert result["supported"] == []
    assert "fixture" in result["coverage"]
