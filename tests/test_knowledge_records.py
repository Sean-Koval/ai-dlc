"""The knowledge-record contract: header rules, generated schema, templates and scenarios."""

import json
import tomllib
from pathlib import Path

import jsonschema
import pytest

from ai_dlc.documentation import knowledge_records as records
from ai_dlc.documentation.knowledge_notes import split
from ai_dlc.files import assets

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/knowledge_records"
SCHEMA = ROOT / "contracts/knowledge-record.schema.json"
VERSIONS = ROOT / "contracts/knowledge-record.versions.toml"
REQUIRED = set(records.REQUIRED_FIELDS)
# JSON Schema cannot compare dates or demand a UTC offset; Python enforces these.
PYTHON_ONLY = {"valid_to first", "naive observed_at", "naive stale_after", "hash on another source"}
HASH = "sha256:" + "0" * 64
DERIVED = [{"type": "derived_from", "target": "SRC-0001"}]
STATUS = {
    "decision": "accepted",
    "convention": "active",
    "lesson": "open",
    "action": "In Progress",
    "question": "answered",
    "source": "raw",
}
SOURCE = {
    "schema_version": 1,
    "revision": "1",
    "provider": "zoom",
    "title": "Call",
    "observed_at": "2026-11-10T15:00:00-05:00",
}


def header(kind="decision", **changes):
    data = {
        "id": "a-slug",
        "type": kind,
        "scope": "team",
        "status": STATUS[kind],
        "date": "2026-11-10",
        "owner": "sean",
        "sources": [{"resource": "https://example.invalid/pr/1"}],
        "links": [],
        **(SOURCE if kind == "source" else {}),
    }
    data.update(changes)
    return {key: value for key, value in data.items() if value is not ...}


def validator():
    return jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text()))


def fixtures():
    return sorted(FIXTURES.rglob("*.md"))


def test_published_schema_is_generated():
    published = json.loads(SCHEMA.read_text())
    assert published == records.schema()
    assert published["x-format-version"] == records.FORMAT_VERSION
    assert set(published["required"]) == REQUIRED
    assert "{" * 2 not in SCHEMA.read_text()


@pytest.mark.parametrize("path", fixtures(), ids=lambda path: path.relative_to(FIXTURES).as_posix())
def test_scenario_fixtures_validate(path):
    data, _raw, _body = split(path.read_text())
    assert data is not None
    assert REQUIRED <= set(data)
    assert records.errors(data) == []
    assert list(validator().iter_errors(json.loads(json.dumps(data, default=str)))) == []


def test_every_spec_scenario_and_type_is_covered():
    scenarios = {path.parent.name for path in fixtures()}
    assert len(scenarios) == 5
    kinds = {split(path.read_text())[0]["type"] for path in fixtures()}  # type: ignore[index]
    assert kinds == set(records.TYPES) - {"question"}


@pytest.mark.parametrize("kind", records.TYPES)
def test_one_valid_record_per_type(kind):
    data = header(kind)
    assert records.errors(data) == []
    assert list(validator().iter_errors(data)) == []


INVALID = [
    ("missing owner", header(owner=...), "owner: Field required"),
    ("missing sources", header(sources=...), "sources: Field required"),
    ("unknown type", header(type="runbook"), "type: Input should be"),
    ("unknown scope", header(scope="engagement"), "scope: Input should be"),
    ("decision status", header(status="draft"), "status: a decision status is one of"),
    ("convention status", header("convention", status="accepted"), "a convention status"),
    ("lesson status", header("lesson", status="active"), "a lesson status"),
    ("question status", header("question", status="closed"), "a question status"),
    ("source status", header("source", status="open"), "a source status"),
    ("bad link type", header(links=[{"type": "relates", "target": "x"}]), "links.0.type"),
    (
        "derived without hash",
        header(links=DERIVED, sources=[{"id": "SRC-0001", "resource": "s.md"}]),
        "sources: a derived_from link to SRC-0001 needs a sources entry",
    ),
    (
        "hash on another source",
        header(links=DERIVED, sources=[{"id": "SRC-0002", "resource": "s.md", "hash": HASH}]),
        "a derived_from link to SRC-0001 needs",
    ),
    ("no sources", header(sources=[]), "sources: List should have at least 1 item"),
    ("source without resource", header(sources=[{"id": "x"}]), "sources.0.resource"),
    (
        "short sha256",
        header(sources=[{"resource": "s.md", "hash": "sha256:3f1c9a"}]),
        "sources.0.hash: a sha256 hash is 64 lowercase hex characters",
    ),
    (
        "bad verifier",
        header(verified=[{"by": "sean", "at": "2026-11-10T09:00:00Z"}]),
        "verified.0.by: String should match",
    ),
    ("naive stale_after", header(stale_after="2027-01-01T00:00:00"), "stale_after"),
    ("old review_by", header(review_by="2027-01-01"), "review_by: Extra inputs"),
    ("old source", header(source="SRC-0001"), "source: Extra inputs"),
    ("old labels", header(labels=["internal"]), "labels: Extra inputs"),
    ("phase without boundary", header(scope="project", phase="build"), "phase: allowed only"),
    ("boundary outside project", header(boundary="customer"), "boundary: only a project"),
    ("domain outside team", header(scope="personal", domain="sdlc"), "domain: allowed only"),
    (
        "checks on a lesson",
        header("lesson", checks=[{"id": "c", "assert": {"never": {}}}]),
        "checks: only decisions",
    ),
    ("superseded without valid_to", header(status="superseded"), "a superseded decision needs"),
    (
        "valid_to first",
        header(valid_from="2026-11-10", valid_to="2026-11-01"),
        "valid_to: precedes",
    ),
    ("wrong numbered prefix", header(id="LES-0001"), "id: a numbered decision id starts with DEC-"),
    ("bad id", header(id="Not A Slug"), "id: String should match"),
    ("source missing envelope", header("source", provider=...), "a source record needs provider"),
    ("envelope on a decision", header(provider="zoom"), "provider: only source records"),
    ("source without title", header("source", title=...), "a source record needs title"),
    ("naive observed_at", header("source", observed_at="2026-11-10T15:00:00"), "observed_at"),
    (
        "obligation without intent",
        header("source", obligations=[{"title": "x"}]),
        "obligations.0.intent_key",
    ),
    ("unknown key", header(kind_of="x"), "kind_of: Extra inputs are not permitted"),
    ("bad author", header(author="sean"), "author: String should match"),
]


@pytest.mark.parametrize(("name", "data", "message"), INVALID, ids=[c[0] for c in INVALID])
def test_each_rule_fails_with_a_clear_message(name, data, message):
    found = records.errors(data)
    assert any(message in line for line in found), found
    if name not in PYTHON_ONLY:
        assert list(validator().iter_errors(json.loads(json.dumps(data)))), "schema accepted it"


def test_field_names_live_in_one_place():
    envelope = {"schema_version", "revision", "provider", "observed_at", "obligations", "url"}
    envelope |= {"participants"}
    names = set(records.REQUIRED_FIELDS) | set(records.OPTIONAL_FIELDS) | envelope
    assert names == set(records.KnowledgeRecord.model_fields)


@pytest.mark.parametrize(
    "path",
    [*fixtures(), *(assets("agents") / "templates/knowledge").glob("*.md")],
    ids=lambda path: path.name,
)
def test_records_are_okf_documents(path):
    """OKF v0.2 section 11: YAML frontmatter, a non-empty string type, no reserved name."""
    data, _raw, _body = split(path.read_text())
    assert data is not None
    assert isinstance(data["type"], str) and data["type"]
    assert path.name not in {"index.md", "log.md"}


def test_okf_fields_and_status_export():
    data = header(
        "lesson",
        title="T",
        description="D",
        tags=["ci"],
        label="confidential",
        stale_after="2027-01-01T00:00:00Z",
        verified={"by": "human:sean", "at": "2026-11-10T09:00:00Z"},
    )
    assert records.errors(data) == []
    record = records.KnowledgeRecord.model_validate(data)
    assert record.verified is not None and len(record.verified) == 1
    assert list(validator().iter_errors(data)) == []
    assert {"title", "description", "tags", "sources", "verified", "stale_after"} <= set(
        records.OPTIONAL_FIELDS + records.REQUIRED_FIELDS
    )
    for kind, statuses in records.STATUSES.items():
        assert set(records.OKF_STATUS[kind]) == set(statuses or ())
    exported = {
        (kind, status): records.okf_status(
            records.KnowledgeRecord.model_validate(header(kind, status=status))
        )
        for kind in records.TYPES
        for status in (records.STATUSES[kind] or ("In Progress",))
        if not (kind == "decision" and status == "superseded")
    }
    assert set(exported.values()) <= {"draft", "stable", "deprecated"}
    assert exported["decision", "rejected"] == "deprecated"
    assert exported["convention", "draft"] == "draft"
    assert exported["action", "In Progress"] == "stable"


def test_title_and_description_are_optional_on_every_type():
    data = header(title="Releases ship on Thursdays", description="Weekly release day.")
    assert records.errors(data) == []
    assert records.errors(header(description="")) == [
        "description: String should have at least 1 character"
    ]


@pytest.mark.parametrize("kind", records.TYPES)
def test_templates_have_the_header_and_validate_once_filled(kind):
    template = assets("agents") / "templates/knowledge" / f"{kind}.md"
    text = template.read_text()
    assert "{" * 2 not in text
    filled = text.replace("YYYY-MM-DDTHH:MM:SS", "2026-11-10T09:00:00").replace(
        "YYYY-MM-DD", "2026-11-10"
    )
    data, _raw, body = split(filled)
    assert data is not None and data["type"] == kind
    assert REQUIRED <= set(data)
    assert records.errors(data) == []
    assert body.strip()


def test_parse_render_round_trip_and_envelope():
    text = (FIXTURES / "1-meeting/source.md").read_text()
    record, body = records.parse(text)
    again, again_body = records.parse(records.render(record, body))
    assert again == record and again_body == body
    envelope = records.envelope(record, body)
    assert envelope.schema_version == records.ENVELOPE_VERSION
    assert envelope.model_dump(mode="json")["obligations"][0]["intent_key"] == (
        "share-release-notes"
    )
    with pytest.raises(ValueError, match="only source records"):
        records.envelope(records.parse((FIXTURES / "1-meeting/action.md").read_text())[0], "")
    with pytest.raises(ValueError, match="no frontmatter"):
        records.parse("just text")


def test_format_version_publishes_this_schema():
    registry = tomllib.loads(VERSIONS.read_text())
    assert records.version_errors(registry) == []
    published = registry["versions"][str(records.FORMAT_VERSION)]["sha256"]
    assert records.schema_sha256(json.loads(SCHEMA.read_text())) == published


def test_a_schema_change_without_a_version_bump_fails(monkeypatch):
    registry = tomllib.loads(VERSIONS.read_text())
    changed = {**records.schema(), "description": "a new field"}
    monkeypatch.setattr(records, "schema", lambda: changed)
    assert "bump FORMAT_VERSION" in records.version_errors(registry)[0]
    bumped = records.FORMAT_VERSION + 1
    registry["versions"][str(bumped)] = {"sha256": records.schema_sha256(changed)}
    monkeypatch.setattr(records, "FORMAT_VERSION", bumped)
    assert records.version_errors(registry) == []
    # Moving the version alone, without publishing it, also fails.
    del registry["versions"][str(bumped)]
    assert "not the newest" in " ".join(records.version_errors(registry))


def test_a_superseded_schema_cannot_be_republished(monkeypatch):
    registry = tomllib.loads(VERSIONS.read_text())
    old = registry["versions"]["1"]["superseded"][0]
    registry["versions"]["2"] = {"sha256": records.schema_sha256(), "superseded": []}
    registry["versions"]["1"]["sha256"] = old
    monkeypatch.setattr(records, "FORMAT_VERSION", 2)
    assert records.version_errors(registry) == []
    registry["versions"]["1"]["superseded"].append(records.schema_sha256())
    assert "matches published version 1" in records.version_errors(registry)[0]


def test_a_published_hash_cannot_be_edited_in_place():
    base = tomllib.loads(VERSIONS.read_text())
    head = tomllib.loads(VERSIONS.read_text())
    assert records.append_errors(base, head) == []
    head["versions"]["1"]["sha256"] = "0" * 64
    assert "cannot change" in records.append_errors(base, head)[0]
    head = tomllib.loads(VERSIONS.read_text())
    head["versions"]["1"]["superseded"] = head["versions"]["1"]["superseded"][1:]
    assert "never removed" in records.append_errors(base, head)[0]
    del head["versions"]["1"]
    assert "cannot be removed" in records.append_errors(base, head)[0]


def test_a_new_version_and_a_longer_superseded_list_append():
    base = tomllib.loads(VERSIONS.read_text())
    head = tomllib.loads(VERSIONS.read_text())
    head["versions"]["1"]["superseded"].append("1" * 64)
    head["versions"]["2"] = {"sha256": "2" * 64}
    assert records.append_errors(base, head) == []


def test_format_pin():
    assert records.pin_errors({"format": {"version": records.FORMAT_VERSION}}) == []
    assert "pin the record format" in records.pin_errors({})[0]
    assert "is not supported" in records.pin_errors({"format": {"version": 99}})[0]
