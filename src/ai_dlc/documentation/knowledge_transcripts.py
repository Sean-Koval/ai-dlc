"""``knowledge pull-transcripts``: land meeting transcripts in the knowledge inbox (KAN-457).

For every transcript the ``transcripts`` role lists since a time, the pull writes two
files into a local checkout of the knowledge repository:

- the raw payload, ``<inbox>/transcripts/<slug>.txt``: one ``[HH:MM:SS] Name: text``
  line per utterance. It expires 30 days after capture, like everything in an inbox.
- a Source record, ``<inbox>/transcripts/<slug>.md`` (``status: raw``): metadata,
  ``sources: [{id, resource, hash}]`` and ``participants``. It becomes permanent only
  when extraction promotes it into a record directory.

``<inbox>`` is ``inbox`` or, for a transcript routed to a project, that project's
``projects/<name>/inbox``. A customer project's transcript never lands outside it
(KAN-465). The pull is idempotent by transcript id: a transcript is skipped when any
record in the checkout cites ``<provider kind>:<id>`` in ``sources``. A transcript the
caller cannot read is skipped and its id logged. Routing lives in ``knowledge.toml``::

    [transcripts]
    owner = "<owner of the Source records>"   # required
    scope = "personal"                        # for unrouted transcripts; or team

    [[transcripts.projects]]
    name = "alpha"                 # projects/alpha/
    boundary = "customer"          # optional
    titles = ["Alpha"]             # case-insensitive substrings of the meeting title
    participants = ["@alpha.example"]  # substrings of a participant name or email
"""

import hashlib
import tomllib
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from ai_dlc.documentation import knowledge_records as records
from ai_dlc.documentation.knowledge_check import SLUG
from ai_dlc.documentation.record_index import read_header
from ai_dlc.errors import RefusedError, UncertainError
from ai_dlc.files import atomic_create, atomic_write, inside

FOLDER = "transcripts"
SCOPES = ("personal", "team")
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
    projects = []
    for number, entry in enumerate(table.get("projects") or []):
        where = f"knowledge.toml [[transcripts.projects]] entry {number + 1}"
        if not isinstance(entry, dict) or not SLUG.fullmatch(str(entry.get("name", ""))):
            raise RefusedError(f"{where}: name must be a project directory name")
        if entry.get("boundary") not in (None, "customer"):
            raise RefusedError(f"{where}: boundary is customer or absent")
        patterns = {}
        for key in ("titles", "participants"):
            values = entry.get(key) or []
            if not isinstance(values, list) or not all(
                isinstance(v, str) and v.strip() for v in values
            ):
                raise RefusedError(f"{where}: {key} must be a list of non-empty strings")
            patterns[key] = [v.strip().casefold() for v in values]
        if not patterns["titles"] and not patterns["participants"]:
            raise RefusedError(f"{where}: give titles or participants to match")
        projects.append({"name": entry["name"], "boundary": entry.get("boundary"), **patterns})
    return {"owner": owner.strip(), "scope": scope, "projects": projects}


def route(item: Mapping[str, Any], projects: list[dict]) -> dict | None | str:
    """The project route of a transcript, None for none, or a reason to skip it.

    A customer match wins over a non-customer one; two different customer projects
    (or two non-customer ones with no customer) are ambiguous, so the transcript is
    skipped rather than guessed.
    """
    title = str(item.get("title", "")).casefold()
    people = [p.casefold() for p in [*item.get("participants", []), *item.get("emails", [])]]
    matched = [
        project
        for project in projects
        if any(pattern in title for pattern in project["titles"])
        or any(pattern in person for pattern in project["participants"] for person in people)
    ]
    customers = {p["name"]: p for p in matched if p["boundary"] == "customer"}
    candidates = customers or {p["name"]: p for p in matched}
    if len(candidates) > 1:
        return "matches several projects: " + ", ".join(sorted(candidates))
    return next(iter(candidates.values()), None)


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
    project: Mapping[str, Any] | None,
) -> str:
    start: datetime = transcript["start"]
    header: dict[str, Any] = {
        "id": slug,
        "type": "source",
        "scope": "project" if project else settings["scope"],
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
    if project and project.get("boundary") == "customer":
        header["boundary"] = "customer"
    if transcript.get("url"):
        header["url"] = transcript["url"]
    # Keep the body short and specific: knowledge check fails a team record that shares
    # eight words in a row with a customer record, so no boilerplate sentence.
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
        seen = captured(root)
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
        for provider in self.providers:
            kind = provider_kind(self.config, provider) or provider
            try:
                listed = self.registry.invoke(provider, "list_since", {"since": since})["items"]
            except UncertainError as exc:
                result["errors"].append({"provider": provider, "reason": str(exc)})
                continue
            for item in listed:
                key = f"{kind}:{item['id']}"
                entry = {"provider": provider, "id": item["id"], "title": item["title"]}
                if key in seen:
                    result["existing"].append(entry)
                    continue
                project = route(item, settings["projects"])
                if isinstance(project, str):
                    result["skipped"].append({**entry, "reason": project})
                    continue
                if dry_run:
                    result["planned"].append({**entry, "project": project and project["name"]})
                    continue
                try:
                    transcript = self.registry.invoke(provider, "fetch", {"id": item["id"]})
                except TranscriptUnavailable as exc:
                    result["skipped"].append({**entry, "reason": str(exc)})
                    continue
                except UncertainError as exc:
                    result["errors"].append({**entry, "reason": str(exc)})
                    continue
                # The fetched participants may add speakers; route again with them.
                project = route({**item, **transcript}, settings["projects"])
                if isinstance(project, str):
                    result["skipped"].append({**entry, "reason": project})
                    continue
                written = self._write(root, transcript, kind, key, settings, project)
                seen.add(key)
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
        project: Mapping[str, Any] | None,
    ) -> dict:
        start: datetime = transcript["start"]
        digest10 = hashlib.sha256(key.encode()).hexdigest()[:10]
        slug = f"{kind}-{start.strftime('%Y%m%d')}-{digest10}"
        inbox = f"projects/{project['name']}/inbox" if project else "inbox"
        resource = f"{inbox}/{FOLDER}/{slug}.txt"
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
            project=project,
        )
        record_path = f"{inbox}/{FOLDER}/{slug}.md"
        # The payload first: the record is the capture marker, so a crash between the
        # two writes leaves an orphan payload that the next run overwrites.
        atomic_write(inside(root, resource), text, 0o644)
        if not atomic_create(inside(root, record_path), record, 0o644):
            raise RefusedError(f"{record_path} already exists with another transcript")
        return {
            "record": record_path,
            "payload": resource,
            "project": project["name"] if project else None,
            "boundary": project.get("boundary") if project else None,
        }
