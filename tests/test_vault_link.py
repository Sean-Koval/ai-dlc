import pytest

from ai_dlc.documentation.knowledge import Knowledge
from ai_dlc.documentation.vault_link import link_vault


def setup(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    project = tmp_path / "my-service"
    (project / "docs").mkdir(parents=True)
    (project / "docs" / "index.md").write_text("# Canonical project map\n")
    return project, vault


def test_vault_link_is_a_portal_not_a_second_document_home(tmp_path):
    project, vault = setup(tmp_path)
    (project / "openspec").mkdir()
    result = link_vault(project, vault=vault)
    portal = vault / "Projects" / "my-service.md"
    assert portal.is_file() and not portal.is_symlink()
    body = portal.read_text()
    assert (project / "docs" / "index.md").as_uri() in body
    assert (project / "openspec").as_uri() in body
    assert "Canonical project map" not in body
    assert not (project / ".gitignore").exists()
    assert result.created_link
    assert not link_vault(project, vault=vault).created_link
    assert Knowledge(vault).find("my-service")[0]["path"] == "Projects/my-service.md"


@pytest.mark.parametrize(
    "name", ["../escape", "../../escape", "ABSOLUTE", ".", "..", "a/b", "a\\b", ""]
)
def test_link_name_refused_before_mutation(tmp_path, name):
    project, vault = setup(tmp_path)
    if name == "ABSOLUTE":
        name = str(tmp_path / "absolute")
    with pytest.raises(ValueError):
        link_vault(project, vault=vault, name=name)
    assert list(vault.iterdir()) == []


def test_portal_preserves_authored_content_even_with_force(tmp_path):
    project, vault = setup(tmp_path)
    (vault / "Projects").mkdir()
    portal = vault / "Projects" / "my-service.md"
    portal.write_text("Personal notes")
    with pytest.raises(ValueError):
        link_vault(project, vault=vault, force=True)
    assert portal.read_text() == "Personal notes"


def test_portal_refuses_symlinked_parent_and_does_not_scaffold_on_conflict(tmp_path):
    project, vault = setup(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (vault / "Projects").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        link_vault(project, vault=vault, docs_preset="organized")
    assert list(outside.iterdir()) == []
    assert not (project / "docs" / "catalog.toml").exists()


def test_portal_never_replaces_legacy_symlink(tmp_path):
    project, vault = setup(tmp_path)
    (vault / "Projects").mkdir()
    link = vault / "Projects" / "my-service"
    link.symlink_to(project / "docs", target_is_directory=True)
    with pytest.raises(ValueError, match="legacy|Legacy"):
        link_vault(project, vault=vault)
    assert link.is_symlink()


def test_missing_vault_does_not_create_docs(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(ValueError, match="vault"):
        link_vault(project, home=tmp_path / "home", environ={}, docs_preset="organized")
    assert list(project.iterdir()) == []


def test_preview_does_not_create_portal_or_documentation(tmp_path):
    project, vault = setup(tmp_path)
    result = link_vault(project, vault=vault, docs_preset="organized", apply=False)
    assert not result.created_link
    assert list(vault.iterdir()) == []
    assert not (project / "docs" / "catalog.toml").exists()


def test_symlinked_vault_preflight_preserves_repository(tmp_path):
    project, vault = setup(tmp_path)
    alias = tmp_path / "vault-alias"
    alias.symlink_to(vault, target_is_directory=True)
    with pytest.raises(ValueError):
        link_vault(project, vault=alias, docs_preset="organized")
    assert not (project / "docs/catalog.toml").exists()
    assert list(vault.iterdir()) == []


@pytest.mark.parametrize("special", [False, True])
def test_non_directory_portal_parent_refused_before_scaffolding(tmp_path, special):
    import os

    project, vault = setup(tmp_path)
    parent = vault / "Projects"
    if special:
        os.mkfifo(parent)
    else:
        parent.write_text("Authored file")
    with pytest.raises(ValueError):
        link_vault(project, vault=vault, docs_preset="organized")
    assert not (project / "docs/catalog.toml").exists()
    if not special:
        assert parent.read_text() == "Authored file"
