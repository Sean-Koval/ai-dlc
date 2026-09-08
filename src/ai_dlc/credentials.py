"""Credential requirement readiness without exposing credential values."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from typing import Any

from ai_dlc.provider_definitions import DEFINITIONS, EnvironmentRequirement


def _environment_name(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) is not None


def _status_entry(
    credential_id: str, entry: Mapping[str, Any], environ: Mapping[str, str]
) -> dict[str, object]:
    source = entry.get("source")
    variable = entry.get("variable")
    configured = source == "environment" and _environment_name(variable)
    present = (
        bool(environ.get(variable, "").strip())
        if configured and isinstance(variable, str)
        else False
    )
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
            kind = provider.get("kind", provider.get("type", provider_id))
            definition = DEFINITIONS.get(kind)
            requirements = list(definition.environment_requirements) if definition else []
            # Preserve legacy/custom explicit token references without inventing requirements.
            if isinstance(provider.get("token_env"), str) and not any(
                requirement.field == "token_env" for requirement in requirements
            ):
                requirements.append(EnvironmentRequirement("token_env"))
            for requirement in requirements:
                if requirement.when and provider.get(requirement.when[0]) != requirement.when[1]:
                    continue
                variable = provider.get(requirement.field)
                if variable is None:
                    variable = requirement.default
                if (
                    _environment_name(variable)
                    and (required_by, variable) in covered_provider_variables
                ):
                    continue
                credential_id = (
                    required_by
                    if requirement.field == "token_env"
                    else f"{required_by}.{requirement.field}"
                )
                base_id = credential_id
                suffix = 2
                while credential_id in entries:
                    credential_id = f"{base_id}.{suffix}"
                    suffix += 1
                entries[credential_id] = {
                    "description": f"Credential for provider {provider_id}",
                    "required_by": [required_by],
                    "source": "environment",
                    "variable": variable,
                }
                if _environment_name(variable):
                    covered_provider_variables.add((required_by, variable))
    return [
        _status_entry(credential_id, entries[credential_id], environment)
        for credential_id in sorted(entries)
    ]
