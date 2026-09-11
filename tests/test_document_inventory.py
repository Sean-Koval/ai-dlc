"""Repository discovery preserves scope before any content review."""

import asyncio
import json
import subprocess

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app


@pytest.fixture
def repository(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    (tmp_path / "README.md").write_text("Root instructions.\n")
    (tmp_path / "legacy").mkdir()
    (tmp_path / "legacy/plan.MD").write_text("Unique historical rationale.\n")
    (tmp_path / ".gitignore").write_text("ignored/\nforced.md\n")
    git("add", ".")
    (tmp_path / "forced.md").write_text("Tracked despite ignore.\n")
    git("add", "-f", "forced.md")
    git("commit", "-qm", "baseline")
    (tmp_path / "draft.md").write_text("A new draft.\n")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored/secret.md").write_text("Excluded secret body.\n")
    (tmp_path / "linked.md").symlink_to(tmp_path / "ignored/secret.md")
    (tmp_path / "linked-directory").symlink_to(tmp_path / "ignored", target_is_directory=True)
    return tmp_path


def test_inventory_includes_scattered_files_and_reports_exclusions_without_bodies(repository):
    from ai_dlc.documentation.document_inventory import inventory_documents

    result = inventory_documents(repository)
    assert result["documents"] == ["README.md", "draft.md", "forced.md", "legacy/plan.MD"]
    assert {item["path"] for item in result["excluded"]} >= {".git", "ignored/"}
    assert {item["path"] for item in result["omitted"]} >= {"linked.md", "linked-directory"}
    assert "Excluded secret body" not in str(result)


def test_inventory_reports_missing_tracked_file_and_unavailable_directory(repository, monkeypatch):
    import ai_dlc.documentation.document_inventory as service

    (repository / "README.md").unlink()
    original = service.os.scandir

    def denied(fd):
        if service.os.fstat(fd).st_ino == (repository / "legacy").stat().st_ino:
            raise PermissionError("fixture inaccessible directory")
        return original(fd)

    monkeypatch.setattr(service.os, "scandir", denied)
    result = service.inventory_documents(repository)
    assert "README.md" not in result["documents"]
    assert {item["path"] for item in result["omitted"]} >= {"README.md", "legacy"}


def test_inventory_and_explicit_review_cli_mcp_parity(repository):
    from ai_dlc.mcp_server import make_server

    runner = CliRunner()
    inventory = runner.invoke(app, ["project", "docs-inventory", "--root", str(repository)])
    assert inventory.exit_code == 0, inventory.output
    server = make_server(repository)

    async def call(name, arguments):
        result = await server.call_tool(name, arguments)
        return json.loads(result[0].text)

    assert json.loads(inventory.stdout) == asyncio.run(call("project_docs_inventory", {}))
    args = [
        "project",
        "docs-review",
        "--root",
        str(repository),
        "--base",
        "HEAD",
        "--path",
        "README.md",
        "--source",
        "inventory",
    ]
    prepared = runner.invoke(app, args)
    assert prepared.exit_code == 0, prepared.output
    assert json.loads(prepared.stdout) == asyncio.run(
        call("project_docs_review", {"base": "HEAD", "paths": ["README.md"], "source": "inventory"})
    )


def test_uncatalogued_review_retains_budget_citations_and_freshness(repository):
    from ai_dlc.documentation.document_review import prepare_review, validate_review

    p = prepare_review(repository, paths=["README.md"], base="HEAD", source="inventory")
    assert p["documents"][0]["content"] == "Root instructions.\n"
    assert "legacy/plan.MD" in p["unreviewed"]
    citation = {"path": "README.md", "start_line": 1, "end_line": 1, "quote": "Root instructions."}
    review = {
        "schema": 1,
        "packet_snapshot": p["snapshot"],
        "reviewed": ["README.md"],
        "unreviewed": [],
        "findings": [
            {
                "category": "vague-prose",
                "target": citation,
                "supporting": [citation],
                "uncertainty": "Intended audience unknown.",
                "suggested_disposition": "investigate",
                "rationale": "Missing concrete steps.",
            }
        ],
    }
    assert validate_review(repository, packet=p, review=review)["valid"]
    citation["quote"] = "Fabricated quote."
    assert not validate_review(repository, packet=p, review=review)["valid"]
    citation["quote"] = "Root instructions."
    (repository / "README.md").write_text("Changed instructions.\n")
    assert not validate_review(repository, packet=p, review=review)["valid"]
    bounded = prepare_review(
        repository, paths=["README.md"], base="HEAD", source="inventory", max_bytes=1
    )
    assert bounded["documents"] == []
    assert any(item["path"] == "README.md" for item in bounded["omitted"])


@pytest.mark.parametrize(
    "selected",
    ["ignored/secret.md", "linked.md", "linked-directory/secret.md", "../outside.md", ".gitignore"],
)
def test_inventory_review_rejects_ineligible_paths(repository, selected):
    from ai_dlc.documentation.document_review import prepare_review

    with pytest.raises(ValueError):
        prepare_review(repository, paths=[selected], base="HEAD", source="inventory")


def test_inventory_does_not_hide_tracked_markdown_in_ignored_directory(repository):
    from ai_dlc.documentation.document_inventory import inventory_documents

    (repository / "ignored/tracked.md").write_text("Tracked policy.\n")
    subprocess.run(["git", "add", "-f", "ignored/tracked.md"], cwd=repository, check=True)
    result = inventory_documents(repository)
    assert "ignored/tracked.md" in result["documents"]
    assert "ignored/secret.md" not in result["documents"]


def test_inventory_never_traverses_nested_git_repository(repository):
    from ai_dlc.documentation.document_inventory import inventory_documents

    nested = repository / "vendor"
    nested.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
    (nested / "private.md").write_text("Another repository's document.\n")
    result = inventory_documents(repository)
    assert "vendor/private.md" not in result["documents"]
    assert any(item["path"].rstrip("/") == "vendor" for item in result["excluded"])


def test_inventory_review_mapping_does_not_expand_document_selection(repository):
    from ai_dlc.documentation.document_review import prepare_review

    (repository / "docs").mkdir()
    (repository / "docs/a.md").write_text("Selected guide.\n")
    (repository / "docs/catalog.toml").write_text(
        'schema=1\n[[documents]]\npath="docs/a.md"\ncode_paths=["legacy/*", "ignored/secret.md"]\n'
    )
    result = prepare_review(repository, paths=["docs/a.md"], base="HEAD", source="inventory")
    assert result["evidence"] == []
    assert any(
        item == {"path": "legacy/plan.MD", "reason": "document not selected"}
        for item in result["omitted"]
    )
    assert "Unique historical rationale" not in str(result)
