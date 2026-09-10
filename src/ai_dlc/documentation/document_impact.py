"""Repository-scoped impact and explicit, content-bound documentation evidence."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path

from ai_dlc.documentation.document_files import read_document
from ai_dlc.documentation.documents import check_documents
from ai_dlc.files import inside

EVIDENCE_PREFIX = ".ai-dlc/documentation/"
MAPPINGS = ("code_paths", "requirements", "verification_paths")
OBJECTIVE = {"owner-missing", "uncatalogued"}


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    if result.returncode:
        raise ValueError(
            "Git comparison unavailable: " + result.stderr.decode(errors="replace").strip()
        )
    return result.stdout


def _path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("Expected a repository-relative path or glob")
    p = Path(value)
    if p.is_absolute() or not p.parts or any(x in {".", "..", ".git"} for x in value.split("/")):
        raise ValueError("Unsafe documentation reference: " + value)
    return p.as_posix()


def content_digest(root: Path, relative: str) -> str:
    path = inside(root, _path(relative))
    try:
        return hashlib.sha256(read_document(path)).hexdigest()
    except FileNotFoundError:
        return "missing"


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def read_catalog(root: Path) -> list[dict]:
    raw = tomllib.loads(read_document(inside(root, "docs/catalog.toml")).decode())
    if raw.get("schema") != 1 or not isinstance(raw.get("documents"), list):
        raise ValueError("Invalid documentation catalog")
    seen = set()
    for entry in raw["documents"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid catalog entry")  # noqa: TRY004 -- user-authored data validation
        path = _path(entry.get("path", ""))
        if path in seen or Path(path).parts[0] not in {"docs", "openspec"}:
            raise ValueError("Invalid or duplicate catalog path")
        seen.add(path)
        for field in MAPPINGS:
            values = entry.get(field, [])
            if not isinstance(values, list):
                raise ValueError("Catalog references must be path lists")  # noqa: TRY004
            for value in values:
                normalized = _path(value)
                if normalized == EVIDENCE_PREFIX.rstrip("/") or normalized.startswith(
                    EVIDENCE_PREFIX
                ):
                    raise ValueError(
                        "Documentation mappings cannot target reserved evidence storage"
                    )
    return raw["documents"]


def inspect_impact(root: Path | str, *, base: str) -> dict:
    root = Path(root).absolute()
    revision = (
        _git(root, "rev-parse", "--verify", "--end-of-options", base + "^{commit}").decode().strip()
    )
    changed = set(
        _git(root, "diff", "--name-only", "--no-renames", "-z", revision, "--").decode().split("\0")
    )
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    changed.update(untracked)
    changed = {p for p in changed if p and not p.startswith(EVIDENCE_PREFIX)}
    entries = read_catalog(root)
    files = set(
        _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
        .decode()
        .split("\0")
    ) - {""}
    files = {p for p in files if not p.startswith(EVIDENCE_PREFIX)}
    impacted, mapped, evidence = set(), set(), {"docs/catalog.toml"} | changed
    for entry in entries:
        patterns = [entry["path"]] + [p for f in MAPPINGS for p in entry.get(f, [])]
        matches = {p for p in changed if any(fnmatch.fnmatchcase(p, pat) for pat in patterns)}
        if matches:
            impacted.add(entry["path"])
            mapped.update(matches)
            evidence.add(entry["path"])
            evidence.update(
                p for p in files if any(fnmatch.fnmatchcase(p, pat) for pat in patterns)
            )
            evidence.update(
                p for pat in patterns if not any(c in pat for c in "*?[") for p in [pat]
            )
    snapshot = {p: content_digest(root, p) for p in sorted(evidence)}
    result = {
        "schema": 1,
        "base": revision,
        "changed": sorted(changed),
        "documents": sorted(impacted),
        "unmapped": sorted(changed - mapped),
        "sources": snapshot,
    }
    result["snapshot"] = digest(result)
    result["limitation"] = (
        "Mappings identify review candidates; they do not prove complete coverage or factual accuracy."
    )
    return result


def _decisions(impact: dict, decisions: object, reviewer: object) -> None:
    if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(decisions, list):
        raise ValueError("A reviewer and documentation dispositions are required")
    required = set(impact["documents"]) | set(impact["unmapped"])
    seen = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("Invalid documentation disposition")  # noqa: TRY004
        target = decision.get("target")
        if not isinstance(target, str) or target not in required or target in seen:
            raise ValueError("Unknown or duplicate documentation disposition target")
        if decision.get("outcome") not in ("updated", "reviewed-no-change", "no-impact"):
            raise ValueError("Invalid documentation disposition outcome")
        if not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
            raise ValueError("A documentation disposition needs a concrete reason")
        seen.add(target)
    if seen != required:
        raise ValueError("Missing documentation disposition: " + ", ".join(sorted(required - seen)))


def prepare_disposition(
    root: Path | str, *, base: str, decisions: list[dict], reviewer: str
) -> dict:
    impact = inspect_impact(root, base=base)
    _decisions(impact, decisions, reviewer)
    return {
        "schema": 1,
        "base": impact["base"],
        "snapshot": impact["snapshot"],
        "reviewer": reviewer,
        "decisions": decisions,
        "sources": impact["sources"],
    }


def check_disposition(root: Path | str, *, base: str, evidence: object) -> dict:
    try:
        impact = inspect_impact(root, base=base)
        if not isinstance(evidence, dict) or evidence.get("schema") != 1:
            raise ValueError("Invalid documentation evidence")
        _decisions(impact, evidence.get("decisions"), evidence.get("reviewer"))
        if (
            evidence.get("base") != impact["base"]
            or evidence.get("snapshot") != impact["snapshot"]
            or evidence.get("sources") != impact["sources"]
        ):
            raise ValueError("Stale documentation evidence; review current sources again")
        return {"valid": True, "errors": []}
    except (OSError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}


def _findings(root: Path) -> list[dict]:
    return [
        f
        for f in check_documents(root)["findings"]
        if f.get("severity") == "error" or f["code"] in OBJECTIVE
    ]


def prepare_baseline(root: Path | str, *, owner: str, reason: str) -> dict:
    root = Path(root).absolute()
    if not owner.strip() or not reason.strip():
        raise ValueError("Historical debt requires a responsible owner and reason")
    return {
        "schema": 1,
        "findings": [
            dict(f, source_digest=content_digest(root, f["path"]), owner=owner, reason=reason)
            for f in _findings(root)
        ],
    }


def check_objective_debt(root: Path | str, *, baseline: object) -> dict:
    root = Path(root).absolute()
    if (
        not isinstance(baseline, dict)
        or baseline.get("schema") != 1
        or not isinstance(baseline.get("findings"), list)
    ):
        return {"valid": False, "errors": ["Invalid documentation baseline"], "new_findings": []}
    accepted = set()
    try:
        for finding in baseline["findings"]:
            if not isinstance(finding, dict) or not all(
                isinstance(finding.get(k), str) and finding[k].strip()
                for k in ("code", "path", "message", "source_digest", "owner", "reason")
            ):
                raise ValueError("Invalid historical finding disposition")
            if content_digest(root, finding["path"]) == finding["source_digest"]:
                accepted.add((finding["code"], finding["path"], finding["message"]))
        findings = _findings(root)
        new = [f for f in findings if (f["code"], f["path"], f["message"]) not in accepted]
        return {
            "valid": not new,
            "new_findings": new,
            "historical_findings": [f for f in findings if f not in new],
            "errors": [],
        }
    except (OSError, ValueError) as exc:
        return {"valid": False, "new_findings": [], "errors": [str(exc)]}


def check_gate(
    root: Path | str,
    *,
    evidence_path: str = ".ai-dlc/documentation/current.json",
    baseline_path: str = ".ai-dlc/documentation/baseline.json",
    base: str | None = None,
) -> dict:
    """Validate the selected reviewed comparison and historical-debt dispositions."""
    root = Path(root).absolute()
    try:
        evidence = json.loads(read_document(inside(root, evidence_path)))
        baseline = json.loads(read_document(inside(root, baseline_path)))
        if not isinstance(evidence, dict) or not isinstance(evidence.get("base"), str):
            raise ValueError("Invalid comparison evidence")  # noqa: TRY004
        comparison = base or evidence["base"]
        disposition = check_disposition(root, base=comparison, evidence=evidence)
        debt = check_objective_debt(root, baseline=baseline)
        return {
            "valid": disposition["valid"] and debt["valid"],
            "disposition": disposition,
            "debt": debt,
        }
    except (OSError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}
