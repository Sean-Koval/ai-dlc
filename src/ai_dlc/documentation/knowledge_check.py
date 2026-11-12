"""``knowledge check``: validate a directory of knowledge records as one bundle.

Each record goes through :class:`~ai_dlc.documentation.knowledge_records.KnowledgeRecord`;
the bundle is then checked for typed-link integrity, supersession, duplicate sources and
the ``knowledge.toml`` format pin. It also applies the three Open Knowledge Format v0.2
section 11 checks: every non-reserved ``.md`` file has parseable YAML frontmatter with a
non-empty ``type``, and the reserved ``index.md`` and ``log.md`` follow sections 8 and 9.
OKF tolerates broken markdown links, so only our typed ``links`` must resolve.

With ``base`` (CI mode) it also refuses in-place edits of decisions that were accepted
at the merge base. The CLI and the MCP tool both call :func:`check_records`.
"""

import re
import tomllib
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from ai_dlc.documentation import knowledge_records as records
from ai_dlc.documentation.knowledge_notes import split
from ai_dlc.files import GitError, run_git

RESERVED = ("index.md", "log.md")
LEGACY_KINDS = ("runbook", "note")
CONFIG = "knowledge.toml"
NUMBERED = re.compile(r"^(?:DEC|CONV|LES|ACT|Q|SRC)-[0-9]{4,}$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*#*[ \t]*$")
# Header changes that do not count as editing an accepted decision: superseding it,
# and numbering at merge (slug id becomes PREFIX-NNNN and the slug moves to aliases).
SUPERSEDE_KEYS = ("status", "valid_to")


class _Bundle:
    def __init__(self) -> None:
        self.failures: list[dict[str, str]] = []
        self.legacy: list[dict[str, str]] = []
        self.records: dict[str, records.KnowledgeRecord] = {}

    def fail(self, path: str, pointer: str, message: str) -> None:
        self.failures.append({"path": path, "pointer": pointer, "message": message})


def check_records(
    root: Path | str,
    *,
    base: str | None = None,
    config: Path | str | None = None,
) -> dict[str, Any]:
    """Check every record under ``root``; read-only.

    ``base`` is a git revision: decisions accepted at its merge base with ``HEAD`` must
    not be edited, except to supersede them or number them. ``config`` is the
    ``knowledge.toml`` path; by default it is looked up from ``root`` to the git root.
    Returns failures as ``{path, pointer, message}`` with ``path`` relative to ``root``
    and ``pointer`` a JSON pointer into the frontmatter (empty for the whole file).
    """
    folder = Path(root).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError(f"records directory not found: {root}")
    bundle = _Bundle()
    for path in _markdown(folder):
        relative = path.relative_to(folder).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.name in RESERVED:
            _check_reserved(bundle, relative, text)
            continue
        _check_record(bundle, relative, text)
    _check_pin(bundle, folder, config)
    index = _index(bundle)
    _check_links(bundle, index)
    _check_supersession(bundle, index)
    _check_duplicate_sources(bundle)
    if base:
        _check_accepted_unchanged(bundle, folder, base)
    bundle.failures.sort(key=lambda item: (item["path"], item["pointer"], item["message"]))
    return {
        "status": "invalid" if bundle.failures else "valid",
        "records": len(bundle.records),
        "failures": bundle.failures,
        "legacy": bundle.legacy,
    }


def failure_lines(result: dict[str, Any], prefix: str = "") -> list[str]:
    """One ``path: pointer: message`` line per failure; ``prefix`` is prepended to paths."""
    lines = []
    for item in result["failures"]:
        path = _join(prefix, item["path"])
        pointer = f" {item['pointer']}:" if item["pointer"] else ""
        lines.append(f"{path}:{pointer} {item['message']}")
    return lines


def legacy_lines(result: dict[str, Any], prefix: str = "") -> list[str]:
    return [
        f"{_join(prefix, item['path'])}: legacy: kind {item['kind']} is not a record type; skipped"
        for item in result["legacy"]
    ]


def _join(prefix: str, path: str) -> str:
    return path if prefix in ("", ".") else f"{prefix.rstrip('/')}/{path}"


def _markdown(folder: Path) -> list[Path]:
    found = []
    for path in sorted(folder.rglob("*.md")):
        parts = path.relative_to(folder).parts
        if any(part.startswith(".") for part in parts) or path.is_symlink():
            continue
        if path.is_file() and path.resolve().is_relative_to(folder):
            found.append(path)
    return found


def _pointer(location: str) -> str:
    return "/" + location.replace(".", "/") if location else ""


def _check_record(bundle: _Bundle, relative: str, text: str) -> None:
    try:
        data, _raw, _body = split(text)
    except ValueError as exc:
        bundle.fail(relative, "", f"{exc} (OKF v0.2 section 11)")
        return
    if data is None:
        bundle.fail(
            relative, "", "no YAML frontmatter; every record needs one (OKF v0.2 section 11)"
        )
        return
    kind = data.get("type")
    if "type" not in data and data.get("kind") in LEGACY_KINDS:
        bundle.legacy.append({"path": relative, "kind": str(data["kind"])})
        return
    if not isinstance(kind, str) or not kind.strip():
        bundle.fail(relative, "/type", "a non-empty type is required (OKF v0.2 section 11)")
        return
    problems = records.errors(data)
    for problem in problems:
        location, _, message = problem.partition(": ")
        if not message:
            location, message = "", problem
        bundle.fail(relative, _pointer(location), message)
    if not problems:
        bundle.records[relative] = records.KnowledgeRecord.model_validate(data)


def _check_reserved(bundle: _Bundle, relative: str, text: str) -> None:
    try:
        data, _raw, body = split(text)
    except ValueError as exc:
        bundle.fail(relative, "", str(exc))
        return
    if relative.endswith("index.md"):
        if data is None:
            return
        if relative != "index.md":
            bundle.fail(relative, "", "an index.md carries no frontmatter (OKF v0.2 section 8)")
            return
        for key in sorted(set(data) - {"okf_version"}):
            bundle.fail(
                relative, f"/{key}", "the root index.md may carry only okf_version (OKF section 12)"
            )
        return
    if data is not None:
        bundle.fail(relative, "", "a log.md carries no frontmatter (OKF v0.2 section 9)")
    for number, line in enumerate(body.splitlines(), start=1):
        match = HEADING.match(line)
        if match and not _iso_day(match.group(1)):
            bundle.fail(
                relative,
                "",
                f"line {number}: date heading {match.group(1)!r} is not YYYY-MM-DD "
                "(OKF v0.2 section 9)",
            )


def _iso_day(text: str) -> bool:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _find_config(folder: Path) -> Path | None:
    for directory in (folder, *folder.parents):
        candidate = directory / CONFIG
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            return None
    return None


def _check_pin(bundle: _Bundle, folder: Path, config: Path | str | None) -> None:
    path = Path(config).expanduser().resolve() if config else _find_config(folder)
    if path is None or not path.is_file():
        bundle.fail(
            CONFIG,
            "/format/version",
            f"no {CONFIG} found; pin the record format: [format] version = "
            f"{records.FORMAT_VERSION}",
        )
        return
    shown = path.relative_to(folder).as_posix() if path.is_relative_to(folder) else str(path)
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        bundle.fail(shown, "", f"not valid TOML: {exc}")
        return
    for problem in records.pin_errors(parsed):
        location, _, message = problem.partition(": ")
        bundle.fail(shown, _pointer(location), message)


def _index(bundle: _Bundle) -> dict[str, str]:
    """Map every id and alias to its record path; report collisions."""
    index: dict[str, str] = {}
    for path, record in bundle.records.items():
        names = [("/id", record.id)]
        names += [(f"/aliases/{n}", alias) for n, alias in enumerate(record.aliases or [])]
        for pointer, name in names:
            owner = index.setdefault(name, path)
            if owner != path:
                bundle.fail(path, pointer, f"{name} is already the id or alias of {owner}")
    return index


def _must_resolve(link: records.Link) -> bool:
    """Record-shaped targets must resolve; paths, URLs and ticket keys are external.

    ``belongs_to`` names a container (a project, epic or ticket), so only a numbered
    record id there is held to resolve; any other link type also checks slugs.
    """
    target = link.target
    if NUMBERED.match(target):
        return True
    return link.type != "belongs_to" and SLUG.match(target) is not None


def _check_links(bundle: _Bundle, index: dict[str, str]) -> None:
    for path, record in bundle.records.items():
        for number, link in enumerate(record.links):
            if _must_resolve(link) and link.target not in index:
                bundle.fail(
                    path,
                    f"/links/{number}/target",
                    f"{link.type} target {link.target} is not the id or alias of any record",
                )


def _supersedes(bundle: _Bundle, index: dict[str, str]) -> dict[str, list[tuple[int, str]]]:
    """For each record path, the ``(link number, target path)`` of its supersedes links."""
    edges: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for path, record in bundle.records.items():
        for number, link in enumerate(record.links):
            if link.type == "supersedes" and link.target in index:
                edges[path].append((number, index[link.target]))
    return edges


def _check_supersession(bundle: _Bundle, index: dict[str, str]) -> None:
    edges = _supersedes(bundle, index)
    successors: dict[str, list[str]] = defaultdict(list)
    for path, targets in edges.items():
        for _number, target in targets:
            successors[target].append(path)
    for path, record in bundle.records.items():
        if record.status != "superseded":
            continue
        found = successors.get(path, [])
        if len(found) != 1:
            names = ", ".join(sorted(found)) or "none"
            bundle.fail(
                path,
                "/status",
                "a superseded record needs exactly one accepted record whose supersedes "
                f"link points to it; found {len(found)} ({names})",
            )
        elif bundle.records[found[0]].status not in ("accepted", "superseded"):
            successor = bundle.records[found[0]]
            bundle.fail(
                path,
                "/status",
                f"superseded by {successor.id}, which is {successor.status}, not accepted",
            )
    for path, targets in edges.items():
        if bundle.records[path].status not in ("accepted", "superseded"):
            continue
        for number, target in targets:
            old = bundle.records[target]
            if old.status != "superseded" and target != path:
                bundle.fail(
                    path,
                    f"/links/{number}/target",
                    f"supersedes {old.id}, which is still {old.status}; mark it superseded "
                    "and set valid_to",
                )
    _check_cycles(bundle, edges)


def _check_cycles(bundle: _Bundle, edges: dict[str, list[tuple[int, str]]]) -> None:
    state: dict[str, int] = {}
    reported: set[frozenset[str]] = set()

    def visit(path: str, trail: list[str]) -> None:
        state[path] = 1
        trail.append(path)
        for _number, target in edges.get(path, []):
            if state.get(target) == 1:
                cycle = trail[trail.index(target) :]
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    first = min(cycle)
                    start = cycle.index(first)
                    ordered = cycle[start:] + cycle[:start] + [first]
                    names = " -> ".join(bundle.records[item].id for item in ordered)
                    bundle.fail(first, "/links", f"supersedes cycle: {names}")
            elif target not in state:
                visit(target, trail)
        trail.pop()
        state[path] = 2

    for path in sorted(edges):
        if path not in state:
            visit(path, [])


def _check_duplicate_sources(bundle: _Bundle) -> None:
    seen: dict[tuple[str, str, str], str] = {}
    for path, record in bundle.records.items():
        if not record.source_hash or not record.title:
            continue
        key = (record.type, record.source_hash, record.title)
        first = seen.setdefault(key, path)
        if first != path:
            bundle.fail(
                path,
                "/source_hash",
                f"duplicate of {first}: same type, source_hash and title; "
                "link it with derived_from instead",
            )


# --- CI mode: accepted decisions are never edited in place ---------------------------


def _git(top: Path, *args: str) -> str:
    return run_git(top, *args, context="knowledge check").stdout


def _check_accepted_unchanged(bundle: _Bundle, folder: Path, base: str) -> None:
    try:
        top = Path(_git(folder, "rev-parse", "--show-toplevel").strip()).resolve()
        merge_base = _git(top, "merge-base", base, "HEAD").strip()
    except GitError as exc:
        raise ValueError(
            f"cannot compare with base {base!r}: {exc}; fetch it (fetch-depth: 0)"
        ) from exc
    scope = folder.relative_to(top).as_posix() or "."
    output = _git(top, "diff", "--name-status", "-M", "-z", merge_base, "--", scope)
    fields = output.split("\0")
    position = 0
    while position < len(fields) and fields[position]:
        status = fields[position]
        if status[0] in "RC":
            old, new = fields[position + 1], fields[position + 2]
            position += 3
        else:
            old = new = fields[position + 1]
            position += 2
        if status[0] not in "MDR" or not old.endswith(".md"):
            continue
        _compare_accepted(bundle, folder, top, merge_base, old, None if status[0] == "D" else new)


def _compare_accepted(
    bundle: _Bundle, folder: Path, top: Path, merge_base: str, old: str, new: str | None
) -> None:
    try:
        before, _raw, old_body = split(_git(top, "show", f"{merge_base}:{old}"))
    except (GitError, ValueError):
        return
    if not before or before.get("type") != "decision" or before.get("status") != "accepted":
        return
    name = before.get("id")
    shown = (top / (new or old)).relative_to(folder).as_posix()
    if new is None or not (top / new).is_file():
        bundle.fail(shown, "", f"accepted decision {name} was deleted; supersede it instead")
        return
    try:
        after, _raw, new_body = split((top / new).read_text(encoding="utf-8", errors="replace"))
    except ValueError:
        return
    if after is None:
        return
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key) and not _allowed_change(key, before, after):
            bundle.fail(
                shown,
                f"/{key}",
                f"accepted decision {name} is edited in place; record the change as a new "
                "decision that supersedes it",
            )
    if old_body.strip() != new_body.strip():
        bundle.fail(
            shown,
            "",
            f"accepted decision {name} has its body edited; record the change as a new "
            "decision that supersedes it",
        )


def _allowed_change(key: str, before: dict, after: dict) -> bool:
    if key == "status":
        return after.get(key) == "superseded"
    if key == "valid_to":
        return before.get(key) is None
    if key == "aliases":
        return set(before.get(key) or []) <= set(after.get(key) or [])
    if key == "id":
        old, new = str(before.get("id")), str(after.get("id"))
        return (
            not NUMBERED.match(old)
            and bool(NUMBERED.match(new))
            and old in (after.get("aliases") or [])
        )
    return False
