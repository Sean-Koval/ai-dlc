import pytest


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
