"""``knowledge check``: validate a directory of knowledge records as one bundle.

Each record goes through :class:`~ai_dlc.documentation.knowledge_records.KnowledgeRecord`;
the bundle is then checked for typed-link integrity, supersession, duplicate sources and
the ``knowledge.toml`` format pin. It also applies the three Open Knowledge Format v0.2
section 11 checks: every non-reserved ``.md`` file has parseable YAML frontmatter with a
non-empty ``type``, and the reserved ``index.md`` and ``log.md`` follow sections 8 and 9.
OKF tolerates broken markdown links, so only our typed ``links`` must resolve.

Only the directories in ``[check] roots`` of ``knowledge.toml`` are read (all of
``root`` when unset), and ``README.md`` is never a record. Source records are
permanent and raw payloads expire, so ``derived_from`` must name a source record, and
a record citing an expiring Source must quote its evidence in ``sources``.

Path resources in ``sources`` must exist in the repository and match their sha256
``hash`` (KAN-478); a missing raw payload under ``inbox/`` or ``processed/`` only
warns, because payloads expire, and an external URL's hash is reported as unverified.
A record under ``team/`` has scope team and one under ``projects/<p>/`` scope project,
and ``belongs_to`` names a work-item key, a URL, a record or, when the repository
has ``projects/``, a project there.

A decision accepted by mistake is never edited: a later decision ``retracts`` it and
says why (KAN-479). The link must come from a decision and name an accepted decision.

With ``base`` (CI mode) it also refuses in-place edits of decisions that were accepted
at the merge base. The CLI and the MCP tool both call :func:`check_records`.

Records with ``boundary: customer`` never leave their project (KAN-465). They must sit
under ``projects/<name>/``, only customer records of that project may link to them,
and no other record may quote their body, cite them or their paths in ``sources`` or
link into their project from its body. Index, render and search keep them out of
team-scope views with :func:`visible_in` and :func:`team_inputs`.

Customer knowledge lives only in a customer knowledge repository (KAN-503): a
``boundary: customer`` record in any other repository fails. A customer knowledge
repository (KAN-475) declares ``[repo] boundary = "customer"`` and
``project = "<name>"`` in ``knowledge.toml``. There every record is a customer record of
that project under ``projects/<name>/``, every typed link resolves to a record of the
repository, no path in ``sources`` or the body leaves it, and a ``[wiki]`` names the
same project. :func:`repo_boundary` reads the declaration.
"""

import posixpath
import re
import tomllib
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

from ai_dlc.documentation import knowledge_records as records
from ai_dlc.documentation.knowledge_notes import split
from ai_dlc.documentation.knowledge_publish import source_sha256
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
# and numbering at merge (slug id becomes PREFIX-NNNN and the slug moves to aliases;
# links and sources that named the slug name the number).
SUPERSEDE_KEYS = ("status", "valid_to")
# Customer records live in projects/<name>/; a quote is this many words in a row.
PROJECTS = "projects"
QUOTE_WORDS = 8
_WORD = re.compile(r"[^\W_]+")
# Markdown link targets: inline [text](target) and reference [label]: target.
_MARKDOWN_LINK = re.compile(
    r"\]\(\s*<?([^)\s>]+)|^\s*\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)", re.MULTILINE
)
_PROJECT_PATH = re.compile(r"(?:^|/)projects/([a-z0-9][a-z0-9-]*)(?:/|$)")
# Raw payloads expire after 30 days, so a missing one is a warning, not a failure.
EXPIRING = ("inbox/", "processed/")
# A work-item key: an upper-case project key, a hyphen and a number (KAN-478).
WORK_ITEM = re.compile(r"^[A-Z][A-Z0-9_]*-[0-9]+$")
TEAM = "team"


class _Bundle:
    def __init__(self) -> None:
        self.failures: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []
        self.legacy: list[dict[str, str]] = []
        self.records: dict[str, records.KnowledgeRecord] = {}
        self.bodies: dict[str, str] = {}
        # Prefix that turns a path relative to the checked folder into one relative to
        # the knowledge repository (the directory holding knowledge.toml).
        self.prefix = ""
        # The knowledge repository: path resources in ``sources`` are relative to it.
        self.repo = Path()

    def fail(self, path: str, pointer: str, message: str) -> None:
        self.failures.append({"path": path, "pointer": pointer, "message": message})

    def warn(self, path: str, pointer: str, message: str) -> None:
        self.warnings.append({"path": path, "pointer": pointer, "message": message})


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
    bundle.repo = folder
    settings = _check_pin(bundle, folder, config)
    if settings and folder.is_relative_to(settings[0].parent):
        bundle.prefix = folder.relative_to(settings[0].parent).as_posix()
        bundle.repo = settings[0].parent
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
    _check_evidence(bundle, index)
    _check_supersession(bundle, index)
    _check_retractions(bundle, index)
    _check_duplicate_sources(bundle)
    _check_resources(bundle, index)
    _check_folders(bundle, index)
    _check_boundary(bundle, index)
    _check_customer_repo(bundle, index, settings)
    if base:
        _check_against_base(bundle, folder, settings, scopes, base)
    for found in (bundle.failures, bundle.warnings):
        found.sort(key=lambda item: (item["path"], item["pointer"], item["message"]))
    return {
        "status": "invalid" if bundle.failures else "valid",
        "records": len(bundle.records),
        "failures": bundle.failures,
        "legacy": bundle.legacy,
        "warnings": bundle.warnings,
    }


def failure_lines(result: dict[str, Any], prefix: str = "") -> list[str]:
    """One ``path: pointer: message`` line per failure; ``prefix`` is prepended to paths."""
    lines = []
    for item in result["failures"]:
        path = _join(prefix, item["path"])
        pointer = f" {item['pointer']}:" if item["pointer"] else ""
        lines.append(f"{path}:{pointer} {item['message']}")
    return lines


def warning_lines(result: dict[str, Any], prefix: str = "") -> list[str]:
    """One ``path: pointer: warning: message`` line per warning."""
    lines = []
    for item in result.get("warnings", []):
        pointer = f" {item['pointer']}:" if item["pointer"] else ""
        lines.append(f"{_join(prefix, item['path'])}:{pointer} warning: {item['message']}")
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
    if link.type in ("derived_from", "retracts") or NUMBERED.match(target):
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


def _check_evidence(bundle: _Bundle, index: dict[str, str]) -> None:
    """A ``derived_from`` link to an expiring Source needs quoted evidence (KAN-466).

    When the Source's payload expires (:func:`records.payload_expires`), the quote,
    its speaker and where it was said (``at`` or ``permalink``) must live in the
    record that cites it. A re-fetchable source (Jira, Confluence, an ADR) needs none.
    """
    for path, record in bundle.records.items():
        for number, link in enumerate(record.links):
            source = bundle.records.get(index.get(link.target, ""))
            if link.type != "derived_from" or not source or not records.payload_expires(source):
                continue
            cited = [e for e in record.sources if link.target in (e.id, e.resource)]
            if not any(e.quote and e.speaker and (e.at or e.permalink) for e in cited):
                bundle.fail(
                    path,
                    f"/links/{number}",
                    f"derived_from {link.target} needs evidence: a sources entry for it "
                    "with quote, speaker and at or permalink (its payload expires)",
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


def _check_retractions(bundle: _Bundle, index: dict[str, str]) -> None:
    """``retracts`` goes from a decision to another, accepted, decision (KAN-479)."""
    for path, record in bundle.records.items():
        for number, link in enumerate(record.links):
            if link.type != "retracts" or link.target not in index:
                continue
            pointer = f"/links/{number}"
            target = bundle.records[index[link.target]]
            if record.type != "decision":
                bundle.fail(path, pointer, f"a {record.type} cannot retract; only a decision can")
            elif index[link.target] == path:
                bundle.fail(path, pointer, "a decision cannot retract itself")
            elif any(item.type == "retracts" for item in target.links):
                bundle.fail(
                    path,
                    pointer,
                    f"retracts {target.id}, which is itself a retraction; supersede it with "
                    "a new decision instead",
                )
            elif target.type != "decision" or target.status != "accepted":
                bundle.fail(
                    path,
                    pointer,
                    f"retracts {target.id}, a {target.status} {target.type}; only an "
                    "accepted decision is retracted (edit or reject a proposal instead)",
                )


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


# --- Resources, folders and belongs_to (KAN-478) -------------------------------------


def _repo_path(value: str) -> str | None:
    """``value`` as a path relative to the repository, or ``None`` if it is not a path.

    URLs, record ids and work-item keys are not paths; a path holds a ``/`` or a ``.``.
    """
    if "://" in value or not ("/" in value or "." in value):
        return None
    return posixpath.normpath(value.replace("\\", "/"))


def _in_repo(repo: Path, relative: str) -> bool:
    """A path names a file of the repository when its first part is there, or expires.

    Other paths (a vault note, a transcript store) live elsewhere and are not checked.
    """
    if relative.startswith(("../", "/")) or relative == "..":
        return False
    return relative.startswith(EXPIRING) or (repo / relative.split("/")[0]).exists()


def _digests(data: bytes) -> set[str]:
    """Accepted hashes of a file: the whole file, or the body of a record file."""
    found = {"sha256:" + source_sha256(data)}
    try:
        front, _raw, body = split(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return found
    if front is not None:
        found.add("sha256:" + source_sha256(body.encode("utf-8")))
    return found


def _check_resources(bundle: _Bundle, index: dict[str, str]) -> None:
    """Path resources exist and match their hash; external hashes are unverified."""
    for path, record in bundle.records.items():
        for number, entry in enumerate(record.sources):
            pointer = f"/sources/{number}"
            value = entry.resource
            relative = None if value in index else _repo_path(value)
            if relative is not None and not _in_repo(bundle.repo, relative):
                relative = None
                if entry.hash:
                    bundle.warn(
                        path, f"{pointer}/hash", f"{value} is not in the repository; unverified"
                    )
            elif "://" in value and entry.hash:
                bundle.warn(path, f"{pointer}/hash", f"{value} is external; hash unverified")
            if relative is None:
                continue
            file = bundle.repo / relative
            if not file.is_file():
                if relative.startswith(EXPIRING):
                    bundle.warn(
                        path,
                        f"{pointer}/resource",
                        f"{value} not found; raw payloads expire after 30 days",
                    )
                else:
                    bundle.fail(
                        path, f"{pointer}/resource", f"{value} does not exist in the repository"
                    )
                continue
            if not entry.hash:
                continue
            if not entry.hash.startswith("sha256:"):
                bundle.warn(path, f"{pointer}/hash", "only sha256 hashes are verified")
            elif entry.hash not in _digests(file.read_bytes()):
                bundle.fail(
                    path,
                    f"{pointer}/hash",
                    f"does not match {value}: neither the sha256 of the file nor of its body",
                )


def _projects(bundle: _Bundle) -> set[str] | None:
    """Project names: the directories under ``projects/`` of the repository.

    ``None`` when there is no ``projects/``: without that registry (a vault, where a
    learning belongs to an ai-dlc work id) a slug target cannot be resolved.
    """
    folder = bundle.repo / PROJECTS
    if not folder.is_dir():
        return None
    return {item.name for item in folder.iterdir() if item.is_dir() and SLUG.match(item.name)}


def _check_folders(bundle: _Bundle, index: dict[str, str]) -> None:
    """Scope matches the folder, and ``belongs_to`` names a key, a record or a project."""
    projects = _projects(bundle)
    for path, record in bundle.records.items():
        located = _join(bundle.prefix, path)
        mine = project_of(located)
        top = PurePosixPath(located).parts[0]
        if top == TEAM and record.scope != "team":
            bundle.fail(
                path, "/scope", f"a record under {TEAM}/ has scope team, not {record.scope}"
            )
        elif mine and record.scope != "project":
            bundle.fail(
                path,
                "/scope",
                f"a record under {PROJECTS}/{mine}/ has scope project, not {record.scope}",
            )
        for number, link in enumerate(record.links):
            target = link.target
            if link.type != "belongs_to" or NUMBERED.match(target) or target in index:
                continue
            if WORK_ITEM.match(target) or "://" in target:
                continue
            pointer = f"/links/{number}/target"
            if not SLUG.match(target):
                bundle.fail(
                    path,
                    pointer,
                    f"belongs_to {target} is malformed: not a work-item key (KEY-123), a URL, "
                    "a record id or a project slug",
                )
            elif projects is None:
                continue
            elif target not in projects:
                bundle.fail(
                    path,
                    pointer,
                    f"belongs_to {target} is not a work-item key (KEY-123), the id of a record "
                    f"or a project under {PROJECTS}/",
                )
            elif mine and target != mine:
                bundle.fail(
                    path,
                    pointer,
                    f"belongs_to project {target}, but the record sits under {PROJECTS}/{mine}/",
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
    _check_sources(bundle, index, owners)
    _check_markdown_links(bundle, owners)
    _check_quotes(bundle, owners)


def _check_markdown_links(bundle: _Bundle, owners: dict[str, str | None]) -> None:
    """No record outside a customer project links into it from its body.

    The link path alone names the customer, so even a broken link fails.
    """
    projects = {owner for owner in owners.values() if owner}
    if not projects:
        return
    for path in bundle.records:
        located = _join(bundle.prefix, path)
        mine = project_of(located)
        for match in _MARKDOWN_LINK.finditer(bundle.bodies.get(path, "")):
            target = re.sub(r"[\\/]+", "/", match.group(1) or match.group(2))
            if "://" not in target and not target.startswith("/"):
                target = posixpath.normpath(posixpath.join(posixpath.dirname(located), target))
            found = _PROJECT_PATH.search(target)
            if found and found.group(1) in projects and found.group(1) != mine:
                bundle.fail(
                    path,
                    "",
                    f"links into customer project {found.group(1)} from its body; the "
                    "path names the customer",
                )
                break


def _check_sources(bundle: _Bundle, index: dict[str, str], owners: dict[str, str | None]) -> None:
    """A record outside the boundary cites no customer record and no customer path.

    Promotion writes a team Source holding a summary a person sanitised; its
    ``sources`` name no customer path, and the team record derives from it.
    """
    projects = {owner for owner in owners.values() if owner}
    for path, record in bundle.records.items():
        if is_customer(record):
            continue
        for number, entry in enumerate(record.sources):
            for value in (entry.id, entry.resource):
                if not value:
                    continue
                target = index.get(value)
                match = _PROJECT_PATH.search(re.sub(r"[\\/]+", "/", value))
                if target in owners:
                    project = owners[target] or "(none)"
                elif match and match.group(1) in projects:
                    project = match.group(1)
                else:
                    continue
                bundle.fail(
                    path,
                    f"/sources/{number}",
                    f"cites customer project {project}; promote through a team source "
                    "whose sources name no customer path",
                )
                break


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


def passages(text: str) -> set[tuple[str, ...]]:
    """Every run of :data:`QUOTE_WORDS` words in ``text``, casefolded: what counts as a quote."""
    return _passages(text)


# --- Customer repository: the whole repository is one customer project (KAN-475) -----

REPO = "repo"
TEAM_REPO_CUSTOMER = (
    "a boundary: customer record belongs in its customer's own repository, whose "
    'knowledge.toml declares [repo] boundary = "customer"; move it there'
)
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_DRIVE = re.compile(r"^[A-Za-z]:")  # a one-letter scheme is a drive
_AUTOLINK = re.compile(r"<([A-Za-z][A-Za-z0-9+.-]*:[^>\s]*)>")
_HTML_LINK = re.compile(r"""\b(?:href|src)\s*=\s*["']?([^"'\s>]+)""", re.IGNORECASE)


def repo_boundary(parsed: Mapping[str, Any]) -> tuple[str | None, list[str]]:
    """``(project, problems)`` of a parsed ``knowledge.toml`` ``[repo]`` declaration.

    ``project`` is set only for a valid customer repository declaration. Any other
    ``[repo]`` table, a typo or a missing key included, yields problems; callers treat it
    as a customer repository of no project, which nothing may enter or leave.
    """
    table = parsed.get(REPO)
    if table is None:
        return None, []
    if not isinstance(table, Mapping):
        return None, [f"{REPO}: a table is required"]
    boundary = table.get("boundary")
    project = table.get("project")
    problems = []
    if boundary != "customer":
        problems.append(f'{REPO}/boundary: the only repository boundary is "customer"')
    if not isinstance(project, str) or not SLUG.fullmatch(project):
        problems.append(f"{REPO}/project: name the customer project (a slug)")
    if problems:
        return None, problems
    return project, []


def _escapes(relative: str) -> bool:
    """A normalized path that climbs out of the repository or is absolute."""
    return (
        relative in ("..", "")
        or relative.startswith(("../", "/", "~"))
        or re.match(r"^[A-Za-z]:/", relative) is not None
    )


def _check_customer_repo(
    bundle: _Bundle, index: dict[str, str], settings: tuple[Path, str, dict] | None
) -> None:
    """In a declared customer repository nothing points outside it (KAN-475).

    Anywhere else a ``boundary: customer`` record fails: customer knowledge lives only
    in its customer's own repository, never in a team one (KAN-503).
    """
    if settings is None or settings[2].get(REPO) is None:
        for path, record in bundle.records.items():
            if is_customer(record):
                bundle.fail(path, "/boundary", TEAM_REPO_CUSTOMER)
        return
    config_path, shown, parsed = settings
    root = config_path.parent.resolve()
    declared = parsed.get(REPO) is not None
    project, problems = repo_boundary(parsed)
    for problem in problems:
        location, _, message = problem.partition(": ")
        bundle.fail(shown, _pointer(location.replace("/", ".")), message)
    if project is None and not (declared and problems):
        return
    wiki = parsed.get("wiki")
    if wiki is not None and (not isinstance(wiki, Mapping) or wiki.get("project") != project):
        bundle.fail(
            shown,
            "/wiki/project",
            f"a customer repository renders only to a wiki declared for project {project}; "
            "leave [wiki] unset until the customer approves one",
        )
    for path, record in bundle.records.items():
        located = _join(bundle.prefix, path)
        if not is_customer(record) or record.project != project:
            bundle.fail(
                path,
                "/boundary",
                f"every record of this customer repository carries boundary: customer and "
                f"project: {project}",
            )
        elif project_of(located) != project:
            bundle.fail(
                path,
                "",
                f"a record of this customer repository sits under {PROJECTS}/{project}/",
            )
        for number, link in enumerate(record.links):
            target = link.target
            if target in index:
                continue
            if link.type == "belongs_to" and (
                target == project or (WORK_ITEM.match(target) and not NUMBERED.match(target))
            ):
                continue
            bundle.fail(
                path,
                f"/links/{number}/target",
                f"{link.type} target {target} resolves outside this customer repository",
            )
        for number, entry in enumerate(record.sources):
            for value in (entry.id, entry.resource):
                if not value or value in index:
                    continue
                relative = _repo_path(value)
                outside = (
                    value.casefold().startswith("file:")
                    or (relative is not None and _escapes(relative))
                    or (value == entry.id and _names_a_record(value))
                )
                if outside:
                    bundle.fail(
                        path,
                        f"/sources/{number}",
                        f"{value} resolves outside this customer repository",
                    )
                    break
        body = bundle.bodies.get(path, "")
        for target in _body_links(body):
            if _leaves_repo(root, located, target):
                bundle.fail(path, "", f"links to {target}, outside this customer repository")
                break


def _names_a_record(value: str) -> bool:
    """A ``sources`` id shaped like a record id or a draft slug, not a work item or key."""
    return bool(NUMBERED.match(value)) or (
        bool(SLUG.fullmatch(value)) and not WORK_ITEM.match(value)
    )


def _body_links(body: str) -> list[str]:
    """Link targets in a body: Markdown links and references, autolinks and HTML."""
    targets = [m.group(1) or m.group(2) for m in _MARKDOWN_LINK.finditer(body)]
    targets += [m.group(1) for m in _AUTOLINK.finditer(body)]
    targets += [m.group(1) for m in _HTML_LINK.finditer(body)]
    return [target.replace("\\", "/") for target in targets]


def _leaves_repo(root: Path, located: str, target: str) -> bool:
    """A body link target that names a local file outside the repository.

    Web links stay allowed; ``file:`` links, drive and network paths, and relative paths
    that climb out, lexically or through a symlink, are not.
    """
    if target.casefold().startswith("file:") or _DRIVE.match(target):
        return True
    if _SCHEME.match(target) or target.startswith("#"):
        return False
    if target.startswith(("/", "~")):
        return True
    plain = target.split("#", 1)[0].split("?", 1)[0]
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(located), plain))
    if _escapes(joined):
        return True
    return not (root / joined).resolve().is_relative_to(root)


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
    _check_reused_slugs(bundle, folder, top, merge_base, base, settings)


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


def _claimed(
    top: Path, folder: Path, revision: str, settings: tuple[Path, str, dict] | None, slugs: set[str]
) -> dict[str, str]:
    """Which of ``slugs`` are an id or alias of a record at ``revision``, and where."""
    roots = _base_roots(folder, top, revision, settings)
    if not roots or not slugs:
        return {}
    patterns = [item for slug in sorted(slugs) for item in ("-e", slug)]
    listed = run_git(
        top, "grep", "-l", "-z", "-F", "-w", *patterns, revision, "--", *roots, check=False
    ).stdout
    found: dict[str, str] = {}
    for hit in sorted(item for item in listed.split("\0") if item):
        name = hit.removeprefix(f"{revision}:")
        if not name.endswith(".md"):
            continue
        try:
            data, _raw, _body = split(_git(top, "show", f"{revision}:{name}"))
        except (GitError, ValueError):
            continue
        if not data:
            continue
        names = {data.get("id"), *(data.get("aliases") or [])}
        for slug in slugs & {item for item in names if isinstance(item, str)}:
            found.setdefault(slug, name)
    return found


def _check_reused_slugs(
    bundle: _Bundle,
    folder: Path,
    top: Path,
    merge_base: str,
    base: str,
    settings: tuple[Path, str, dict] | None,
) -> None:
    """A new record's slug id is not already an id or alias on the base branch.

    The base tip is read, not the merge base: a record merged since this branch
    forked, and perhaps numbered with the slug moved to ``aliases``, still owns it.
    A slug the merge base already held belongs to this record, not a new one.
    """
    slugs = {
        record.id: path for path, record in bundle.records.items() if not NUMBERED.match(record.id)
    }
    taken = _claimed(top, folder, base, settings, set(slugs))
    if not taken:
        return
    held = _claimed(top, folder, merge_base, settings, set(taken))
    for slug, name in sorted(taken.items()):
        if slug in held:
            continue
        bundle.fail(
            slugs[slug],
            "/id",
            f"{slug} is already the id or alias of {name} on {base}; choose another slug",
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
    aliases = _aliases(bundle)
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key) and not _allowed_change(key, before, after, aliases):
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


def _aliases(bundle: _Bundle) -> dict[str, set[str]]:
    """The aliases of every numbered record at ``HEAD``, keyed by its id."""
    return {
        record.id: set(record.aliases or [])
        for record in bundle.records.values()
        if NUMBERED.match(record.id)
    }


def _renumbered(old: object, new: object, aliases: dict[str, set[str]]) -> bool:
    """``old`` is a slug that numbering replaced with ``new``, which keeps it as an alias."""
    return (
        isinstance(old, str)
        and isinstance(new, str)
        and not NUMBERED.match(old)
        and bool(NUMBERED.match(new))
        and old in aliases.get(new, set())
    )


def _only_renumbered(
    before: object, after: object, fields: tuple[str, ...], aliases: dict[str, set[str]]
) -> bool:
    """Lists equal entry by entry, except ``fields`` that numbering moved slug to number."""
    if not isinstance(before, list) or not isinstance(after, list) or len(before) != len(after):
        return False
    for old, new in zip(before, after, strict=True):
        if not isinstance(old, dict) or not isinstance(new, dict) or set(old) != set(new):
            return False
        for name in old:
            if old[name] != new[name] and not (
                name in fields
                and (
                    _renumbered(old[name], new[name], aliases)
                    or (name == "resource" and _renamed_file(old[name], new[name], aliases))
                )
            ):
                return False
    return True


def _renamed_file(old: object, new: object, aliases: dict[str, set[str]]) -> bool:
    """``old`` is a path to a slug-named record file that numbering renamed to ``new``."""
    if not isinstance(old, str) or not isinstance(new, str) or "://" in old:
        return False
    before, after = PurePosixPath(old.replace("\\", "/")), PurePosixPath(new)
    return (
        before.parent == after.parent
        and before.suffix == after.suffix == ".md"
        and _renumbered(before.stem, after.stem, aliases)
    )


def _allowed_change(
    key: str, before: dict, after: dict, aliases: dict[str, set[str]] | None = None
) -> bool:
    known = aliases or {}
    if key == "links":
        return _only_renumbered(before.get(key), after.get(key), ("target",), known)
    if key == "sources":
        return _only_renumbered(before.get(key), after.get(key), ("id", "resource"), known)
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
