"""Repository-scoped impact and explicit, content-bound documentation evidence."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import tomllib
from pathlib import Path

from ai_dlc.config import digest
from ai_dlc.documentation.document_files import read_document
from ai_dlc.documentation.documents import check_documents
from ai_dlc.files import inside, run_git

EVIDENCE_PREFIX = ".ai-dlc/documentation/"
EVIDENCE_DIR = ".ai-dlc/documentation/evidence"
LEGACY_EVIDENCE = ".ai-dlc/documentation/current.json"
OUTCOMES = ("updated", "reviewed-no-change", "no-impact")
WORK_PREFIX = ".ai-dlc/work/"
MAPPINGS = ("code_paths", "requirements", "verification_paths")
OBJECTIVE = {"owner-missing", "uncatalogued"}


def _git(root: Path, *args: str) -> bytes:
    return run_git(root, *args, text=False, context="Git comparison unavailable").stdout


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
    explicit_work = [
        p
        for entry in entries
        for field in MAPPINGS
        for p in entry.get(field, [])
        if p.startswith(WORK_PREFIX)
    ]

    def included(path: str) -> bool:
        return not path.startswith(WORK_PREFIX) or any(
            fnmatch.fnmatchcase(path, pattern) for pattern in explicit_work
        )

    changed = {p for p in changed if included(p)}
    files = set(
        _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
        .decode()
        .split("\0")
    ) - {""}
    files = {p for p in files if not p.startswith(EVIDENCE_PREFIX) and included(p)}
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


def _decisions(impact: dict, decisions: object, reviewer: object, *, partial: bool = False) -> None:
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
        if decision.get("outcome") not in OUTCOMES:
            raise ValueError("Invalid documentation disposition outcome")
        if not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
            raise ValueError("A documentation disposition needs a concrete reason")
        seen.add(target)
    if seen != required and not partial:
        raise ValueError("Missing documentation disposition: " + ", ".join(sorted(required - seen)))


def _require_contained_base(root: Path, revision: str) -> None:
    result = run_git(root, "merge-base", "--is-ancestor", revision, "HEAD", check=False)
    if result.returncode == 1:
        raise ValueError(
            f"Comparison base {revision} is not contained in HEAD; update the branch from "
            "the target branch before recording documentation dispositions"
        )
    if result.returncode:
        raise ValueError(
            "Git comparison unavailable: " + result.stderr.decode(errors="replace").strip()
        )


def prepare_disposition(
    root: Path | str, *, base: str, decisions: list[dict], reviewer: str
) -> dict:
    impact = inspect_impact(root, base=base)
    # CI compares against a revision its checkout contains; other evidence cannot pass there.
    _require_contained_base(Path(root).absolute(), impact["base"])
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
        if (
            not isinstance(evidence, dict)
            or evidence.get("schema") != 1
            or not isinstance(evidence.get("base"), str)
        ):
            raise ValueError("Invalid documentation evidence")
        # Report a moved target branch before decisions, whose targets depend on the base.
        if evidence["base"] != impact["base"]:
            raise ValueError(
                f"Documentation evidence was recorded against base {evidence['base']}, but "
                f"this check compares against {impact['base']}. Update the branch from the "
                "target branch, inspect impact against that base and record dispositions again"
            )
        _decisions(impact, evidence.get("decisions"), evidence.get("reviewer"))
        if (
            evidence.get("snapshot") != impact["snapshot"]
            or evidence.get("sources") != impact["sources"]
        ):
            raise ValueError("Stale documentation evidence; review current sources again")
        return {"valid": True, "errors": []}
    except (OSError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}


def _resolve(root: Path, revision: str) -> str:
    verified = _git(root, "rev-parse", "--verify", "--end-of-options", revision + "^{commit}")
    return verified.decode().strip()


def inspect_targets(root: Path | str, *, base: str) -> dict:
    """Required targets since the merge base, each with the content a decision must bind."""
    root = Path(root).absolute()
    start = _git(root, "merge-base", _resolve(root, base), "HEAD").decode().strip()
    impact = inspect_impact(root, base=start)
    tracked = set(_git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
                  .decode().split("\0")) - {""}  # fmt: skip
    tracked = {p for p in tracked if not p.startswith((EVIDENCE_PREFIX, WORK_PREFIX))}
    bound: dict[str, dict[str, str]] = {}
    for entry in read_catalog(root):
        if entry["path"] not in impact["documents"]:
            continue
        patterns = [p for field in MAPPINGS for p in entry.get(field, [])]
        paths = {entry["path"]} | {p for p in patterns if not any(c in p for c in "*?[")}
        paths |= {p for p in tracked if any(fnmatch.fnmatchcase(p, pat) for pat in patterns)}
        paths |= {p for p in impact["sources"] if any(fnmatch.fnmatchcase(p, x) for x in patterns)}
        bound[entry["path"]] = {p: content_digest(root, p) for p in sorted(paths)}
        # The entry, not the catalog file: unrelated enrollments must not stale this decision.
        bound[entry["path"]]["catalog:" + entry["path"]] = digest(entry)
    for path in impact["unmapped"]:
        bound[path] = {path: content_digest(root, path)}
    return {"schema": 2, "start": start, "changed": impact["changed"], "bound": bound}


def _stored_decisions(root: Path) -> tuple[list[dict], list[str]]:
    """Well-formed decisions from every per-work file; malformed files are errors, not evidence."""
    folder = inside(root, EVIDENCE_DIR)
    decisions, errors = [], []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        relative = f"{EVIDENCE_DIR}/{path.name}"
        try:
            raw = json.loads(read_document(path))
            if not isinstance(raw, dict) or raw.get("schema") != 2:
                raise ValueError
            for item in raw["decisions"]:
                if (
                    item["outcome"] not in OUTCOMES
                    or not all(
                        isinstance(item[k], str) and item[k].strip()
                        for k in ("target", "reason", "reviewer")
                    )
                    or not isinstance(item["bound"], dict)
                    or not item["bound"]
                ):
                    raise ValueError
                decisions.append(dict(item, file=relative))
        except (OSError, ValueError, KeyError, TypeError):
            errors.append("Invalid documentation evidence: " + relative)
    return decisions, errors


def _has_evidence(root: Path) -> bool:
    folder = inside(root, EVIDENCE_DIR)
    return folder.is_dir() and any(folder.glob("*.json"))


def check_evidence(root: Path | str, *, base: str) -> dict:
    """A target passes when any stored decision bound exactly the content present now."""
    root = Path(root).absolute()
    try:
        required = inspect_targets(root, base=base)["bound"]
        decisions, errors = _stored_decisions(root)
    except (OSError, ValueError) as exc:
        return {"valid": False, "missing": [], "stale": [], "errors": [str(exc)]}
    missing, stale = [], []
    for target, current in sorted(required.items()):
        candidates = [d["bound"] for d in decisions if d["target"] == target]
        if current in candidates:
            continue
        if not candidates:
            missing.append(target)
            continue
        differing = [
            sorted(p for p in current.keys() | old.keys() if current.get(p) != old.get(p))
            for old in candidates
        ]
        stale.append({"target": target, "paths": min(differing, key=lambda d: (len(d), d))})
    return {
        "valid": not (missing or stale or errors),
        "missing": missing,
        "stale": stale,
        "errors": errors,
    }


def _evidence_file(root: Path, evidence_id: object) -> Path:
    if (
        not isinstance(evidence_id, str)
        or not evidence_id
        or evidence_id.startswith(".")
        or not all(c.isalnum() or c in "-_." for c in evidence_id)
    ):
        raise ValueError("Unsafe documentation evidence identifier")
    return inside(root, f"{EVIDENCE_DIR}/{evidence_id}.json")


def record_disposition(
    root: Path | str, *, base: str, decisions: object, reviewer: object, evidence_id: object
) -> dict:
    """Merge reviewed decisions into one work item's evidence, keeping those still valid."""
    root = Path(root).absolute()
    path = _evidence_file(root, evidence_id)
    required = inspect_targets(root, base=base)["bound"]
    _decisions({"documents": list(required), "unmapped": []}, decisions, reviewer, partial=True)
    relative = f"{EVIDENCE_DIR}/{path.name}"
    previous = [d for d in _stored_decisions(root)[0] if d["file"] == relative]
    supplied = {d["target"]: d for d in decisions}  # type: ignore[union-attr]
    kept = {
        d["target"]: d
        for d in previous
        if d["target"] not in supplied and required.get(d["target"]) == d["bound"]
    }
    outstanding = sorted(required.keys() - supplied.keys() - kept.keys())
    if outstanding:
        raise ValueError("Missing documentation disposition: " + ", ".join(outstanding))
    known = {d["target"] for d in previous}
    merged = [
        {
            "target": target,
            "outcome": item["outcome"],
            "reason": item["reason"],
            "reviewer": item["reviewer"] if target in kept else reviewer,
            "bound": required[target],
        }
        for target, item in sorted({**kept, **supplied}.items())
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": 2, "decisions": merged}, indent=2, sort_keys=True) + "\n")
    return {
        "path": relative,
        "kept": sorted(kept),
        "added": sorted(supplied.keys() - known),
        "replaced": sorted(supplied.keys() & known),
        "dropped": sorted(known - required.keys()),
        "legacy": LEGACY_EVIDENCE if inside(root, LEGACY_EVIDENCE).exists() else None,
    }


def prune_evidence(root: Path | str, *, base: str, apply: bool = False) -> dict:
    """List, or remove, evidence files in which no decision satisfies a current target."""
    root = Path(root).absolute()
    required = inspect_targets(root, base=base)["bound"]
    decisions, _ = _stored_decisions(root)
    live = {d["file"] for d in decisions if required.get(d["target"]) == d["bound"]}
    inert = sorted({d["file"] for d in decisions} - live)
    if apply:
        for relative in inert:
            inside(root, relative).unlink()
    return {"inert": inert, "removed": inert if apply else []}


def _target_branch(root: Path) -> str:
    """Without a supplied comparison, compare against the configured target branch."""
    try:
        config = tomllib.loads(read_document(inside(root, "ai-dlc.toml")).decode())
    except FileNotFoundError:
        config = {}
    branch = config.get("scm", {}).get("target_branch", "main")
    for candidate in (f"origin/{branch}", branch):
        if not run_git(root, "rev-parse", "--verify", "--quiet", candidate, check=False).returncode:
            return candidate
    raise ValueError(
        f"Documentation comparison unavailable: target branch {branch} is not in this "
        "checkout; pass --base"
    )


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
        baseline = json.loads(read_document(inside(root, baseline_path)))
        if _has_evidence(root):
            disposition = check_evidence(root, base=base or _target_branch(root))
            debt = check_objective_debt(root, baseline=baseline)
            return {
                "valid": disposition["valid"] and debt["valid"],
                "disposition": disposition,
                "debt": debt,
            }
        # Schema 1 keeps its recorded-base rules for one release.
        evidence = json.loads(read_document(inside(root, evidence_path)))
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
