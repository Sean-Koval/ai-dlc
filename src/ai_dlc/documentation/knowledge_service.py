"""Knowledge-record operations through the ``knowledge`` role, shared by CLI and MCP.

Each call resolves the selected knowledge provider (``roles.knowledge``, or an explicit
provider id) and goes through :meth:`ai_dlc.providers.Registry.invoke`, so requests
and results are validated against the provider contract. Results carry ``status``.

A root that holds ``knowledge.toml`` is itself a knowledge repository: without an
explicit provider, :meth:`KnowledgeRecords.at` reads it in place with the ``git``
provider, so ``records search --root <clone>`` needs no ``KNOWLEDGE_REPO`` (KAN-494).
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

from ai_dlc.errors import RefusedError


class ProposedRecord(TypedDict):
    """One record file to propose: its repository path and its full text."""

    path: str
    text: str


def _template_dir() -> Path:
    from ai_dlc.files import assets

    return assets("agents") / "templates" / "knowledge"


def templates() -> dict:
    """The record types that have a packaged template, in contract order."""
    from ai_dlc.documentation.knowledge_records import TYPES

    folder = _template_dir()
    return {"status": "ok", "types": [kind for kind in TYPES if (folder / f"{kind}.md").is_file()]}


def template(kind: str) -> dict:
    """The packaged record template for one type, as text; refuses an unknown type."""
    from ai_dlc.documentation.knowledge_records import TYPES

    if kind not in TYPES:
        return {"status": "refused", "reason": f"no record type {kind}; one of {', '.join(TYPES)}"}
    path = _template_dir() / f"{kind}.md"
    if not path.is_file():
        return {"status": "unavailable", "reason": f"the {kind} template is not packaged"}
    return {"status": "ok", "type": kind, "text": path.read_text(encoding="utf-8")}


def _relevance(item: dict, needle: str | None) -> int:
    """How strongly an item's header names ``needle``: id, then title, then the rest."""
    if not needle:
        return 0
    header = item.get("header") or {}
    score = 0
    for field, weight in (("id", 8), ("title", 4), ("description", 2)):
        if needle in str(header.get(field) or item.get(field) or "").casefold():
            score += weight
    if any(needle in str(tag).casefold() for tag in header.get("tags") or ()):
        score += 1
    return score


def rank(items: list[dict], text: str | None = None) -> list[dict]:
    """Items in reading order: header matches of ``text``, current before ended, newest first."""
    from ai_dlc.documentation.record_index import status_rank

    needle = text.casefold() if text else None

    def key(item: dict) -> tuple:
        header = item.get("header") or {}
        status = "retracted" if item.get("retracted_by") else str(header.get("status") or "")
        return (
            -_relevance(item, needle),
            status_rank(status),
            -int(str(header.get("date") or "0000-00-00").replace("-", "")[:8] or 0),
            str(item.get("id") or ""),
        )

    return sorted(items, key=key)


def search_lines(result: dict) -> list[str]:
    """The compact answer: one ranked row per record and the line that says what it is."""
    if result.get("status") != "ok":
        return [f"knowledge records search: {result.get('reason') or result.get('status')}"]
    items = result.get("items") or []
    out = []
    for item in items:
        header = item.get("header") or {}
        status = "retracted" if item.get("retracted_by") else header.get("status")
        facts = [f"owner {header['owner']}"] if header.get("owner") else []
        cited = [ref.get("id") or ref.get("resource") for ref in header.get("sources") or ()]
        if cited:
            facts.append("evidence " + ", ".join(str(name) for name in cited if name))
        out.append(f"{item['id']}  {header.get('type')}  {status}  {header.get('title') or ''}")
        line = " ".join(str(header.get("description") or "").split())
        tail = f"  [{'; '.join(facts)}]" if facts else ""
        out.append(f"    {line}{tail}".rstrip())
    hidden = result.get("hidden_sources") or 0
    summary = f"{len(items)} record{'s' if len(items) != 1 else ''}"
    if hidden:
        summary += f"; {hidden} source record{'s' if hidden != 1 else ''} hidden (--type source)"
    if result.get("invalid"):
        summary += f"; {len(result['invalid'])} unreadable (--json lists them)"
    return [*out, summary]


def _type(item: dict) -> str | None:
    return (item.get("header") or {}).get("type")


class KnowledgeRecords:
    @classmethod
    def at(
        cls,
        root: Path,
        config: Mapping[str, Any],
        *,
        provider: str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> "KnowledgeRecords":
        """The records of ``root``: read in place when it is a knowledge repository.

        An explicit ``provider`` wins. Otherwise a ``knowledge.toml`` at ``root`` (the
        format pin every knowledge repository carries) selects the ``git`` provider
        with ``root`` as its location, whatever ``roles.knowledge`` says.
        """
        from ai_dlc.documentation.record_index import PIN_FILE

        if provider is None and (Path(root) / PIN_FILE).is_file():
            config = dict(config)
            providers = dict(config.get("providers") or {})
            local = {"kind": "git", "location": str(Path(root).expanduser().resolve())}
            providers["knowledge-root"] = local
            config["providers"] = providers
            provider = "knowledge-root"
        return cls(root, config, provider=provider, environ=environ)

    def __init__(
        self,
        root: Path,
        config: Mapping[str, Any],
        *,
        provider: str | None = None,
        registry: Any = None,
        environ: Mapping[str, str] | None = None,
    ):
        from ai_dlc.providers import Registry

        self.config = dict(config)
        self.provider = provider or self.config.get("roles", {}).get("knowledge")
        if not self.provider:
            raise ValueError("knowledge unavailable: select a provider for the knowledge role")
        self.registry = registry or Registry(self.config, root=root, environ=environ)

    def _call(self, operation: str, payload: dict) -> dict:
        try:
            result = self.registry.invoke(self.provider, operation, payload)
        except LookupError as exc:
            return {"status": "failed", "reason": str(exc.args[0] if exc.args else exc)}
        except RefusedError as exc:
            return {"status": "refused", "reason": str(exc)}
        return {"status": "ok", **result}

    def get(self, id: str, project: str | None = None) -> dict:
        return self._call("get", {"id": id, "project": project})

    def search(
        self,
        type: str | None = None,
        scope: str | None = None,
        labels: list[str] | None = None,
        status: str | None = None,
        text: str | None = None,
        project: str | None = None,
    ) -> dict:
        """Ranked by :func:`rank`; Source records only when ``type`` is ``source``.

        Sources are the raw captures records derive from, so they would crowd out the
        answers; ``hidden_sources`` counts those left out.
        """
        payload = {
            "type": type,
            "scope": scope,
            "labels": list(labels or []),
            "status": status,
            "text": text,
            "project": project,
        }
        result = self._call("search", payload)
        if result["status"] != "ok":
            return result
        items = list(result.get("items") or [])
        kept = items if type == "source" else [i for i in items if _type(i) != "source"]
        return {**result, "items": rank(kept, text), "hidden_sources": len(items) - len(kept)}

    def list_changed(self, since: str) -> dict:
        return self._call("list_changed", {"since": since})

    def propose(self, records: list[dict], branch: str, title: str, body: str = "") -> dict:
        payload = {"records": records, "branch": branch, "title": title, "body": body}
        result = self._call("propose", payload)
        if result["status"] == "ok":
            result["status"] = "proposed"
        return result

    def captured(self, source: Path) -> dict:
        """``new`` or ``captured``: whether a record already carries this text's sha256."""
        provider = self.registry.get(self.provider)
        if not hasattr(provider, "captured"):
            return {"status": "refused", "reason": "this knowledge provider has no record hashes"}
        return provider.captured(source)
