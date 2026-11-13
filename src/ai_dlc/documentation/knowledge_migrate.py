"""Migrate knowledge-note frontmatter to the knowledge-record contract (ADR 0005, KAN-452).

The "migrate" step of expand, migrate, contract. :func:`convert` maps one note's
frontmatter to a :class:`~ai_dlc.documentation.knowledge_records.KnowledgeRecord`
header; :func:`migrate` rewrites files in place. It is idempotent: a record, a file
without frontmatter and a ``runbook`` or ``note`` (not record types) are left alone,
so a second run changes nothing. It is reversible: ``write`` journals each file's
original bytes under ``.ai-dlc/local/knowledge-migrate/`` and :func:`revert` restores
them while the file still holds what the migration wrote. The body is never touched;
leading ``<!-- ai-dlc:... -->`` operation markers move below the frontmatter.

Readers accept both shapes until :data:`LEGACY_DROPPED_IN`; KAN-453 then removes the
note format.
"""

import hashlib
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

from ai_dlc.documentation import knowledge_records
from ai_dlc.documentation.knowledge_notes import CAPTURE_KINDS, split
from ai_dlc.files import atomic_write

LEGACY_DROPPED_IN = "the release after 1.0"
"""When ai-dlc stops reading knowledge-note frontmatter (KAN-453; the owner picks the version)."""
DEPRECATION = (
    "knowledge-note frontmatter (kind:) is deprecated and is read until "
    f"{LEGACY_DROPPED_IN} of ai-dlc; run `ai-dlc knowledge migrate --write`"
)
JOURNAL_DIR = ".ai-dlc/local/knowledge-migrate"
TYPES = {"learning": "lesson", "decision": "decision", **{kind: "source" for kind in CAPTURE_KINDS}}
LEGACY_KINDS = ("runbook", "note")
# Fields carried over unchanged (KAN-452 comment 10458), in record order.
CARRIED = ("label", "valid_from", "valid_to", "confidence", "checks", "author", "tags")
# Old fields with a mapping; anything else in an old note is reported as dropped.
MAPPED = {
    "id",
    "kind",
    "scope",
    "status",
    "sources",
    "review_by",
    "supersedes",
    "work",
    "lane",
    "origin",
    "source",
    *CARRIED,
}
_MARKERS = re.compile(r"\A((?:<!-- ai-dlc:[^\n]*-->\n)*)")
_TITLE = re.compile(r"^# +(.+?)\s*$", re.MULTILINE)
_DECISION = re.compile(r"^decision/([0-9]{4,})-")


def is_note(data: dict | None) -> bool:
    """Whether ``data`` is knowledge-note frontmatter: ``kind`` and no record ``type``."""
    return bool(data) and "kind" in data and "type" not in data  # type: ignore[operator]


def record_id(note_id: str) -> str:
    """``decision/0001-x`` becomes ``DEC-0001``; any other note id becomes a slug."""
    numbered = _DECISION.match(note_id)
    if numbered:
        return f"DEC-{numbered.group(1)}"
    return re.sub(r"[^a-z0-9]+", "-", note_id.lower()).strip("-") or "note"


def _day(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _owner(author: Any, owner: str | None) -> str | None:
    if owner:
        return owner
    if not isinstance(author, str) or not author:
        return None
    return author.removeprefix("human:")


def _sources(data: dict, kind: str, path: str) -> list[dict]:
    found = []
    for entry in data.get("sources") or []:
        if isinstance(entry, dict):
            item = {"resource": entry.get("uri")}
            if entry.get("hash"):
                item["hash"] = entry["hash"]
            found.append(item)
    capture = data.get("source")
    if isinstance(capture, dict):
        item = {"resource": capture.get("file") or capture.get("room")}
        if capture.get("sha256"):
            item["hash"] = f"sha256:{capture['sha256']}"
        found.append(item)
    if not found and kind in CAPTURE_KINDS:
        # A daily note is its own source: it was written in the vault, not exported.
        found.append({"resource": path})
    return found


def _links(data: dict) -> list[dict]:
    links = [
        {"type": "supersedes", "target": record_id(str(old))}
        for old in data.get("supersedes") or []
    ]
    for key in ("work", "lane"):
        if data.get(key):
            links.append({"type": "belongs_to", "target": str(data[key])})
    return links


def convert(
    data: dict, *, path: str = "", body: str = "", owner: str | None = None
) -> tuple[dict, list[str]]:
    """``(record header, dropped field names)`` for one note's frontmatter.

    Raises ``ValueError`` for a note that is not a record type (``runbook``, ``note``).
    The header is not validated here; :func:`migrate_text` validates it.
    """
    kind = str(data.get("kind"))
    if kind not in TYPES:
        raise ValueError(f"kind {kind} is not a record type; it stays legacy")
    record_type = TYPES[kind]
    start = _day(data.get("valid_from"))
    title = _TITLE.search(body)
    status = {"decision": data.get("status"), "lesson": "open", "source": "raw"}[record_type]
    header: dict[str, Any] = {
        "id": record_id(str(data.get("id", ""))),
        "type": record_type,
        "scope": data.get("scope"),
        "status": status,
        "date": start,
        "owner": _owner(data.get("author"), owner),
        "sources": _sources(data, kind, path),
        "links": _links(data),
    }
    if title or record_type == "source":
        header["title"] = title.group(1) if title else Path(path).stem or header["id"]
    for key in CARRIED:
        if data.get(key) is not None:
            header[key] = data[key]
    tags = [kind] if record_type == "source" else []
    if data.get("origin"):
        tags.append(f"origin:{data['origin']}")
    if tags:
        header["tags"] = [*(header.get("tags") or []), *tags]
    stale = _day(data.get("review_by"))
    if stale:
        header["stale_after"] = datetime(stale.year, stale.month, stale.day, tzinfo=UTC)
    if data.get("id"):
        header["aliases"] = [str(data["id"])]
    if record_type == "source":
        header.update(
            schema_version=knowledge_records.ENVELOPE_VERSION,
            revision="1",
            provider="notes",
            observed_at=datetime(start.year, start.month, start.day, tzinfo=UTC) if start else None,
        )
    ordered = (*knowledge_records.REQUIRED_FIELDS, *knowledge_records.OPTIONAL_FIELDS)
    header = {
        key: header[key]
        for key in sorted(header, key=lambda k: ordered.index(k) if k in ordered else len(ordered))
        if header[key] is not None
    }
    dropped = sorted(key for key in data if key not in MAPPED and data[key] is not None)
    return header, dropped


class _Dumper(yaml.SafeDumper):
    """Block YAML without anchors: ``date`` and ``valid_from`` share one value."""

    def ignore_aliases(self, data: Any) -> bool:
        return True


def _serialize(header: dict) -> str:
    def plain(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat().replace("+00:00", "Z")
        if isinstance(value, dict):
            return {key: plain(item) for key, item in value.items()}
        if isinstance(value, list):
            return [plain(item) for item in value]
        return value

    return yaml.dump(
        plain(header),
        Dumper=_Dumper,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )


def migrate_text(text: str, path: str = "", owner: str | None = None) -> dict:
    """Migrate one file's text; returns ``{status, text?, dropped?, errors?}``.

    ``status`` is ``migrated``, ``unchanged`` (already a record, or no frontmatter),
    ``unreadable`` (frontmatter that is not YAML, so not a note), ``legacy`` (not a
    record type) or ``invalid`` (the result fails the contract).
    """
    prefix = _MARKERS.match(text)
    markers = prefix.group(1) if prefix else ""
    try:
        data, _raw, body = split(text[len(markers) :])
    except ValueError as exc:
        return {"status": "unreadable", "errors": [str(exc)]}
    if not is_note(data):
        return {"status": "unchanged"}
    assert data is not None
    if str(data.get("kind")) not in TYPES:
        return {"status": "legacy", "kind": str(data.get("kind"))}
    header, dropped = convert(data, path=path, body=body, owner=owner)
    problems = knowledge_records.errors(json.loads(json.dumps(header, default=str)))
    if problems:
        return {"status": "invalid", "errors": problems, "dropped": dropped}
    # Operation markers move below the frontmatter: OKF needs the file to open with it.
    new = "---\n" + _serialize(header) + "---\n" + markers + body
    return {"status": "migrated", "text": new, "dropped": dropped}


def _files(root: Path, paths: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for target in paths:
        target = (root / target).resolve() if not target.is_absolute() else target.resolve()
        if not target.is_relative_to(root):
            raise ValueError(f"{target} is outside {root}")
        candidates = [target] if target.is_file() else sorted(target.rglob("*.md"))
        for path in candidates:
            parts = path.relative_to(root).parts
            if path.suffix != ".md" or path.is_symlink() or not path.is_file():
                continue
            if any(part.startswith(".") for part in parts):
                continue
            found.add(path)
    return sorted(found)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def migrate(
    root: Path | str,
    paths: list[Path] | None = None,
    *,
    write: bool = False,
    owner: str | None = None,
) -> dict:
    """Migrate the notes under ``paths`` (default: ``root``); a dry run unless ``write``.

    Files that fail the contract after conversion are reported and never written, so a
    run is safe to repeat. With ``write``, the journal path is returned for :func:`revert`.
    """
    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        raise ValueError(f"directory not found: {root}")
    report: dict[str, list] = {"migrated": [], "legacy": [], "invalid": [], "unreadable": []}
    unchanged = 0
    changes = []
    for path in _files(base, paths or [base]):
        relative = path.relative_to(base).as_posix()
        before = path.read_text(encoding="utf-8")
        result = migrate_text(before, relative, owner)
        status = result["status"]
        if status == "unchanged":
            unchanged += 1
        elif status == "unreadable":
            report["unreadable"].append(relative)
        elif status == "legacy":
            report["legacy"].append({"path": relative, "kind": result["kind"]})
        elif status == "invalid":
            report["invalid"].append({"path": relative, "errors": result["errors"]})
        else:
            report["migrated"].append({"path": relative, "dropped": result["dropped"]})
            changes.append((path, relative, before, result["text"]))
    journal = None
    if write and changes:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        journal = base / JOURNAL_DIR / f"{stamp}.json"
        entries = [
            {"path": relative, "before": before, "after_sha256": _digest(after)}
            for _path, relative, before, after in changes
        ]
        # The journal is written first, so an interrupted run can still be reverted.
        journal.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(journal, json.dumps({"schema": 1, "files": entries}, indent=2) + "\n")
        for path, _relative, _before, after in changes:
            atomic_write(path, after)
    return {
        "status": "invalid" if report["invalid"] else "ok",
        "mode": "write" if write else "dry-run",
        **report,
        "unchanged": unchanged,
        "journal": journal.relative_to(base).as_posix() if journal else None,
        "deprecation": DEPRECATION,
    }


def revert(root: Path | str, journal: Path | str, *, write: bool = False) -> dict:
    """Restore the files a ``migrate`` run wrote; a dry run unless ``write``.

    A file edited since the migration is reported as ``conflict`` and left alone.
    """
    base = Path(root).expanduser().resolve()
    source = Path(journal)
    source = source if source.is_absolute() else base / source
    entries = json.loads(source.read_text(encoding="utf-8"))["files"]
    restored, conflict = [], []
    for entry in entries:
        path = (base / entry["path"]).resolve()
        if not path.is_relative_to(base):
            raise ValueError(f"{entry['path']} is outside {base}")
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current == entry["before"]:
            continue
        if current is None or _digest(current) != entry["after_sha256"]:
            conflict.append(entry["path"])
            continue
        restored.append(entry["path"])
        if write:
            atomic_write(path, entry["before"])
    return {
        "status": "conflict" if conflict else "ok",
        "mode": "write" if write else "dry-run",
        "restored": restored,
        "conflict": conflict,
    }
