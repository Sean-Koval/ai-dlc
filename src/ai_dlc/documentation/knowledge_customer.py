"""Customer knowledge repositories and promotion out of them (KAN-475, KAN-465).

Customer knowledge lives in a separate repository per customer. ``knowledge init
--customer <name>`` writes one: ``knowledge.toml`` declares ``[repo] boundary =
"customer"`` and ``project = "<name>"``, records live under ``projects/<name>/``, there
is no wiki target, and ``deny-terms.txt`` lists the words a promoted record may never
contain. ``knowledge check`` then refuses any record, link or path that leaves the
repository (:func:`ai_dlc.documentation.knowledge_check.repo_boundary`).

``knowledge promote <id> --to <team repository>`` is the one way out (ADR 0006,
ADR 0007). A person writes a sanitised summary. Promote refuses it when it holds a
deny-list term, a web address, a customer path or eight words in a row of the customer
record, its Sources or their payloads. Otherwise it writes, on a new local branch of the
team repository, a team Source holding the summary, citing the customer record by id
only (``customer-record:<ID>``), and a team record derived from that Source. Nothing is
pushed; a person reviews the pull request. The same command promotes from
``projects/<name>/`` of a team repository when ``--to`` is left out.
"""

import os
import re
import shutil
import tempfile
import tomllib
import unicodedata
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from ai_dlc.documentation import knowledge_records as records
from ai_dlc.documentation.knowledge_check import (
    CONFIG,
    NUMBERED,
    PROJECTS,
    SLUG,
    check_records,
    is_customer,
    passages,
    project_of,
    repo_boundary,
)
from ai_dlc.documentation.knowledge_notes import split
from ai_dlc.documentation.knowledge_publish import source_sha256
from ai_dlc.errors import RefusedError
from ai_dlc.files import GitError, inside, run_git

DENY_LIST = "deny-terms.txt"
CUSTOMER_RECORD = "customer-record:"
# Promoted types and the status a new record of each starts in.
PROMOTED = {"lesson": "open", "convention": "draft", "decision": "proposed", "question": "open"}
FOLDERS = {
    "lesson": "lessons",
    "convention": "conventions",
    "decision": "decisions",
    "question": "questions",
    "source": "sources",
}
_URL = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://|\bwww\.", re.IGNORECASE)
_CUSTOMER_PATH = re.compile(r"(?:^|[\s(/`'\"])projects[\\/][a-z0-9]", re.IGNORECASE)
_SEPARATORS = re.compile(r"[\W_]+")
_IDENTITY = {
    "GIT_AUTHOR_NAME": "ai-dlc",
    "GIT_AUTHOR_EMAIL": "ai-dlc@localhost",
    "GIT_COMMITTER_NAME": "ai-dlc",
    "GIT_COMMITTER_EMAIL": "ai-dlc@localhost",
}
# Quotes are looked for in the first this-many bytes of each customer file.
_PAYLOAD_LIMIT = 5_000_000


# --- knowledge init --customer -----------------------------------------------------


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def customer_files(
    name: str,
    *,
    codeowners: Iterable[str] = (),
    deny: Iterable[str] = (),
    ai_dlc_ref: str | None = None,
) -> dict[str, str]:
    """The files of a new customer knowledge repository, by path.

    The workflow pins ai-dlc's reusable workflows to ``ai_dlc_ref``: by default the
    release tag of the installed version, never a moving branch."""
    ai_dlc_ref = ai_dlc_ref or release_ref()
    owners = [owner.strip() for owner in codeowners if owner.strip()]
    for owner in owners:
        if not re.fullmatch(r"@[A-Za-z0-9][A-Za-z0-9-]*(?:/[A-Za-z0-9._-]+)?", owner):
            raise RefusedError(f"--codeowner takes a GitHub @user or @org/team: {owner!r}")
    terms = [name, *(term.strip() for term in deny if term.strip())]
    for term in terms:
        if "\n" in term or term.startswith("#"):
            raise RefusedError(f"a deny-list term is one line and not a comment: {term!r}")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", ai_dlc_ref) or ai_dlc_ref in {"main", "master"}:
        raise RefusedError(f"--ai-dlc-ref must be a release tag or commit: {ai_dlc_ref!r}")
    workflow = "Sean-Koval/ai-dlc/.github/workflows"
    return {
        CONFIG: (
            f"# Customer knowledge repository for {name} (KAN-475). Customer knowledge\n"
            "# never leaves it; `ai-dlc knowledge promote --to <team repository>` is the\n"
            "# one way out, through a sanitised summary a person reviews.\n"
            "[format]\n"
            f"version = {records.FORMAT_VERSION}\n\n"
            "[repo]\n"
            'boundary = "customer"\n'
            f"project = {_toml_string(name)}\n"
            f"deny_list = {_toml_string(DENY_LIST)}\n\n"
            "[check]\n"
            f"roots = [{_toml_string(f'{PROJECTS}/{name}')}]\n\n"
            "# No [wiki]: nothing renders. Add [wiki] site, source and\n"
            f"# project = {_toml_string(name)} only for a wiki parent the customer approved.\n"
        ),
        DENY_LIST: (
            "# Words a promoted record may never contain: the customer's names, people,\n"
            "# products, hosts and system identifiers. One term per line; case and\n"
            "# punctuation are ignored. `ai-dlc knowledge promote` refuses a match.\n"
            + "".join(f"{term}\n" for term in dict.fromkeys(terms))
        ),
        "CODEOWNERS": (
            "# Every change to customer knowledge needs a review from these owners.\n"
            + (f"* {' '.join(owners)}\n" if owners else "# * @org/engagement-team\n")
        ),
        "README.md": (
            f"# {name} knowledge\n\n"
            "Customer knowledge for one engagement: decisions, lessons, questions and\n"
            "sources. Records carry `boundary: customer` and stay in this repository.\n\n"
            "## Where this repository may live\n\n"
            "Host it only in the company's GitHub organisation, as a private repository,\n"
            "or in the customer's own systems. Never in a personal account and never public.\n\n"
            "## Rules\n\n"
            f"- Records live under `{PROJECTS}/{name}/` and carry `boundary: customer` and\n"
            f"  `project: {name}`. `ai-dlc knowledge check .` enforces this in CI.\n"
            "- No link, source or path points outside this repository.\n"
            f"- CI runs ai-dlc's workflows pinned to `{ai_dlc_ref}`. Keep them pinned to a\n"
            "  release tag or commit; a branch would let anyone who can push there run\n"
            "  code against this repository.\n"
            "- Nothing renders to a wiki until a wiki parent the customer approved is set\n"
            "  in `knowledge.toml`.\n"
            "- Raw payloads under `inbox/` follow the team repository's 30-day retention\n"
            "  rule; nothing here deletes them automatically yet.\n"
            "- To share a lesson with the team, write a summary without customer names,\n"
            "  quotes or system identifiers and run\n"
            "  `ai-dlc knowledge promote <ID> --to <team repository> --summary <file>`.\n"
            f"  It refuses any term in `{DENY_LIST}` and any quote, and writes a branch\n"
            "  of the team repository for review.\n"
        ),
        ".github/workflows/knowledge.yml": (
            "name: Knowledge\n"
            "on:\n"
            "  pull_request:\n"
            "  push:\n"
            "    branches: [main]\n"
            "permissions:\n"
            "  contents: read\n"
            "jobs:\n"
            "  check:\n"
            "    permissions:\n"
            "      contents: read\n"
            f"    uses: {workflow}/knowledge-check.yml@{ai_dlc_ref}\n"
            "    with:\n"
            '      records: "."\n'
            f"      ai-dlc-ref: {ai_dlc_ref}\n"
            "  number:\n"
            "    # Numbers records and writes indexes through a reviewed pull request.\n"
            "    # Needs a GitHub App token in KNOWLEDGE_APP_TOKEN (contracts/README.md).\n"
            "    # The App token does the writing; GITHUB_TOKEN stays read-only.\n"
            "    if: github.event_name == 'push'\n"
            "    permissions:\n"
            "      contents: read\n"
            f"    uses: {workflow}/knowledge-merge.yml@{ai_dlc_ref}\n"
            "    with:\n"
            '      records: "."\n'
            f"      ai-dlc-ref: {ai_dlc_ref}\n"
            "    secrets:\n"
            "      token: ${{ secrets.KNOWLEDGE_APP_TOKEN }}\n"
        ),
        f"{PROJECTS}/{name}/.gitkeep": "",
        "inbox/.gitkeep": "",
    }


def release_ref() -> str:
    """The release tag of the installed ai-dlc, which customer CI pins to."""
    from ai_dlc import __version__

    return f"v{__version__}"


def init_customer(
    path: Path | str,
    name: str,
    *,
    dry_run: bool = False,
    codeowners: Iterable[str] = (),
    deny: Iterable[str] = (),
    ai_dlc_ref: str | None = None,
) -> dict[str, Any]:
    """Write a customer knowledge repository skeleton into an empty or new directory."""
    if not SLUG.fullmatch(name):
        raise RefusedError(f"--customer takes a project name (a slug): {name!r}")
    target = Path(path).expanduser()
    files = customer_files(name, codeowners=codeowners, deny=deny, ai_dlc_ref=ai_dlc_ref)
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise RefusedError(f"{target} exists and is not empty; choose a new directory")
    enclosing = _enclosing_repository(target)
    if enclosing is not None:
        raise RefusedError(
            f"{target} is inside {enclosing}; a customer repository is its own git "
            "repository, so choose a directory outside any checkout"
        )
    result: dict[str, Any] = {
        "status": "ok",
        "path": str(target),
        "project": name,
        "dry_run": dry_run,
        "files": sorted(files),
        "render": None,
        "warnings": []
        if any(o.strip() for o in codeowners)
        else ["CODEOWNERS names no owner; pass --codeowner @org/team or edit it"],
    }
    if ai_dlc_ref is None:
        result["warnings"].append(
            f"CI is pinned to {release_ref()}, the installed release. A release that "
            "predates the knowledge workflows cannot run them, so CI would not check "
            "this repository; pass --ai-dlc-ref with a tag or commit that has them"
        )
    if dry_run:
        return result
    for relative, text in files.items():
        file = inside(target, relative)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")
    run_git(target, "init", "--quiet")
    return result


def _enclosing_repository(target: Path) -> Path | None:
    """The git checkout or knowledge repository ``target`` would sit inside, if any."""
    here = target.resolve()
    for folder in (here, *here.parents):
        if (folder / ".git").exists() or (folder / CONFIG).is_file():
            return folder
    return None


# --- knowledge promote --------------------------------------------------------------


def _settings(root: Path) -> dict:
    path = root / CONFIG
    if not path.is_file():
        raise RefusedError(f"not a knowledge repository: {root} has no {CONFIG}")
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise RefusedError(f"{path} is not valid TOML: {exc}") from exc
    pinned = records.pin_errors(parsed)
    if pinned:
        raise RefusedError(f"{path}: {pinned[0]}")
    return parsed


# Letters that look like Latin ones, folded to them so "Аcme" (Cyrillic А) still matches.
_CONFUSABLES = str.maketrans(
    {
        **dict(zip("АВЕКМНОРСТУХаеорсухіјѕԁԛԝӏ", "ABEKMHOPCTYXaeopcyxijsdqwl", strict=True)),
        **dict(zip("ΑΒΕΖΗΙΚΜΝΟΡΤΥΧαικνορτυχ", "ABEZHIKMNOPTYXaiknoptux", strict=True)),
    }
)


def _normal(text: str) -> str:
    """Casefolded words: NFKC, look-alike letters folded to Latin, invisible format
    characters removed, punctuation as spaces, and runs of single letters joined
    (``A.C.M.E.`` reads ``acme``)."""
    text = unicodedata.normalize("NFKC", text).translate(_CONFUSABLES)
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    words = _SEPARATORS.sub(" ", text.casefold()).split()
    joined: list[str] = []
    run = ""
    for word in words:
        if len(word) == 1 and word.isalpha():
            run += word
            continue
        if run:
            joined.append(run)
            run = ""
        joined.append(word)
    if run:
        joined.append(run)
    return " " + " ".join(joined) + " "


def _script(char: str) -> str:
    return unicodedata.name(char, "").split(" ", 1)[0]


def mixed_script(text: str) -> list[str]:
    """Words that mix Latin letters with another alphabet's, which hide a name from
    a reader as well as from the deny list."""
    mixed = []
    for word in unicodedata.normalize("NFKC", text).split():
        scripts = {_script(char) for char in word if char.isalpha()}
        if "LATIN" in scripts and len(scripts) > 1:
            mixed.append(word)
    return mixed


def deny_terms(root: Path, parsed: Mapping[str, Any], project: str) -> list[str]:
    """The deny list of a customer project; always includes the project name.

    A customer repository names its list in ``[repo] deny_list`` (default
    ``deny-terms.txt``) and must keep one. In a team repository the optional list is
    ``projects/<name>/deny-terms.txt``.
    """
    table = parsed.get("repo")
    if isinstance(table, Mapping) and table.get("boundary") is not None:
        name = table.get("deny_list", DENY_LIST)
        if not isinstance(name, str):
            raise RefusedError("knowledge.toml [repo] deny_list names a file")
        try:
            file = inside(root, name)
        except ValueError as exc:
            raise RefusedError(str(exc)) from exc
        if not file.is_file():
            raise RefusedError(f"a customer repository keeps a deny list: {name} not found")
    else:
        file = root / PROJECTS / project / DENY_LIST
    terms = [project]
    if file.is_file():
        for line in file.read_text(encoding="utf-8").splitlines():
            term = line.strip()
            if term and not term.startswith("#"):
                terms.append(term)
    return [term for term in dict.fromkeys(terms) if _normal(term).strip()]


def denied(text: str, terms: Iterable[str]) -> list[str]:
    """The deny-list terms in ``text`` as whole words, ignoring case, width, punctuation
    and invisible characters; a plural or possessive of a term counts too."""
    haystack = _normal(text)
    found = set()
    for term in terms:
        words = _normal(term).strip()
        # A multi-word term also matches written as one word ("AcmeCorp").
        forms = {words, words.replace(" ", "")} - {""}
        if any(re.search(rf" {re.escape(form)}(?:e?s)? ", haystack) for form in forms):
            found.add(term)
    return sorted(found)


def _walk(root: Path) -> dict[str, tuple[records.KnowledgeRecord, str]]:
    """Every valid record under ``root`` by relative path, with its body."""
    found = {}
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts) or path.is_symlink():
            continue
        if not path.resolve().is_relative_to(root):
            continue
        try:
            data, _raw, body = split(path.read_text(encoding="utf-8", errors="replace"))
        except ValueError:
            continue
        if not data or "type" not in data or records.errors(data):
            continue
        found[relative.as_posix()] = (records.KnowledgeRecord.model_validate(data), body)
    return found


def _customer_texts(
    root: Path, area: Path, every: Mapping[str, tuple[records.KnowledgeRecord, str]]
) -> list[str]:
    """Every customer word a summary may not quote, read fail-closed.

    That is the raw text of every file in the customer area (the whole customer
    repository, or ``projects/<name>/`` of a team one), parsed or not, plus every
    in-repository file a record there cites. A large file is read up to a limit.
    """
    files: set[Path] = set()
    for file in area.rglob("*"):
        relative = file.relative_to(root)
        if any(part == ".git" for part in relative.parts) or file.is_symlink():
            continue
        if file.is_file():
            files.add(file)
    for key, (item, _body) in every.items():
        if not (root / key).resolve().is_relative_to(area):
            continue
        for entry in item.sources:
            relative = PurePosixPath(entry.resource.replace("\\", "/"))
            if "://" in entry.resource or relative.is_absolute() or ".." in relative.parts:
                continue
            file = root / relative
            if file.is_file() and not file.is_symlink() and file.resolve().is_relative_to(root):
                files.add(file)
    texts = []
    for file in sorted(files):
        with file.open("rb") as handle:
            texts.append(handle.read(_PAYLOAD_LIMIT).decode("utf-8", errors="replace"))
    return texts


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")[:60].strip("-")
    if not slug or not SLUG.fullmatch(slug):
        raise RefusedError("pass --slug: the title gives no usable record slug")
    return slug


def _roots(parsed: Mapping[str, Any]) -> list[str] | None:
    table = parsed.get("check")
    roots = table.get("roots") if isinstance(table, Mapping) else None
    if isinstance(roots, list) and all(isinstance(item, str) for item in roots):
        return [PurePosixPath(item).as_posix().strip("/") for item in roots]
    return None


def _git(top: Path, *args: str, environ: Mapping[str, str] | None = None) -> str:
    return run_git(top, *args, environ=environ, context="knowledge promote").stdout


def promote(
    root: Path | str,
    record_id: str,
    *,
    summary: str,
    title: str,
    owner: str,
    to: Path | str | None = None,
    kind: str | None = None,
    slug: str | None = None,
    branch: str | None = None,
    dry_run: bool = False,
    today: date | None = None,
) -> dict[str, Any]:
    """Promote a customer record to a team repository through a sanitised summary.

    Every refusal happens before anything is written. Without ``dry_run`` the two team
    records are committed on a new local branch of the team repository, checked by
    ``knowledge check``; the working tree and current branch are not touched.
    """
    source_root = Path(root).expanduser().resolve()
    source_settings = _settings(source_root)
    declared, problems = repo_boundary(source_settings)
    if problems:
        raise RefusedError(f"{source_root / CONFIG}: {problems[0]}")
    every = _walk(source_root)
    path = next(
        (key for key, (item, _b) in every.items() if record_id in (item.id, *(item.aliases or ()))),
        None,
    )
    if path is None:
        raise RefusedError(f"no valid record with id or alias {record_id} in {source_root}")
    record = every[path][0]
    if not is_customer(record):
        raise RefusedError(f"{record.id} is not a customer record; only those are promoted")
    if not NUMBERED.match(record.id):
        raise RefusedError(f"{record.id} has a draft slug id; promote it once it is numbered")
    project = project_of(path)
    if project is None or (declared is not None and project != declared):
        raise RefusedError(f"{record.id} sits outside {PROJECTS}/<name>/; fix it first")

    area = source_root if declared is not None else source_root / PROJECTS / project
    if to is None and declared is not None:
        raise RefusedError("pass --to: promotion leaves a customer repository for a team one")
    target = Path(to).expanduser().resolve() if to is not None else source_root
    target_settings = _settings(target)
    if target_settings.get("repo") is not None:
        raise RefusedError(
            f"{target} declares a repository boundary; promote only into a team repository"
        )

    kind = kind or (record.type if record.type in PROMOTED else "lesson")
    if kind not in PROMOTED:
        raise RefusedError(f"--type is one of {', '.join(PROMOTED)}")
    summary = summary.strip()
    title = title.strip()
    owner = owner.strip()
    if not summary or not title or not owner:
        raise RefusedError("a promotion needs a summary, a title and an owner")
    slug = slug or slugify(title)
    if not SLUG.fullmatch(slug) or NUMBERED.match(slug):
        raise RefusedError(f"--slug must be a lowercase slug: {slug!r}")
    branch = branch or f"promote/{slug}"
    written = f"{title}\n{summary}\n{slug}\n{branch}\n{owner}"

    terms = deny_terms(source_root, source_settings, project)
    found = denied(written, terms)
    if found:
        raise RefusedError(
            f"the promotion contains {len(found)} deny-list term(s); remove customer "
            "names and identifiers from the title, summary, slug and branch"
        )
    if mixed_script(written):
        raise RefusedError(
            "the promotion mixes Latin letters with another alphabet in one word; "
            "retype it in one alphabet"
        )
    if _URL.search(written):
        raise RefusedError("a promoted summary carries no web address; cite it after review")
    if _CUSTOMER_PATH.search(written) or f"{PROJECTS}/{project}" in written:
        raise RefusedError("a promoted summary names no customer path")
    quoted = passages(f"{title}\n{summary}") & set().union(
        *(passages(text) for text in _customer_texts(source_root, area, every))
    )
    if quoted:
        raise RefusedError(
            "the summary quotes eight or more words in a row from the customer record, "
            "its sources or their payloads; write it in your own words"
        )

    taken = {
        name for item, _body in _walk(target).values() for name in (item.id, *(item.aliases or ()))
    }
    if {slug, f"{slug}-source"} & taken:
        raise RefusedError(f"{slug} is already a record id in {target}; pass another --slug")
    folder = "team/" if (target / "team").is_dir() else ""
    source_id = f"{slug}-source"
    source_path = f"{folder}{FOLDERS['source']}/{source_id}.md"
    record_path = f"{folder}{FOLDERS[kind]}/{slug}.md"
    roots = _roots(target_settings)
    for new in (source_path, record_path):
        if roots is not None and not any(
            new == root or new.startswith(f"{root}/") or root in ("", ".") for root in roots
        ):
            raise RefusedError(f"{new} is outside [check] roots of {target / CONFIG}")
    day = today or datetime.now(UTC).date()
    body = summary + "\n"
    source = records.KnowledgeRecord.model_validate(
        {
            "id": source_id,
            "type": "source",
            "scope": "team",
            "status": "processed",
            "date": day,
            "owner": owner,
            "sources": [{"resource": f"{CUSTOMER_RECORD}{record.id}"}],
            "links": [],
            "title": title,
            "schema_version": records.ENVELOPE_VERSION,
            "revision": "1",
            "provider": "promotion",
            "observed_at": datetime.now(UTC).replace(microsecond=0),
        }
    )
    source_text = records.render(source, body)
    header = {
        "id": slug,
        "type": kind,
        "scope": "team",
        "status": PROMOTED[kind],
        "date": day.isoformat(),
        "owner": owner,
        "sources": [
            {
                "id": source_id,
                "resource": source_path,
                "hash": "sha256:" + source_sha256(body.encode("utf-8")),
            }
        ],
        "links": [{"type": "derived_from", "target": source_id}],
        "title": title,
    }
    invalid = records.errors(header)
    if invalid:
        raise RefusedError("the promoted record is invalid: " + "; ".join(invalid))
    record_text = records.render(records.KnowledgeRecord.model_validate(header), body)
    for text in (source_text, record_text):
        data, _raw, _body = split(text)
        if data is None or any(key in data for key in ("boundary", "project", "phase")):
            raise RefusedError("a promoted record never carries boundary, project or phase")

    result: dict[str, Any] = {
        "status": "ok",
        "dry_run": dry_run,
        "from": record.id,
        "to": str(target),
        "branch": branch,
        "records": [source_id, slug],
        "paths": [source_path, record_path],
    }
    if dry_run:
        result["planned"] = {source_path: source_text, record_path: record_text}
        return result
    result.update(_commit(target, branch, {source_path: source_text, record_path: record_text}))
    return result


def _commit(target: Path, branch: str, files: Mapping[str, str]) -> dict[str, Any]:
    """Commit ``files`` on a new branch in a temporary worktree; the checkout is untouched."""
    try:
        top = Path(_git(target, "rev-parse", "--show-toplevel").strip()).resolve()
    except GitError as exc:
        raise RefusedError(f"{target} is not a git checkout: {exc}") from exc
    prefix = target.relative_to(top).as_posix() if target != top else ""
    if run_git(top, "check-ref-format", "--branch", branch, check=False).returncode:
        raise RefusedError(f"not a valid branch name: {branch}")
    if (
        run_git(
            top, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False
        ).returncode
        == 0
    ):
        raise RefusedError(f"branch {branch} already exists in {top}")
    # Branch from the remote default branch when there is one, so a promotion never
    # carries the checkout's unrelated local commits.
    default = run_git(
        top, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/HEAD", check=False
    )
    base = (
        default.stdout.strip()
        if default.returncode == 0
        else _git(top, "rev-parse", "HEAD").strip()
    )
    workspace = Path(tempfile.mkdtemp(prefix="ai-dlc-promote-"))
    tree = workspace / "tree"
    created = False
    try:
        _git(top, "worktree", "add", "--quiet", "-b", branch, str(tree), base)
        created = True
        repo = tree / prefix if prefix else tree
        for relative, text in files.items():
            file = inside(repo, relative)
            if file.exists():
                raise RefusedError(f"{relative} already exists in the team repository")
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text, encoding="utf-8")
        checked = check_records(repo)
        ours = [item for item in checked["failures"] if item["path"] in files]
        if ours:
            raise RefusedError(
                "knowledge check refused the promotion: "
                + "; ".join(f"{i['path']}{i['pointer']}: {i['message']}" for i in ours)
            )
        _git(repo, "add", "--", *files)
        environ = dict(os.environ)
        if run_git(tree, "config", "user.email", check=False).returncode:
            environ.update({k: v for k, v in _IDENTITY.items() if k not in environ})
        message = f"knowledge: promote {', '.join(sorted(PurePosixPath(p).stem for p in files))}"
        _git(tree, "commit", "--quiet", "-m", message, environ=environ)
        commit = _git(tree, "rev-parse", "HEAD").strip()
    except BaseException:
        if created:
            run_git(top, "worktree", "remove", "--force", str(tree), check=False)
            run_git(top, "branch", "-D", branch, check=False)
        shutil.rmtree(workspace, ignore_errors=True)
        raise
    run_git(top, "worktree", "remove", "--force", str(tree), check=False)
    shutil.rmtree(workspace, ignore_errors=True)
    return {
        "base": base,
        "commit": commit,
        "next": f"push {branch} and open a pull request; a person reviews it before merge",
    }
