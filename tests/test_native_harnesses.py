"""Native output contracts exercised through the real project renderer."""

import json

from ai_dlc.agents import render_agents


def test_claude_remote_definition_upgrades_owned_url_only_entry(tmp_path):
    """Missing HTTP type must be repaired without losing unrelated native servers."""
    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["claude-code"]\n'
        '[[agents.servers]]\nid="tracker"\nurl="https://example.com/mcp"\n'
    )
    old = {"tracker": {"url": "https://example.com/mcp"}}
    (tmp_path / ".mcp.json").write_text(
        json.dumps(
            {"mcpServers": {**old, "authored": {"command": "mine"}}, "authoredSetting": True}
        )
    )
    (tmp_path / ".ai-dlc").mkdir()
    (tmp_path / ".ai-dlc/agent-ownership.json").write_text(json.dumps({"schema": 2, "mcp": old}))
    render_agents(tmp_path, apply=True)
    result = json.loads((tmp_path / ".mcp.json").read_text())
    assert result == {
        "mcpServers": {
            "tracker": {"type": "http", "url": "https://example.com/mcp"},
            "authored": {"command": "mine"},
        },
        "authoredSetting": True,
    }
    assert render_agents(tmp_path)["clean"] is True


def _native_project(root, clients='["antigravity"]', extra=""):
    (root / "ai-dlc.toml").write_text(
        f'schema=4\n[roles]\nagent-client={clients}\n[agents]\nskills=["day-start"]\n'
        '[[agents.servers]]\nid="remote"\nurl="https://example.com/mcp"\n'
        '[[agents.servers]]\nid="local"\ncommand="ai-dlc"\nargs=["mcp", "serve"]\n' + extra
    )


def _snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_antigravity_emits_native_paths_and_transports(tmp_path):
    """Selecting Antigravity must produce usable native files, not Claude aliases."""
    _native_project(tmp_path)
    render_agents(tmp_path, apply=True)
    mcp = json.loads((tmp_path / ".agents/mcp_config.json").read_text())
    assert mcp == {
        "mcpServers": {
            "remote": {"serverUrl": "https://example.com/mcp"},
            "local": {"command": "ai-dlc", "args": ["mcp", "serve"]},
        }
    }
    assert (tmp_path / ".agents/skills/day-start/SKILL.md").is_file()
    rule = (tmp_path / ".agents/rules/ai-dlc.md").read_text()
    assert "Read ai-dlc.toml" in rule
    assert "ai-dlc work finish" in rule
    assert not (tmp_path / ".mcp.json").exists()
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / ".codex").exists()
    before = _snapshot(tmp_path)
    assert render_agents(tmp_path, apply=True)["clean"] is True
    assert before == _snapshot(tmp_path)


def test_codex_antigravity_share_one_owned_skill_set(tmp_path):
    """Shared client storage must not cause duplicate deletion or ownership drift."""
    _native_project(tmp_path, '["codex", "antigravity"]')
    render_agents(tmp_path, apply=True)
    owned = json.loads((tmp_path / ".ai-dlc/agent-ownership.json").read_text())
    assert ".agents/skills/day-start/SKILL.md" in owned["files"]
    assert render_agents(tmp_path, apply=True)["clean"] is True
    before = (tmp_path / ".agents/skills/day-start/SKILL.md").read_bytes()
    assert render_agents(tmp_path, apply=True, client="antigravity")["clean"] is True
    assert (tmp_path / ".agents/skills/day-start/SKILL.md").read_bytes() == before


def test_antigravity_preserves_authored_servers_and_rejects_edited_owned_entry(tmp_path):
    """Native ownership cannot overwrite an edited server or unrelated account."""
    import pytest

    _native_project(tmp_path)
    mcp = tmp_path / ".agents/mcp_config.json"
    mcp.parent.mkdir()
    mcp.write_text(json.dumps({"mcpServers": {"mine": {"command": "authored"}}}))
    render_agents(tmp_path, apply=True)
    data = json.loads(mcp.read_text())
    assert data["mcpServers"]["mine"] == {"command": "authored"}
    data["mcpServers"]["remote"]["serverUrl"] = "https://other-account.example.com/mcp"
    mcp.write_text(json.dumps(data))
    before = _snapshot(tmp_path)
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    assert before == _snapshot(tmp_path)


def test_antigravity_authored_rule_conflict_refuses_all_writes(tmp_path):
    """A rule filename is not proof AI-DLC owns its authored contents."""
    import pytest

    _native_project(tmp_path)
    rule = tmp_path / ".agents/rules/ai-dlc.md"
    rule.parent.mkdir(parents=True)
    rule.write_text("Authored rules for my work repository.\n")
    before = _snapshot(tmp_path)
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    assert before == _snapshot(tmp_path)


def test_antigravity_refuses_unqualified_env_interpolation(tmp_path):
    """Never emit literal credential placeholders the native client may not expand."""
    import pytest

    _native_project(tmp_path, extra='env=["SERVICE_TOKEN"]\n')
    before = _snapshot(tmp_path)
    with pytest.raises(ValueError, match="environment.*Antigravity|Antigravity.*environment"):
        render_agents(tmp_path, apply=True)
    assert before == _snapshot(tmp_path)


def test_antigravity_readiness_distinguishes_guidance_from_live_client(tmp_path):
    """Delivered files alone must not become a native recognition/login claim."""
    from ai_dlc.config import load_project
    from ai_dlc.readiness import inspect_readiness

    _native_project(tmp_path)
    render_agents(tmp_path, apply=True)
    result = inspect_readiness(tmp_path, load_project(tmp_path), environ={}, probe=lambda _: {})
    rows = [row for row in result["checks"] if row["component"] == "antigravity"]
    assert any(row["dimension"] == "guidance" and row["status"] == "ready" for row in rows)
    assert any(
        row["dimension"] == "client-recognition" and row["status"] == "unverified" for row in rows
    )
    (tmp_path / ".agents/rules/ai-dlc.md").write_text("edited")
    result = inspect_readiness(tmp_path, load_project(tmp_path), environ={}, probe=lambda _: {})
    assert any(
        row["component"] == "antigravity"
        and row["dimension"] == "guidance"
        and row["status"] == "missing"
        for row in result["checks"]
    )


def test_antigravity_refuses_ambiguous_transport_without_writes(tmp_path):
    """A server carrying command and URL must not silently select one credential path."""
    import pytest

    _native_project(tmp_path, extra='url="https://other.example.com/mcp"\n')
    before = _snapshot(tmp_path)
    with pytest.raises(ValueError, match="transport"):
        render_agents(tmp_path, apply=True)
    assert before == _snapshot(tmp_path)


def test_antigravity_required_hooks_remain_unqualified(tmp_path):
    import pytest

    _native_project(tmp_path, extra='[agents.clients.antigravity]\nrequired_hooks=["bound-push"]\n')
    before = _snapshot(tmp_path)
    with pytest.raises(ValueError, match="unsupported required hooks"):
        render_agents(tmp_path, apply=True)
    assert before == _snapshot(tmp_path)
