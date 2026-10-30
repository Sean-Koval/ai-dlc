"""The knowledge-note frontmatter shared by learnings and decision records.

One schema covers authored and derived notes (``contracts/knowledge-note.schema.json``).
ai-dlc validates shape only: a decision's ``checks:`` entries use flightdeck's
``flightdeck.spec/v1`` grammar and are evaluated by flightdeck, never here.
"""

import re
from datetime import date
from typing import Any, Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

MAX_NOTE_BYTES = 64 * 1024
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
KINDS = ("learning", "decision", "runbook", "note")
ID_PATTERN = r"^(learning|decision|runbook|note)/[a-z0-9][a-z0-9._-]*$"
AUTHOR_PATTERN = r"^(human|agent):\S+$"

# Learnings and decisions need these conditional rules in the published JSON schema too.
_CONDITIONS: list[dict[str, Any]] = [
    {
        "if": {"properties": {"kind": {"const": "learning"}}, "required": ["kind"]},
        "then": {"required": ["sources"], "properties": {"sources": {"minItems": 1}}},
    },
    {
        "if": {"properties": {"kind": {"const": "decision"}}, "required": ["kind"]},
        "then": {"required": ["status"]},
        "else": {"not": {"anyOf": [{"required": ["status"]}, {"required": ["checks"]}]}},
    },
]


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    uri: str = Field(min_length=1)
    hash: str = Field(pattern=r"^[a-z0-9-]+:\S+$")


class Check(BaseModel):
    """One ADR check: a ``flightdeck.spec/v1`` spec without its header.

    Only the shape is checked. Unknown keys are kept because the grammar is additive.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    assert_: dict[str, Any] = Field(
        alias="assert", json_schema_extra={"minProperties": 1, "maxProperties": 1}
    )
    scope: Literal["turn", "job", "session"] | None = None
    harness: str | None = None
    applies_when: dict[str, Any] | None = None
    severity: Literal["warn", "fail"] | None = None

    @field_validator("assert_")
    @classmethod
    def _one_operator(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) != 1:
            raise ValueError("assert holds exactly one flightdeck.spec/v1 operator")
        return value


class KnowledgeNote(BaseModel):
    """Frontmatter of a learning, decision, runbook or note.

    ``work`` and ``repository`` are kept for learnings written before this schema.
    Extra keys are allowed and preserved so neighbouring tools can extend notes additively.
    """

    model_config = ConfigDict(
        extra="allow",
        title="Knowledge note frontmatter",
        json_schema_extra=cast("dict[str, Any]", {"allOf": _CONDITIONS}),
    )
    id: str = Field(pattern=ID_PATTERN)
    kind: Literal["learning", "decision", "runbook", "note"]
    scope: Literal["personal", "project", "team"]
    label: str = Field(min_length=1, description="internal | confidential; free text is recorded")
    sources: list[Source] = Field(default_factory=list)
    author: str = Field(pattern=AUTHOR_PATTERN)
    confidence: Literal["low", "medium", "high"] = "medium"
    valid_from: date
    valid_to: date | None = None
    review_by: date | None = None
    supersedes: list[str] = Field(default_factory=list)
    status: Literal["proposed", "accepted", "superseded", "rejected"] | None = None
    checks: list[Check] | None = None
    work: str | None = None
    repository: str | None = None

    @model_validator(mode="after")
    def _kind_rules(self) -> "KnowledgeNote":
        if not self.id.startswith(self.kind + "/"):
            raise ValueError(f"id must start with {self.kind}/")
        if self.kind == "learning" and not self.sources:
            raise ValueError("a learning needs at least one source")
        if self.kind == "decision":
            if self.status is None:
                raise ValueError("a decision needs status")
            if self.status == "superseded" and self.valid_to is None:
                raise ValueError("a superseded decision needs valid_to")
        elif self.status is not None or self.checks is not None:
            raise ValueError("status and checks belong to decisions")
        ids = [check.id for check in self.checks or []]
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        if duplicates:
            raise ValueError("check ids must be unique: " + ", ".join(duplicates))
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to precedes valid_from")
        return self


def schema() -> dict:
    return KnowledgeNote.model_json_schema()


def split(text: str) -> tuple[dict | None, str, str]:
    """Return ``(frontmatter, raw frontmatter text, body)``; ``None`` when there is none.

    Raises ``ValueError`` for oversized notes or frontmatter that is not a YAML mapping.
    """
    if len(text.encode()) > MAX_NOTE_BYTES:
        raise ValueError(f"note exceeds {MAX_NOTE_BYTES // 1024} KB")
    match = FRONT_MATTER.match(text)
    if not match:
        return None, "", text
    try:
        data = yaml.safe_load(match.group(1)) if match.group(1).strip() else {}
    except yaml.YAMLError as exc:
        raise ValueError(f"frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")  # noqa: TRY004 -- callers catch ValueError
    return data, match.group(1), text[match.end() :]


def errors(data: dict) -> list[str]:
    """Schema errors for a frontmatter mapping, as ``field: message`` lines."""
    try:
        KnowledgeNote.model_validate(data)
    except ValidationError as exc:
        found = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"]) or "frontmatter"
            message = error["msg"].removeprefix("Value error, ")
            found.append(f"{location.replace('assert_', 'assert')}: {message}")
        return found
    return []


def dump(fields: dict) -> str:
    """Serialize frontmatter fields in the given order as block YAML."""
    return yaml.safe_dump(fields, sort_keys=False, default_flow_style=False, allow_unicode=True)


def with_missing(text: str, defaults: dict) -> str:
    """Add only the ``defaults`` keys a note lacks; supplied values and text are untouched."""
    data, raw, body = split(text)
    if data is None:
        return "---\n" + dump(defaults) + "---\n" + text.lstrip("\n")
    missing = {key: value for key, value in defaults.items() if key not in data}
    if not missing:
        return text
    return "---\n" + raw.rstrip("\n") + "\n" + dump(missing) + "---\n" + body


def strip_markers(text: str) -> str:
    return re.sub(r"\A(?:<!-- ai-dlc:[^\n]*-->\n)+", "", text)


def check_vault(vault) -> dict:
    """Read-only schema check of the notes under ``<vault>/learnings``.

    Notes without frontmatter, or with frontmatter lacking ``kind`` (the pre-schema
    ``work/repository/pr/tags`` form), are reported as ``legacy`` and do not fail.
    """
    from pathlib import Path

    root = Path(vault).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("knowledge unavailable: existing vault path is required")
    invalid, legacy, valid = [], [], 0
    folder = root / "learnings"
    for path in sorted(folder.rglob("*.md")) if folder.is_dir() else []:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            continue
        relative = str(path.relative_to(root))
        try:
            data, _raw, _body = split(strip_markers(path.read_text(errors="replace")))
        except ValueError as exc:
            invalid.append({"path": relative, "errors": [str(exc)]})
            continue
        if data is None or "kind" not in data:
            legacy.append(relative)
            continue
        problems = errors(data)
        if problems:
            invalid.append({"path": relative, "errors": problems})
        else:
            valid += 1
    return {
        "status": "invalid" if invalid else "valid",
        "valid": valid,
        "invalid": invalid,
        "legacy": legacy,
    }
