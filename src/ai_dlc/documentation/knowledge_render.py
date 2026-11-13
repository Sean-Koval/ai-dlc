"""``knowledge render``: the one writer of the wiki, a read view of the records (KAN-430).

The git knowledge repository is canonical (ADR 0004). For each record changed since a
revision, render upserts one page, keyed by the record id, through the ``wiki`` role.
It also regenerates one index page per scope. Every page opens with a do-not-edit banner
that links to its source file. Render never reads a page body: a page whose content hash
and version are what the last render wrote is skipped, and any other page is rewritten,
so a hand edit is restored.

The knowledge repository declares its one wiki site in ``knowledge.toml``; there is no
default, and a wiki provider bound to any other site is refused before anything leaves::

    [wiki]
    site = "example.atlassian.net"
    source = "https://github.com/<owner>/<repo>/blob/main/"  # banner link prefix
    # project = "<name>"  # a customer project's own wiki: only projects/<name>/ records

Render filters its inputs with :func:`~ai_dlc.documentation.knowledge_check.team_inputs`
(KAN-465). A wiki that declares no ``project`` gets no ``boundary: customer`` record.
A wiki declared for a customer project gets only the records under ``projects/<name>/``.
"""

import hashlib
import json
import re
import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ai_dlc.documentation.knowledge_check import SLUG, project_of, team_inputs
from ai_dlc.documentation.knowledge_records import RETRACTED
from ai_dlc.errors import RefusedError

HASH_PROPERTY = "ai-dlc-hash"
SCOPES = ("personal", "project", "team")
_SITE = re.compile(r"[a-z0-9-]+\.atlassian\.net")


def wiki_target(root: Path) -> dict:
    """The ``[wiki]`` table of the repository's ``knowledge.toml``; raises when undeclared."""
    path = root / "knowledge.toml"
    try:
        data = tomllib.loads(path.read_text()) if path.is_file() else {}
    except tomllib.TOMLDecodeError as exc:
        raise RefusedError(f"knowledge.toml is not valid TOML: {exc}") from exc
    wiki = data.get("wiki")
    if not isinstance(wiki, dict):
        raise RefusedError("no wiki target: declare [wiki] site in knowledge.toml")
    site = wiki.get("site")
    if not isinstance(site, str) or not _SITE.fullmatch(site):
        raise RefusedError("knowledge.toml [wiki] site must be a bare atlassian.net host name")
    source = wiki.get("source")
    if not isinstance(source, str) or not source.startswith("https://"):
        raise RefusedError("knowledge.toml [wiki] source must be an https link prefix")
    if "boundary" in wiki:
        raise RefusedError(
            "knowledge.toml [wiki] boundary is retired: declare [wiki] project for a "
            "customer project's wiki"
        )
    project = wiki.get("project")
    if project is not None and (not isinstance(project, str) or not SLUG.fullmatch(project)):
        raise RefusedError("knowledge.toml [wiki] project must be a project directory name")
    return {
        "site": site,
        "source": source if source.endswith("/") else source + "/",
        "project": project,
    }


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(_text(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, default=str)
    return "" if value is None else str(value)


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def banner(source: str, path: str | None) -> str:
    where = f"[{path}]({source}{path})" if path else f"[the knowledge repository]({source})"
    return (
        "> **Do not edit this page.** `ai-dlc knowledge render` writes it from "
        f"{where}; the next render overwrites any edit here. Change the record in git."
    )


def content_hash(page: Mapping[str, Any]) -> str:
    """Digest of everything an upsert writes, so an unchanged page is never rewritten."""
    fields = {key: page[key] for key in ("title", "body", "labels", "parent")}
    fields["properties"] = {k: v for k, v in page["properties"].items() if k != HASH_PROPERTY}
    data = json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _finish(page: dict) -> dict:
    page["properties"][HASH_PROPERTY] = content_hash(page)
    return page


def _title(header: Mapping[str, Any], path: str) -> str:
    name = header.get("title") or header.get("description") or Path(path).stem
    return f"{header['id']} · {_text(name)}"


def _shown(item: Mapping[str, Any]) -> dict:
    """The header readers see: a retracted record (KAN-479) shows status ``retracted``."""
    header = dict(item["header"])
    if item.get("retracted_by"):
        header["status"] = RETRACTED
    return header


def record_page(record: Mapping[str, Any], target: Mapping[str, str]) -> dict:
    header, path = _shown(record), record["path"]
    properties = {
        str(key): _text(value)
        for key, value in header.items()
        if key not in {"title", "description", "links", "sources"} and value is not None
    }
    if record.get("retracted_by"):
        properties["retracted_by"] = _text(record["retracted_by"])
    properties["path"] = path
    rows = "\n".join(f"| {key} | {_cell(value)} |" for key, value in sorted(properties.items()))
    links = "\n".join(
        f"- {link.get('type')}: {link.get('target')}"
        for link in header.get("links") or []
        if isinstance(link, dict)
    )
    sections = [
        banner(target["source"], path),
        "| Field | Value |\n| --- | --- |\n" + rows,
    ]
    if links:
        sections.append("## Links\n\n" + links)
    if record.get("body", "").strip():
        sections.append(record["body"].strip())
    labels = [header["id"], str(header.get("type")), str(header.get("scope"))]
    labels += [str(header["status"])] if header.get("status") else []
    labels += [str(tag) for tag in header.get("tags") or []]
    return _finish(
        {
            "key": header["id"],
            "title": _title(header, path),
            "body": "\n\n".join(sections) + "\n",
            "properties": properties,
            "labels": sorted(set(labels)),
            "parent": f"index-{header.get('scope')}",
        }
    )


def index_page(scope: str, records: list[dict], target: Mapping[str, str]) -> dict:
    rows = "\n".join(
        "| {id} | {type} | {status} | {title} |".format(
            id=item["header"]["id"],
            type=_cell(_text(item["header"].get("type"))),
            status=_cell(_text(_shown(item).get("status"))),
            title=_cell(_title(item["header"], item["path"]).split(" · ", 1)[1]),
        )
        for item in sorted(records, key=lambda item: item["header"]["id"])
    )
    body = (
        banner(target["source"], None)
        + f"\n\n{len(records)} {scope} records.\n\n"
        + "| Id | Type | Status | Title |\n| --- | --- | --- | --- |\n"
        + rows
        + "\n"
    )
    return _finish(
        {
            "key": f"index-{scope}",
            "title": f"Knowledge index: {scope}",
            "body": body,
            "properties": {"scope": scope, "records": str(len(records))},
            "labels": ["knowledge-index", scope],
            "parent": None,
        }
    )


def _action(existing: Mapping[str, Any] | None, page: Mapping[str, Any]) -> str:
    if existing is None:
        return "create"
    same = existing.get("properties", {}).get(HASH_PROPERTY) == page["properties"][HASH_PROPERTY]
    untouched = existing.get("version") == existing.get("rendered_version")
    if same and untouched:
        return "unchanged"
    return "update" if untouched else "restore"


class KnowledgeRender:
    """Render through the ``knowledge`` and ``wiki`` roles of one project configuration."""

    def __init__(
        self,
        root: Path,
        config: Mapping[str, Any],
        *,
        knowledge: str | None = None,
        wiki: str | None = None,
        registry: Any = None,
        environ: Mapping[str, str] | None = None,
    ):
        from ai_dlc.providers import Registry

        self.config = dict(config)
        roles = self.config.get("roles", {})
        self.knowledge = knowledge or roles.get("knowledge")
        self.wiki = wiki or roles.get("wiki")
        if not self.knowledge:
            raise RefusedError("knowledge unavailable: select a provider for the knowledge role")
        if not self.wiki:
            raise RefusedError("wiki unavailable: select a provider for the wiki role")
        self.registry = registry or Registry(self.config, root=root, environ=environ)

    def _call(self, provider: str, operation: str, payload: dict) -> dict:
        return self.registry.invoke(provider, operation, payload)

    def _target(self) -> dict:
        source = self.registry.get(self.knowledge)
        if not hasattr(source, "repository_root"):
            raise RefusedError("knowledge render needs a knowledge provider with a repository")
        target = wiki_target(Path(source.repository_root()))
        settings = self.config.get("providers", {}).get(self.wiki, {})
        bound = urlsplit(str(settings.get("site_url") or "")).hostname
        if bound != target["site"]:
            raise RefusedError(
                f"site mismatch: knowledge.toml renders to {target['site']}, "
                f"the wiki provider is bound to {bound or 'no site'}"
            )
        return target

    def render(self, since: str, *, dry_run: bool = False) -> dict:
        try:
            return self._render(since, dry_run)
        except RefusedError as exc:
            return {"status": "refused", "reason": str(exc)}

    def _render(self, since: str, dry_run: bool) -> dict:
        target = self._target()
        changed = self._call(self.knowledge, "list_changed", {"since": since})
        project = target["project"]
        found = self._call(
            self.knowledge,
            "search",
            {
                "type": None,
                "scope": None,
                "labels": [],
                "status": None,
                "text": None,
                "project": project,
            },
        )
        # The provider already filters; render filters again so no provider can leak.
        everything = team_inputs(found["items"], project)
        if project is not None:
            everything = [item for item in everything if project_of(item["path"]) == project]
        kept = {id(item) for item in everything}
        skipped = [
            {"key": item["id"], "reason": "outside this wiki's project"}
            for item in found["items"]
            if id(item) not in kept
        ]
        by_scope: dict[str, list[dict]] = {}
        for item in everything:
            by_scope.setdefault(str(item["header"].get("scope")), []).append(item)
        pages = [index_page(scope, by_scope[scope], target) for scope in sorted(by_scope)]
        visible = {item["id"] for item in everything}
        retracted = {
            item["id"]: item["retracted_by"] for item in everything if item.get("retracted_by")
        }
        orphaned = []
        wanted: list[str] = []
        for entry in changed["changed"]:
            if entry["change"] == "deleted" or not entry.get("id"):
                if entry["change"] == "deleted":
                    orphaned.append(entry["path"])
                continue
            wanted.append(entry["id"])
        # A new retraction changes the page of the record it retracts (KAN-479).
        wanted += sorted(name for name, by in retracted.items() if set(by) & set(wanted))
        for name in dict.fromkeys(wanted):
            if name not in visible:
                continue
            record = self._call(self.knowledge, "get", {"id": name, "project": project})
            if name in retracted:
                record = {**record, "retracted_by": retracted[name]}
            pages.append(record_page(record, target))
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        planned = []
        for page in pages:
            found_page = self._call(self.wiki, "get_page_by_key", {"key": page["key"]})["page"]
            action = _action(found_page, page)
            entry = {
                "key": page["key"],
                "title": page["title"],
                "action": action,
                "parent": page["parent"],
                "hash": page["properties"][HASH_PROPERTY],
            }
            if action != "unchanged" and not dry_run:
                written = self._call(
                    self.wiki,
                    "upsert_page",
                    {
                        **page,
                        "expected_version": found_page["version"] if found_page else None,
                        "operation_id": f"render-{changed['head'][:12]}-{stamp}",
                    },
                )
                entry.update(page_id=written["page_id"], version=written["version"])
                entry["url"] = written["url"]
            planned.append(entry)
        writes = sum(1 for entry in planned if entry["action"] != "unchanged")
        return {
            "status": "planned" if dry_run else ("rendered" if writes else "unchanged"),
            "dry_run": dry_run,
            "since": changed["since"],
            "head": changed["head"],
            "site": target["site"],
            "pages": planned,
            "writes": 0 if dry_run else writes,
            "skipped": skipped,
            "orphaned": orphaned,
        }
