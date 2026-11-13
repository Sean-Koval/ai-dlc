"""Tracker items through the ``tracker`` role, shared by CLI and MCP.

Each call resolves the provider selected for ``roles.tracker`` and goes through
:meth:`ai_dlc.providers.Registry.invoke`, so requests and results are validated
against the provider contract. There is no transition here: lifecycle moves stay
with the work service and its gates.

A session may file and edit tickets, but never queue one for an agent: a label that
starts a hangar job (``exec:agent``, or the older ``lane:agent``) is refused in any
letter case. Every result lists the item's ``exec:`` labels, so hooks can see them.
"""

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ai_dlc.errors import RefusedError

# Labels that make a ticket start an agent job; only a person sets them.
AGENT_LABELS = frozenset({"exec:agent", "lane:agent"})


def _labels(labels: list[str] | None) -> list[str] | None:
    if labels is None:
        return None
    cleaned = [label.strip() for label in labels]
    if any(not label or any(char.isspace() for char in label) for label in cleaned):
        raise RefusedError("A label must be one word without spaces")
    agent = [label for label in cleaned if label.casefold() in AGENT_LABELS]
    if agent:
        raise RefusedError(
            f"{agent[0]} starts an agent job; only a person queues a ticket for an agent"
        )
    return list(dict.fromkeys(cleaned))


def exec_labels(labels: list[str]) -> list[str]:
    """The execution labels among ``labels``, as the tracker stores them."""
    return [label for label in labels if label.casefold().startswith("exec:")]


class TrackerItems:
    def __init__(
        self,
        root: Path,
        config: Mapping[str, Any],
        *,
        registry: Any = None,
        environ: Mapping[str, str] | None = None,
    ):
        from ai_dlc.providers import Registry

        self.config = dict(config)
        self.provider = self.config.get("roles", {}).get("tracker")
        if not self.provider:
            raise ValueError("tracker unavailable: select a provider for the tracker role")
        self.registry = registry or Registry(self.config, root=root, environ=environ)

    def _writes_labels(self) -> bool:
        """Whether the provider lists ``update``, which carries label writes."""
        if not self.registry.declares(self.provider, "capabilities"):
            return self.registry.declares(self.provider, "update")
        capabilities = self.registry.invoke(self.provider, "capabilities", {})
        return "update" in capabilities["optional_operations"]

    def _call(self, status: str, operation: str, payload: dict, requested=None) -> dict:
        try:
            item = self.registry.invoke(self.provider, operation, payload)
        except LookupError as exc:
            return {"status": "failed", "reason": str(exc.args[0] if exc.args else exc)}
        except RefusedError as exc:
            return {"status": "refused", "reason": str(exc)}
        labels = item.get("labels")
        if not isinstance(labels, list):
            labels = requested or []
        return {
            "status": status,
            "provider": self.provider,
            "item": item,
            "labels": labels,
            "exec_labels": exec_labels(labels),
        }

    def get(self, reference: str) -> dict:
        return self._call("ok", "read", {"reference": reference})

    def create(
        self,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
        correlation: str | None = None,
    ) -> dict:
        """File an item once: a repeat with the same correlation returns the first one.

        Without ``correlation`` the title and body are the correlation.
        """
        try:
            wanted = _labels(labels) or []
        except RefusedError as exc:
            return {"status": "refused", "reason": str(exc)}
        if wanted and not self._writes_labels():
            return {
                "status": "refused",
                "reason": f"tracker provider {self.provider} cannot write labels",
            }
        digest = hashlib.sha256(f"{title}\0{body}".encode()).hexdigest()[:16]
        marker = correlation or f"<!-- ai-dlc:ticket:{digest} -->"
        operation_id = "tracker-create-" + hashlib.sha256(marker.encode()).hexdigest()[:16]
        payload = {
            "title": title,
            "body": body,
            "labels": wanted,
            "correlation": marker,
            "operation_id": operation_id,
        }
        return self._call("created", "create", payload, wanted)

    def update(
        self,
        reference: str,
        title: str | None = None,
        body: str | None = None,
        labels: list[str] | None = None,
    ) -> dict:
        """Replace the given fields of an open item; ``labels`` replaces the whole set."""
        try:
            wanted = _labels(labels)
        except RefusedError as exc:
            return {"status": "refused", "reason": str(exc)}
        if title is None and body is None and wanted is None:
            return {"status": "refused", "reason": "give a title, body or labels to update"}
        if not self._writes_labels():
            return {
                "status": "refused",
                "reason": f"tracker provider {self.provider} has no update operation",
            }
        if wanted is not None:
            current = self.get(reference)
            if current["status"] != "ok":
                return current
            # Replacing the set must not drop a label only a person may set.
            kept = [label for label in current["labels"] if label.casefold() in AGENT_LABELS]
            wanted = list(dict.fromkeys([*wanted, *kept]))
        digest = hashlib.sha256(repr((reference, title, body, wanted)).encode()).hexdigest()
        payload = {
            "reference": reference,
            "title": title,
            "body": body,
            "labels": wanted,
            "operation_id": "tracker-update-" + digest[:16],
        }
        return self._call("updated", "update", payload, wanted)
