"""Offline project readiness derived from validated component requirements."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ai_dlc.components import MissingComponentGuidance, load_component_catalog, resolve_components
from ai_dlc.config import read_toml
from ai_dlc.credentials import credential_status
from ai_dlc.files import assets, inside

_READY = "ready"
_BLOCKING_DIMENSIONS = {"tool", "configuration", "credential", "guidance"}


def _check(
    component: str,
    dimension: str,
    status: str,
    reason: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "component": component,
        "dimension": dimension,
        "status": status,
        "reason": reason,
        "next_action": next_action,
    }


def _configured(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _config_value(config: Mapping[str, Any], path: str) -> Any:
    value: Any = config
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def _guidance_available(root: Path, path: str) -> bool:
    packaged = assets("agents") / path
    if packaged.is_file() and not packaged.is_symlink():
        return True
    try:
        project_path = inside(root, path)
    except ValueError:
        return False
    return project_path.is_file() and not project_path.is_symlink()


def _probe_module(commands: list[str], probe: Callable[[list[str]], dict]) -> bool | None:
    try:
        result = probe(commands)
    except Exception:  # noqa: BLE001 -- readiness reports an unavailable bounded probe
        return None
    available = result.get("available") if isinstance(result, Mapping) else None
    return available if type(available) is bool else None


def _tool_checks(
    component: dict[str, Any],
    catalog: Mapping[str, Any],
    *,
    headless: bool,
    probe: Callable[[list[str]], dict],
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for module_id in component["modules"]:
        module = catalog[module_id]
        if headless and module.get("desktop"):
            checks.append(
                _check(
                    component["id"],
                    "tool",
                    "blocked",
                    f"headless desktop capability unavailable for module {module_id}",
                    f"Use a non-headless environment to provide module {module_id}.",
                )
            )
            continue
        commands = module.get("verify", [])
        if not commands:
            checks.append(
                _check(
                    component["id"],
                    "tool",
                    _READY,
                    f"module {module_id} has no executable verification requirement",
                    "No action required.",
                )
            )
            continue
        available = _probe_module(commands, probe)
        if available is True:
            checks.append(
                _check(
                    component["id"],
                    "tool",
                    _READY,
                    f"module {module_id} executable requirements are available",
                    "No action required.",
                )
            )
        elif available is False:
            checks.append(
                _check(
                    component["id"],
                    "tool",
                    "missing",
                    f"module {module_id} executable requirements are unavailable",
                    f"Install module {module_id} with the explicit setup apply command.",
                )
            )
        else:
            checks.append(
                _check(
                    component["id"],
                    "tool",
                    "unverified",
                    f"module {module_id} executable requirements could not be inspected",
                    f"Run the module {module_id} verification in a prepared environment.",
                )
            )
    return checks


def inspect_readiness(
    root: Path,
    config: dict,
    *,
    environ: Mapping[str, str],
    probe: Callable[[list[str]], dict],
) -> dict:
    """Inspect offline requirements without reading credentials or contacting providers."""
    root = Path(root).resolve()
    missing_guidance: set[tuple[str, str]] = set()
    try:
        catalog = load_component_catalog(root, config)
    except MissingComponentGuidance as exc:
        catalog = exc.catalog
        missing_guidance = set(exc.missing)
    resolved = resolve_components(config, catalog)
    modules = read_toml(assets("modules") / "catalog.toml")
    checks: list[dict[str, str]] = []
    headless = bool(config.get("preferences", {}).get("headless", False))

    for unresolved in resolved["unresolved"]:
        checks.append(
            _check(
                unresolved["provider"],
                "configuration",
                "blocked",
                unresolved["reason"],
                "Select a compatible configured provider component.",
            )
        )

    credentials = credential_status(config, environ)
    clients = config.get("roles", {}).get("agent-client", [])
    if isinstance(clients, str):
        clients = [clients]
    if clients:
        from ai_dlc.agents import provider_guidance_ready, provider_index

        index, copies = provider_index(resolved)
        for client in clients:
            supported = client in {"codex", "claude-code"}
            delivered = supported and provider_guidance_ready(root, index, copies, client)
            checks.append(
                _check(
                    client,
                    "guidance",
                    _READY if delivered else "missing" if supported else "blocked",
                    "configured provider index is delivered"
                    if delivered
                    else (
                        "configured provider index or instructions are missing or stale"
                        if supported
                        else "unsupported agent client"
                    ),
                    "No action required."
                    if delivered
                    else (
                        "Declare the selected providers in shared ai-dlc.toml, then run "
                        "ai-dlc agents render --apply after resolving authored-file conflicts."
                        if supported
                        else "Select an implemented agent client: codex or claude-code."
                    ),
                )
            )
    for component in resolved["components"]:
        checks.extend(_tool_checks(component, modules, headless=headless, probe=probe))

        provider_config = config.get("providers", {}).get(component["provider"], {})
        for path in component["required_config"]:
            value = _config_value(provider_config, path)
            if _configured(value):
                checks.append(
                    _check(
                        component["id"],
                        "configuration",
                        _READY,
                        f"provider configuration {path} is set",
                        "No action required.",
                    )
                )
            else:
                checks.append(
                    _check(
                        component["id"],
                        "configuration",
                        "missing",
                        f"provider configuration {path} is required",
                        f"Configure providers.{component['provider']}.{path}.",
                    )
                )

        for credential in credentials:
            required_by = credential.get("required_by", [])
            if (
                not isinstance(required_by, list)
                or f"provider.{component['provider']}" not in required_by
            ):
                continue
            configured = credential["configured"]
            present = credential["present"]
            if present:
                status = _READY
                reason = f"credential {credential['id']} is present"
                action = "No action required."
            elif configured:
                status = "missing"
                reason = f"credential {credential['id']} is not present"
                variable = credential.get("variable")
                action = (
                    f"Set {variable} using your credential store."
                    if isinstance(variable, str)
                    else f"Bind credential {credential['id']} in machine configuration."
                )
            else:
                status = "blocked"
                reason = f"credential {credential['id']} has no environment binding"
                action = f"Bind credential {credential['id']} in machine configuration."
            checks.append(_check(component["id"], "credential", status, reason, action))

        for guidance in component["guidance"]:
            if (component["id"], guidance) not in missing_guidance and _guidance_available(
                root, guidance
            ):
                checks.append(
                    _check(
                        component["id"],
                        "guidance",
                        _READY,
                        f"guidance {guidance} is available",
                        "No action required.",
                    )
                )
            else:
                checks.append(
                    _check(
                        component["id"],
                        "guidance",
                        "missing",
                        f"guidance {guidance} is unavailable",
                        f"Restore the configured guidance file {guidance}.",
                    )
                )

        checks.append(
            _check(
                component["id"],
                "provider-health",
                "unverified",
                "provider health is not inspected during offline readiness",
                "Run doctor for an explicit provider health inspection.",
            )
        )

    ready = all(
        check["status"] == _READY or check["dimension"] not in _BLOCKING_DIMENSIONS
        for check in checks
    )
    return {
        "schema": 1,
        "ready": ready,
        "checks": checks,
        "qualification": "not-assessed",
    }
