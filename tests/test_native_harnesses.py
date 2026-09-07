"""Native output contracts exercised through the real project renderer."""

import json

import pytest

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
    _native_project(tmp_path, extra='url="https://other.example.com/mcp"\n')
    before = _snapshot(tmp_path)
    with pytest.raises(ValueError, match="transport"):
        render_agents(tmp_path, apply=True)
    assert before == _snapshot(tmp_path)


def test_antigravity_required_hooks_remain_unqualified(tmp_path):
    _native_project(tmp_path, extra='[agents.clients.antigravity]\nrequired_hooks=["bound-push"]\n')
    before = _snapshot(tmp_path)
    with pytest.raises(ValueError, match="unsupported required hooks"):
        render_agents(tmp_path, apply=True)
    assert before == _snapshot(tmp_path)


def test_native_rule_custom_provider_links_resolve_to_project_files(tmp_path):
    """A provider can put guidance anywhere permitted in the project, not just .ai-dlc."""
    import hashlib
    import re

    _native_project(tmp_path)
    guide = tmp_path / "providers/custom.md"
    guide.parent.mkdir()
    guide.write_text("Authored specification instructions.\n")
    manifest = tmp_path / "component.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "components": [
                    {
                        "id": "custom",
                        "roles": ["specs"],
                        "modules": [],
                        "guidance": ["providers/custom.md"],
                        "required_config": [],
                    }
                ],
            }
        )
    )
    project = tmp_path / "ai-dlc.toml"
    text = project.read_text().replace("[roles]\n", '[roles]\nspecs="custom"\n')
    text += '[providers.custom]\ncomponent_manifest="component.json"\n'
    text += f'component_manifest_sha256="{hashlib.sha256(manifest.read_bytes()).hexdigest()}"\n'
    project.write_text(text)
    render_agents(tmp_path, apply=True)
    rule = tmp_path / ".agents/rules/ai-dlc.md"
    targets = re.findall(r"\]\(<([^>]+)>\)", rule.read_text())
    assert targets
    assert all((rule.parent / target).is_file() for target in targets)
    assert guide.resolve() in [(rule.parent / target).resolve() for target in targets]


@pytest.mark.parametrize(
    "missing", [".agents/skills/day-start/SKILL.md", ".agents/mcp_config.json"]
)
def test_native_readiness_refuses_missing_selected_assets(tmp_path, missing):
    """The delivered row must not remain ready when a selected native asset disappears."""
    from ai_dlc.config import load_project
    from ai_dlc.readiness import inspect_readiness

    _native_project(tmp_path)
    render_agents(tmp_path, apply=True)
    (tmp_path / missing).unlink()
    result = inspect_readiness(tmp_path, load_project(tmp_path), environ={}, probe=lambda _: {})
    assert not result["ready"]
    assert any(
        row["component"] == "antigravity"
        and row["dimension"] == "guidance"
        and row["status"] == "missing"
        for row in result["checks"]
    )


def test_native_rule_preserves_client_authored_metadata_outside_owned_guidance(tmp_path):
    """Native rule activation metadata must survive regeneration of owned guidance."""
    _native_project(tmp_path)
    render_agents(tmp_path, apply=True)
    rule = tmp_path / ".agents/rules/ai-dlc.md"
    metadata = "---\ndescription: My project activation settings\n---\n"
    rule.write_text(metadata + rule.read_text())
    render_agents(tmp_path, apply=True)
    assert rule.read_text().startswith(metadata)
    assert render_agents(tmp_path)["clean"]


@pytest.mark.parametrize("edited", [False, True])
def test_native_legacy_whole_file_upgrade_preserves_ownership_boundary(tmp_path, edited):
    """Only the intact old owned format may upgrade to independently editable metadata."""
    import hashlib
    from pathlib import Path

    _native_project(tmp_path)
    render_agents(tmp_path, apply=True)
    rule = tmp_path / ".agents/rules/ai-dlc.md"
    legacy = (Path(__file__).parent / "fixtures/native/legacy-antigravity-rule.md").read_bytes()
    rule.write_bytes(legacy)
    manifest = tmp_path / ".ai-dlc/agent-ownership.json"
    ownership = json.loads(manifest.read_text())
    ownership["files"][".agents/rules/ai-dlc.md"] = hashlib.sha256(legacy).hexdigest()
    manifest.write_text(json.dumps(ownership))
    if edited:
        rule.write_bytes(legacy + b"\nAuthored local changes.\n")
        before = _snapshot(tmp_path)
        with pytest.raises(ValueError, match="conflict"):
            render_agents(tmp_path, apply=True)
        assert before == _snapshot(tmp_path)
    else:
        render_agents(tmp_path, apply=True)
        assert rule.read_text().count("<!-- ai-dlc:begin ") == 1
        assert "Read ai-dlc.toml" in rule.read_text()
        current = json.loads(manifest.read_text())
        assert (
            current["files"][".agents/rules/ai-dlc.md"]
            == hashlib.sha256(rule.read_bytes()).hexdigest()
        )
        assert render_agents(tmp_path)["clean"]
