"""``knowledge check``: validate a directory of knowledge records as one bundle.

Each record goes through :class:`~ai_dlc.documentation.knowledge_records.KnowledgeRecord`;
the bundle is then checked for typed-link integrity, supersession, duplicate sources and
the ``knowledge.toml`` format pin. It also applies the three Open Knowledge Format v0.2
section 11 checks: every non-reserved ``.md`` file has parseable YAML frontmatter with a
non-empty ``type``, and the reserved ``index.md`` and ``log.md`` follow sections 8 and 9.
OKF tolerates broken markdown links, so only our typed ``links`` must resolve.

Only the directories in ``[check] roots`` of ``knowledge.toml`` are read (all of
``root`` when unset), and ``README.md`` is never a record. Source records are
permanent and raw payloads expire, so ``derived_from`` must name a source record.

With ``base`` (CI mode) it also refuses in-place edits of decisions that were accepted
at the merge base. The CLI and the MCP tool both call :func:`check_records`.

Records with ``boundary: customer`` never leave their project (KAN-465). They must sit
under ``projects/<name>/``, only customer records of that project may link to them,
and no other record may quote their body. Index, render and search keep them out of
team-scope views with :func:`visible_in` and :func:`team_inputs`.
"""

import re
import tomllib
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

from ai_dlc.documentation import knowledge_records as records
from ai_dlc.documentation.knowledge_notes import split
from ai_dlc.files import GitError, run_git

RESERVED = ("index.md", "log.md")
# Not records and not OKF documents: repository prose that may sit beside the records.
SKIPPED = ("README.md",)
LEGACY_KINDS = ("runbook", "note")
CONFIG = "knowledge.toml"
NUMBERED = re.compile(r"^(?:DEC|CONV|LES|ACT|Q|SRC)-[0-9]{4,}$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*#*[ \t]*$")
# Header changes that do not count as editing an accepted decision: superseding it,
# and numbering at merge (slug id becomes PREFIX-NNNN and the slug moves to aliases).
SUPERSEDE_KEYS = ("status", "valid_to")
# Customer records live in projects/<name>/; a quote is this many words in a row.
PROJECTS = "projects"
QUOTE_WORDS = 8
_WORD = re.compile(r"[^\W_]+")


class _Bundle:
    def __init__(self) -> None:
        self.failures: list[dict[str, str]] = []
        self.legacy: list[dict[str, str]] = []
        self.records: dict[str, records.KnowledgeRecord] = {}
        self.bodies: dict[str, str] = {}
        # Prefix that turns a path relative to the checked folder into one relative to
        # the knowledge repository (the directory holding knowledge.toml).
        self.prefix = ""

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
    settings = _check_pin(bundle, folder, config)
    if settings and folder.is_relative_to(settings[0].parent):
        bundle.prefix = folder.relative_to(settings[0].parent).as_posix()
    scopes = _roots(bundle, folder, settings)
    for scope in scopes:
        for path in _markdown(scope):
            relative = path.relative_to(folder).as_posix()
            if path.name in SKIPPED:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if path.name in RESERVED:
                _check_reserved(bundle, relative, text)
                continue
            _check_record(bundle, relative, text)
    index = _index(bundle)
    _check_links(bundle, index)
    _check_supersession(bundle, index)
    _check_duplicate_sources(bundle)
    _check_boundary(bundle, index)
    if base:
        _check_against_base(bundle, folder, settings, scopes, base)
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
        data, _raw, body = split(text)
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
    bundle.bodies[relative] = body
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


def _check_pin(
    bundle: _Bundle, folder: Path, config: Path | str | None
) -> tuple[Path, str, dict] | None:
    """Check the format pin; return ``(knowledge.toml, shown path, parsed)`` when readable."""
    path = Path(config).expanduser().resolve() if config else _find_config(folder)
    if path is None or not path.is_file():
        bundle.fail(
            CONFIG,
            "/format/version",
            f"no {CONFIG} found; pin the record format: [format] version = "
            f"{records.FORMAT_VERSION}",
        )
        return None
    shown = path.relative_to(folder).as_posix() if path.is_relative_to(folder) else str(path)
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        bundle.fail(shown, "", f"not valid TOML: {exc}")
        return None
    for problem in records.pin_errors(parsed):
        location, _, message = problem.partition(": ")
        bundle.fail(shown, _pointer(location), message)
    return path, shown, parsed


def _roots(bundle: _Bundle, folder: Path, settings: tuple[Path, str, dict] | None) -> list[Path]:
    """The directories read as records: ``[check] roots`` of knowledge.toml, else ``folder``.

    Roots are relative to the directory holding knowledge.toml and must lie inside
    ``folder``. Everything outside them (raw payloads, README.md) is not read.
    """
    if settings is None:
        return [folder]
    path, shown, parsed = settings
    table = parsed.get("check")
    roots = table.get("roots") if isinstance(table, dict) else None
    if roots is None:
        return [folder]
    if not isinstance(roots, list) or not all(isinstance(item, str) for item in roots):
        bundle.fail(shown, "/check/roots", "a list of record directories is required")
        return [folder]
    found = []
    for number, name in enumerate(roots):
        directory = (path.parent / name).resolve()
        if not directory.is_relative_to(folder):
            bundle.fail(shown, f"/check/roots/{number}", f"{name} is outside {folder.name or '.'}")
        elif not directory.is_dir():
            bundle.fail(shown, f"/check/roots/{number}", f"record directory {name} not found")
        else:
            found.append(directory)
    return found


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
    ``derived_from`` always names a source record: raw payloads expire, records do not.
    """
    target = link.target
    if link.type == "derived_from" or NUMBERED.match(target):
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
            elif (
                link.type == "derived_from" and bundle.records[index[link.target]].type != "source"
            ):
                bundle.fail(
                    path,
                    f"/links/{number}/target",
                    f"derived_from target {link.target} is a "
                    f"{bundle.records[index[link.target]].type}; it must be a source record",
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
    """Two records of one type and title citing the same hashed source are duplicates."""
    seen: dict[tuple[str, str, str], str] = {}
    for path, record in bundle.records.items():
        if not record.title:
            continue
        for number, entry in enumerate(record.sources):
            if not entry.hash:
                continue
            first = seen.setdefault((record.type, entry.hash, record.title), path)
            if first != path:
                bundle.fail(
                    path,
                    f"/sources/{number}/hash",
                    f"duplicate of {first}: same type, title and source hash; "
                    "link it with derived_from instead",
                )


# --- Customer boundary: customer records never leave their project (KAN-465) -------


def project_of(path: str | PurePosixPath) -> str | None:
    """The project of a record path relative to the knowledge repository root.

    ``projects/<name>/...`` belongs to ``<name>``; any other path to no project.
    """
    parts = PurePosixPath(path).parts
    if len(parts) > 2 and parts[0] == PROJECTS and SLUG.match(parts[1]):
        return parts[1]
    return None


def _boundary(record: records.KnowledgeRecord | Mapping[str, Any]) -> object:
    if isinstance(record, Mapping):
        return record.get("boundary")
    return record.boundary


def is_customer(record: records.KnowledgeRecord | Mapping[str, Any]) -> bool:
    """Whether a record (a model or a header mapping) carries ``boundary: customer``."""
    return _boundary(record) == "customer"


def visible_in(
    record: records.KnowledgeRecord | Mapping[str, Any],
    path: str | PurePosixPath,
    project: str | None = None,
) -> bool:
    """Whether a record may appear in a view of ``project`` (``None``: a team-scope view).

    ``path`` is relative to the knowledge repository root. A customer record is
    visible only in a view of the project it sits under; a customer record outside
    ``projects/<name>/`` is visible nowhere. Every other record is visible.
    """
    if not is_customer(record):
        return True
    owner = project_of(path)
    return owner is not None and owner == project


def team_inputs[Entry: Mapping[str, Any]](
    entries: Iterable[Entry], project: str | None = None
) -> list[Entry]:
    """The entries an index, render or search of ``project`` may use, in order.

    Each entry is a mapping with ``path`` (relative to the knowledge repository root)
    and ``record`` (a model) or ``header`` (a mapping), the shapes
    :func:`ai_dlc.documentation.record_index.scan` and ``search`` return. With
    ``project`` unset, the result is safe for the top-level index and the team tree.
    """
    kept = []
    for entry in entries:
        record = entry.get("record", entry.get("header"))
        if record is None or visible_in(record, entry["path"], project):
            kept.append(entry)
    return kept


def _passages(body: str) -> set[tuple[str, ...]]:
    words = [word.casefold() for word in _WORD.findall(body)]
    return {tuple(words[n : n + QUOTE_WORDS]) for n in range(len(words) - QUOTE_WORDS + 1)}


def _check_boundary(bundle: _Bundle, index: dict[str, str]) -> None:
    owners: dict[str, str | None] = {}
    for path, record in bundle.records.items():
        if not is_customer(record):
            continue
        owner = owners[path] = project_of(_join(bundle.prefix, path))
        if owner is None:
            bundle.fail(
                path,
                "/boundary",
                f"a customer record must sit under {PROJECTS}/<name>/; it never leaves its project",
            )
    for path, record in bundle.records.items():
        mine = owners.get(path) if is_customer(record) else None
        for number, link in enumerate(record.links):
            target = index.get(link.target)
            if target is None or target not in owners:
                continue
            theirs = owners[target]
            if not is_customer(record):
                bundle.fail(
                    path,
                    f"/links/{number}/target",
                    f"{link.target} is a customer record of project {theirs or '(none)'}; "
                    "only customer records of that project may link to it",
                )
            elif mine != theirs:
                bundle.fail(
                    path,
                    f"/links/{number}/target",
                    f"{link.target} is a customer record of project {theirs or '(none)'}, "
                    f"not {mine or '(none)'}; links never cross customer projects",
                )
    _check_quotes(bundle, owners)


def _check_quotes(bundle: _Bundle, owners: dict[str, str | None]) -> None:
    """No record outside a customer project repeats a passage of its records' bodies."""
    quoted: dict[tuple[str, ...], str] = {}
    for path in sorted(owners):
        for passage in _passages(bundle.bodies.get(path, "")):
            quoted.setdefault(passage, path)
    if not quoted:
        return
    for path, record in bundle.records.items():
        mine = owners.get(path) if is_customer(record) else None
        for passage in sorted(_passages(bundle.bodies.get(path, ""))):
            source = quoted.get(passage)
            if source is None or source == path:
                continue
            if mine is not None and mine == owners[source]:
                continue
            bundle.fail(
                path,
                "",
                f"quotes {QUOTE_WORDS} or more words in a row from customer record "
                f"{bundle.records[source].id} (project {owners[source] or '(none)'}); "
                "promote it without customer content instead",
            )
            break


# --- CI mode: accepted decisions are never edited in place ---------------------------


def _git(top: Path, *args: str) -> str:
    return run_git(top, *args, context="knowledge check").stdout


def _check_against_base(
    bundle: _Bundle,
    folder: Path,
    settings: tuple[Path, str, dict] | None,
    scopes: list[Path],
    base: str,
) -> None:
    """CI mode. The base's own roots decide what is protected, never the change's.

    Every accepted decision and source record of the merge base is compared wherever
    it now lives, and a change to ``[check] roots`` may not drop a base record.
    """
    try:
        top = Path(_git(folder, "rev-parse", "--show-toplevel").strip()).resolve()
        merge_base = _git(top, "merge-base", base, "HEAD").strip()
    except GitError as exc:
        raise ValueError(
            f"cannot compare with base {base!r}: {exc}; fetch it (fetch-depth: 0)"
        ) from exc
    _check_dropped_roots(bundle, folder, top, merge_base, settings, scopes)
    _check_accepted_unchanged(bundle, folder, top, merge_base)


def _base_roots(
    folder: Path, top: Path, merge_base: str, settings: tuple[Path, str, dict] | None
) -> list[str]:
    """Record directories at the merge base, relative to the git root."""
    whole = [folder.relative_to(top).as_posix() or "."]
    config = settings[0] if settings else _find_config(folder)
    if config is None or not config.is_relative_to(top):
        return whole
    try:
        text = _git(top, "show", f"{merge_base}:{config.relative_to(top).as_posix()}")
        table = tomllib.loads(text).get("check")
    except (GitError, tomllib.TOMLDecodeError):
        return whole
    roots = table.get("roots") if isinstance(table, dict) else None
    if not isinstance(roots, list) or not all(isinstance(item, str) for item in roots):
        return whole
    found = []
    for name in roots:
        directory = (config.parent / name).resolve()
        if directory.is_relative_to(folder):
            found.append(directory.relative_to(top).as_posix() or ".")
    return found


def _check_dropped_roots(
    bundle: _Bundle,
    folder: Path,
    top: Path,
    merge_base: str,
    settings: tuple[Path, str, dict] | None,
    scopes: list[Path],
) -> None:
    roots = _base_roots(folder, top, merge_base, settings)
    if not roots:
        return
    listed = _git(top, "ls-tree", "-r", "-z", "--name-only", merge_base, "--", *roots)
    dropped = []
    for name in sorted(item for item in listed.split("\0") if item.endswith(".md")):
        path = top / name
        if path.name in SKIPPED or path.name in RESERVED or not path.is_file():
            continue
        if not any(path.resolve().is_relative_to(scope) for scope in scopes):
            dropped.append(name)
    if dropped:
        shown = settings[1] if settings else CONFIG
        bundle.fail(
            shown,
            "/check/roots",
            f"drops {len(dropped)} record file(s) checked at the base, e.g. {dropped[0]}; "
            "keep their directory in [check] roots",
        )


def _check_accepted_unchanged(bundle: _Bundle, folder: Path, top: Path, merge_base: str) -> None:
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
    if not before:
        return
    name = before.get("id")
    moved = (top / (new or old)).resolve()
    shown = moved.relative_to(folder).as_posix() if moved.is_relative_to(folder) else new or old
    deleted = new is None or not (top / new).is_file()
    if before.get("type") == "source" and deleted:
        bundle.fail(shown, "", f"source record {name} was deleted; source records are permanent")
        return
    if before.get("type") != "decision" or before.get("status") != "accepted":
        return
    if new is None or deleted:
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
