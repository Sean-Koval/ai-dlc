"""Knowledge-record operations through the ``knowledge`` role, shared by CLI and MCP.

Each call resolves the selected knowledge provider (``roles.knowledge``, or an explicit
provider id) and goes through :meth:`ai_dlc.providers.Registry.invoke`, so requests
and results are validated against the provider contract. Results carry ``status``.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ai_dlc.errors import RefusedError


class KnowledgeRecords:
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

    def get(self, id: str) -> dict:
        return self._call("get", {"id": id})

    def search(
        self,
        type: str | None = None,
        scope: str | None = None,
        labels: list[str] | None = None,
        status: str | None = None,
        text: str | None = None,
    ) -> dict:
        payload = {
            "type": type,
            "scope": scope,
            "labels": list(labels or []),
            "status": status,
            "text": text,
        }
        return self._call("search", payload)

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
