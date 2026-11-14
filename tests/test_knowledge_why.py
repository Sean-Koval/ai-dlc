"""``knowledge why`` (KAN-466): a decision, its chain and evidence, from local records."""

import asyncio
import json
import shutil
import socket
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.documentation.knowledge_check import check_records
from ai_dlc.documentation.knowledge_why import lines, why

FIXTURE = Path(__file__).parent / "fixtures/knowledge_why"
RETRACTS = Path(__file__).parent / "fixtures/knowledge_retracts"
QUOTE_MARCH = "CI minutes cost too much; let's build nightly only until the budget resets."
QUOTE_SEPTEMBER = (
    "Three broken mains this quarter were found a day late. We build every merge again."
)


@pytest.fixture
def bundle(tmp_path):
    folder = tmp_path / "records"
    shutil.copytree(FIXTURE, folder)
    return folder


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Outcome O1: the answer comes from local git only."""

    def refuse(*_args, **_kwargs):
        raise AssertionError("knowledge why opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)


def test_fixture_is_a_valid_bundle_with_no_payloads():
    assert check_records(FIXTURE)["failures"] == []
    assert not (FIXTURE / "inbox").exists() and not (FIXTURE / "transcripts").exists()


@pytest.mark.parametrize("name", ["DEC-0001", "DEC-0002", "nightly-builds-only"])
def test_either_end_of_a_reversal_shows_both_with_quotes_after_payloads_expire(name):
    result = why(FIXTURE, name)
    assert result["status"] == "ok"
    chain = [result["record"], *result["supersedes"], *result["superseded_by"]]
    assert [entry["id"] for entry in chain] in (["DEC-0001", "DEC-0002"], ["DEC-0002", "DEC-0001"])
    quotes = [e["quote"] for e in result["evidence"]]
    quotes += [e["quote"] for entry in chain[1:] for e in entry["evidence"]]
    assert sorted(quotes) == sorted([QUOTE_MARCH, QUOTE_SEPTEMBER])
    for evidence in result["evidence"]:
        assert evidence["payload"] == "expired"
        assert evidence["source"]["participants"] and evidence["source"]["title"]
    text = "\n".join(lines(result))
    assert QUOTE_MARCH in text and QUOTE_SEPTEMBER in text and "payload: expired" in text


def test_the_reversal_carries_its_reason_status_dates_and_derived_successor():
    result = why(FIXTURE, "DEC-0001")
    record = result["record"]
    assert (record["status"], record["valid_from"], record["valid_to"]) == (
        "superseded",
        "2026-03-04",
        "2026-09-15",
    )
    (successor,) = result["superseded_by"]
    assert successor["id"] == "DEC-0002" and successor["via"] == "DEC-0001"
    assert "three broken mains" in successor["reason"]
    assert result["tickets"] == []


def test_each_end_of_the_reversal_says_who_owns_wrote_and_verified_it():
    """Six months on, the reader needs who decided, not only what and why."""
    march = why(FIXTURE, "DEC-0001")
    assert (march["record"]["owner"], march["record"]["author"]) == ("sean", "human:sean")
    assert march["record"]["verified"] == [{"by": "human:dana", "at": "2026-03-05T15:00:00+00:00"}]
    (successor,) = march["superseded_by"]
    assert (successor["owner"], successor["author"]) == ("priya", "agent:capture")
    assert successor["verified"] == []
    text = "\n".join(lines(march))
    # sean wrote his own record, so he is named once.
    assert "owner sean, verified by dana on 2026-03-05" in lines(march)[1]
    assert "written by human:sean" not in text
    assert "date 2026-09-15, owner priya, written by agent:capture" in text

    september = why(FIXTURE, "DEC-0002")
    (predecessor,) = september["supersedes"]
    assert predecessor["owner"] == "sean"
    assert "owner priya, written by agent:capture" in lines(september)[1]
    shown = "\n".join(lines(september))
    supersedes = shown.split("Supersedes:", 1)[1].splitlines()[1]
    assert "owner sean, verified by dana" in supersedes and "written by" not in supersedes
    (convention,) = [link for link in september["linked"] if link["id"] == "CONV-0001"]
    assert convention["owner"] == "sean"
    assert any(line.startswith("  CONV-0001") and "owner sean" in line for line in lines(september))


def test_a_person_is_named_once_by_bare_name_whichever_side_carries_the_prefix():
    from ai_dlc.documentation.knowledge_why import _by

    entry = {"owner": "human:sean", "author": "human:sean", "verified": []}
    assert _by(entry) == ["owner sean"]
    entry = {"owner": "sean", "author": "agent:capture", "verified": []}
    assert _by(entry) == ["owner sean", "written by agent:capture"]


def test_linked_conventions_lessons_tickets_and_source_metadata():
    result = why(FIXTURE, "DEC-0002")
    assert {(link["id"], link["link"]) for link in result["linked"]} == {
        ("CONV-0001", "implements"),
        ("LES-0001", "codified_as"),
    }
    assert result["tickets"] == ["OPS-12"]
    (evidence,) = result["evidence"]
    assert evidence["speaker"] == "dana" and evidence["at"] == "00:12:31"
    assert evidence["source"]["id"] == "SRC-0002"
    assert evidence["source"]["date"] == "2026-09-15"


def test_a_kept_payload_is_present(bundle):
    (bundle / "transcripts").mkdir()
    (bundle / "transcripts/2026-09-15-retro.vtt").write_text("WEBVTT\n")
    source = bundle / "sources/SRC-0002.md"
    source.write_text(source.read_text().replace("status: expired", "status: processed"))
    assert why(bundle, "DEC-0002")["evidence"][0]["payload"] == "present"


def test_a_three_deep_chain_stays_within_the_output_budget(bundle):
    long = "word " * 2000
    for path in (bundle / "decisions").glob("*.md"):
        path.write_text(path.read_text() + long)
    third = (bundle / "decisions/DEC-0002.md").read_text()
    third = (
        third.replace("id: DEC-0002", "id: DEC-0003")
        .replace("aliases: [build-every-merge]", "aliases: [build-and-gate]")
        .replace("target: nightly-builds-only", "target: DEC-0002")
    )
    (bundle / "decisions/DEC-0003.md").write_text(third)
    middle = bundle / "decisions/DEC-0002.md"
    middle.write_text(
        middle.read_text()
        .replace("status: accepted", "status: superseded")
        .replace("valid_from: 2026-09-15", "valid_from: 2026-09-15\nvalid_to: 2026-10-01")
    )
    result = why(bundle, "DEC-0001")
    assert [entry["id"] for entry in result["superseded_by"]] == ["DEC-0002", "DEC-0003"]
    assert result["record"]["truncated"] is True
    tokens = len(json.dumps(result)) / 4
    assert tokens < 4000, tokens


def test_customer_records_are_shown_only_to_their_project(bundle):
    folder = bundle / "projects/alpha"
    folder.mkdir(parents=True)
    (folder / "LES-0009.md").write_text(
        "---\nid: LES-0009\ntype: lesson\nscope: project\nboundary: customer\nstatus: open\n"
        "date: 2026-09-20\nowner: sean\nsources:\n  - {resource: DEC-0002}\n"
        "links:\n  - {type: codified_as, target: DEC-0002}\n---\nAlpha detail\n"
    )
    team = why(bundle, "DEC-0002")
    assert "LES-0009" not in {link["id"] for link in team["linked"]}
    assert why(bundle, "LES-0009")["status"] == "not_found"
    alpha = why(bundle, "DEC-0002", project="alpha")
    assert "LES-0009" in {link["id"] for link in alpha["linked"]}


def test_unknown_id_exits_non_zero_with_did_you_mean():
    result = CliRunner().invoke(app, ["knowledge", "why", "nightly-build", "--root", str(FIXTURE)])
    assert result.exit_code == 1
    assert "did you mean nightly-builds-only" in result.output
    found = CliRunner().invoke(
        app, ["knowledge", "why", "DEC-0002", "--root", str(FIXTURE), "--json"]
    )
    assert found.exit_code == 0 and json.loads(found.output)["record"]["id"] == "DEC-0002"


def test_mcp_tool_shares_the_service(tmp_path):
    from ai_dlc.mcp_server import make_server

    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    shutil.copytree(FIXTURE, tmp_path / "records")
    server = make_server(tmp_path)
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert "knowledge_why" in names
    called = asyncio.run(
        server.call_tool("knowledge_why", {"id": "DEC-0002", "records": "records"})
    )
    assert QUOTE_SEPTEMBER in str(called)


def test_check_fails_a_derived_record_without_evidence(bundle):
    path = bundle / "decisions/DEC-0002.md"
    path.write_text(path.read_text().replace("    speaker: dana\n", ""))
    (failure,) = check_records(bundle)["failures"]
    assert failure["path"] == "decisions/DEC-0002.md" and "needs evidence" in failure["message"]


def test_a_refetchable_source_needs_no_quote_and_why_says_where_to_fetch(bundle):
    source = bundle / "sources/SRC-0002.md"
    source.write_text(
        source.read_text()
        .replace(
            "provider: zoom", "provider: jira\nurl: https://jira.example.invalid/browse/OPS-12"
        )
        .replace("transcripts/2026-09-15-retro.vtt", "https://jira.example.invalid/browse/OPS-12")
    )
    decision = bundle / "decisions/DEC-0002.md"
    text = decision.read_text()
    start = text.index("    quote:")
    decision.write_text(text[:start] + text[text.index("links:") :])
    assert check_records(bundle)["failures"] == []
    result = why(bundle, "DEC-0002")
    assert result["evidence"][0]["fetch"] == "https://jira.example.invalid/browse/OPS-12"
    assert "fetch from https://jira.example.invalid/browse/OPS-12" in "\n".join(lines(result))


def test_a_retracted_decision_shows_retracted_and_the_decision_retracting_it():
    """KAN-479: ``retracted_by`` is derived, as the index derives it; the record is unchanged."""
    original = (RETRACTS / "decisions/DEC-0001.md").read_text()

    result = why(RETRACTS, "git-is-the-system-of-record")

    assert result["record"]["id"] == "DEC-0001"
    assert result["record"]["status"] == "retracted"
    assert [entry["id"] for entry in result["retracted_by"]] == ["DEC-0002"]
    assert "never\ndecided" in result["retracted_by"][0]["reason"]
    assert result["retracts"] == [] and result["linked"] == []
    text = "\n".join(lines(result))
    assert "retracted, date 2026-11-10" in text
    assert "Retracted by:\n  DEC-0002  Retract DEC-0001, accepted by mistake" in text
    assert (RETRACTS / "decisions/DEC-0001.md").read_text() == original


def test_the_retracting_decision_names_what_it_retracts():
    result = why(RETRACTS, "DEC-0002")

    assert result["record"]["status"] == "accepted" and result["retracted_by"] == []
    assert [(entry["id"], entry["status"]) for entry in result["retracts"]] == [
        ("DEC-0001", "retracted")
    ]
    assert "Retracts:\n  DEC-0001" in "\n".join(lines(result))


def test_answers_without_a_retraction_do_not_mention_one():
    result = why(FIXTURE, "DEC-0002")

    assert result["retracts"] == [] and result["retracted_by"] == []
    assert "Retract" not in "\n".join(lines(result))


def test_a_proposed_retraction_changes_nothing(tmp_path):
    folder = tmp_path / "records"
    shutil.copytree(RETRACTS, folder)
    path = folder / "decisions/DEC-0002.md"
    path.write_text(path.read_text().replace("status: accepted", "status: proposed"))

    result = why(folder, "DEC-0001")

    assert result["record"]["status"] == "accepted" and result["retracted_by"] == []


# KAN-494: ticket keys and ids in any case; a Source answers with its decision.

TICKET_SOURCE = """---
id: {id}
type: source
scope: team
status: processed
date: 2026-10-29
owner: sean
sources:
  - {{resource: 'https://tracker.example.invalid/browse/{key}'}}
links: []
schema_version: 1
revision: "1"
provider: jira
title: Decide the freeze
observed_at: 2026-10-29T18:00:00+00:00
url: https://tracker.example.invalid/browse/{key}
---
Ruling: adopted.
"""

DERIVED = """---
id: {id}
type: decision
scope: team
status: {status}
date: {date}
owner: sean
author: agent:capture
sources:
  - {{id: {source}, resource: sources/{source}.md, hash: 'sha256:{hash}'}}
links:
  - {{type: derived_from, target: {source}}}
title: {title}
{extra}---
# {title}
"""


def _ticket_bundle(bundle: Path, source: str = "kan-241", key: str = "KAN-241") -> Path:
    (bundle / "sources" / f"{source}.md").write_text(TICKET_SOURCE.format(id=source, key=key))
    (bundle / "decisions/freeze.md").write_text(
        DERIVED.format(
            id="feature-freeze",
            status="accepted",
            date="2026-10-29",
            source=source,
            title="Freeze features until adoption",
            extra="",
            hash="2" * 64,
        )
    )
    (bundle / "decisions/old-freeze.md").write_text(
        DERIVED.format(
            id="old-freeze",
            status="superseded",
            date="2026-10-01",
            source=source,
            title="An earlier freeze",
            extra="valid_to: 2026-10-29\n",
            hash="3" * 64,
        )
    )
    return bundle


@pytest.mark.parametrize("name", ["KAN-241", "kan-241", "Kan-241"])
def test_knowledge_why_a_ticket_key_in_any_case_answers_with_the_decision_derived_from_it(
    bundle, name
):
    result = why(_ticket_bundle(bundle), name)
    assert result["status"] == "ok"
    assert result["record"]["id"] == "feature-freeze"
    assert (result["record"]["owner"], result["record"]["author"]) == ("sean", "agent:capture")
    assert result["resolved_from"]["id"] == "kan-241" and result["resolved_from"]["name"] == name
    assert [entry["id"] for entry in result["also_derived"]] == ["old-freeze"]
    text = "\n".join(lines(result))
    assert f"({name} is the source kan-241; the record derived from it:)" in text
    assert "owner sean, written by agent:capture" in text
    assert "Also derived from the same source:" in text and "old-freeze" in text


def test_knowledge_why_a_ticket_key_finds_its_source_by_url_when_the_id_differs(bundle):
    result = why(_ticket_bundle(bundle, source="jira-freeze", key="KAN-77"), "kan-77")
    assert result["record"]["id"] == "feature-freeze"
    assert result["resolved_from"]["id"] == "jira-freeze"


def test_knowledge_why_record_ids_match_in_any_case_and_need_no_redirect():
    result = why(FIXTURE, "dec-0002")
    assert result["record"]["id"] == "DEC-0002" and result["resolved_from"] is None
    assert why(FIXTURE, "NIGHTLY-BUILDS-ONLY")["record"]["id"] == "DEC-0001"


def test_knowledge_why_a_source_nothing_derives_from_is_still_shown(bundle):
    (bundle / "sources/kan-9.md").write_text(TICKET_SOURCE.format(id="kan-9", key="KAN-9"))
    result = why(bundle, "KAN-9")
    assert result["record"]["id"] == "kan-9" and result["resolved_from"] is None


def test_knowledge_why_cli_resolves_an_upper_case_ticket_key(bundle):
    found = CliRunner().invoke(
        app, ["knowledge", "why", "KAN-241", "--root", str(_ticket_bundle(bundle))]
    )
    assert found.exit_code == 0, found.output
    assert "feature-freeze  Freeze features until adoption" in found.output
