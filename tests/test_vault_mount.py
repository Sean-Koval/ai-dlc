import json
import subprocess

import pytest

from ai_dlc.documentation.knowledge import Knowledge
from ai_dlc.documentation.vault_link import link_vault


def setup(tmp_path):
    root = tmp_path / "project"
    (root / "docs").mkdir(parents=True)
    (root / "docs/index.md").write_text("Canonical unique body")
    (root / ".gitignore").write_text(".ai-dlc/local/\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    vault = tmp_path / "vault"
    vault.mkdir()
    return root, vault


def mount(root, vault, **kwargs):
    return link_vault(root, vault=vault, mode="mount", **kwargs).as_dict()


def test_mount_preview_and_repeat_preserve_notes_and_canonical_edit(tmp_path):
    root, vault = setup(tmp_path)
    (root / "openspec").mkdir()
    (vault / "Projects/project").mkdir(parents=True)
    (vault / "Projects/project/notes.md").write_text("Private")
    (vault / "Projects/project.md").write_text("Authored portal")
    preview = mount(root, vault, apply=False)
    assert preview["mounts"] == [
        {
            "source": str(root / part),
            "path": str(vault / "Projects/project" / part),
            "action": "create",
        }
        for part in ("docs", "openspec")
    ]
    binding = root / ".ai-dlc/local/vault-mounts" / preview["binding_path"].split("/")[-1]
    assert not binding.exists()
    first = mount(root, vault)
    assert first["created_link"]
    assert json.loads(binding.read_text())["project_root"] == str(root)
    assert all(item["action"] == "unchanged" for item in mount(root, vault)["mounts"])
    (vault / "Projects/project/docs/index.md").write_text("Updated canonical body")
    assert (root / "docs/index.md").read_text() == "Updated canonical body"
    assert (vault / "Projects/project.md").read_text() == "Authored portal"
    assert (vault / "Projects/project/notes.md").read_text() == "Private"
    assert not Knowledge(vault).find("Updated canonical body")
    with pytest.raises(ValueError):
        Knowledge(vault).append("Projects/project/docs/index.md", "bad", "op")


def test_missing_openspec_reported_without_creation(tmp_path):
    root, vault = setup(tmp_path)
    result = mount(root, vault)
    assert result["missing_sources"] == ["openspec"]
    assert not (root / "openspec").exists()
    assert not (vault / "Projects/project/openspec").exists()


def test_matching_unowned_mount_requires_explicit_adoption(tmp_path):
    root, vault = setup(tmp_path)
    (vault / "Projects/project").mkdir(parents=True)
    link = vault / "Projects/project/docs"
    link.symlink_to(root / "docs", target_is_directory=True)
    with pytest.raises(ValueError, match="adopt"):
        mount(root, vault)
    assert mount(root, vault, adopt=True, apply=False)["mounts"][0]["action"] == "adopt"
    mount(root, vault, adopt=True)
    assert mount(root, vault)["mounts"][0]["action"] == "unchanged"


@pytest.mark.parametrize(
    "problem", ["conflict", "nested", "source-link", "worktree", "overlap", "unignored"]
)
def test_unsafe_mount_refused_without_binding_or_output(tmp_path, problem):
    root, vault = setup(tmp_path)
    if problem == "conflict":
        (vault / "Projects/project/docs").mkdir(parents=True)
    elif problem == "nested":
        (root / "docs/private").symlink_to(vault, target_is_directory=True)
    elif problem == "source-link":
        (root / "openspec").symlink_to(root / "docs", target_is_directory=True)
    elif problem == "worktree":
        import shutil

        shutil.rmtree(root / ".git")
        (root / ".git").write_text("gitdir: /missing/worktrees/project\n")
    elif problem == "overlap":
        vault = root / "docs"
    elif problem == "unignored":
        (root / ".gitignore").write_text("")
    with pytest.raises(ValueError):
        mount(root, vault)
    assert not (root / ".ai-dlc/local").exists()


def test_mount_failure_reports_retained_binding_and_links(tmp_path, monkeypatch):
    import os

    root, vault = setup(tmp_path)
    (root / "openspec").mkdir()
    original = os.symlink

    def fail_second(source, destination, **kwargs):
        if destination == "openspec":
            raise OSError("simulated disk failure")
        return original(source, destination, **kwargs)

    monkeypatch.setattr(os, "symlink", fail_second)
    with pytest.raises(ValueError, match="retained.*docs"):
        mount(root, vault)
    assert (vault / "Projects/project/docs").is_symlink()
    monkeypatch.setattr(os, "symlink", original)
    assert mount(root, vault)["created_link"]


def test_cli_mount_preview_and_apply(tmp_path):
    from typer.testing import CliRunner

    from ai_dlc.cli import app

    root, vault = setup(tmp_path)
    args = ["project", "link-vault", "--root", str(root), "--vault", str(vault), "--mode", "mount"]
    result = CliRunner().invoke(app, args + ["--preview"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["mode"] == "mount"
    assert not (vault / "Projects").exists()
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    assert (vault / "Projects/project/docs").is_symlink()


def test_mcp_mount_preview_is_read_only(tmp_path, monkeypatch):
    import asyncio

    import ai_dlc.mcp_server as module

    root, vault = setup(tmp_path)
    (root / "ai-dlc.toml").write_text("schema=4\n")
    server = module.make_server(root)
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert "project_vault_mount_preview" in names
    result = asyncio.run(server.call_tool("project_vault_mount_preview", {"vault": str(vault)}))
    assert "missing_sources" in str(result)
    assert not (vault / "Projects").exists()
    assert not (root / ".ai-dlc/local").exists()


def test_mount_rejects_indirect_link_even_with_adoption(tmp_path):
    root, vault = setup(tmp_path)
    (vault / "Projects/project").mkdir(parents=True)
    alias = tmp_path / "alias"
    alias.symlink_to(root / "docs", target_is_directory=True)
    (vault / "Projects/project/docs").symlink_to(alias, target_is_directory=True)
    with pytest.raises(ValueError, match="conflict"):
        mount(root, vault, adopt=True)


def test_mount_bindings_read_without_following_links(tmp_path):
    import ai_dlc.documentation.vault_mount as module

    root, vault = setup(tmp_path)
    mount(root, vault)
    assert hasattr(module, "read_mount_bindings")
    bindings = module.read_mount_bindings(root)
    assert bindings[0]["project_root"] == str(root)
    assert bindings[0]["vault_path"] == str(vault)
    extra = root / ".ai-dlc/local/vault-mounts/other.json"
    extra.symlink_to(root / "docs/index.md")
    with pytest.raises((OSError, ValueError)):
        module.read_mount_bindings(root)


@pytest.mark.parametrize("target_part", ["", "docs", "docs/sub"])
def test_mount_refuses_other_vault_links_with_overlapping_targets(tmp_path, target_part):
    root, vault = setup(tmp_path)
    (root / "docs/sub").mkdir()
    (vault / "other").symlink_to(root / target_part, target_is_directory=True)
    with pytest.raises(ValueError, match="overlap"):
        mount(root, vault)
    assert not (root / ".ai-dlc/local").exists()


def test_mount_cannot_duplicate_binding_under_another_project_name(tmp_path):
    root, vault = setup(tmp_path)
    mount(root, vault)
    with pytest.raises(ValueError, match="overlap"):
        mount(root, vault, name="another")


def test_lexical_parent_segments_cannot_bypass_mount_overlap(tmp_path):
    root, _ = setup(tmp_path)
    (tmp_path / "other").mkdir()
    alias = tmp_path / "other" / ".." / root.name
    vault = root / "docs/vault"
    vault.mkdir()
    with pytest.raises(ValueError, match="overlap"):
        mount(alias, vault)
    assert not (vault / "Projects").exists()


@pytest.mark.parametrize("surface", ["source", "vault"])
def test_unreadable_tree_refuses_mount_before_binding(tmp_path, monkeypatch, surface):
    import os

    root, vault = setup(tmp_path)
    hidden = (root / "docs" if surface == "source" else vault) / "hidden"
    hidden.mkdir()
    original = os.scandir

    def denied(path):
        if str(path) == str(hidden):
            raise PermissionError("directory unreadable")
        return original(path)

    monkeypatch.setattr(os, "scandir", denied)
    with pytest.raises(ValueError, match="inaccessible"):
        mount(root, vault)
    assert not (root / ".ai-dlc/local").exists()
    assert not (vault / "Projects").exists()


def test_mount_normalization_does_not_hide_symlink_components(tmp_path):
    root, vault = setup(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(root / "docs", target_is_directory=True)
    with pytest.raises(ValueError):
        mount(alias / "..", vault)
    assert not (vault / "Projects").exists()
