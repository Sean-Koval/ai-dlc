"""``knowledge pull-transcripts``: land meeting transcripts in the knowledge inbox (KAN-457).

For every transcript the ``transcripts`` role lists since a time, the pull writes two
files into a local checkout of the knowledge repository:

- the raw payload, ``<inbox>/transcripts/<slug>.txt``: one ``[HH:MM:SS] Name: text``
  line per utterance. It expires 30 days after capture, like everything in an inbox.
- a Source record, ``<inbox>/transcripts/<slug>.md`` (``status: raw``): metadata,
  ``sources: [{id, resource, hash}]`` and ``participants``. It becomes permanent only
  when extraction promotes it into a record directory.

``<inbox>`` is the top-level ``inbox`` of the team checkout. A transcript routed to a
customer lands in the top-level ``inbox`` of that customer's own knowledge repository
instead, with ``boundary: customer`` and ``project: <name>``; customer knowledge never
enters the team repository. When that repository's local path is not configured, or it
does not declare ``[repo] boundary = "customer"`` and that ``project`` (KAN-475), the
transcript is skipped and logged; there is no fallback to the team repository.

The pull is idempotent by transcript id: a transcript is skipped when any record in
the target checkout cites ``<provider kind>:<id>`` in ``sources``. A transcript the
caller cannot read is skipped and its id logged. Routing lives in the team checkout's
``knowledge.toml``; local paths stay out of it, in the environment::

    [transcripts]
    owner = "<owner of the Source records>"   # required
    scope = "personal"                        # for team-repository transcripts; or team

    [[transcripts.customers]]
    project = "alpha"
    titles = ["Alpha"]                 # whole words of the meeting title, any case
    participants = ["@alpha.example"]  # a domain or subdomain, an exact address or name
    repo_env = "KNOWLEDGE_REPO_ALPHA"  # default; names the variable holding the local path

Once customer rules exist, a transcript that matches none goes to the team repository
only when every participant matches ``[transcripts] internal`` (internal email domains or
addresses, or exact names when the provider gives no emails); otherwise it is skipped and
logged. A customer transcript is reported by id and project only.
"""

import hashlib
import os
import re
import tomllib
import unicodedata
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from ai_dlc.documentation import knowledge_records as records
from ai_dlc.documentation.knowledge_check import SLUG, repo_boundary
from ai_dlc.documentation.record_index import read_header
from ai_dlc.errors import RefusedError, UncertainError
from ai_dlc.files import atomic_create, atomic_write, inside

FOLDER = "transcripts"
SCOPES = ("personal", "team")
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def repo_env(project: str) -> str:
    """The default variable naming a customer repository's local path."""
    return "KNOWLEDGE_REPO_" + project.upper().replace("-", "_")


_SINCE = TypeAdapter(datetime)


def parse_since(value: str | datetime) -> datetime:
    """A timezone-aware time; a bare date means its midnight UTC. A naive time is refused."""
    if isinstance(value, datetime):
        moment = value
    else:
        text = str(value).strip()
        try:
            if len(text) == 10:
                return datetime.combine(date.fromisoformat(text), datetime.min.time(), UTC)
            moment = _SINCE.validate_python(text)
        except (ValueError, ValidationError):
            raise RefusedError(f"--since must be an ISO date or time: {text!r}") from None
    if moment.tzinfo is None:
        raise RefusedError("--since needs a UTC offset, such as 2026-11-01T09:00:00-05:00")
    return moment


def routing(root: Path) -> dict:
    """The validated ``[transcripts]`` table of the checkout's ``knowledge.toml``."""
    path = root / "knowledge.toml"
    if not path.is_file():
        raise RefusedError(f"not a knowledge repository: {root} has no knowledge.toml")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise RefusedError(f"knowledge.toml is not valid TOML: {exc}") from exc
    pinned = records.pin_errors(data)
    if pinned:
        raise RefusedError("knowledge.toml " + pinned[0])
    table = data.get("transcripts")
    if not isinstance(table, dict):
        raise RefusedError("declare [transcripts] owner in knowledge.toml before pulling")
    owner = table.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        raise RefusedError("knowledge.toml [transcripts] owner is required")
    scope = table.get("scope", "personal")
    if scope not in SCOPES:
        raise RefusedError("knowledge.toml [transcripts] scope is personal or team")
    if "projects" in table:
        raise RefusedError(
            "knowledge.toml [[transcripts.projects]] is retired: customer transcripts go to "
            "the customer's own repository through [[transcripts.customers]]"
        )
    customers = []
    for number, entry in enumerate(table.get("customers") or []):
        where = f"knowledge.toml [[transcripts.customers]] entry {number + 1}"
        if not isinstance(entry, dict) or not SLUG.fullmatch(str(entry.get("project", ""))):
            raise RefusedError(f"{where}: project must be a project name (a slug)")
        patterns = {}
        for key in ("titles", "participants"):
            values = entry.get(key) or []
            if not isinstance(values, list) or not all(
                isinstance(v, str) and v.strip() for v in values
            ):
                raise RefusedError(f"{where}: {key} must be a list of non-empty strings")
            patterns[key] = [v.strip().casefold() for v in values]
        patterns["titles"] = [_folded(v) for v in patterns["titles"]]
        if bare := _bare_domains(patterns["participants"]):
            raise RefusedError(f"{where}: participants {bare[0]!r} {_BARE}")
        if not patterns["titles"] and not patterns["participants"]:
            raise RefusedError(f"{where}: give titles or participants to match")
        variable = entry.get("repo_env", repo_env(entry["project"]))
        if not isinstance(variable, str) or not _ENV_NAME.fullmatch(variable):
            raise RefusedError(f"{where}: repo_env must name an environment variable")
        customers.append({"project": entry["project"], "repo_env": variable, **patterns})
    internal = table.get("internal") or []
    if not isinstance(internal, list) or not all(
        isinstance(v, str) and v.strip() for v in internal
    ):
        raise RefusedError("knowledge.toml [transcripts] internal must be a list of strings")
    if bare := _bare_domains(internal):
        raise RefusedError(f"knowledge.toml [transcripts] internal {bare[0]!r} {_BARE}")
    return {
        "owner": owner.strip(),
        "scope": scope,
        "customers": customers,
        "internal": [v.strip().casefold() for v in internal],
    }


def route(
    item: Mapping[str, Any], customers: list[dict], internal: list[str] | None = None
) -> dict | None | str:
    """The customer a transcript belongs to, None for the team repository, or a skip reason.

    A transcript that matches two customers is skipped rather than guessed. Once customer
    rules exist, a transcript that matches none goes to the team repository only when
    every participant is internal (KAN-475); otherwise it may be an unmapped customer
    meeting, so it goes nowhere and is reported.
    """
    title = _folded(str(item.get("title", "")))
    names = [str(p).strip().casefold() for p in item.get("participants") or [] if str(p).strip()]
    emails = [str(e).strip().casefold() for e in item.get("emails") or [] if str(e).strip()]
    matched = {
        customer["project"]: customer
        for customer in customers
        if any(_has_words(title, _folded(pattern)) for pattern in customer["titles"])
        or _any_matches(names, emails, customer["participants"])
    }
    if len(matched) > 1:
        return "matches several customers: " + ", ".join(sorted(matched))
    if matched:
        return next(iter(matched.values()))
    if customers and not all_internal(names, emails, internal or []):
        return (
            "matches no customer rule and not every participant is internal; add a "
            "customer rule or list internal participants in [transcripts] internal"
        )
    return None


def all_internal(names: list[str], emails: list[str], internal: list[str]) -> bool:
    """Whether every participant is positively internal.

    An ``internal`` entry is a domain (``@corp.com`` or ``corp.com``), an exact email,
    or an exact name. An email matches its exact domain or a subdomain of it, never a
    look-alike such as ``corp.com.example`` or ``notcorp.com``. With emails, each one
    must match and no participant may be without one; without emails, each name must
    match exactly.
    """
    if not internal or not names and not emails:
        return False
    if emails and len(emails) < len(names):
        return False
    known = _People(internal)
    if emails:
        return all(known.has_email(email) for email in emails)
    return all(known.has_name(name) for name in names)


def _any_matches(names: list[str], emails: list[str], patterns: list[str]) -> bool:
    """Whether any participant matches a customer's ``participants`` rule (KAN-490).

    The rule reads as ``internal`` does: a domain matches itself and its subdomains, an
    address or a name matches exactly. When the provider gives emails, only they count,
    since a guest chooses their own display name; without emails, a name shaped like an
    address is read as one.
    """
    if not patterns:
        return False
    known = _People(patterns)
    if emails:
        return any(known.has_email(email) for email in emails)
    return any(known.has_email(name) if "@" in name else known.has_name(name) for name in names)


class _People:
    """Domains (``@corp.com`` or ``corp.com``), exact addresses and exact names."""

    def __init__(self, entries: list[str]):
        self.domains: set[str] = set()
        self.addresses: set[str] = set()
        self.names: set[str] = set()
        for entry in entries:
            value = " ".join(entry.casefold().split())
            if value.startswith("@"):
                self.domains.add(value[1:].strip("."))
            elif "@" in value:
                self.addresses.add(value)
            elif "." in value and " " not in value:
                self.domains.add(value.strip("."))
            else:
                self.names.add(value)
        self.domains.discard("")

    def has_email(self, email: str) -> bool:
        """An exact address, or an address at a domain or one of its subdomains.

        Never a look-alike such as ``corp.com.example`` or ``notcorp.com``.
        """
        email = email.strip().casefold()
        if email in self.addresses:
            return True
        _local, at, domain = email.rpartition("@")
        domain = domain.strip(".")
        return bool(at) and any(
            domain == known or domain.endswith("." + known) for known in self.domains
        )

    def has_name(self, name: str) -> bool:
        return " ".join(name.casefold().split()) in self.names


_BARE = "is a whole top-level domain; give a domain such as @alpha.example"
# Scripts written without spaces between words: no word boundary can be found there.
_UNSPACED = ("CJK ", "HIRAGANA", "KATAKANA", "THAI", "LAO", "KHMER", "MYANMAR", "TIBETAN")


def _bare_domains(entries: list[str]) -> list[str]:
    """``@io`` and the like: a domain entry with one label would match a whole TLD."""
    return [e for e in entries if e.startswith("@") and "." not in e.strip().strip("@.")]


def _folded(text: str) -> str:
    """Text compared case-blind after NFKC, without invisible format characters
    (soft hyphens, zero-width spaces), with whitespace collapsed."""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return " ".join(text.casefold().split())


def _has_words(title: str, pattern: str) -> bool:
    """Whether ``pattern`` appears in ``title`` as whole words (both already folded).

    A letter or digit next to the pattern makes it part of a longer word, so "alpha"
    is not in "alphabet"; an underscore separates. At an edge in a script written
    without spaces (Chinese, Japanese, Thai and the like) there is no boundary to
    find, so that edge matches as it is.
    """
    words = r"\s+".join(re.escape(word) for word in pattern.split())
    if not words:
        return False
    before = "" if _unspaced(pattern[0]) else r"(?<![^\W_])"
    after = "" if _unspaced(pattern[-1]) else r"(?![^\W_])"
    return re.search(before + words + after, title) is not None


def _unspaced(char: str) -> bool:
    return unicodedata.name(char, "").startswith(_UNSPACED)


def customer_repo(
    customer: Mapping[str, Any], environ: Mapping[str, str], team: Path | None = None
) -> Path | str:
    """The customer repository's local checkout, or the reason it is unusable."""
    location = environ.get(customer["repo_env"], "").strip()
    if not location:
        return (
            f"customer repository for {customer['project']} is not configured: "
            f"set {customer['repo_env']} to its local checkout"
        )
    root = Path(location).expanduser().resolve()
    if team is not None:
        team = team.resolve()
        if root == team or root.is_relative_to(team) or team.is_relative_to(root):
            return f"{customer['repo_env']} names the team checkout or a folder that overlaps it"
    config = root / "knowledge.toml"
    if not config.is_file():
        return f"{customer['repo_env']} does not name a knowledge repository checkout"
    try:
        parsed = tomllib.loads(config.read_text(encoding="utf-8"))
        problems = records.pin_errors(parsed)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        parsed, problems = {}, ["knowledge.toml is not valid TOML"]
    if problems:
        return f"customer repository for {customer['project']}: {problems[0]}"
    # The repository must declare itself this customer's (KAN-475), so a variable that
    # points at the team repository or another customer's never receives a transcript.
    declared, _problems = repo_boundary(parsed)
    if declared != customer["project"]:
        return (
            f"{customer['repo_env']} names a repository that does not declare "
            f'[repo] boundary = "customer" and project = "{customer["project"]}"'
        )
    return root


def captured(root: Path) -> set[str]:
    """``sources`` ids cited by any record in the checkout (inbox, processed or promoted)."""
    found: set[str] = set()
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts) or path.is_symlink():
            continue
        try:
            header = read_header(path)
        except (OSError, ValueError):
            continue
        for entry in (header or {}).get("sources") or []:
            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                found.add(entry["id"])
    return found


def payload(transcript: Mapping[str, Any], key: str) -> str:
    start = transcript["start"]
    lines = [
        f"# {transcript['title']}",
        f"# {key} started {start.isoformat()}",
        "# Participants: " + ", ".join(transcript.get("participants") or []),
        "",
    ]
    lines += [f"[{s['at']}] {s['speaker']}: {s['text']}" for s in transcript["segments"]]
    return "\n".join(lines) + "\n"


def source_record(
    transcript: Mapping[str, Any],
    *,
    kind: str,
    key: str,
    slug: str,
    resource: str,
    digest: str,
    settings: Mapping[str, Any],
    customer: Mapping[str, Any] | None,
) -> str:
    start: datetime = transcript["start"]
    header: dict[str, Any] = {
        "id": slug,
        "type": "source",
        "scope": "project" if customer else settings["scope"],
        "status": "raw",
        "date": start.date(),
        "owner": settings["owner"],
        "sources": [{"id": key, "resource": resource, "hash": digest}],
        "links": [],
        "title": transcript["title"],
        "tags": ["transcript", kind],
        "schema_version": records.ENVELOPE_VERSION,
        "revision": "1",
        "provider": kind,
        "observed_at": start,
        "participants": list(transcript.get("participants") or []),
    }
    if customer:
        header["boundary"] = "customer"
        header["project"] = customer["project"]
    if transcript.get("url"):
        header["url"] = transcript["url"]
    # A short, specific body: the payload carries the words, and boilerplate repeated
    # across records would only trip duplicate-quote checks.
    body = f"Raw transcript: `{resource}`.\n"
    record = records.KnowledgeRecord.model_validate(header)
    return records.render(record, body)


class TranscriptPull:
    """Pull through the ``transcripts`` role into a local knowledge checkout."""

    def __init__(
        self,
        root: Path,
        config: Mapping[str, Any],
        *,
        providers: list[str] | None = None,
        into: Path | None = None,
        registry: Any = None,
        environ: Mapping[str, str] | None = None,
    ):
        from ai_dlc.providers import Registry

        self.config = dict(config)
        selected = providers or self.config.get("roles", {}).get("transcripts") or []
        self.providers = [selected] if isinstance(selected, str) else list(selected)
        if not self.providers:
            raise RefusedError(
                "transcripts unavailable: select a provider for the transcripts role"
            )
        self.environ = os.environ if environ is None else environ
        self.registry = registry or Registry(self.config, root=root, environ=environ)
        self.into = into

    def _checkout(self) -> Path:
        if self.into is not None:
            return Path(self.into).expanduser().resolve()
        knowledge = self.config.get("roles", {}).get("knowledge")
        source = self.registry.get(knowledge) if knowledge else None
        if source is None or not hasattr(source, "repository_root") or source.remote:
            raise RefusedError(
                "pull-transcripts writes into a local knowledge checkout: pass --into, or "
                "select a git knowledge provider whose location is a local clone"
            )
        return Path(source.repository_root())

    def pull(self, since: str | datetime, *, dry_run: bool = False) -> dict:
        try:
            return self._pull(parse_since(since), dry_run)
        except RefusedError as exc:
            return {"status": "refused", "reason": str(exc)}

    def _pull(self, since: datetime, dry_run: bool) -> dict:
        from ai_dlc.providers import provider_kind
        from ai_dlc.providers.transcripts_common import TranscriptUnavailable

        root = self._checkout()
        settings = routing(root)
        seen: dict[Path, set[str]] = {root: captured(root)}
        result: dict[str, Any] = {
            "status": "ok",
            "since": since.isoformat(),
            "into": str(root),
            "dry_run": dry_run,
            "written": [],
            "planned": [],
            "existing": [],
            "skipped": [],
            "errors": [],
        }

        def target(item: Mapping[str, Any]) -> tuple[Path, dict | None] | str:
            customer = route(item, settings["customers"], settings["internal"])
            if customer is None:
                return root, None
            if isinstance(customer, str):
                return customer
            found = customer_repo(customer, self.environ, root)
            if isinstance(found, str):
                return found  # never fall back to the team repository
            if found not in seen:
                seen[found] = captured(found)
            return found, customer

        for provider in self.providers:
            kind = provider_kind(self.config, provider) or provider
            try:
                listed = self.registry.invoke(provider, "list_since", {"since": since})["items"]
            except UncertainError as exc:
                result["errors"].append({"provider": provider, "reason": str(exc)})
                continue
            for item in listed:
                key = f"{kind}:{item['id']}"
                # The result leaves the customer repository (logs, the batch), so a
                # transcript that is, or may be, a customer's is reported by id and
                # project only: no title, no local path (KAN-475).
                entry = {"provider": provider, "id": item["id"]}
                routed = target(item)
                if isinstance(routed, str):
                    result["skipped"].append({**entry, "reason": routed})
                    continue
                where, customer = routed
                project = customer["project"] if customer else None
                if customer is None:
                    entry["title"] = item["title"]
                if key in seen[where]:
                    result["existing"].append({**entry, "project": project})
                    continue
                if dry_run:
                    result["planned"].append({**entry, "project": project})
                    continue
                try:
                    transcript = self.registry.invoke(provider, "fetch", {"id": item["id"]})
                # A provider's message may quote the meeting; a customer's never leaves.
                except TranscriptUnavailable as exc:
                    reason = "the provider has no transcript for it" if customer else str(exc)
                    result["skipped"].append({**entry, "reason": reason})
                    continue
                except UncertainError as exc:
                    reason = (
                        "the provider fetch failed; run the pull again" if customer else str(exc)
                    )
                    result["errors"].append({**entry, "reason": reason})
                    continue
                # The fetched participants may add speakers; the route must not change.
                if target({**item, **transcript}) != routed:
                    result["skipped"].append(
                        {**entry, "reason": "the full transcript routes elsewhere; add a rule"}
                    )
                    continue
                written = self._write(where, transcript, kind, key, settings, customer)
                seen[where].add(key)
                if customer is not None:
                    written = {"project": customer["project"], "record": written["record"]}
                result["written"].append({**entry, **written})
        if result["errors"]:
            result["status"] = "failed"
        return result

    def _write(
        self,
        root: Path,
        transcript: Mapping[str, Any],
        kind: str,
        key: str,
        settings: Mapping[str, Any],
        customer: Mapping[str, Any] | None,
    ) -> dict:
        start: datetime = transcript["start"]
        digest10 = hashlib.sha256(key.encode()).hexdigest()[:10]
        slug = f"{kind}-{start.strftime('%Y%m%d')}-{digest10}"
        resource = f"inbox/{FOLDER}/{slug}.txt"
        text = payload(transcript, key)
        digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        record = source_record(
            transcript,
            kind=kind,
            key=key,
            slug=slug,
            resource=resource,
            digest=digest,
            settings=settings,
            customer=customer,
        )
        record_path = f"inbox/{FOLDER}/{slug}.md"
        # The payload first: the record is the capture marker, so a crash between the
        # two writes leaves an orphan payload that the next run overwrites.
        atomic_write(inside(root, resource), text, 0o644)
        if not atomic_create(inside(root, record_path), record, 0o644):
            raise RefusedError(f"{record_path} already exists with another transcript")
        return {
            "repository": str(root),
            "record": record_path,
            "payload": resource,
            "project": customer["project"] if customer else None,
        }
