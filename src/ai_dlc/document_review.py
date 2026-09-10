"""Bounded local review context and mechanical grounding, never semantic judgment."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import stat
from pathlib import Path

from ai_dlc.document_files import directory
from ai_dlc.document_impact import MAPPINGS, _git, _path, digest, read_catalog

LIMITATION = "Citation grounding does not establish semantic truth or repository-wide accuracy."
CATEGORIES = {
    "contradiction",
    "unsupported-claim",
    "obsolete-instruction",
    "unnecessary-repetition",
    "missing-explanation",
    "vague-prose",
    "useful-repetition",
}


def _body(root: Path, relative: str, remaining: int) -> dict:
    path = root / _path(relative)
    with directory(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("not a regular file")
            if info.st_size > remaining:
                raise ValueError("body budget exceeded; content not read")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(remaining + 1)
            if len(raw) > remaining:
                raise ValueError("body budget exceeded")
            text = raw.decode("utf-8")
            if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
                raise ValueError("binary content")
            return {
                "path": relative,
                "content": text,
                "digest": hashlib.sha256(raw).hexdigest(),
                "start_line": 1,
                "end_line": len(text.splitlines()),
            }
        finally:
            os.close(fd)


def prepare_review(
    root: Path | str, *, paths: list[str], base: str, max_bytes: int = 64000
) -> dict:
    """Include only selected documents and their mapped, bounded local evidence."""
    root = Path(root).absolute()
    if type(max_bytes) is not int or not 0 < max_bytes <= 1048576:
        raise ValueError("max_bytes must be a positive integer at most 1048576")
    if (
        not isinstance(paths, list)
        or not 1 <= len(paths) <= 32
        or any(not isinstance(p, str) for p in paths)
        or len(set(paths)) != len(paths)
    ):
        raise ValueError("Select 1 to 32 unique catalog document paths")
    selected = sorted(_path(p) for p in paths)
    if not isinstance(base, str) or not base:
        raise ValueError("A Git base is required")
    revision = (
        _git(root, "rev-parse", "--verify", "--end-of-options", base + "^{commit}").decode().strip()
    )
    entries = read_catalog(root)
    catalog = {entry["path"]: entry for entry in entries}
    if set(selected) - catalog.keys():
        raise ValueError("Select only catalog document paths")
    files = set(
        _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
        .decode()
        .split("\0")
    ) - {""}
    sources = set()
    omitted = []
    for path in selected:
        entry = catalog[path]
        for field in MAPPINGS:
            for pattern in entry.get(field, []):
                matches = {p for p in files if fnmatch.fnmatchcase(p, pattern)}
                if not any(c in pattern for c in "*?["):
                    matches.add(pattern)
                if not matches:
                    omitted.append({"path": pattern, "reason": "mapping has no local matches"})
                sources.update(matches)
    # A nonselected catalog document remains out of review scope even if a broad mapping matches it.
    excluded = (sources & catalog.keys()) - set(selected)
    omitted.extend({"path": p, "reason": "document not selected"} for p in sorted(excluded))
    sources -= excluded | set(selected)
    documents, evidence = [], []
    remaining = max_bytes
    for relative in selected + sorted(sources):
        try:
            body = _body(root, relative, remaining)
        except (OSError, ValueError) as exc:
            reason = "missing source" if isinstance(exc, FileNotFoundError) else str(exc)
            omitted.append({"path": relative, "reason": reason})
            continue
        remaining -= len(body["content"].encode("utf-8"))
        (documents if relative in selected else evidence).append(body)
    result = {
        "schema": 1,
        "base": revision,
        "selected": selected,
        "max_bytes": max_bytes,
        "catalog_digest": digest(entries),
        "documents": documents,
        "evidence": evidence,
        "omitted": omitted,
        "unreviewed": sorted(catalog.keys() - set(selected)),
        "constraints": [
            LIMITATION,
            "No automatic edits, deletion or external fetching.",
            "Omitted content has not been reviewed or freshness-checked.",
        ],
        "rubric": [
            "Identify contradictions, unsupported claims and obsolete instructions.",
            "Explain missing context and vague prose with grounded passages.",
            "Consolidate needless overlap only after review; preserve unique information, rationale and useful audience summaries.",
            "Record useful repetition with retain; state uncertainty explicitly.",
        ],
    }
    result["snapshot"] = digest(result)
    return result


def _scope(value: object, name: str) -> set[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(p, str) for p in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError(f"{name} must be a unique path list")
    return set(value)


def _citation(citation: object, bodies: dict) -> str:
    if not isinstance(citation, dict):
        raise ValueError("Malformed citation")  # noqa: TRY004
    path = citation.get("path")
    start, end = citation.get("start_line"), citation.get("end_line")
    quote = citation.get("quote")
    if not isinstance(path, str) or path not in bodies:
        raise ValueError("Citation path is not included review evidence")
    lines = bodies[path]["content"].splitlines()
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
        raise ValueError("Citation line bounds are invalid")
    if (
        not isinstance(quote, str)
        or not quote.strip()
        or quote != "\n".join(lines[start - 1 : end])
    ):
        raise ValueError("Citation quote does not match the actual passage")
    return path


def validate_review(root: Path | str, *, packet: dict, review: dict) -> dict:
    """Rebuild local evidence before checking review scope and every citation."""
    try:
        if not isinstance(packet, dict) or packet.get("schema") != 1:
            raise ValueError("Invalid review packet")
        current = prepare_review(
            root,
            paths=packet.get("selected", []),
            base=packet.get("base", ""),
            max_bytes=packet.get("max_bytes", 0),
        )
        if current != packet:
            raise ValueError("Stale or fabricated review packet; prepare current evidence again")
        if (
            not isinstance(review, dict)
            or review.get("schema") != 1
            or review.get("packet_snapshot") != packet["snapshot"]
        ):
            raise ValueError("Review does not reference this packet")
        reviewed = _scope(review.get("reviewed"), "reviewed")
        unreviewed = _scope(review.get("unreviewed"), "unreviewed")
        selected = set(packet["selected"])
        available = {body["path"] for body in current["documents"]}
        if reviewed & unreviewed or reviewed | unreviewed != selected or reviewed - available:
            raise ValueError(
                "Review coverage must partition selected paths; omitted documents remain unreviewed"
            )
        bodies = {body["path"]: body for body in current["documents"] + current["evidence"]}
        findings = review.get("findings")
        if not isinstance(findings, list):
            raise ValueError("findings must be a list")  # noqa: TRY004
        for finding in findings:
            if not isinstance(finding, dict):
                raise ValueError("Malformed finding")  # noqa: TRY004
            if finding.get("category") not in tuple(CATEGORIES):
                raise ValueError("Unknown finding category")
            disposition = finding.get("suggested_disposition")
            if disposition not in ("revise", "consolidate", "retain", "investigate"):
                raise ValueError("Unknown suggested disposition")
            if finding["category"] == "useful-repetition" and disposition != "retain":
                raise ValueError("Useful repetition must be retained")
            for field in ("uncertainty", "rationale"):
                if not isinstance(finding.get(field), str) or not finding[field].strip():
                    raise ValueError(f"Finding requires explicit {field}")
            if _citation(finding.get("target"), bodies) not in reviewed:
                raise ValueError("Finding target must be a reviewed selected document")
            supporting = finding.get("supporting")
            if not isinstance(supporting, list) or not supporting:
                raise ValueError("Finding requires nonempty supporting evidence")
            for citation in supporting:
                _citation(citation, bodies)
        return {
            "valid": True,
            "errors": [],
            "reviewed": sorted(reviewed),
            "unreviewed": sorted(unreviewed | set(current["unreviewed"])),
            "omitted": current["omitted"],
            "limitation": LIMITATION,
        }
    except (OSError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)], "limitation": LIMITATION}
