import json
import tomllib
from pathlib import Path

import pytest


def personal(*servers):
    return {"agents": {"servers": list(servers)}}


def test_preview_then_apply_is_home_scoped_and_idempotent(tmp_path, monkeypatch):
    from ai_dlc.user_agents import render_user_agents

    home = tmp_path / "user"
    home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("ACCESS_TOKEN", "must-never-be-written")
    config = personal(
        {"id": "notes", "command": "notes-mcp", "args": ["serve"], "env": ["ACCESS_TOKEN"]}
    )
    result = render_user_agents(config, home)
    assert result["changed"] and result["applied"] is False
    assert not list(home.iterdir())
    assert render_user_agents(config, home, apply=True)["applied"] is True
    assert not list(project.iterdir())
    claude = json.loads((home / ".claude.json").read_text())
    codex = tomllib.loads((home / ".codex/config.toml").read_text())
    assert claude["mcpServers"]["notes"]["env"] == {"ACCESS_TOKEN": "${ACCESS_TOKEN}"}
    assert codex["mcp_servers"]["notes"]["env_vars"] == ["ACCESS_TOKEN"]
    assert all("must-never-be-written" not in p.read_text() for p in home.rglob("*") if p.is_file())
    assert render_user_agents(config, home)["clean"] is True


def test_empty_personal_config_does_not_invent_servers_or_write(tmp_path):
    from ai_dlc.user_agents import render_user_agents

    assert render_user_agents({}, tmp_path, apply=True)["clean"] is True
    assert not list(tmp_path.iterdir())


def test_unrelated_authored_settings_and_servers_survive_removal(tmp_path):
    from ai_dlc.user_agents import render_user_agents

    authored = {
        "theme": "dark",
        "projects": {"/project": {"hasTrustDialogAccepted": True}},
        "mcpServers": {"manual": {"command": "manual"}},
    }
    (tmp_path / ".claude.json").write_text(json.dumps(authored))
    (tmp_path / ".codex").mkdir()
    original = '# authored comment\nmodel = "chosen"\n[mcp_servers.manual]\ncommand = "manual"\n'
    (tmp_path / ".codex/config.toml").write_text(original)
    config = personal({"id": "managed", "command": "managed"})
    render_user_agents(config, tmp_path, apply=True)
    render_user_agents({}, tmp_path, apply=True)
    assert json.loads((tmp_path / ".claude.json").read_text()) == authored
    assert (tmp_path / ".codex/config.toml").read_text() == original


@pytest.mark.parametrize("client", ["claude-code", "codex"])
def test_unowned_server_collision_does_not_overwrite(tmp_path, client):
    from ai_dlc.user_agents import render_user_agents

    if client == "claude-code":
        path = tmp_path / ".claude.json"
        original = json.dumps({"mcpServers": {"same": {"command": "manual"}}})
    else:
        (tmp_path / ".codex").mkdir()
        path = tmp_path / ".codex/config.toml"
        original = '[mcp_servers.same]\ncommand="manual"\n'
    path.write_text(original)
    with pytest.raises(ValueError, match="conflict"):
        render_user_agents(
            personal({"id": "same", "command": "managed"}), tmp_path, apply=True, client=client
        )
    assert path.read_text() == original
    assert not (tmp_path / ".local/state/ai-dlc/user-agent-ownership.json").exists()


@pytest.mark.parametrize("client", ["claude-code", "codex"])
def test_owned_server_drift_blocks_all_writes(tmp_path, client):
    from ai_dlc.user_agents import render_user_agents

    config = personal({"id": "owned", "command": "original"})
    render_user_agents(config, tmp_path, apply=True)
    path = tmp_path / (".claude.json" if client == "claude-code" else ".codex/config.toml")
    path.write_text(path.read_text().replace("original", "authored-edit"))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="conflict"):
        render_user_agents(personal({"id": "owned", "command": "new"}), tmp_path, apply=True)
    assert all(p.read_bytes() == body for p, body in before.items())


def test_client_selection_preserves_other_client_ownership(tmp_path):
    from ai_dlc.user_agents import render_user_agents

    config = personal({"id": "owned", "command": "original"})
    render_user_agents(config, tmp_path, apply=True)
    claude = (tmp_path / ".claude.json").read_bytes()
    render_user_agents({}, tmp_path, apply=True, client="codex")
    assert (tmp_path / ".claude.json").read_bytes() == claude
    manifest = json.loads((tmp_path / ".local/state/ai-dlc/user-agent-ownership.json").read_text())
    assert "owned" in manifest["clients"]["claude-code"]["servers"]


def test_http_credentials_are_environment_references(tmp_path):
    from ai_dlc.user_agents import render_user_agents

    config = personal(
        {
            "id": "remote",
            "url": "https://example.test/mcp",
            "bearer_token_env_var": "MCP_TOKEN",
            "env_http_headers": {"X-Workspace": "WORKSPACE_ID"},
        }
    )
    render_user_agents(config, tmp_path, apply=True)
    claude = json.loads((tmp_path / ".claude.json").read_text())["mcpServers"]["remote"]
    assert claude["type"] == "http"
    assert claude["headers"] == {
        "Authorization": "Bearer ${MCP_TOKEN}",
        "X-Workspace": "${WORKSPACE_ID}",
    }
    codex = tomllib.loads((tmp_path / ".codex/config.toml").read_text())["mcp_servers"]["remote"]
    assert codex["bearer_token_env_var"] == "MCP_TOKEN"
    with pytest.raises(ValueError, match="environment|unsupported"):
        render_user_agents(
            personal({"id": "bad", "command": "bad", "env": {"TOKEN": "secret"}}), tmp_path
        )


def test_empty_profile_leaves_unowned_configuration_bytes_unchanged(tmp_path):
    from ai_dlc.user_agents import render_user_agents

    claude = tmp_path / ".claude.json"
    claude.write_text('{"theme":"dark","mcpServers":{}}')
    codex = tmp_path / ".codex/config.toml"
    codex.parent.mkdir()
    codex.write_text('# Keep formatting\nmodel="chosen"')
    before = {path: path.read_bytes() for path in [claude, codex]}
    assert render_user_agents({}, tmp_path, apply=True)["clean"] is True
    assert {path: path.read_bytes() for path in before} == before
    assert not (tmp_path / ".local").exists()


def test_empty_profile_ignores_invalid_unowned_codex_toml(tmp_path):
    from ai_dlc.user_agents import render_user_agents

    codex = tmp_path / ".codex/config.toml"
    codex.parent.mkdir()
    codex.write_text("this is not = valid = toml")
    assert render_user_agents({}, tmp_path, apply=True)["clean"] is True
    assert codex.read_text() == "this is not = valid = toml"


def test_lost_ownership_cannot_replace_existing_codex_section(tmp_path):
    from ai_dlc.user_agents import render_user_agents

    render_user_agents(personal({"id": "old", "command": "old"}), tmp_path, apply=True)
    (tmp_path / ".local/state/ai-dlc/user-agent-ownership.json").unlink()
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="conflict"):
        render_user_agents(personal({"id": "new", "command": "new"}), tmp_path, apply=True)
    assert {p: p.read_bytes() for p in before} == before


def test_empty_profile_rejects_orphaned_codex_managed_section(tmp_path):
    from ai_dlc.user_agents import render_user_agents

    render_user_agents(personal({"id": "old", "command": "old"}), tmp_path, apply=True)
    (tmp_path / ".local/state/ai-dlc/user-agent-ownership.json").unlink()
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="conflict"):
        render_user_agents({}, tmp_path, apply=True)
    assert {p: p.read_bytes() for p in before} == before


def test_codex_removal_preserves_original_missing_final_newline(tmp_path):
    from ai_dlc.user_agents import render_user_agents

    path = tmp_path / ".codex/config.toml"
    path.parent.mkdir()
    original = '# authored\nmodel="chosen"'
    path.write_text(original)
    render_user_agents(personal({"id": "owned", "command": "server"}), tmp_path, apply=True)
    render_user_agents({}, tmp_path, apply=True)
    assert path.read_text() == original


@pytest.mark.parametrize(
    "definition",
    [
        {"command": 123, "url": "https://example.test/mcp"},
        {"command": "server", "headers": {"Authorization": "literal-secret"}},
        {"url": "https://example.test/mcp", "args": ["ignored"]},
    ],
)
def test_invalid_or_unsupported_server_fields_fail_before_writes(tmp_path, definition):
    from ai_dlc.user_agents import render_user_agents

    with pytest.raises(ValueError):
        render_user_agents(personal({"id": "invalid", **definition}), tmp_path, apply=True)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("failed_write", [1, 2, 3])
def test_failed_apply_rolls_back_every_completed_write(tmp_path, monkeypatch, failed_write):
    import ai_dlc.user_agents
    from ai_dlc.files import atomic_write as real_atomic_write
    from ai_dlc.user_agents import render_user_agents

    render_user_agents(personal({"id": "owned", "command": "old"}), tmp_path, apply=True)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    calls = 0

    def fail_once(path, text):
        nonlocal calls
        calls += 1
        if calls == failed_write:
            raise OSError("injected write failure")
        real_atomic_write(path, text)

    monkeypatch.setattr(ai_dlc.user_agents, "atomic_write", fail_once)
    with pytest.raises(OSError, match="injected"):
        render_user_agents(personal({"id": "owned", "command": "new"}), tmp_path, apply=True)
    assert {p: p.read_bytes() for p in before} == before
    monkeypatch.setattr(ai_dlc.user_agents, "atomic_write", real_atomic_write)
    render_user_agents(personal({"id": "owned", "command": "new"}), tmp_path, apply=True)
    assert "new" in (tmp_path / ".claude.json").read_text()


def test_interrupted_apply_restores_bytes_and_permissions(tmp_path, monkeypatch):
    import ai_dlc.user_agents
    from ai_dlc.files import atomic_write as real_atomic_write
    from ai_dlc.user_agents import render_user_agents

    render_user_agents(personal({"id": "owned", "command": "old"}), tmp_path, apply=True)
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    for path in files:
        path.chmod(0o600)
    before = {path: (path.read_bytes(), path.stat().st_mode & 0o777) for path in files}
    calls = 0

    def interrupt_second_write(path, text):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        real_atomic_write(path, text)

    monkeypatch.setattr(ai_dlc.user_agents, "atomic_write", interrupt_second_write)
    with pytest.raises(KeyboardInterrupt):
        render_user_agents(personal({"id": "owned", "command": "new"}), tmp_path, apply=True)
    assert {path: (path.read_bytes(), path.stat().st_mode & 0o777) for path in files} == before


@pytest.mark.parametrize("failed_removal", [1, 2, 3])
def test_failed_apply_rolls_back_every_completed_removal(tmp_path, monkeypatch, failed_removal):
    import ai_dlc.user_agents
    from ai_dlc.user_agents import render_user_agents

    render_user_agents(personal({"id": "owned", "command": "old"}), tmp_path, apply=True)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    for path in before:
        path.chmod(0o600)
    calls = 0

    def fail_once(path):
        nonlocal calls
        calls += 1
        if calls == failed_removal:
            raise OSError("injected removal failure")
        path.unlink()

    monkeypatch.setattr(ai_dlc.user_agents, "_unlink", fail_once)
    with pytest.raises(OSError, match="injected"):
        render_user_agents({}, tmp_path, apply=True)
    assert {p: p.read_bytes() for p in before} == before
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in before)
    monkeypatch.setattr(ai_dlc.user_agents, "_unlink", lambda path: Path.unlink(path))
    render_user_agents({}, tmp_path, apply=True)
    assert not any(p.is_file() for p in tmp_path.rglob("*"))
