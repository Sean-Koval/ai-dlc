"""Deterministic local document diagnostics, without publication or semantic claims."""

import hashlib
import os
import re
import tomllib
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ai_dlc.document_files import read_document
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


def check_documents(root: Path | str = ".", *, today: date | None = None) -> dict:
    root = Path(root).absolute()
    today = today or datetime.now(UTC).date()
    findings: list[dict] = []

    def report(code: str, path: str, message: str, severity: str = "warning"):
        findings.append({"code": code, "path": path, "message": message, "severity": severity})

    result = {
        "status": "attention",
        "findings": findings,
        "freshness": "Review metadata only; semantic accuracy is not verified.",
    }
    try:
        catalog = inside(root, "docs/catalog.toml")
        raw = tomllib.loads(read_document(catalog).decode())
        entries = raw.get("documents", [])
        if (
            raw.get("schema") != 1
            or not isinstance(entries, list)
            or not all(isinstance(e, dict) for e in entries)
        ):
            raise ValueError("Expected schema = 1 and a documents array")
    except FileNotFoundError:
        report("catalog-missing", "docs/catalog.toml", "Enroll canonical documents in a catalog.")
        return result
    except (OSError, ValueError, UnicodeError) as exc:
        report("invalid-catalog", "docs/catalog.toml", str(exc), "error")
        return result
    ids: set[str] = set()
    paths: set[str] = set()
    for entry in entries:
        relative = entry.get("path", "")
        identity = entry.get("id")
        if not isinstance(identity, str) or not identity.strip():
            report("invalid-metadata", str(relative), "A stable nonempty id is required.", "error")
        elif identity in ids:
            report("duplicate-id", str(relative), f"Duplicate document id: {identity}", "error")
        else:
            ids.add(identity)
        if (
            not isinstance(relative, str)
            or not relative
            or not Path(relative).parts
            or Path(relative).parts[0] not in {"docs", "openspec"}
        ):
            report(
                "invalid-path",
                str(relative),
                "Use a project-relative docs/ or openspec/ file.",
                "error",
            )
            continue
        normalized = Path(relative).as_posix()
        if normalized in paths:
            report(
                "duplicate-path",
                relative,
                "One canonical path must have one catalog entry.",
                "error",
            )
        paths.add(normalized)
        if (
            not isinstance(entry.get("kind"), str)
            or entry["kind"] not in KINDS
            or not isinstance(entry.get("status"), str)
            or entry["status"] not in STATUSES
        ):
            report(
                "invalid-metadata", relative, "Unknown document kind or lifecycle status.", "error"
            )
        if not isinstance(entry.get("owner"), str) or entry["owner"].strip().lower() in {
            "",
            "unassigned",
            "unknown",
        }:
            report(
                "owner-missing",
                relative,
                "Assign the person or role responsible for this document.",
            )
        if entry.get("status") not in ("archived", "superseded"):
            reviewed = entry.get("reviewed_on")
            interval = entry.get("review_after_days")
            try:
                reviewed_date = date.fromisoformat(str(reviewed))
                if type(interval) is not int or interval <= 0 or reviewed_date > today:
                    raise ValueError("Invalid review date or interval")
                if (today - reviewed_date).days > interval:
                    report(
                        "review-overdue",
                        relative,
                        "Declared review interval has elapsed; inspect the source.",
                    )
            except (ValueError, TypeError):
                report(
                    "review-unknown",
                    relative,
                    "Record an actual review date and positive review interval.",
                )
        sources = entry.get("sources", [])
        if not isinstance(sources, list) or not all(isinstance(x, dict) for x in sources):
            report(
                "invalid-metadata",
                relative,
                "Sources must be tables with URL, retrieval date and optional version.",
                "error",
            )
        elif entry.get("kind") == "summary" and not sources:
            report(
                "source-missing",
                relative,
                "A derived summary must identify its authoritative sources.",
            )
        else:
            for source in sources:
                url = source.get("url")
                if not isinstance(url, str) or not url.startswith("https://"):
                    report(
                        "source-invalid",
                        relative,
                        "An external source needs an HTTPS URL.",
                        "error",
                    )
                try:
                    if date.fromisoformat(str(source.get("retrieved_on"))) > today:
                        raise ValueError("Future date")
                except ValueError:
                    report("source-date-unknown", relative, "Record when the source was retrieved.")
        try:
            path = inside(root, relative)
            read_document(path)
        except FileNotFoundError:
            report("missing-document", relative, "The canonical file does not exist.", "error")
        except (ValueError, OSError):
            report(
                "invalid-path",
                relative,
                "Refused a symlink, special file or inaccessible path.",
                "error",
            )
    for entry in entries:
        if entry.get("status") == "superseded" and (
            not isinstance(entry.get("superseded_by"), str)
            or entry["superseded_by"] not in ids
            or entry["superseded_by"] == entry.get("id")
        ):
            report(
                "replacement-missing",
                str(entry.get("path")),
                "Name a different catalogued replacement id.",
                "error",
            )
    # Scan only docs, not the vault or external sources. OpenSpec owns its own lifecycle.
    hashes: dict[str, str] = {}
    docs = root / "docs"
    try:
        inside(root, "docs")
        for parent, directories, names in os.walk(docs, followlinks=False):
            directories[:] = sorted(
                d
                for d in directories
                if not d.startswith(".") and not (Path(parent) / d).is_symlink()
            )
            for name in sorted(names):
                path = Path(parent) / name
                if path.suffix != ".md":
                    continue
                relative = path.relative_to(root).as_posix()
                try:
                    body = read_document(path)
                except (ValueError, OSError):
                    report(
                        "invalid-path",
                        relative,
                        "Skipped symlink, special or inaccessible document.",
                        "error",
                    )
                    continue
                # Check ordinary inline Markdown links only, excluding fenced examples.
                text = re.sub(r"(?ms)^```.*?^```[^\n]*", "", body.decode(errors="replace"))
                for match in re.finditer(r"\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", text):
                    target = match.group(1).strip("<>")
                    try:
                        parsed = urlsplit(target)
                    except ValueError:
                        report("broken-link", relative, f"Malformed link target: {target}", "error")
                        continue
                    if parsed.scheme or parsed.netloc or not parsed.path:
                        continue
                    destination = Path(os.path.abspath(path.parent / unquote(parsed.path)))
                    try:
                        rel = destination.relative_to(root).as_posix()
                        resolved = inside(root, rel)
                        if not resolved.exists():
                            report(
                                "broken-link",
                                relative,
                                f"Missing local link target: {target}",
                                "error",
                            )
                    except ValueError:
                        report(
                            "broken-link",
                            relative,
                            f"Local link escapes the project or traverses a symlink: {target}",
                            "error",
                        )
                if relative not in paths and relative != "docs/index.md":
                    report(
                        "uncatalogued",
                        relative,
                        "Classify this document or link it to an existing canonical source.",
                    )
                if body.strip():
                    digest = hashlib.sha256(body).hexdigest()
                    if digest in hashes:
                        report(
                            "duplicate-content",
                            relative,
                            f"Exact duplicate of {hashes[digest]}; review before consolidating.",
                        )
                    else:
                        hashes[digest] = relative
    except ValueError:
        report("invalid-path", "docs", "Document directory must not be a symlink.", "error")
    result["status"] = "clean" if not findings else "attention"
    return result
