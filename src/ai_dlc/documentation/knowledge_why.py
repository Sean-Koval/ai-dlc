"""``knowledge why``: reconstruct a decision from local records, with its evidence.

One call answers what was decided and when, what it replaced and what replaced it,
which conventions and lessons carry it, and what evidence it rests on. Source
payloads expire (KAN-458), so the evidence is the quote, speaker and place kept in
the record's ``sources`` entries; the Source record's metadata stands beside each
quote, and the payload is reported ``present`` or ``expired``, never a failure. A
re-fetchable source (Jira, Confluence, an ADR) without a quote says where to fetch it.

It reads a records directory on disk and nothing else: no provider, no network
(outcome O1). ``superseded_by`` is derived the way ``knowledge index`` derives it
(KAN-456). The CLI and the MCP tool both call :func:`why`.
"""

import difflib
import re
from collections import deque
from pathlib import Path
from typing import Any

from ai_dlc.documentation import knowledge_bundle, record_index
from ai_dlc.documentation.knowledge_records import KnowledgeRecord, SourceRef, payload_expires

BODY_LIMIT = 1200
"""Most characters of the asked record's body; a longer body points at its file."""
REASON_LIMIT = 280
"""Most characters of a chain record's body, which says why it changed course."""
TICKET = re.compile(r"^(?!(?:DEC|CONV|LES|ACT|Q|SRC)-)[A-Z][A-Z0-9]+-[0-9]+$")
_URL = re.compile(r"^[a-z][a-z0-9+.-]*://")


class _Store:
    """One scan of the records, as ``knowledge index`` reads them."""

    def __init__(self, root: Path, project: str | None):
        self.root = root
        self.project = project
        scan = knowledge_bundle._scan(root)
        self.items = [item for item in scan.records if _visible(item, project)]
        self.names: dict[str, Any] = {}
        for item in self.items:
            for name in (item.record.id, *(item.record.aliases or ())):
                self.names.setdefault(name, item)
        visible = {item.record.id for item in self.items}
        self.successors = {
            name: [s for s in after if s in visible]
            for name, after in knowledge_bundle.superseded_by(scan).items()
        }

    def find(self, name: str):
        return self.names.get(name)


def _visible(item: Any, project: str | None) -> bool:
    """Whether a record may be shown to a caller working in ``project``.

    TODO(#261): replace with ``knowledge_check.visible_in(record, path, project)``
    once KAN-465 merges. Until then a ``boundary: customer`` record is shown only
    to a caller naming the project it sits under (``projects/<name>/``).
    """
    if item.record.boundary != "customer":
        return True
    return bool(project) and item.relative.startswith(f"projects/{project}/")


def why(root: Path | str, id: str, project: str | None = None) -> dict[str, Any]:
    """Reconstruct the record named ``id`` (an id or alias) from ``root``; read-only.

    ``status`` is ``ok``, or ``not_found`` with ``suggestions`` over ids and aliases.
    ``project`` admits ``boundary: customer`` records of that project.
    """
    folder = Path(root).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError(f"records directory not found: {root}")
    store = _Store(folder, project)
    try:
        # TODO(#261): pass project= once get takes it (KAN-465); _visible guards until then.
        found = record_index.get(folder, id)
    except LookupError:
        found = None
    item = store.find(found["id"]) if found else None
    if item is None:
        return {
            "status": "not_found",
            "id": id,
            "reason": f"no knowledge record has id or alias {id}",
            "suggestions": difflib.get_close_matches(id, sorted(store.names), n=3, cutoff=0.5),
        }
    record: KnowledgeRecord = item.record
    body, truncated = _clip(item.body, BODY_LIMIT)
    return {
        "status": "ok",
        "record": {**_summary(item), "body": body, "truncated": truncated},
        "supersedes": _chain(store, item, older=True),
        "superseded_by": _chain(store, item, older=False),
        "linked": _linked(store, item),
        "tickets": _tickets(store, item),
        "evidence": [_evidence(store, entry) for entry in record.sources],
    }


def _summary(item: Any) -> dict[str, Any]:
    record: KnowledgeRecord = item.record
    return {
        "id": record.id,
        "type": record.type,
        "title": record.title,
        "status": record.status,
        "date": record.date.isoformat(),
        "valid_from": record.valid_from.isoformat() if record.valid_from else None,
        "valid_to": record.valid_to.isoformat() if record.valid_to else None,
        "description": record.description,
        "path": item.relative,
    }


def _clip(text: str, limit: int) -> tuple[str, bool]:
    text = text.strip()
    if len(text) <= limit:
        return text, False
    return text[:limit].rstrip() + " …", True


def _chain(store: _Store, start: Any, *, older: bool) -> list[dict[str, Any]]:
    """Every record before (``supersedes``) or after (``superseded_by``) ``start``."""
    found: list[dict[str, Any]] = []
    seen = {start.record.id}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if older:
            names = [link.target for link in current.record.links if link.type == "supersedes"]
        else:
            names = store.successors.get(current.record.id, [])
        for name in names:
            item = store.find(name)
            if item is None or item.record.id in seen:
                continue
            seen.add(item.record.id)
            prose = "\n".join(line for line in item.body.splitlines() if not line.startswith("#"))
            reason, _cut = _clip(prose, REASON_LIMIT)
            found.append(
                {
                    **_summary(item),
                    "via": current.record.id,
                    "reason": reason,
                    "evidence": [
                        _evidence(store, entry) for entry in item.record.sources if entry.quote
                    ],
                }
            )
            queue.append(item)
    return found


def _names(record: KnowledgeRecord) -> set[str]:
    return {record.id, *(record.aliases or ())}


def _linked(store: _Store, item: Any) -> list[dict[str, Any]]:
    """Records that link to it (but do not supersede it), and records it implements."""
    mine = _names(item.record)
    found = []
    for other in store.items:
        if other is item or other.record.type == "source":
            continue
        for link in other.record.links:
            if link.type != "supersedes" and link.target in mine:
                found.append(_link(other, link.type, "in"))
    for link in item.record.links:
        target = store.find(link.target)
        if link.type in ("implements", "codified_as") and target is not None:
            found.append(_link(target, link.type, "out"))
    return found


def _link(item: Any, kind: str, direction: str) -> dict[str, Any]:
    record = item.record
    return {
        "id": record.id,
        "type": record.type,
        "title": record.title,
        "status": record.status,
        "link": kind,
        "direction": direction,
        "path": item.relative,
    }


def _tickets(store: _Store, item: Any) -> list[str]:
    """Tracker keys it links to, and those linked by records that cite it."""
    mine = _names(item.record)
    keys = {link.target for link in item.record.links if TICKET.match(link.target)}
    for other in store.items:
        if any(link.target in mine and link.type != "supersedes" for link in other.record.links):
            keys |= {link.target for link in other.record.links if TICKET.match(link.target)}
    return sorted(keys)


def _evidence(store: _Store, entry: SourceRef) -> dict[str, Any]:
    """One ``sources`` entry: its quote, the Source record beside it, and the payload."""
    found: dict[str, Any] = {
        "resource": entry.resource,
        "title": entry.title,
        "quote": entry.quote,
        "speaker": entry.speaker,
        "at": entry.at,
        "permalink": entry.permalink,
        "fetch": None,
    }
    source = store.find(entry.id or entry.resource) or store.find(entry.resource)
    if source is not None and source.record.type == "source":
        record: KnowledgeRecord = source.record
        found["source"] = {
            "id": record.id,
            "title": record.title,
            "date": record.date.isoformat(),
            "observed_at": record.observed_at.isoformat() if record.observed_at else None,
            "permalink": record.url,
            "participants": record.participants or [],
            "status": record.status,
            "path": source.relative,
        }
        found["title"] = found["title"] or record.title
        found["payload"] = _payload(store.root, source)
        if not payload_expires(record):
            # Jira, Confluence and ADR sources stay re-fetchable; a quote is optional.
            found["fetch"] = record.url or record.sources[0].resource
    else:
        found["source"] = None
        found["payload"] = _resource(store.root, entry.resource)
    return found


def _payload(root: Path, source: Any) -> str:
    """``present`` while the Source's raw text is kept; ``expired`` once it is gone."""
    if source.record.status == "expired":
        return "expired"
    states = [_resource(root, entry.resource) for entry in source.record.sources]
    if "present" in states or source.body.strip():
        return "present"
    return "expired"


def _resource(root: Path, resource: str) -> str:
    """A local path is ``present`` or ``missing``; a URL is not fetched (``external``)."""
    if _URL.match(resource):
        return "external"
    path = (root / resource).resolve()
    if path.is_relative_to(root) and path.is_file():
        return "present"
    return "missing"


def lines(result: dict[str, Any]) -> list[str]:
    """The plain-text answer, in the order the JSON gives it."""
    if result["status"] != "ok":
        hint = result.get("suggestions") or []
        more = f"; did you mean {', '.join(hint)}?" if hint else ""
        return [f"knowledge why: {result['reason']}{more}"]
    record = result["record"]
    out = [f"{record['id']}  {record['title'] or ''}".rstrip(), _facts(record)]
    out.append(f"file: {record['path']}")
    if record["description"]:
        out.append(record["description"])
    if record["body"]:
        out += ["", *record["body"].splitlines()]
        if record["truncated"]:
            out.append(f"(truncated; read {record['path']})")
    for heading, key in (("Supersedes", "supersedes"), ("Superseded by", "superseded_by")):
        out += ["", f"{heading}:"]
        if not result[key]:
            out.append("  (none)")
        for entry in result[key]:
            out.append(f"  {entry['id']}  {entry['title'] or ''}  [{_facts(entry)}]")
            if entry["reason"]:
                out.append(f"    why: {' '.join(entry['reason'].split())}")
            for evidence in entry["evidence"]:
                out += ["    " + text for text in _source(evidence)]
                out += ["      " + text for text in _quote(evidence)]
    out += ["", "Linked:"]
    if not result["linked"]:
        out.append("  (none)")
    for link in result["linked"]:
        arrow = f"{link['link']} -> {record['id']}" if link["direction"] == "in" else link["link"]
        out.append(f"  {link['id']}  {link['type']}  ({arrow})  {link['title'] or ''}".rstrip())
    if result["tickets"]:
        out += ["", "Tickets: " + ", ".join(result["tickets"])]
    out += ["", "Evidence:"]
    for evidence in result["evidence"]:
        out += ["  " + text for text in _source(evidence)]
        out += ["    " + text for text in _quote(evidence)]
    return out


def _facts(entry: dict[str, Any]) -> str:
    facts = [entry["status"], f"date {entry['date']}"]
    if entry["valid_from"] or entry["valid_to"]:
        facts.append(f"valid {entry['valid_from'] or '?'} to {entry['valid_to'] or 'now'}")
    return ", ".join(facts)


def _source(evidence: dict[str, Any]) -> list[str]:
    source = evidence["source"]
    if source is None:
        return [f"{evidence['resource']}  payload: {evidence['payload']}"]
    facts = [source["date"], f"payload: {evidence['payload']}"]
    if source["permalink"]:
        facts.insert(1, source["permalink"])
    if source["participants"]:
        facts.insert(-1, "participants: " + ", ".join(source["participants"]))
    return [f"{source['id']}  {source['title'] or ''}  ({'; '.join(facts)})"]


def _quote(evidence: dict[str, Any]) -> list[str]:
    if not evidence["quote"]:
        return [f"fetch from {evidence['fetch']}"] if evidence["fetch"] else []
    where = [part for part in (evidence["speaker"], evidence["at"]) if part]
    out = [f'"{evidence["quote"]}"', "  - " + ", ".join(where or ["unattributed"])]
    if evidence["permalink"]:
        out.append(f"  {evidence['permalink']}")
    return out
