"""The knowledge-record contract: one format every knowledge repository pins.

A record is one markdown file: YAML frontmatter (the header validated here) and a
markdown body. Types are decision, convention, lesson, action, question and source;
``contracts/knowledge-record.schema.json`` is generated from :class:`KnowledgeRecord`.
This is the expand step: :mod:`ai_dlc.documentation.knowledge_notes` is unchanged and
still validates existing notes until the migration (KAN-452) and removal (KAN-453).

A knowledge repository pins :data:`FORMAT_VERSION` in its ``knowledge.toml``::

    [format]
    version = 1

Records are also Open Knowledge Format v0.2 documents: parseable YAML frontmatter
with a non-empty ``type`` (OKF types are open). ``links`` is an OKF extension key, and
``title`` and ``description`` feed an OKF ``index.md``.

A Source record carries work-copilot's source envelope in its frontmatter, with the
markdown body as the envelope ``body``; :func:`envelope` returns that envelope.
"""

from datetime import date as Day
from datetime import datetime
from typing import Any, Literal, cast

import yaml
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from ai_dlc.documentation.knowledge_notes import AUTHOR_PATTERN, Check, split

FORMAT_VERSION = 1
"""Version of the record format; knowledge repos pin it as ``[format] version``."""
ENVELOPE_VERSION = 1
"""``schema_version`` of the work-copilot source envelope carried by Source records."""

RecordType = Literal["decision", "convention", "lesson", "action", "question", "source"]
TYPES: tuple[str, ...] = ("decision", "convention", "lesson", "action", "question", "source")
PREFIXES = {
    "decision": "DEC",
    "convention": "CONV",
    "lesson": "LES",
    "action": "ACT",
    "question": "Q",
    "source": "SRC",
}
# None means the tracker owns the status values (actions).
STATUSES: dict[str, tuple[str, ...] | None] = {
    "decision": ("proposed", "accepted", "rejected", "superseded"),
    "convention": ("draft", "active", "retired"),
    "lesson": ("open", "codified"),
    "action": None,
    "question": ("open", "answered"),
    "source": ("raw", "processed", "expired"),
}
LINK_TYPES = ("belongs_to", "derived_from", "supersedes", "implements", "codified_as")
# Every header field name, in one place, in serialization order. KAN-471 may rename some
# for Open Knowledge Format v0.2 (review_by, source, source_hash, labels); change them here.
REQUIRED_FIELDS = ("id", "type", "scope", "status", "date", "owner", "source", "links")
OPTIONAL_FIELDS = (
    "title",
    "description",
    "boundary",
    "phase",
    "domain",
    "labels",
    "source_hash",
    "valid_from",
    "valid_to",
    "review_by",
    "confidence",
    "checks",
    "author",
    "aliases",
)
SOURCE_FIELDS = ("schema_version", "revision", "provider", "title", "observed_at")
SOURCE_ONLY = ("schema_version", "revision", "provider", "observed_at", "obligations", "url")
SLUG = r"[a-z0-9][a-z0-9-]*"
NUMBER = "[0-9][0-9][0-9][0-9]+"
ID_PATTERN = rf"^(?:{SLUG}|(?:DEC|CONV|LES|ACT|Q|SRC)-{NUMBER})$"
HASH_PATTERN = r"^[a-z0-9-]+:\S+$"


def _present(field: str) -> dict[str, Any]:
    return {"required": [field], "properties": {field: {"not": {"type": "null"}}}}


def _when_type(kind: str, then: dict[str, Any], otherwise: dict[str, Any] | None = None) -> dict:
    rule: dict[str, Any] = {
        "if": {"properties": {"type": {"const": kind}}, "required": ["type"]},
        "then": then,
    }
    if otherwise is not None:
        rule["else"] = otherwise
    return rule


def _conditions() -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for kind in TYPES:
        statuses = STATUSES[kind]
        status = {"enum": list(statuses)} if statuses else {"type": "string", "minLength": 1}
        numbered = rf"^(?:{SLUG}|{PREFIXES[kind]}-{NUMBER})$"
        rules.append(
            _when_type(kind, {"properties": {"status": status, "id": {"pattern": numbered}}})
        )
    rules.append(_when_type("decision", {}, {"not": _present("checks")}))
    rules.append(
        _when_type(
            "source",
            {"required": list(SOURCE_FIELDS)},
            {"not": {"anyOf": [_present(field) for field in SOURCE_ONLY]}},
        )
    )
    rules.append(
        {
            "if": {
                "properties": {"type": {"const": "decision"}, "status": {"const": "superseded"}},
                "required": ["type", "status"],
            },
            "then": _present("valid_to"),
        }
    )
    derived = {"properties": {"type": {"const": "derived_from"}}, "required": ["type"]}
    rules.append(
        {
            "if": {"properties": {"links": {"contains": derived}}, "required": ["links"]},
            "then": _present("source_hash"),
        }
    )
    project = {"properties": {"scope": {"const": "project"}}, "required": ["scope"]}
    customer = {"properties": {"boundary": {"const": "customer"}}, "required": ["boundary"]}
    team = {"properties": {"scope": {"const": "team"}}, "required": ["scope"]}
    rules.append({"if": _present("boundary"), "then": project})
    rules.append({"if": _present("phase"), "then": customer})
    rules.append({"if": _present("domain"), "then": team})
    return rules


class Link(BaseModel):
    """A typed edge to another record, ticket, document or URL."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["belongs_to", "derived_from", "supersedes", "implements", "codified_as"]
    target: str = Field(min_length=1, description="record id, alias, ticket key, path or URL")


class Obligation(BaseModel):
    """An obligation candidate in a source envelope, as work-copilot ingests it."""

    model_config = ConfigDict(extra="forbid")
    intent_key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: Literal["candidate", "open", "waiting", "resolved", "dismissed"] | None = None


class KnowledgeRecord(BaseModel):
    """Frontmatter of one knowledge record.

    Required: ``id``, ``type``, ``scope``, ``status``, ``date``, ``owner``, ``source`` and
    ``links``; :data:`REQUIRED_FIELDS` and :data:`OPTIONAL_FIELDS` list every name. A draft's ``id`` is a slug; the numbered id (``DEC-0001`` and so on) is
    assigned at merge, and the slug is then kept in ``aliases``. Source records also
    carry the work-copilot envelope fields. Unknown keys are refused.
    """

    model_config = ConfigDict(
        extra="forbid",
        title="Knowledge record frontmatter",
        json_schema_extra=cast(
            "dict[str, Any]",
            {"allOf": _conditions(), "x-format-version": FORMAT_VERSION},
        ),
    )
    id: str = Field(pattern=ID_PATTERN, description="draft slug, or PREFIX-NNNN after merge")
    type: RecordType
    scope: Literal["personal", "project", "team"]
    status: str = Field(min_length=1, description="allowed values depend on type")
    date: Day
    owner: str = Field(min_length=1)
    source: str = Field(min_length=1, description="where it came from: record id, path or URL")
    links: list[Link]
    title: str | None = Field(default=None, min_length=1, description="index title")
    description: str | None = Field(default=None, min_length=1, description="one index line")
    boundary: Literal["customer"] | None = None
    phase: Literal["discovery", "scoping", "design", "build", "handoff"] | None = None
    domain: Literal["sdlc", "tooling", "integration", "harness"] | None = None
    labels: list[str] | None = None
    source_hash: str | None = Field(default=None, pattern=HASH_PATTERN)
    valid_from: Day | None = None
    valid_to: Day | None = None
    review_by: Day | None = None
    confidence: Literal["low", "medium", "high"] | None = None
    checks: list[Check] | None = None
    author: str | None = Field(default=None, pattern=AUTHOR_PATTERN)
    aliases: list[str] | None = None
    schema_version: Literal[1] | None = Field(default=None, description="source envelope version")
    revision: str | None = Field(default=None, min_length=1)
    provider: str | None = Field(default=None, min_length=1)
    observed_at: AwareDatetime | None = None
    obligations: list[Obligation] | None = None
    url: str | None = None

    @model_validator(mode="after")
    def _rules(self) -> "KnowledgeRecord":
        problems = record_rule_errors(self)
        if problems:
            raise ValueError("; ".join(problems))
        return self


def record_rule_errors(record: KnowledgeRecord) -> list[str]:
    """Cross-field rules, one message each; shape errors are Pydantic's."""
    found: list[str] = []
    kind = record.type
    prefix = record.id.split("-", 1)[0]
    if record.id[:1].isupper() and prefix != PREFIXES[kind]:
        found.append(f"id: a numbered {kind} id starts with {PREFIXES[kind]}-")
    statuses = STATUSES[kind]
    if statuses and record.status not in statuses:
        found.append(f"status: a {kind} status is one of {', '.join(statuses)}")
    if record.checks is not None and kind != "decision":
        found.append("checks: only decisions carry checks")
    if kind == "decision" and record.status == "superseded" and record.valid_to is None:
        found.append("valid_to: a superseded decision needs valid_to")
    if any(link.type == "derived_from" for link in record.links) and not record.source_hash:
        found.append("source_hash: required on a record with a derived_from link")
    if record.boundary is not None and record.scope != "project":
        found.append("boundary: only a project-scoped record has a boundary")
    if record.phase is not None and record.boundary != "customer":
        found.append("phase: allowed only with boundary: customer")
    if record.domain is not None and record.scope != "team":
        found.append("domain: allowed only with scope: team")
    if record.valid_from and record.valid_to and record.valid_to < record.valid_from:
        found.append("valid_to: precedes valid_from")
    if kind == "source":
        missing = [field for field in SOURCE_FIELDS if getattr(record, field) is None]
        if missing:
            found.append("source: a source record needs " + ", ".join(missing))
    else:
        extra = [field for field in SOURCE_ONLY if getattr(record, field) is not None]
        if extra:
            found.append(f"{extra[0]}: only source records carry " + ", ".join(extra))
    ids = [check.id for check in record.checks or []]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        found.append("checks: check ids must be unique: " + ", ".join(duplicates))
    return found


class SourceEnvelope(BaseModel):
    """work-copilot's source envelope (``Store.ingest``) with a schema version."""

    model_config = ConfigDict(extra="forbid", title="Source envelope")
    schema_version: Literal[1] = ENVELOPE_VERSION
    id: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str
    observed_at: AwareDatetime
    obligations: list[Obligation] = Field(default_factory=list)
    url: str | None = None


def schema() -> dict:
    return KnowledgeRecord.model_json_schema()


def errors(data: dict) -> list[str]:
    """Problems in a frontmatter mapping, as ``field: message`` lines."""
    try:
        KnowledgeRecord.model_validate(data)
    except ValidationError as exc:
        found = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"])
            message = error["msg"].removeprefix("Value error, ")
            if location:
                found.append(f"{location.replace('assert_', 'assert')}: {message}")
            else:
                found.extend(message.split("; "))
        return found
    return []


def parse(text: str) -> tuple[KnowledgeRecord, str]:
    """Return the validated header and the markdown body of a record file."""
    data, _raw, body = split(text)
    if data is None:
        raise ValueError("record has no frontmatter")
    problems = errors(data)
    if problems:
        raise ValueError("; ".join(problems))
    return KnowledgeRecord.model_validate(data), body


def render(record: KnowledgeRecord, body: str = "") -> str:
    """Serialize a record as YAML frontmatter plus markdown body, omitting empty fields."""
    data = record.model_dump(mode="json", by_alias=True, exclude_none=True)
    front = yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True)
    return "---\n" + front + "---\n" + body


def envelope(record: KnowledgeRecord, body: str) -> SourceEnvelope:
    """The work-copilot source envelope a Source record carries."""
    if record.type != "source":
        raise ValueError("only source records carry an envelope")
    observed = cast("datetime", record.observed_at)
    return SourceEnvelope(
        schema_version=ENVELOPE_VERSION,
        id=record.id,
        revision=cast("str", record.revision),
        provider=cast("str", record.provider),
        title=cast("str", record.title),
        body=body,
        observed_at=observed,
        obligations=record.obligations or [],
        url=record.url,
    )


def pin_errors(knowledge_toml: dict) -> list[str]:
    """Check a parsed ``knowledge.toml`` pins a record format this ai-dlc reads."""
    table = knowledge_toml.get("format")
    version = table.get("version") if isinstance(table, dict) else None
    if version is None:
        return [f"format.version: pin the record format, e.g. version = {FORMAT_VERSION}"]
    if isinstance(version, bool) or version != FORMAT_VERSION:
        return [f"format.version: {version!r} is not supported; this ai-dlc reads {FORMAT_VERSION}"]
    return []
