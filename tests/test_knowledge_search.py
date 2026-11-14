"""``knowledge records search`` (KAN-494): usable cold against a knowledge clone.

``--root <clone>`` needs no ``KNOWLEDGE_REPO`` or ``--provider``. On a terminal it
prints a ranked, compact list; piped or captured (skills parse it) it prints JSON;
``--format`` forces either. Sources only on request.
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


def rows(*args: str):
    return search(*args, "--format", "text")


def test_knowledge_search_root_needs_no_knowledge_repo_or_provider(clone):
    result = rows("--root", str(clone))
    assert result.exit_code == 0, result.output
    found = [line for line in result.output.splitlines() if not line.startswith("    ")]
    assert found[0].split()[:3] == ["DEC-0002", "decision", "accepted"]
    assert found[-1] == "4 records; 2 source records hidden (--type source)"
    assert "SRC-0001" not in "\n".join(found)


def test_knowledge_search_compact_rows_carry_the_line_owner_and_evidence(clone):
    output = rows("--root", str(clone), "--type", "decision").output
    assert "DEC-0001  decision  superseded  Nightly builds only\n" in output
    line = "    CI builds main once a night instead of on every merge.  [owner sean; evidence SRC-0001]"
    assert line in output
    assert output.index("DEC-0002") < output.index("DEC-0001")  # current before ended


def test_knowledge_search_sources_only_with_type_source(clone):
    output = rows("--root", str(clone), "--type", "source").output
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
    output = rows("--root", str(clone), "--text", "nightly").output
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


def test_knowledge_search_captured_output_defaults_to_json_for_skills(clone):
    """Skills run it through a shell and parse ``items``, ``path`` and ``header``."""
    result = search("--root", str(clone), "--type", "decision")
    assert result.exit_code == 0, result.output
    found = json.loads(result.output)
    assert [item["id"] for item in found["items"]] == ["DEC-0002", "DEC-0001"]
    assert {"id", "path", "header"} <= set(found["items"][0])


def test_knowledge_search_a_terminal_gets_ranked_rows(clone, monkeypatch):
    monkeypatch.setattr("ai_dlc.cli._stdout_is_terminal", lambda: True)
    output = search("--root", str(clone), "--type", "decision").output
    assert output.startswith("DEC-0002  decision  accepted")
    forced = search("--root", str(clone), "--type", "decision", "--format", "json").output
    assert json.loads(forced)["items"][0]["id"] == "DEC-0002"
    assert json.loads(search("--root", str(clone), "--json").output)["status"] == "ok"


def test_knowledge_search_refuses_an_unknown_format(clone):
    result = search("--root", str(clone), "--format", "yaml")
    assert result.exit_code == 2
