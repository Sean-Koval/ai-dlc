"""Project-document access stays scoped, bounded and separate from private notes."""

import asyncio
import hashlib
import json
import os
import subprocess

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout


def make_repository(root, files):
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    for relative, body in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_bytes(body.encode() if isinstance(body, str) else body)
    git(root, "add", ".")
    git(root, "commit", "-qm", "baseline")
    return root


@pytest.fixture
def vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Private.md").write_text("Carrier private note.\n")
    return vault


@pytest.fixture
def repository(tmp_path, vault):
    root = make_repository(
        tmp_path / "project",
        {
            "docs/architecture.md": "# Architecture\nCarrier retries use backoff.\n",
            "docs/guide/setup.md": "Install the toolkit.\n",
            "openspec/specs/delivery/spec.md": "## Requirement: Carrier retry\n",
            "README.md": "Carrier overview at the root.\n",
            "legacy/notes.md": "Carrier legacy rationale.\n",
            ".gitignore": "docs/private/\n",
        },
    )
    (root / "docs/private").mkdir()
    (root / "docs/private/secret.md").write_text("Carrier ignored secret.\n")
    (root / "docs/vault").symlink_to(vault, target_is_directory=True)
    (root / "docs/linked.md").symlink_to(vault / "Private.md")
    return root


@pytest.fixture
def reads(monkeypatch):
    """Record every body read requested through the shared bounded reader."""
    import ai_dlc.documentation.document_access as service

    original = service.read_bounded
    requested = []

    def track(root, relative, remaining):
        requested.append(relative)
        return original(root, relative, remaining)

    monkeypatch.setattr(service, "read_bounded", track)
    return requested


def search(root, **kwargs):
    from ai_dlc.documentation.document_access import search_project_documents

    return search_project_documents(root, **kwargs)


def read(root, **kwargs):
    from ai_dlc.documentation.document_access import read_project_document

    return read_project_document(root, **kwargs)


def test_default_scope_is_docs_and_openspec_without_catalog_or_private_bodies(repository, reads):
    result = search(repository, query="CARRIER")
    assert [m["path"] for m in result["matches"]] == [
        "docs/architecture.md",
        "openspec/specs/delivery/spec.md",
    ]
    assert {
        "match": "body",
        "start_line": 2,
        "end_line": 2,
        "excerpt": "Carrier retries use backoff.",
        "source": {"kind": "project-document", "scope": "docs"},
        "absolute_path": str(repository / "docs/architecture.md"),
    }.items() <= result["matches"][0].items()
    assert result["repository"] == str(repository)
    assert set(reads) == {
        "docs/architecture.md",
        "docs/guide/setup.md",
        "openspec/specs/delivery/spec.md",
    }
    for body in ("overview at the root", "legacy rationale", "ignored secret", "Carrier private"):
        assert body not in str(result)
    assert {item["path"] for item in result["inventory"]["omitted"]} == {
        "docs/linked.md",
        "docs/vault",
    }
    assert {item["path"] for item in result["inventory"]["excluded"]} == {"docs/private/"}
    assert result["coverage"]["complete"] is False


def test_declared_source_adds_exact_file_for_one_call_without_writes(repository):
    before = git(repository, "status", "--porcelain", "--ignored")
    result = search(repository, query="carrier", sources=["README.md"])
    assert [m["path"] for m in result["matches"]] == [
        "README.md",
        "docs/architecture.md",
        "openspec/specs/delivery/spec.md",
    ]
    assert result["matches"][0]["source"]["scope"] == "declared"
    assert result["sources"] == {"defaults": ["docs", "openspec"], "declared": ["README.md"]}
    assert "legacy rationale" not in str(result)
    assert git(repository, "status", "--porcelain", "--ignored") == before
    assert "README.md" not in str(search(repository, query="carrier")["matches"])


def test_read_does_not_expand_scope_and_returns_bounded_identity(repository, reads):
    for path in ("README.md", "legacy/notes.md"):
        with pytest.raises(ValueError, match="declare"):
            read(repository, path=path)
    assert reads == []
    result = read(repository, path="README.md", sources=["README.md"])
    body = b"Carrier overview at the root.\n"
    assert result["document"] == {
        "path": "README.md",
        "absolute_path": str(repository / "README.md"),
        "source": {"kind": "project-document", "scope": "declared"},
        "digest": hashlib.sha256(body).hexdigest(),
        "start_line": 1,
        "end_line": 1,
        "bytes": len(body),
        "content": body.decode(),
    }
    assert result["omitted"] == []


@pytest.mark.parametrize(
    "sources",
    [
        "README.md",
        [7],
        ["README.md", "README.md"],
        [f"docs/{index}.md" for index in range(33)],
        ["/README.md"],
        ["../outside.md"],
        ["./README.md"],
        ["docs/*.md"],
        ["docs"],
        ["legacy/"],
        [".gitignore"],
        ["docs/private/secret.md"],
        ["docs/linked.md"],
        ["docs/vault/Private.md"],
        ["missing.md"],
    ],
)
def test_invalid_declarations_are_rejected_before_body_reads(repository, reads, sources):
    before = git(repository, "status", "--porcelain", "--ignored")
    with pytest.raises(ValueError):
        search(repository, query="carrier", sources=sources)
    with pytest.raises(ValueError):
        read(repository, path="docs/architecture.md", sources=sources)
    assert reads == []
    assert git(repository, "status", "--porcelain", "--ignored") == before


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": ""},
        {"query": "   "},
        {"query": "two\nlines"},
        {"query": 7},
        {"query": "carrier", "max_bytes": 0},
        {"query": "carrier", "max_bytes": -1},
        {"query": "carrier", "max_bytes": True},
        {"query": "carrier", "max_bytes": 1048577},
        {"query": "carrier", "max_bytes": "3"},
        {"query": "carrier", "max_bytes": 1.5},
        {"query": "carrier", "limit": 0},
        {"query": "carrier", "limit": 101},
        {"query": "carrier", "limit": True},
    ],
)
def test_invalid_queries_and_limits_are_rejected_before_body_reads(repository, reads, arguments):
    with pytest.raises(ValueError):
        search(repository, **arguments)
    assert reads == []


@pytest.mark.parametrize("budget", [0, True, 1048577])
def test_invalid_read_budget(repository, reads, budget):
    with pytest.raises(ValueError):
        read(repository, path="docs/architecture.md", max_bytes=budget)
    assert reads == []


def test_nonmatches_consume_one_budget_and_oversized_bodies_are_not_read(tmp_path, monkeypatch):
    root = make_repository(
        tmp_path / "project",
        {
            "docs/a.md": "z" * 60 + "\n",
            "docs/b.md": "needle here\n",
            "docs/c.md": "x" * 5000 + "\n",
        },
    )
    opened = []
    original = os.fdopen

    def track(fd, *args, **kwargs):
        opened.append(os.fstat(fd).st_size)
        return original(fd, *args, **kwargs)

    monkeypatch.setattr(os, "fdopen", track)
    result = search(root, query="needle", max_bytes=65)
    assert result["matches"] == []
    assert result["bytes_examined"] == 61
    assert result["coverage"]["examined"][0]["path"] == "docs/a.md"
    assert {item["path"] for item in result["coverage"]["not_examined"]} == {
        "docs/b.md",
        "docs/c.md",
    }
    assert result["coverage"]["complete"] is False
    assert 5001 not in opened and 12 not in opened
    assert search(root, query="needle", max_bytes=100)["matches"][0]["path"] == "docs/b.md"


def test_result_limit_is_deterministic_and_partial(repository):
    first = search(repository, query="carrier", limit=1)
    assert first == search(repository, query="carrier", limit=1)
    assert [m["path"] for m in first["matches"]] == ["docs/architecture.md"]
    assert first["coverage"]["not_examined"] == [
        {"path": "docs/guide/setup.md", "reason": "result limit reached"},
        {"path": "openspec/specs/delivery/spec.md", "reason": "result limit reached"},
    ]
    assert first["coverage"]["complete"] is False


def test_path_only_match_has_no_invented_line_and_long_excerpt_is_clipped(tmp_path):
    root = make_repository(
        tmp_path / "project",
        {
            "docs/setup.md": "Install the toolkit.\n",
            "docs/long.md": "a" * 500 + "Needle" + "b" * 500,
        },
    )
    result = search(root, query="setup")
    assert result["coverage"]["complete"] is True
    [match] = result["matches"]
    assert match["match"] == "path" and match["body_examined"] is True
    assert "start_line" not in match and "excerpt" not in match
    [clipped] = search(root, query="needle")["matches"]
    assert clipped["excerpt_clipped"] is True
    assert len(clipped["excerpt"]) <= 240 and "needle" in clipped["excerpt"].casefold()


def test_read_budget_omits_oversized_body_without_reading(repository, monkeypatch):
    opened = []
    original = os.fdopen
    monkeypatch.setattr(
        os, "fdopen", lambda fd, *a, **k: opened.append(fd) or original(fd, *a, **k)
    )
    result = read(repository, path="docs/architecture.md", max_bytes=5)
    assert result["document"] is None
    assert result["omitted"] == [
        {"path": "docs/architecture.md", "reason": "body budget exceeded; content not read"}
    ]
    assert opened == []


def test_binary_undecodable_and_special_files_are_reported(tmp_path):
    root = make_repository(
        tmp_path / "project",
        {"docs/binary.md": b"a\x00b", "docs/latin.md": b"\xff\xfe", "docs/ok.md": "ok\n"},
    )
    os.mkfifo(root / "docs/pipe.md")
    result = search(root, query="ok")
    reasons = {item["path"]: item["reason"] for item in result["coverage"]["not_examined"]}
    assert reasons == {"docs/binary.md": "binary content", "docs/latin.md": "not UTF-8 text"}
    assert "docs/pipe.md" not in str(result["matches"] + result["coverage"]["examined"])
    assert result["coverage"]["complete"] is False
    assert read(root, path="docs/binary.md")["omitted"][0]["reason"] == "binary content"


@pytest.mark.parametrize("replace", ["file", "special", "parent"])
def test_substitution_after_inventory_is_refused(repository, vault, monkeypatch, replace):
    import shutil

    import ai_dlc.documentation.document_access as service

    (vault / "setup.md").write_text("Private substituted body.\n")
    original = service.inventory_documents

    def substitute(root):
        result = original(root)
        if replace == "file":
            (repository / "docs/guide/setup.md").unlink()
            (repository / "docs/guide/setup.md").symlink_to(vault / "setup.md")
        elif replace == "special":
            (repository / "docs/guide/setup.md").unlink()
            os.mkfifo(repository / "docs/guide/setup.md")
        else:
            shutil.rmtree(repository / "docs/guide")
            (repository / "docs/guide").symlink_to(vault, target_is_directory=True)
        return result

    monkeypatch.setattr(service, "inventory_documents", substitute)
    result = read(repository, path="docs/guide/setup.md")
    assert result["document"] is None
    assert result["omitted"][0]["path"] == "docs/guide/setup.md"
    assert "Private substituted body" not in str(result)


def test_missing_default_directory_is_reported_without_creation(tmp_path):
    root = make_repository(tmp_path / "project", {"docs/a.md": "Present.\n"})
    result = search(root, query="present")
    assert result["unavailable_sources"] == [{"source": "openspec", "reason": "missing"}]
    assert [m["path"] for m in result["matches"]] == ["docs/a.md"]
    assert result["coverage"]["complete"] is True
    assert not (root / "openspec").exists()


def test_symlinked_default_directory_is_not_followed(tmp_path, vault):
    root = make_repository(tmp_path / "project", {"openspec/a.md": "Spec.\n"})
    (root / "docs").symlink_to(vault, target_is_directory=True)
    result = search(root, query="carrier")
    assert result["unavailable_sources"] == [{"source": "docs", "reason": "symlink not followed"}]
    assert result["matches"] == [] and result["coverage"]["complete"] is False


def test_repository_root_is_required_and_linked_worktrees_are_valid(repository, tmp_path):
    with pytest.raises(ValueError, match="repository root"):
        search(repository / "docs", query="carrier")
    with pytest.raises(ValueError):
        search(tmp_path / "absent", query="carrier")
    worktree = tmp_path / "worktree"
    git(repository, "worktree", "add", "-q", str(worktree))
    result = search(worktree, query="carrier")
    assert result["repository"] == str(worktree)
    assert result["matches"][0]["absolute_path"] == str(worktree / "docs/architecture.md")


def test_cli_and_mcp_share_scope_results_and_omissions(repository, monkeypatch):
    from ai_dlc.mcp_server import make_server

    monkeypatch.chdir(repository)
    runner = CliRunner()
    server = make_server(repository)

    async def call(name, arguments):
        result = await server.call_tool(name, arguments)
        return json.loads(result[0].text)

    cli = runner.invoke(
        app,
        ["project", "docs-search", "carrier", "--source", "README.md", "--limit", "2"]
        + ["--max-bytes", "4096"],
    )
    assert cli.exit_code == 0, cli.output
    assert json.loads(cli.stdout) == asyncio.run(
        call(
            "project_docs_search",
            {"query": "carrier", "sources": ["README.md"], "limit": 2, "max_bytes": 4096},
        )
    )
    cli = runner.invoke(app, ["project", "docs-read", "docs/architecture.md", "--root", "."])
    assert cli.exit_code == 0, cli.output
    assert json.loads(cli.stdout) == asyncio.run(
        call("project_docs_read", {"path": "docs/architecture.md"})
    )
    assert runner.invoke(app, ["project", "docs-read", "README.md"]).exit_code != 0


def test_private_knowledge_tools_remain_separate(repository):
    from ai_dlc.mcp_server import make_server

    tools = {tool.name: tool for tool in asyncio.run(make_server(repository).list_tools())}
    assert {"knowledge_find", "knowledge_append", "knowledge_note"} <= set(tools)
    for name in ("project_docs_search", "project_docs_read"):
        assert "vault" not in json.dumps(tools[name].inputSchema)
