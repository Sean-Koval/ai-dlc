from pathlib import Path
import pytest

from ai_dlc.knowledge import Knowledge
from ai_dlc.moc import scaffold_5_pillar_docs
from ai_dlc.vault_link import ensure_gitignore_entries, link_vault


def test_ensure_gitignore_entries(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    gitignore = project / ".gitignore"
    gitignore.write_text("node_modules/\n.venv/\n")

    updated = ensure_gitignore_entries(project, [".obsidian/", ".trash/"])
    assert updated is True
    content = gitignore.read_text()
    assert ".obsidian/" in content
    assert ".trash/" in content
    assert "node_modules/" in content

    # Calling again should be idempotent
    assert ensure_gitignore_entries(project, [".obsidian/", ".trash/"]) is False


def test_scaffold_5_pillar_docs_non_destructive(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# Custom Existing Index\n")

    created = scaffold_5_pillar_docs(docs, "my-app")
    assert "index.md" not in created
    assert (docs / "index.md").read_text() == "# Custom Existing Index\n"
    assert (docs / "architecture" / "system-design.md").exists()
    assert (docs / "adr" / "0000-template.md").exists()
    assert (docs / "specs" / "README.md").exists()
    assert (docs / "runbooks" / "README.md").exists()
    assert (docs / "reference" / "README.md").exists()


def test_link_vault_creates_symlink_and_gitignores(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    project = tmp_path / "my-service"
    project.mkdir()

    res = link_vault(project, vault=vault, docs_preset="5-pillar")
    assert res.created_link is True
    assert res.created_docs is True
    assert res.gitignore_updated is True
    assert (project / ".gitignore").exists()

    link = vault / "Projects" / "my-service"
    assert link.is_symlink()
    assert link.resolve() == (project / "docs").resolve()

    # Verify Knowledge integration
    knowledge = Knowledge(vault)
    find_results = knowledge.find("Map of Content")
    assert len(find_results) >= 1
    assert any(item["path"] == "Projects/my-service/index.md" for item in find_results)


def test_link_vault_idempotency_and_force(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    project1 = tmp_path / "proj1"
    project1.mkdir()
    project2 = tmp_path / "proj2"
    project2.mkdir()

    # Initial link
    res1 = link_vault(project1, vault=vault, name="shared-name")
    assert res1.created_link is True

    # Same project relink is a no-op
    res2 = link_vault(project1, vault=vault, name="shared-name")
    assert res2.created_link is False

    # Different project collision without force fails
    with pytest.raises(ValueError, match="already points to"):
        link_vault(project2, vault=vault, name="shared-name", force=False)

    # Different project with force updates
    res3 = link_vault(project2, vault=vault, name="shared-name", force=True)
    assert res3.created_link is True
    assert (vault / "Projects" / "shared-name").resolve() == (project2 / "docs").resolve()


def test_link_vault_existing_directory_refuses_overwrite(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "Projects" / "real-dir").mkdir(parents=True)
    project = tmp_path / "proj"
    project.mkdir()

    with pytest.raises(ValueError, match="Refusing to overwrite"):
        link_vault(project, vault=vault, name="real-dir", force=True)


def test_link_vault_missing_vault_raises(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()
    empty_home = tmp_path / "empty_home"
    empty_home.mkdir()

    with pytest.raises(ValueError, match="Configure paths.vault"):
        link_vault(project, vault=None, home=empty_home, environ={})
