import pytest

from ai_dlc.knowledge import Knowledge


def test_append_is_idempotent_and_preserves_note(tmp_path):
    from ai_dlc.knowledge import Knowledge

    note = tmp_path / "Daily.md"
    note.write_text("Existing note\n")
    knowledge = Knowledge(tmp_path)
    knowledge.append("Daily.md", "Finished work", "session-1")
    knowledge.append("Daily.md", "Finished work", "session-1")
    assert note.read_text().count("Finished work") == 1
    assert note.read_text().startswith("Existing note\n")
    with pytest.raises(ValueError, match="conflict"):
        knowledge.append("Daily.md", "Different content", "session-1")


def test_vault_escape_and_symlinks_rejected(tmp_path):
    from ai_dlc.knowledge import Knowledge

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "escape").symlink_to(tmp_path, target_is_directory=True)
    knowledge = Knowledge(vault)
    for path in ["../secret.md", "escape/secret.md", "/tmp/secret.md"]:
        with pytest.raises(ValueError, match="vault"):
            knowledge.append(path, "no", "op")


def test_unavailable_vault_is_not_created(tmp_path):
    from ai_dlc.knowledge import Knowledge

    with pytest.raises(ValueError, match="unavailable"):
        Knowledge(tmp_path / "missing")
    assert not (tmp_path / "missing").exists()


def test_project_directory_name_does_not_authorize_external_access(tmp_path):
    vault = tmp_path / "vault"
    (vault / "Projects").mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    note = external / "private.md"
    note.write_text("private sentinel")
    (vault / "Projects" / "unregistered").symlink_to(external, target_is_directory=True)
    knowledge = Knowledge(vault)
    assert knowledge.find("sentinel") == []
    with pytest.raises(ValueError):
        knowledge.append("Projects/unregistered/private.md", "unauthorized", "escape")
    assert note.read_text() == "private sentinel"


def test_nested_project_symlink_is_not_a_note_write_boundary(tmp_path):
    vault = tmp_path / "vault"
    docs = tmp_path / "docs"
    outside = tmp_path / "outside"
    (vault / "Projects").mkdir(parents=True)
    docs.mkdir()
    outside.mkdir()
    (docs / "escape").symlink_to(outside, target_is_directory=True)
    (vault / "Projects" / "project").symlink_to(docs, target_is_directory=True)
    with pytest.raises(ValueError):
        Knowledge(vault).note("Projects/project/escape/new.md", "private", "escape")
    assert not (outside / "new.md").exists()
