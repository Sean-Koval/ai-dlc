"""Tracker items through the ``tracker`` role, shared by CLI and MCP.

Each call resolves the provider selected for ``roles.tracker`` and goes through
:meth:`ai_dlc.providers.Registry.invoke`, so requests and results are validated
against the provider contract. There is no transition here: lifecycle moves stay
with the work service and its gates. A decision is filed with its blocking link in one
call (``create_decision``); the tracker's own automation moves the blocked work.

A session may file, edit, search and comment on tickets, but never queue one for an
agent: a label that starts a hangar job (``exec:agent``, or the older ``lane:agent``)
is refused in any letter case, and so is a comment that names one. Labels and comments
are compared after NFKC normalisation with format characters (zero-width and the
like) removed, so look-alike spellings cannot slip past. Every result lists the
item's ``exec:`` labels, so hooks can see them.
"""

import hashlib
import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

from pydantic import ValidationError

from ai_dlc.errors import RefusedError

# Labels that make a ticket start an agent job; only a person sets them.
AGENT_LABELS = frozenset({"exec:agent", "lane:agent"})


# Naming an agent label in a comment, however spaced, could make automation set it.
AGENT_MENTION = re.compile(r"\b(?:exec|lane)\s*:\s*agent\b")


def canonical(text: str) -> str:
    """NFKC, without format characters (Unicode category Cf: zero-width and the like)."""
    folded = unicodedata.normalize("NFKC", text)
    return "".join(char for char in folded if unicodedata.category(char) != "Cf")


def _labels(labels: list[str] | None) -> list[str] | None:
    if labels is None:
        return None
    cleaned = [canonical(label).strip() for label in labels]
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
    return [label for label in labels if canonical(label).casefold().startswith("exec:")]


def _comment(body: str) -> str:
    """Plain text only: no control or format characters, and no agent label named."""
    if not body.strip():
        raise RefusedError("A comment needs text")
    if any(unicodedata.category(char) in {"Cc", "Cf"} and char not in "\n\t" for char in body):
        raise RefusedError("A comment must be plain text, without control or format characters")
    if AGENT_MENTION.search(canonical(body).casefold()):
        raise RefusedError(
            "A comment may not name exec:agent; only a person queues a ticket for an agent"
        )
    return body


class CustomField(TypedDict):
    """One custom field of a new item: its ID and a plain value."""

    field: str
    value: str | float | list[str]


class ItemLink(TypedDict):
    """A link made from the new item: ``{"type": "Blocks", "target": "KAN-1"}``."""

    type: str
    target: str


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

    def _offers(self, operation: str) -> bool:
        """Whether the provider lists an optional operation in its capabilities."""
        if not self.registry.declares(self.provider, "capabilities"):
            return self.registry.declares(self.provider, operation)
        capabilities = self.registry.invoke(self.provider, "capabilities", {})
        return operation in capabilities["optional_operations"]

    def _writes_labels(self) -> bool:
        """Whether the provider lists ``update``, which carries label writes."""
        return self._offers("update")

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

    def search(
        self,
        text: str | None = None,
        labels: list[str] | None = None,
        state: str | None = None,
        limit: int = 20,
    ) -> dict:
        """Items matching every filter given, newest first; read-only."""
        if not self._offers("query"):
            return {
                "status": "refused",
                "reason": f"tracker provider {self.provider} has no search operation",
            }
        payload = {
            "text": text,
            "labels": [canonical(label).strip() for label in labels or []],
            "state": state,
            "limit": limit,
        }
        try:
            found = self.registry.invoke(self.provider, "query", payload)
        except LookupError as exc:
            return {"status": "failed", "reason": str(exc.args[0] if exc.args else exc)}
        except RefusedError as exc:
            return {"status": "refused", "reason": str(exc)}
        items = [
            {**item, "exec_labels": exec_labels(item.get("labels") or [])}
            for item in found["items"]
        ]
        return {"status": "ok", "provider": self.provider, "items": items}

    def comment(self, reference: str, body: str) -> dict:
        """Add one plain-text comment once; it never edits labels or status."""
        try:
            text = _comment(body)
        except RefusedError as exc:
            return {"status": "refused", "reason": str(exc)}
        if not self._offers("comment"):
            return {
                "status": "refused",
                "reason": f"tracker provider {self.provider} has no comment operation",
            }
        current = self.get(reference)
        if current["status"] != "ok":
            return current
        digest = hashlib.sha256(f"{reference}\0{text}".encode()).hexdigest()[:16]
        payload = {
            "reference": reference,
            "body": text,
            "operation_id": "tracker-comment-" + digest,
        }
        try:
            comment = self.registry.invoke(self.provider, "comment", payload)
        except LookupError as exc:
            return {"status": "failed", "reason": str(exc.args[0] if exc.args else exc)}
        except RefusedError as exc:
            return {"status": "refused", "reason": str(exc)}
        return {**current, "status": "commented", "comment": comment}

    def create(
        self,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
        correlation: str | None = None,
        issue_type: str | None = None,
        fields: dict | None = None,
        parent: str | None = None,
        links: list[dict] | None = None,
    ) -> dict:
        """File an item once: a repeat with the same correlation returns the first one.

        Without ``correlation`` the title and body are the correlation. ``issue_type``,
        ``fields`` (custom field ID to a plain value), ``parent`` and ``links`` (``type``
        and ``target``, made from the new item) need a provider offering ``create_typed``.
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
        typed = {
            key: value
            for key, value in (
                ("issue_type", issue_type),
                ("fields", fields),
                ("parent", parent),
                ("links", links),
            )
            if value
        }
        if typed and not self._offers("create_typed"):
            return {
                "status": "refused",
                "reason": f"tracker provider {self.provider} cannot set a type, fields, "
                "parent or links",
            }
        if any(AGENT_MENTION.search(canonical(str(value)).casefold()) for value in typed.values()):
            return {
                "status": "refused",
                "reason": "exec:agent starts an agent job; only a person queues a ticket for an agent",
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
            **typed,
        }
        return self._contract_call("created", "create", payload, wanted)

    def create_decision(
        self,
        question: str,
        blocks: str,
        options: list[str],
        recommendation: str,
        default: str,
        scope: str,
        due: str,
        body: str = "",
        labels: list[str] | None = None,
        correlation: str | None = None,
        parent: str | None = None,
    ) -> dict:
        """File a decision for a person, once, that blocks ``blocks``; it never moves either.

        The ``decision`` label is always set. A repeat with the same correlation (default:
        the question and the blocked item) returns the first decision.
        """
        try:
            wanted = _labels(["decision", *(labels or [])]) or []
        except RefusedError as exc:
            return {"status": "refused", "reason": str(exc)}
        if not question.strip().endswith("?"):
            return {
                "status": "refused",
                "reason": "A decision's title is its question, ending in ?",
            }
        if not self._offers("decide"):
            return {
                "status": "refused",
                "reason": f"tracker provider {self.provider} cannot file a decision",
            }
        digest = hashlib.sha256(f"{question}\0{blocks}".encode()).hexdigest()[:16]
        marker = correlation or f"<!-- ai-dlc:decision:{digest} -->"
        payload = {
            "title": question.strip(),
            "body": body,
            "labels": wanted,
            "correlation": marker,
            "operation_id": "tracker-decide-" + hashlib.sha256(marker.encode()).hexdigest()[:16],
            "blocks": blocks,
            "options": options,
            "recommendation": recommendation,
            "default": default,
            "scope": scope,
            "due": due,
        }
        if parent:
            payload["parent"] = parent
        return self._contract_call("created", "decide", payload, wanted)

    def _contract_call(self, status: str, operation: str, payload: dict, requested) -> dict:
        """``_call``, reporting a payload the provider contract refuses field by field."""
        try:
            return self._call(status, operation, payload, requested)
        except ValidationError as exc:
            problems = [
                f"{'.'.join(map(str, error['loc']))}: {error['msg']}" for error in exc.errors()
            ]
            return {"status": "refused", "reason": "; ".join(problems)}

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
            kept = [
                label for label in current["labels"] if canonical(label).casefold() in AGENT_LABELS
            ]
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
