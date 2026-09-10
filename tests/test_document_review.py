"""Packets and findings are bounded, scoped and checked against actual local bytes."""

import copy
import subprocess

import pytest


@pytest.fixture
def project(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    (tmp_path / "docs").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "docs/a.md").write_text("Uses version one.\nAudience summary.\n")
    (tmp_path / "docs/b.md").write_text("Unselected secret.\n")
    (tmp_path / "src/api.py").write_text("VERSION = 2\n")
    (tmp_path / "docs/catalog.toml").write_text("""schema = 1
[[documents]]
path = "docs/a.md"
code_paths = ["src/*", "missing.py"]
[[documents]]
path = "docs/b.md"
""")
    git("add", ".")
    git("commit", "-qm", "baseline")
    return tmp_path


def packet(root, **kwargs):
    from ai_dlc.document_review import prepare_review

    return prepare_review(root, paths=["docs/a.md"], base="HEAD", **kwargs)


def review(p):
    return {
        "schema": 1,
        "packet_snapshot": p["snapshot"],
        "reviewed": ["docs/a.md"],
        "unreviewed": [],
        "findings": [
            {
                "category": "contradiction",
                "target": {
                    "path": "docs/a.md",
                    "start_line": 1,
                    "end_line": 1,
                    "quote": "Uses version one.",
                },
                "supporting": [
                    {"path": "src/api.py", "start_line": 1, "end_line": 1, "quote": "VERSION = 2"}
                ],
                "uncertainty": "Runtime not checked.",
                "suggested_disposition": "revise",
                "rationale": "Align stated version.",
            }
        ],
    }


def check(root, p, r):
    from ai_dlc.document_review import validate_review

    return validate_review(root, packet=p, review=r)


def test_packet_scope_and_missing_evidence(project):
    p = packet(project)
    assert [x["path"] for x in p["documents"]] == ["docs/a.md"]
    assert "docs/b.md" in p["unreviewed"]
    assert "Unselected secret" not in str(p)
    assert any(x["path"] == "missing.py" for x in p["omitted"])
    assert check(project, p, review(p))["valid"]


def test_budget_and_explicit_unreviewed(project):
    p = packet(project, max_bytes=3)
    assert p["documents"] == [] and p["evidence"] == []
    assert not check(project, p, review(p))["valid"]
    r = review(p) | {"reviewed": [], "unreviewed": ["docs/a.md"], "findings": []}
    assert check(project, p, r)["valid"]


@pytest.mark.parametrize("budget", [0, -1, True, 1048577, "3"])
def test_invalid_budget(project, budget):
    with pytest.raises(ValueError):
        packet(project, max_bytes=budget)


def test_actual_bytes_invalidate_even_rehashed_forgery(project):
    from ai_dlc.document_impact import digest

    p = packet(project)
    forged = copy.deepcopy(p)
    forged["evidence"][0]["content"] = "VERSION = 9\n"
    forged["snapshot"] = digest({k: v for k, v in forged.items() if k != "snapshot"})
    assert not check(project, forged, review(forged))["valid"]
    (project / "src/api.py").write_text("VERSION = 3\n")
    assert not check(project, p, review(p))["valid"]


@pytest.mark.parametrize(
    "change",
    [
        {"quote": "Invented"},
        {"start_line": 0},
        {"end_line": 999},
        {"start_line": True},
        {"path": "docs/b.md"},
        {"quote": ""},
    ],
)
def test_fabricated_citations(project, change):
    p = packet(project)
    r = review(p)
    r["findings"][0]["supporting"][0].update(change)
    assert not check(project, p, r)["valid"]


@pytest.mark.parametrize("support", [[], None, [None], [{}], "bad"])
def test_malformed_support(project, support):
    p = packet(project)
    r = review(p)
    r["findings"][0]["supporting"] = support
    assert not check(project, p, r)["valid"]


def test_useful_repetition_retained(project):
    p = packet(project)
    r = review(p)
    r["findings"][0].update(category="useful-repetition", suggested_disposition="retain")
    assert check(project, p, r)["valid"]
    r["findings"][0]["suggested_disposition"] = "consolidate"
    assert not check(project, p, r)["valid"]


def test_binary_symlink_and_fifo_omitted(project):
    import os

    (project / "src/binary").write_bytes(b"a\x00b")
    (project / "src/link").symlink_to(project / "docs/b.md")
    os.mkfifo(project / "src/pipe")
    catalog = project / "docs/catalog.toml"
    catalog.write_text(catalog.read_text().replace('"missing.py"', '"missing.py", "src/pipe"'))
    p = packet(project)
    assert {x["path"] for x in p["omitted"]} >= {"src/binary", "src/link", "src/pipe"}
    assert "Unselected secret" not in str(p)


def test_selection_rejected_outside_catalog(project):
    from ai_dlc.document_review import prepare_review

    for paths in (["../outside"], ["src/api.py"], [], ["docs/a.md"] * 33):
        with pytest.raises(ValueError):
            prepare_review(project, paths=paths, base="HEAD")


@pytest.mark.parametrize("malformed", [None, [], {}, {"schema": 1}, {"schema": 1, "selected": 7}])
def test_malformed_packet_returns_diagnostic(project, malformed):
    assert not check(project, malformed, {})["valid"]


def test_document_freshness_and_incomplete_coverage(project):
    p = packet(project)
    r = review(p)
    r["reviewed"] = []
    assert not check(project, p, r)["valid"]
    (project / "docs/a.md").write_text("Uses version two.\n")
    assert not check(project, p, review(p))["valid"]


def test_body_budget_is_total_and_oversized_body_not_read(project, monkeypatch):
    import ai_dlc.document_review as service

    original = service.os.fdopen
    opened = []

    def track(fd, *args, **kwargs):
        opened.append(service.os.fstat(fd).st_size)
        return original(fd, *args, **kwargs)

    (project / "src/large").write_text("x" * 10000)
    monkeypatch.setattr(service.os, "fdopen", track)
    p = packet(project, max_bytes=100)
    assert sum(len(x["content"].encode()) for x in p["documents"] + p["evidence"]) <= 100
    assert 10000 not in opened
    assert any(x["path"] == "src/large" for x in p["omitted"])


def test_review_cli_and_mcp_boundaries(project, tmp_path):
    import asyncio
    import json

    from typer.testing import CliRunner

    from ai_dlc.cli import app
    from ai_dlc.mcp_server import make_server

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["project", "docs-review", "--root", str(project), "--base", "HEAD", "--path", "docs/a.md"],
    )
    assert result.exit_code == 0, result.output
    prepared = json.loads(result.stdout)
    assert [d["path"] for d in prepared["documents"]] == ["docs/a.md"]
    tools = asyncio.run(make_server(project).list_tools())
    assert {"project_docs_review", "project_docs_review_check"} <= {t.name for t in tools}
    packet_file = tmp_path / "packet.json"
    packet_file.write_text(json.dumps(prepared))
    review_file = tmp_path / "review.json"
    review_file.write_text("{}")
    invalid = runner.invoke(
        app,
        [
            "project",
            "docs-review-check",
            "--root",
            str(project),
            "--packet",
            str(packet_file),
            "--review",
            str(review_file),
        ],
    )
    assert invalid.exit_code == 2
