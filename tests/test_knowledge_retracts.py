"""A decision accepted by mistake is retracted, never edited (KAN-479)."""

import shutil
from pathlib import Path

from ai_dlc.documentation import knowledge_records, record_index
from ai_dlc.documentation.knowledge_bundle import index_records
from ai_dlc.documentation.knowledge_check import check_records
from ai_dlc.documentation.knowledge_render import index_page, record_page

FIXTURE = Path(__file__).parent / "fixtures/knowledge_retracts"
TARGET = {"source": "https://github.com/example/knowledge/blob/main/"}


def copy(tmp_path):
    shutil.copytree(FIXTURE, tmp_path / "kb")
    return tmp_path / "kb"


def test_the_fixture_checks_and_the_retracted_record_is_unchanged(tmp_path):
    root = copy(tmp_path)
    assert check_records(root)["failures"] == []
    header, _body = knowledge_records.parse((root / "decisions/DEC-0001.md").read_text())
    assert header.status == "accepted"


def test_retracted_by_resolves_aliases_and_needs_an_accepted_retraction(tmp_path):
    root = copy(tmp_path)
    parsed = [
        knowledge_records.parse(path.read_text())[0]
        for path in sorted((root / "decisions").glob("*.md"))
    ]
    assert knowledge_records.retracted_by(parsed) == {"DEC-0001": ["DEC-0002"]}
    proposed = parsed[1].model_copy(update={"status": "proposed"})
    assert knowledge_records.retracted_by([parsed[0], proposed]) == {}
    assert knowledge_records.effective_status(parsed[0], {"DEC-0001": ["DEC-0002"]}) == (
        "retracted"
    )


def test_index_lists_the_original_as_retracted(tmp_path):
    root = copy(tmp_path)
    result = index_records(root)
    assert result["retracted_by"] == {"DEC-0001": ["DEC-0002"]}
    page = (root / "decisions/index.md").read_text()
    assert (
        "## Superseded, retracted and rejected\n\n* [Git is the knowledge system of record]"
        "(DEC-0001.md) - (DEC-0001; decision; retracted; retracted_by: DEC-0002)"
    ) in page
    assert "## Decisions\n\n* [Retract DEC-0001, accepted by mistake](DEC-0002.md)" in page
    assert check_records(root)["failures"] == []


def test_search_treats_the_retracted_record_as_not_accepted(tmp_path):
    root = copy(tmp_path)
    accepted = record_index.search(root, status="accepted")["items"]
    assert [item["id"] for item in accepted] == ["DEC-0002"]
    (retracted,) = record_index.search(root, status="retracted")["items"]
    assert retracted["id"] == "DEC-0001"
    assert retracted["retracted_by"] == ["DEC-0002"]
    assert retracted["header"]["status"] == "accepted"


def test_render_shows_the_original_as_retracted(tmp_path):
    root = copy(tmp_path)
    items = {item["id"]: item for item in record_index.search(root)["items"]}
    page = record_page({**record_index.get(root, "DEC-0001"), **items["DEC-0001"]}, TARGET)
    assert page["properties"]["status"] == "retracted"
    assert page["properties"]["retracted_by"] == "DEC-0002"
    assert "retracted" in page["labels"] and "accepted" not in page["labels"]
    index = index_page("team", list(items.values()), TARGET)
    assert "| DEC-0001 | decision | retracted |" in index["body"]
    assert "| DEC-0002 | decision | accepted |" in index["body"]
