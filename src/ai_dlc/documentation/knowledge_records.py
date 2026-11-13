"""The knowledge-record contract: one format every knowledge repository pins.

A record is one markdown file: YAML frontmatter (the header validated here) and a
markdown body. Types are decision, convention, lesson, action, question and source;
``contracts/knowledge-record.schema.json`` is generated from :class:`KnowledgeRecord`.
This is the expand step: :mod:`ai_dlc.documentation.knowledge_notes` is unchanged and
still validates existing notes until the migration (KAN-452) and removal (KAN-453).

A knowledge repository pins :data:`FORMAT_VERSION` in its ``knowledge.toml``::

    [format]
    version = 1

Records are Open Knowledge Format v0.2 documents (ADR 0004, KAN-471): parseable YAML
frontmatter with a non-empty ``type`` (OKF types are open). ``title``, ``description``,
``tags``, ``sources``, ``verified``, ``stale_after`` and ``status`` use OKF's names;
``status`` keeps the record values and :func:`okf_status` maps them to OKF's. ``links``
and the other keys are OKF extension keys.

A Source record carries work-copilot's source envelope in its frontmatter, with the
markdown body as the envelope ``body``; :func:`envelope` returns that envelope.
"""

import re
from datetime import date as Day
from datetime import datetime
from typing import Any, Literal, cast

import yaml
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

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
# Every header field name, in one place, in serialization order (KAN-471: OKF v0.2 names).
REQUIRED_FIELDS = ("id", "type", "scope", "status", "date", "owner", "sources", "links")
OPTIONAL_FIELDS = (
    "title",
    "description",
    "tags",
    "label",
    "boundary",
    "project",
    "phase",
    "domain",
    "valid_from",
    "valid_to",
    "stale_after",
    "verified",
    "confidence",
    "checks",
    "author",
    "aliases",
)
# Fixed export of each record status to OKF's draft | stable | deprecated (OKF section 5.4).
# Actions carry the tracker's status, which exports as stable (OKF's default).
OKF_STATUS: dict[str, dict[str, str]] = {
    "decision": {
        "proposed": "draft",
        "accepted": "stable",
        "rejected": "deprecated",
        "superseded": "deprecated",
    },
    "convention": {"draft": "draft", "active": "stable", "retired": "deprecated"},
    "lesson": {"open": "stable", "codified": "stable"},
    "action": {},
    "question": {"open": "draft", "answered": "stable"},
    "source": {"raw": "draft", "processed": "stable", "expired": "deprecated"},
}
SOURCE_FIELDS = ("schema_version", "revision", "provider", "title", "observed_at")
SOURCE_ONLY = (
    "schema_version",
    "revision",
    "provider",
    "observed_at",
    "obligations",
    "url",
    "participants",
)
SLUG = r"[a-z0-9][a-z0-9-]*"
NUMBER = "[0-9][0-9][0-9][0-9]+"
ID_PATTERN = rf"^(?:{SLUG}|(?:DEC|CONV|LES|ACT|Q|SRC)-{NUMBER})$"
HASH_PATTERN = r"^[a-z0-9-]+:\S+$"
# A sha256 hash is 64 lowercase hex characters, so duplicate sources can be found.
SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"
ACTOR_PATTERN = r"^(?:(?:human|process):\S+|[^\s:/]+/\S+)$"
# Where in its source a quote was said: an offset (HH:MM:SS) or a time with an offset.
AT_PATTERN = r"^(?:[0-9]{1,3}:[0-5][0-9]:[0-5][0-9]|[0-9]{4}-[0-9]{2}-[0-9]{2}T\S+)$"
QUOTE_LIMIT = 500
"""Most characters of one evidence quote; a longer passage is cited in pieces."""


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
    # Python also checks the hashed entry matches the link target; JSON Schema cannot.
    derived = {"properties": {"type": {"const": "derived_from"}}, "required": ["type"]}
    hashed = {"required": ["hash"], "properties": {"hash": {"type": "string"}}}
    rules.append(
        {
            "if": {"properties": {"links": {"contains": derived}}, "required": ["links"]},
            "then": {"properties": {"sources": {"contains": hashed}}},
        }
    )
    project = {"properties": {"scope": {"const": "project"}}, "required": ["scope"]}
    customer = {"properties": {"boundary": {"const": "customer"}}, "required": ["boundary"]}
    team = {"properties": {"scope": {"const": "team"}}, "required": ["scope"]}
    rules.append({"if": _present("boundary"), "then": project})
    rules.append({"if": _present("phase"), "then": customer})
    rules.append({"if": _present("project"), "then": customer})
    rules.append({"if": _present("domain"), "then": team})
    return rules


class Link(BaseModel):
    """A typed edge to another record, ticket, document or URL."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["belongs_to", "derived_from", "supersedes", "implements", "codified_as"]
    target: str = Field(min_length=1, description="record id, alias, ticket key, path or URL")


class SourceRef(BaseModel):
    """One OKF ``sources`` entry (OKF section 5.1) with an optional content hash."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "if": {
                "properties": {"hash": {"type": "string", "pattern": "^sha256:"}},
                "required": ["hash"],
            },
            "then": {"properties": {"hash": {"pattern": SHA256_PATTERN}}},
        },
    )
    id: str | None = Field(default=None, min_length=1, description="record id or citation key")
    resource: str = Field(min_length=1, description="URL, path or record id it came from")
    hash: str | None = Field(default=None, pattern=HASH_PATTERN)
    title: str | None = Field(default=None, min_length=1)
    author: str | None = Field(default=None, min_length=1)
    last_modified: AwareDatetime | None = None
    # Evidence (KAN-466): source payloads expire, so the words stay in the record.
    quote: str | None = Field(
        default=None, min_length=1, max_length=QUOTE_LIMIT, description="verbatim evidence"
    )
    speaker: str | None = Field(default=None, min_length=1, description="who said the quote")
    at: str | None = Field(
        default=None, pattern=AT_PATTERN, description="HH:MM:SS offset or time in the source"
    )
    permalink: str | None = Field(default=None, min_length=1, description="link to the quote")

    @field_validator("hash")
    @classmethod
    def _sha256(cls, value: str | None) -> str | None:
        if value and value.startswith("sha256:") and not re.match(SHA256_PATTERN, value):
            raise ValueError("a sha256 hash is 64 lowercase hex characters")
        return value


class Verification(BaseModel):
    """One OKF ``verified`` event (OKF section 5.2)."""

    model_config = ConfigDict(extra="forbid")
    by: str = Field(pattern=ACTOR_PATTERN, description="human:<id>, process:<id> or tool/version")
    at: AwareDatetime


class Obligation(BaseModel):
    """An obligation candidate in a source envelope, as work-copilot ingests it."""

    model_config = ConfigDict(extra="forbid")
    intent_key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: Literal["candidate", "open", "waiting", "resolved", "dismissed"] | None = None


class KnowledgeRecord(BaseModel):
    """Frontmatter of one knowledge record.

    :data:`REQUIRED_FIELDS` and :data:`OPTIONAL_FIELDS` list every name. A draft's ``id``
    is a slug; the numbered id (``DEC-0001`` and so on) is assigned at merge, and the
    slug is then kept in ``aliases``. Source records also carry the work-copilot
    envelope fields. Unknown keys are refused.
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
    sources: list[SourceRef] = Field(min_length=1, description="what it came from (OKF 5.1)")
    links: list[Link]
    title: str | None = Field(default=None, min_length=1, description="index title")
    description: str | None = Field(default=None, min_length=1, description="one index line")
    tags: list[str] | None = None
    label: str | None = Field(default=None, min_length=1, description="internal | confidential")
    boundary: Literal["customer"] | None = None
    project: str | None = Field(
        default=None, pattern=rf"^{SLUG}$", description="customer project (boundary: customer)"
    )
    phase: Literal["discovery", "scoping", "design", "build", "handoff"] | None = None
    domain: Literal["sdlc", "tooling", "integration", "harness"] | None = None
    valid_from: Day | None = None
    valid_to: Day | None = None
    stale_after: AwareDatetime | None = None
    verified: list[Verification] | None = Field(
        default=None, description="a bare mapping is read as a one-element list (OKF 5.2)"
    )
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
    participants: list[str] | None = Field(default=None, description="who took part (sources)")

    @field_validator("verified", mode="before")
    @classmethod
    def _one_verifier(cls, value: object) -> object:
        # OKF 5.2: a bare mapping is a one-element list.
        return [value] if isinstance(value, dict) else value

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
    for link in record.links:
        if link.type != "derived_from":
            continue
        entries = [e for e in record.sources if link.target in (e.id, e.resource)]
        if not any(entry.hash for entry in entries):
            found.append(
                f"sources: a derived_from link to {link.target} needs a sources entry "
                "with that id or resource and a hash"
            )
    if record.boundary is not None and record.scope != "project":
        found.append("boundary: only a project-scoped record has a boundary")
    if record.project is not None and record.boundary != "customer":
        found.append("project: allowed only with boundary: customer")
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
    published = KnowledgeRecord.model_json_schema()
    # OKF 5.2 also allows one bare verification mapping; Python wraps it in a list.
    published["properties"]["verified"]["anyOf"].insert(1, {"$ref": "#/$defs/Verification"})
    return published


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


# Sources whose raw payload expires (KAN-458): captured into the inbox, or a
# transcript, chat or meeting. Jira, Confluence and ADR sources stay re-fetchable.
EXPIRING_DIRECTORIES = ("inbox/", "processed/")
EXPIRING_KINDS = frozenset(
    {"transcript", "chat", "meeting", "thread", "zoom", "google-meet", "meet", "symphony"}
)


def payload_expires(record: KnowledgeRecord) -> bool:
    """Whether a Source record's payload expires, so citing records must quote it.

    It does when a ``sources`` resource lies under ``inbox/`` or ``processed/``, or
    when its provider or a tag names a transcript, chat or meeting kind.
    """
    if record.type != "source":
        return False
    if any(entry.resource.startswith(EXPIRING_DIRECTORIES) for entry in record.sources):
        return True
    kinds = {*(record.tags or ()), *([record.provider] if record.provider else [])}
    return bool({kind.casefold() for kind in kinds} & EXPIRING_KINDS)


def okf_status(record: KnowledgeRecord) -> str:
    """The OKF v0.2 lifecycle status (draft | stable | deprecated) for a record."""
    return OKF_STATUS[record.type].get(record.status, "stable")


def pin_errors(knowledge_toml: dict) -> list[str]:
    """Check a parsed ``knowledge.toml`` pins a record format this ai-dlc reads."""
    table = knowledge_toml.get("format")
    version = table.get("version") if isinstance(table, dict) else None
    if version is None:
        return [f"format.version: pin the record format, e.g. version = {FORMAT_VERSION}"]
    if isinstance(version, bool) or version != FORMAT_VERSION:
        return [f"format.version: {version!r} is not supported; this ai-dlc reads {FORMAT_VERSION}"]
    return []
