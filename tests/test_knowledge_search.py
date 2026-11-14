"""``knowledge records search`` (KAN-494): usable cold against a knowledge clone.

``--root <clone>`` needs no ``KNOWLEDGE_REPO`` or ``--provider``; the default output
is a ranked, compact list; full JSON is behind ``--json``; Sources only on request.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.documentation.knowledge_service import KnowledgeRecords, rank

FIXTURE = Path(__file__).parent / "fixtures/knowledge_why"


@pytest.fixture
def clone(tmp_path, monkeypatch):
    """A knowledge repository clone: the why fixture, committed, with no ai-dlc config."""
    monkeypatch.delenv("KNOWLEDGE_REPO", raising=False)
    folder = tmp_path / "knowledge"
    shutil.copytree(FIXTURE, folder)
    subprocess.run(["git", "init", "--quiet", str(folder)], check=True)
    return folder


def search(*args: str):
    return CliRunner().invoke(app, ["knowledge", "records", "search", *args])


def test_knowledge_search_root_needs_no_knowledge_repo_or_provider(clone):
    result = search("--root", str(clone))
    assert result.exit_code == 0, result.output
    rows = [line for line in result.output.splitlines() if not line.startswith("    ")]
    assert rows[0].split()[:3] == ["DEC-0002", "decision", "accepted"]
    assert rows[-1] == "4 records; 2 source records hidden (--type source)"
    assert "SRC-0001" not in "\n".join(rows)


def test_knowledge_search_compact_rows_carry_the_line_owner_and_evidence(clone):
    output = search("--root", str(clone), "--type", "decision").output
    assert "DEC-0001  decision  superseded  Nightly builds only\n" in output
    line = "    CI builds main once a night instead of on every merge.  [owner sean; evidence SRC-0001]"
    assert line in output
    assert output.index("DEC-0002") < output.index("DEC-0001")  # current before ended


def test_knowledge_search_sources_only_with_type_source(clone):
    output = search("--root", str(clone), "--type", "source").output
    assert "SRC-0001  source" in output and "SRC-0002  source" in output
    assert "DEC-0001" not in output and "hidden" not in output


def test_knowledge_search_json_keeps_full_headers_ranked(clone):
    result = search("--root", str(clone), "--json")
    assert result.exit_code == 0, result.output
    found = json.loads(result.output)
    assert found["status"] == "ok" and found["hidden_sources"] == 2
    assert found["items"][0]["id"] == "DEC-0002"
    assert set(found["items"][0]["header"]) >= {"owner", "sources", "links", "date"}


def test_knowledge_search_text_ranks_header_matches_first(clone):
    output = search("--root", str(clone), "--text", "nightly").output
    assert output.splitlines()[0].startswith("DEC-0001  decision  superseded")


def test_knowledge_search_explicit_provider_still_wins(clone, tmp_path):
    result = search("--root", str(clone), "--provider", "git")
    assert result.exit_code != 0  # git without KNOWLEDGE_REPO or a location
    assert "KNOWLEDGE_REPO" in result.output


def test_knowledge_search_get_matches_ids_in_any_case(clone):
    store = KnowledgeRecords.at(clone, {})
    assert store.get("dec-0002")["id"] == "DEC-0002"


def test_knowledge_search_rank_orders_status_then_newest():
    items = [
        {"id": "a", "header": {"status": "superseded", "date": "2026-11-01"}},
        {"id": "b", "header": {"status": "accepted", "date": "2026-01-01"}},
        {"id": "c", "header": {"status": "accepted", "date": "2026-06-01"}},
        {"id": "d", "header": {"status": "accepted", "date": "2026-12-01"}, "retracted_by": ["x"]},
    ]
    assert [item["id"] for item in rank(items)] == ["c", "b", "a", "d"]
