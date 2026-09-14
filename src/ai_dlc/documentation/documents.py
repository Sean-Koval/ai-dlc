"""Deterministic local document diagnostics, without publication or semantic claims."""

import hashlib
import os
import tomllib
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ai_dlc.documentation.document_files import read_document
from ai_dlc.files import inside

KINDS = {
    "architecture",
    "decision",
    "specification",
    "runbook",
    "reference",
    "navigation",
    "summary",
    "template",
    "example",
}
STATUSES = {"draft", "active", "superseded", "archived"}


def _finding(code: str, path: str, message: str, severity: str = "warning") -> dict:
    return {"code": code, "path": path, "message": message, "severity": severity}


def _read_catalog_entries(root: Path) -> list[dict]:
    """Load ``docs/catalog.toml``; raise the underlying error for the caller to classify."""
    catalog = inside(root, "docs/catalog.toml")
    raw = tomllib.loads(read_document(catalog).decode())
    entries = raw.get("documents", [])
    if (
        raw.get("schema") != 1
        or not isinstance(entries, list)
        or not all(isinstance(e, dict) for e in entries)
    ):
        raise ValueError("Expected schema = 1 and a documents array")
    return entries


def _identity_findings(entry: dict, ids: set[str]) -> list[dict]:
    """Validate the entry id and record it in ``ids`` when it is new."""
    relative = entry.get("path", "")
    identity = entry.get("id")
    if not isinstance(identity, str) or not identity.strip():
        return [
            _finding(
                "invalid-metadata", str(relative), "A stable nonempty id is required.", "error"
            )
        ]
    if identity in ids:
        return [
            _finding("duplicate-id", str(relative), f"Duplicate document id: {identity}", "error")
        ]
    ids.add(identity)
    return []


def _catalogued_path(relative: object) -> bool:
    return (
        isinstance(relative, str)
        and bool(relative)
        and bool(Path(relative).parts)
        and Path(relative).parts[0] in {"docs", "openspec"}
    )


def _metadata_findings(entry: dict, relative: str, today: date) -> list[dict]:
    findings: list[dict] = []
    if (
        not isinstance(entry.get("kind"), str)
        or entry["kind"] not in KINDS
        or not isinstance(entry.get("status"), str)
        or entry["status"] not in STATUSES
    ):
        findings.append(
            _finding(
                "invalid-metadata", relative, "Unknown document kind or lifecycle status.", "error"
            )
        )
    if not isinstance(entry.get("owner"), str) or entry["owner"].strip().lower() in {
        "",
        "unassigned",
        "unknown",
    }:
        findings.append(
            _finding(
                "owner-missing",
                relative,
                "Assign the person or role responsible for this document.",
            )
        )
    if entry.get("status") not in ("archived", "superseded"):
        findings.extend(_review_findings(entry, relative, today))
    return findings


def _review_findings(entry: dict, relative: str, today: date) -> list[dict]:
    reviewed = entry.get("reviewed_on")
    interval = entry.get("review_after_days")
    try:
        reviewed_date = date.fromisoformat(str(reviewed))
        if type(interval) is not int or interval <= 0 or reviewed_date > today:
            raise ValueError("Invalid review date or interval")
        if (today - reviewed_date).days > interval:
            return [
                _finding(
                    "review-overdue",
                    relative,
                    "Declared review interval has elapsed; inspect the source.",
                )
            ]
    except (ValueError, TypeError):
        return [
            _finding(
                "review-unknown",
                relative,
                "Record an actual review date and positive review interval.",
            )
        ]
    return []


def _source_findings(entry: dict, relative: str, today: date) -> list[dict]:
    sources = entry.get("sources", [])
    if not isinstance(sources, list) or not all(isinstance(x, dict) for x in sources):
        return [
            _finding(
                "invalid-metadata",
                relative,
                "Sources must be tables with URL, retrieval date and optional version.",
                "error",
            )
        ]
    if entry.get("kind") == "summary" and not sources:
        return [
            _finding(
                "source-missing",
                relative,
                "A derived summary must identify its authoritative sources.",
            )
        ]
    findings: list[dict] = []
    for source in sources:
        url = source.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            findings.append(
                _finding(
                    "source-invalid",
                    relative,
                    "An external source needs an HTTPS URL.",
                    "error",
                )
            )
        try:
            if date.fromisoformat(str(source.get("retrieved_on"))) > today:
                raise ValueError("Future date")
        except ValueError:
            findings.append(
                _finding("source-date-unknown", relative, "Record when the source was retrieved.")
            )
    return findings


def _document_file_findings(root: Path, relative: str) -> list[dict]:
    try:
        path = inside(root, relative)
        read_document(path)
    except FileNotFoundError:
        return [
            _finding("missing-document", relative, "The canonical file does not exist.", "error")
        ]
    except (ValueError, OSError):
        return [
            _finding(
                "invalid-path",
                relative,
                "Refused a symlink, special file or inaccessible path.",
                "error",
            )
        ]
    return []


def _replacement_findings(entries: list[dict], ids: set[str]) -> list[dict]:
    findings: list[dict] = []
    for entry in entries:
        if entry.get("status") == "superseded" and (
            not isinstance(entry.get("superseded_by"), str)
            or entry["superseded_by"] not in ids
            or entry["superseded_by"] == entry.get("id")
        ):
            findings.append(
                _finding(
                    "replacement-missing",
                    str(entry.get("path")),
                    "Name a different catalogued replacement id.",
                    "error",
                )
            )
    return findings


def _validate_entries(
    entries: list[dict], root: Path, today: date
) -> tuple[list[dict], set[str], set[str]]:
    """Validate catalog entries; return findings, the known ids and the catalogued paths."""
    findings: list[dict] = []
    ids: set[str] = set()
    paths: set[str] = set()
    for entry in entries:
        relative = entry.get("path", "")
        findings.extend(_identity_findings(entry, ids))
        if not _catalogued_path(relative):
            findings.append(
                _finding(
                    "invalid-path",
                    str(relative),
                    "Use a project-relative docs/ or openspec/ file.",
                    "error",
                )
            )
            continue
        normalized = Path(relative).as_posix()
        if normalized in paths:
            findings.append(
                _finding(
                    "duplicate-path",
                    relative,
                    "One canonical path must have one catalog entry.",
                    "error",
                )
            )
        paths.add(normalized)
        findings.extend(_metadata_findings(entry, relative, today))
        findings.extend(_source_findings(entry, relative, today))
        findings.extend(_document_file_findings(root, relative))
    findings.extend(_replacement_findings(entries, ids))
    return findings, ids, paths


def _link_findings(root: Path, path: Path, relative: str, body: bytes) -> list[dict]:
    """Check ordinary inline Markdown links only, excluding fenced examples."""
    from ai_dlc.documentation.document_access import markdown_links

    findings: list[dict] = []
    for _line, target in markdown_links(body.decode(errors="replace")):
        try:
            parsed = urlsplit(target)
        except ValueError:
            findings.append(
                _finding("broken-link", relative, f"Malformed link target: {target}", "error")
            )
            continue
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        destination = Path(os.path.abspath(path.parent / unquote(parsed.path)))
        try:
            rel = destination.relative_to(root).as_posix()
            resolved = inside(root, rel)
            if not resolved.exists():
                findings.append(
                    _finding(
                        "broken-link",
                        relative,
                        f"Missing local link target: {target}",
                        "error",
                    )
                )
        except ValueError:
            findings.append(
                _finding(
                    "broken-link",
                    relative,
                    f"Local link escapes the project or traverses a symlink: {target}",
                    "error",
                )
            )
    return findings


def _duplicate_content_findings(hashes: dict[str, str], body: bytes, relative: str) -> list[dict]:
    """Record the body digest in ``hashes``; report an exact duplicate of an earlier document."""
    if not body.strip():
        return []
    digest = hashlib.sha256(body).hexdigest()
    if digest in hashes:
        return [
            _finding(
                "duplicate-content",
                relative,
                f"Exact duplicate of {hashes[digest]}; review before consolidating.",
            )
        ]
    hashes[digest] = relative
    return []


def _markdown_documents(root: Path, docs: Path) -> list[Path]:
    paths: list[Path] = []
    for parent, directories, names in os.walk(docs, followlinks=False):
        directories[:] = sorted(
            d for d in directories if not d.startswith(".") and not (Path(parent) / d).is_symlink()
        )
        for name in sorted(names):
            path = Path(parent) / name
            if path.suffix != ".md":
                continue
            paths.append(path)
    return paths


def _scan_docs(root: Path, paths: set[str]) -> list[dict]:
    """Scan only docs, not the vault or external sources. OpenSpec owns its own lifecycle."""
    findings: list[dict] = []
    hashes: dict[str, str] = {}
    docs = root / "docs"
    try:
        inside(root, "docs")
        for path in _markdown_documents(root, docs):
            relative = path.relative_to(root).as_posix()
            try:
                body = read_document(path)
            except (ValueError, OSError):
                findings.append(
                    _finding(
                        "invalid-path",
                        relative,
                        "Skipped symlink, special or inaccessible document.",
                        "error",
                    )
                )
                continue
            findings.extend(_link_findings(root, path, relative, body))
            if relative not in paths and relative != "docs/index.md":
                findings.append(
                    _finding(
                        "uncatalogued",
                        relative,
                        "Classify this document or link it to an existing canonical source.",
                    )
                )
            findings.extend(_duplicate_content_findings(hashes, body, relative))
    except ValueError:
        findings.append(
            _finding("invalid-path", "docs", "Document directory must not be a symlink.", "error")
        )
    return findings


def check_documents(root: Path | str = ".", *, today: date | None = None) -> dict:
    root = Path(root).absolute()
    today = today or datetime.now(UTC).date()
    findings: list[dict] = []
    result = {
        "status": "attention",
        "findings": findings,
        "freshness": "Review metadata only; semantic accuracy is not verified.",
    }
    try:
        entries = _read_catalog_entries(root)
    except FileNotFoundError:
        findings.append(
            _finding(
                "catalog-missing", "docs/catalog.toml", "Enroll canonical documents in a catalog."
            )
        )
        return result
    except (OSError, ValueError, UnicodeError) as exc:
        findings.append(_finding("invalid-catalog", "docs/catalog.toml", str(exc), "error"))
        return result
    entry_findings, _ids, paths = _validate_entries(entries, root, today)
    findings.extend(entry_findings)
    findings.extend(_scan_docs(root, paths))
    result["status"] = "clean" if not findings else "attention"
    return result
