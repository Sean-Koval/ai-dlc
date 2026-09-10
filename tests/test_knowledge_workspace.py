"""Workspace upgrades add navigation, never replace private authored notes."""

import pytest

from ai_dlc.vault_link import link_vault


def api():
    from ai_dlc.knowledge_workspace import setup_workspace

    return setup_workspace


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "docs/index.md").write_text("# Docs\n")
    vault = tmp_path / "vault"
    vault.mkdir()
    return root, vault


def test_preview_is_read_only_and_apply_keeps_repository_bodies_out(workspace):
    root, vault = workspace
    (root / "docs/private.md").write_text("Canonical source body must stay in Git.")
    preview = api()(root, vault=vault, name="demo", bases=True)
    assert list(vault.iterdir()) == []
    assert any(f["path"] == "Projects/demo-workspace.md" for f in preview["files"])
    result = api()(root, vault=vault, name="demo", bases=True, apply=True)
    assert result["status"] == "applied"
    note = (vault / "Projects/demo-workspace.md").read_text()
    assert "note_kind: project" in note
    assert "[[Projects/demo]]" in note
    assert not any(
        "Canonical source body must stay in Git." in p.read_text()
        for p in vault.rglob("*")
        if p.is_file()
    )
    assert (vault / "AI-DLC/Views/projects.base").exists()


def test_legacy_portal_and_appended_workspace_annotations_survive(workspace):
    root, vault = workspace
    link_vault(root, vault=vault, name="demo")
    portal = vault / "Projects/demo.md"
    original = portal.read_bytes() + b"\nMy private observation.\n"
    portal.write_bytes(original)
    api()(root, vault=vault, name="demo", apply=True)
    assert portal.read_bytes() == original
    note = vault / "Projects/demo-workspace.md"
    body = note.read_bytes() + b"\nPersonal question.\n"
    note.write_bytes(body)
    api()(root, vault=vault, name="demo", apply=True)
    assert note.read_bytes() == body


def test_conflicting_template_refuses_before_creating_portal(workspace):
    root, vault = workspace
    conflict = vault / "AI-DLC/Templates/learning.md"
    conflict.parent.mkdir(parents=True)
    conflict.write_text("An authored template")
    with pytest.raises(ValueError):
        api()(root, vault=vault, name="demo", apply=True)
    assert not (vault / "Projects").exists()
    assert conflict.read_text() == "An authored template"


def test_missing_repository_and_symlink_parent_refuse(workspace):
    root, vault = workspace
    with pytest.raises(ValueError, match="repository"):
        api()(root / "missing", vault=vault, name="demo")
    outside = root / "outside"
    outside.mkdir()
    (vault / "AI-DLC").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        api()(root, vault=vault, name="demo", apply=True)
    assert list(outside.iterdir()) == []


def test_concurrent_destination_appearance_is_preserved(workspace, monkeypatch):
    root, vault = workspace
    from ai_dlc import document_files

    original = document_files.create_document

    def racing(path, body):
        if path.name == "demo-workspace.md":
            path.write_text("Concurrent authored note")
        return original(path, body)

    monkeypatch.setattr(document_files, "create_document", racing)
    with pytest.raises(ValueError, match="retained"):
        api()(root, vault=vault, name="demo", apply=True)
    assert (vault / "Projects/demo-workspace.md").read_text() == "Concurrent authored note"


def test_workspace_cli_preview_and_mcp_are_available(workspace):
    import asyncio
    import json

    from typer.testing import CliRunner

    from ai_dlc.cli import app
    from ai_dlc.mcp_server import make_server

    root, vault = workspace
    result = CliRunner().invoke(
        app,
        ["project", "workspace-init", "--root", str(root), "--vault", str(vault), "--name", "demo"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["status"] == "preview"
    assert list(vault.iterdir()) == []
    assert "project_workspace_preview" in {
        t.name for t in asyncio.run(make_server(root).list_tools())
    }


def test_partial_creation_failure_reports_attempted_path(workspace, monkeypatch):
    import ai_dlc.document_files as files

    root, vault = workspace

    def fail_sync(fd):
        raise OSError("simulated fsync failure")

    monkeypatch.setattr(files.os, "fsync", fail_sync)
    with pytest.raises(ValueError, match="simulated fsync failure") as error:
        api()(root, vault=vault, name="demo", apply=True)
    assert "Projects/demo.md" in str(error.value)
    assert (vault / "Projects/demo.md").exists()
