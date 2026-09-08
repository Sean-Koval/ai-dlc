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


def test_symlinked_project_docs_are_found_and_writable(tmp_path):
    from ai_dlc.knowledge import Knowledge

    vault = tmp_path / "vault"
    projects = vault / "Projects"
    projects.mkdir(parents=True)

    repo_docs = tmp_path / "repos" / "dart-mcp" / "docs"
    arch = repo_docs / "architecture"
    arch.mkdir(parents=True)
    doc_file = arch / "system-design.md"
    doc_file.write_text("# System Design\nBuilt using FastMCP architecture.\n")

    # Symlink Projects/dart-mcp -> repo_docs
    (projects / "dart-mcp").symlink_to(repo_docs, target_is_directory=True)

    knowledge = Knowledge(vault)
    results = knowledge.find("FastMCP")
    assert len(results) == 1
    assert results[0]["path"] == "Projects/dart-mcp/architecture/system-design.md"
    assert results[0]["title"] == "system-design"

    # Append note through symlink
    res = knowledge.append(
        "Projects/dart-mcp/architecture/system-design.md",
        "Added security section",
        "op-symlink-1",
    )
    assert res["created"] is True
    assert "Added security section" in doc_file.read_text()


def test_symlink_cycle_and_escape_under_projects_ignored(tmp_path):
    from ai_dlc.knowledge import Knowledge

    vault = tmp_path / "vault"
    projects = vault / "Projects"
    projects.mkdir(parents=True)

    # Symlink pointing back to vault root (cycle)
    (projects / "cycle-to-vault").symlink_to(vault, target_is_directory=True)

    knowledge = Knowledge(vault)
    # Searching should safely skip the cycle and not recurse infinitely
    results = knowledge.find("NonexistentQuery")
    assert results == []
