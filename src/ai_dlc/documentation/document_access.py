"""Scoped, bounded project-document search and reading; never private notes or vault links."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from ai_dlc.documentation.document_files import directory, read_bounded
from ai_dlc.documentation.document_impact import _git, _path
from ai_dlc.documentation.document_inventory import inventory_documents

DEFAULT_SOURCES = ("docs", "openspec")
MAX_DECLARATIONS = 32
MAX_BYTES = 1048576
MAX_RESULTS = 100
EXCERPT_CHARS = 240
CONSTRAINTS = [
    "Project documents only: docs/, openspec/ and Markdown sources declared for this call.",
    "Symlinks, vault links and Markdown links are not followed; private notes are never read.",
    "Edit returned repository paths with ordinary file and Git tools, then run project checks.",
    "Omitted and unexamined content has not been searched or read.",
]


def _integer(value: object, name: str, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be an integer from 1 through {maximum}")
    return value


def _declarations(sources: object) -> list[str]:
    """Validate shape before inventory; eligibility is checked against inventory later."""
    if sources is None:
        return []
    if not isinstance(sources, list) or any(not isinstance(s, str) for s in sources):
        raise ValueError("sources must be a list of repository-relative Markdown paths")
    if len(sources) > MAX_DECLARATIONS:
        raise ValueError(f"Declare at most {MAX_DECLARATIONS} additional sources")
    if len(set(sources)) != len(sources):
        raise ValueError("Source declarations must be unique")
    for value in sources:
        if any(c in value for c in "*?["):
            raise ValueError("Source declarations are exact paths, not globs: " + value)
        if _path(value) != value or Path(value).suffix.lower() != ".md":
            raise ValueError("Declare an exact repository-relative Markdown file: " + value)
    return sorted(sources)


def _repository(root: Path | str) -> Path:
    """One canonical repository root for inventory, eligibility, reads and returned paths."""
    candidate = Path(os.path.abspath(root))
    try:
        with directory(candidate):
            pass
    except (FileNotFoundError, ValueError) as exc:
        raise ValueError(f"Repository root unavailable or unsafe: {root}") from exc
    top = _git(candidate, "rev-parse", "--show-toplevel").decode().strip()
    if os.path.realpath(top) != os.path.realpath(candidate):
        raise ValueError("Select the repository root; document access is repository-scoped")
    return candidate


def _scope(root: Path, declared: list[str]) -> dict:
    inventory = inventory_documents(root)
    ineligible = sorted(set(declared) - set(inventory["documents"]))
    if ineligible:
        raise ValueError(
            "Declared sources must be inventory-eligible Markdown files: " + ", ".join(ineligible)
        )
    eligible = {
        path: path.split("/", 1)[0]
        for path in inventory["documents"]
        if "/" in path and path.split("/", 1)[0] in DEFAULT_SOURCES
    }
    for path in declared:
        eligible.setdefault(path, "declared")
    unavailable = []
    with directory(root) as fd:
        for name in DEFAULT_SOURCES:
            try:
                mode = os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
            except FileNotFoundError:
                unavailable.append({"source": name, "reason": "missing"})
                continue
            except OSError:
                unavailable.append({"source": name, "reason": "inaccessible"})
                continue
            if stat.S_ISLNK(mode):
                unavailable.append({"source": name, "reason": "symlink not followed"})
            elif not stat.S_ISDIR(mode):
                unavailable.append({"source": name, "reason": "not a directory"})

    def within(path: str) -> bool:
        path = path.rstrip("/")
        return path in declared or any(
            path == source or path.startswith(source + "/") for source in DEFAULT_SOURCES
        )

    return {
        "eligible": eligible,
        "unavailable": unavailable,
        "inventory": {
            "excluded": [item for item in inventory["excluded"] if within(item["path"])],
            "omitted": [item for item in inventory["omitted"] if within(item["path"])],
        },
    }


def _reason(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return "missing or changed source"
    if isinstance(exc, UnicodeDecodeError):
        return "not UTF-8 text"
    if isinstance(exc, ValueError):
        return str(exc)
    return "unavailable or unsafe source"


def _identity(root: Path, relative: str, source: str) -> dict:
    return {
        "path": relative,
        "absolute_path": str(root / relative),
        "source": {"kind": "project-document", "scope": source},
    }


def _result(root: Path, declared: list[str], scope: dict, **fields) -> dict:
    return {
        "schema": 1,
        "repository": str(root),
        "sources": {"defaults": list(DEFAULT_SOURCES), "declared": declared},
        "unavailable_sources": scope["unavailable"],
        "inventory": scope["inventory"],
        **fields,
        "constraints": CONSTRAINTS,
    }


def _locate(content: str, needle: str) -> dict | None:
    for number, line in enumerate(content.splitlines(), 1):
        position = line.casefold().find(needle)
        if position < 0:
            continue
        clipped = len(line) > EXCERPT_CHARS
        start = max(0, min(position - EXCERPT_CHARS // 3, len(line) - EXCERPT_CHARS))
        return {
            "start_line": number,
            "end_line": number,
            "excerpt": line[start : start + EXCERPT_CHARS] if clipped else line,
            "excerpt_clipped": clipped,
        }
    return None


def read_project_document(
    root: Path | str, *, path: str, sources: list[str] | None = None, max_bytes: int = 64000
) -> dict:
    """Return one complete eligible body within budget, or an explicit omission."""
    budget = _integer(max_bytes, "max_bytes", MAX_BYTES)
    declared = _declarations(sources)
    relative = _path(path)
    repository = _repository(root)
    scope = _scope(repository, declared)
    source = scope["eligible"].get(relative)
    if source is None:
        raise ValueError(
            "Not an eligible project document; declare an inventory-eligible Markdown "
            "source explicitly: " + relative
        )
    document, omitted = None, []
    try:
        body = read_bounded(repository, relative, budget)
    except (OSError, ValueError) as exc:
        omitted.append({"path": relative, "reason": _reason(exc)})
    else:
        document = _identity(repository, relative, source) | {
            "digest": body["digest"],
            "start_line": body["start_line"],
            "end_line": body["end_line"],
            "bytes": len(body["content"].encode("utf-8")),
            "content": body["content"],
        }
    return _result(
        repository, declared, scope, max_bytes=budget, document=document, omitted=omitted
    )


def search_project_documents(
    root: Path | str,
    *,
    query: str,
    sources: list[str] | None = None,
    max_bytes: int = 64000,
    limit: int = 20,
) -> dict:
    """Literal case-insensitive search; one body budget covers every examined document."""
    if not isinstance(query, str) or not query.strip() or "\n" in query or "\r" in query:
        raise ValueError("query must be a nonempty single-line literal string")
    budget = _integer(max_bytes, "max_bytes", MAX_BYTES)
    maximum = _integer(limit, "limit", MAX_RESULTS)
    declared = _declarations(sources)
    repository = _repository(root)
    scope = _scope(repository, declared)
    needle = query.casefold()
    remaining = budget
    matches, examined, unexamined = [], [], []
    ordered = sorted(scope["eligible"])
    for index, relative in enumerate(ordered):
        if len(matches) >= maximum:
            unexamined.extend(
                {"path": p, "reason": "result limit reached"} for p in ordered[index:]
            )
            break
        identity = _identity(repository, relative, scope["eligible"][relative])
        path_match = needle in relative.casefold()
        try:
            body = read_bounded(repository, relative, remaining)
        except (OSError, ValueError) as exc:
            unexamined.append({"path": relative, "reason": _reason(exc)})
            if path_match:
                matches.append(identity | {"match": "path", "body_examined": False})
            continue
        size = len(body["content"].encode("utf-8"))
        remaining -= size
        examined.append({"path": relative, "digest": body["digest"], "bytes": size})
        located = _locate(body["content"], needle)
        if located is not None:
            matches.append(
                identity
                | {"match": "body", "path_matched": path_match, "digest": body["digest"]}
                | located
            )
        elif path_match:
            matches.append(
                identity | {"match": "path", "body_examined": True, "digest": body["digest"]}
            )
    complete = not (
        unexamined
        or scope["inventory"]["omitted"]
        or any(item["reason"] != "missing" for item in scope["unavailable"])
    )
    return _result(
        repository,
        declared,
        scope,
        query=query,
        max_bytes=budget,
        limit=maximum,
        bytes_examined=budget - remaining,
        matches=matches,
        coverage={"complete": complete, "examined": examined, "not_examined": unexamined},
    )
