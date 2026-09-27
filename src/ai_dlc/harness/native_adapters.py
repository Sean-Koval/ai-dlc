"""Documentation-backed smoke contracts, without invented native qualification."""

from __future__ import annotations

import hashlib
import json
from types import MappingProxyType

CLIENTS = ("codex", "claude-code", "antigravity")
MARKERS = MappingProxyType(
    {
        "instruction": "NHV-INSTRUCTION-1",
        "skill": "NHV-SKILL-1",
        "mcp": "NHV-MCP-1",
    }
)
_SOURCES = {
    "codex": [
        "https://learn.chatgpt.com/docs/agent-configuration/agents-md",
        "https://learn.chatgpt.com/docs/build-skills",
        "https://learn.chatgpt.com/docs/extend/mcp?surface=cli",
    ],
    "claude-code": [
        "https://code.claude.com/docs/en/memory",
        "https://code.claude.com/docs/en/skills",
        "https://code.claude.com/docs/en/mcp",
    ],
    "antigravity": ["https://antigravity.google/docs/rules/"],
}


def _digest(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def adapter_contract(client_id: str) -> dict:
    """Return public fixture identity and documentation-only adapter metadata.

    Empty tested_versions is intentional. Documentation review does not establish
    compatibility with any installed edition/version or authorize rendering.
    """
    if client_id not in CLIENTS:
        raise ValueError("Unsupported native client.")
    fixture = {
        "fixture_id": "native-smoke-v1",
        "markers": dict(MARKERS),
        "steps": {
            "instruction": "Observe a response containing the project instruction marker.",
            "skill": "Invoke the explicitly selected reviewed skill and observe its distinct marker.",
            "mcp": "Enumerate tools, then invoke the reviewed read-only non-billable tool and check its prescribed output.",
        },
        "provenance": "operator-attested",
    }
    contract = {
        "adapter_contract_id": f"native-{client_id}-v1",
        "client_id": client_id,
        "sources": list(_SOURCES[client_id]),
        "reviewed_at": "2026-09-26",
        "tested_versions": [],
        "compatibility": "client-schema-unverified",
        "safe_operations": [],
        "fixture_id": fixture["fixture_id"],
        "fixture_sha256": _digest(fixture),
    }
    return {**contract, "adapter_contract_sha256": _digest(contract), "fixture": fixture}
