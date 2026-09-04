"""Credential requirement readiness without exposing credential values."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


def _status_entry(
    credential_id: str, entry: Mapping[str, Any], environ: Mapping[str, str]
) -> dict[str, object]:
    source = entry.get("source")
    variable = entry.get("variable")
    configured = source == "environment" and isinstance(variable, str)
    present = bool(environ.get(variable)) if configured and isinstance(variable, str) else False
    result: dict[str, object] = {
        "id": credential_id,
        "description": entry.get("description", ""),
        "required_by": entry.get("required_by", []),
        "configured": configured,
        "present": present,
    }
    if configured:
        result["source"] = source
        result["variable"] = variable
    return result


def credential_status(
    config: dict[str, Any],
    environ: Mapping[str, str] | None = None,
) -> list[dict[str, object]]:
    """Return credential readiness metadata without returning credential values."""
    environment = os.environ if environ is None else environ
    credentials = config.get("credentials", {})
    entries: dict[str, Mapping[str, Any]] = {
        credential_id: entry
        for credential_id, entry in credentials.items()
        if isinstance(credential_id, str) and isinstance(entry, Mapping)
    }
    covered_provider_variables = {
        (provider, entry.get("variable"))
        for entry in entries.values()
        for provider in entry.get("required_by", [])
        if isinstance(provider, str) and isinstance(entry.get("variable"), str)
    }
    providers = config.get("providers", {})
    if isinstance(providers, Mapping):
        for provider_id, provider in providers.items():
            if not isinstance(provider_id, str) or not isinstance(provider, Mapping):
                continue
            required_by = f"provider.{provider_id}"
            token_env = provider.get("token_env")
            kind = provider.get("kind", provider.get("type", provider_id))
            if token_env is None and kind == "linear":
                token_env = "LINEAR_API_KEY"
            if (
                isinstance(token_env, str)
                and (required_by, token_env) not in covered_provider_variables
            ):
                entries[required_by] = {
                    "description": f"Credential for provider {provider_id}",
                    "required_by": [required_by],
                    "source": "environment",
                    "variable": token_env,
                }
    return [
        _status_entry(credential_id, entries[credential_id], environment)
        for credential_id in sorted(entries)
    ]
