"""Scoped configuration resolution; project files never depend on personal state."""

from __future__ import annotations

import copy
import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = 4
SCOPES = {
    "schema": {"base", "personal", "project", "machine"},
    "engine": {"base", "project"},
    "roles": {"base", "personal", "project"},
    "providers": {"base", "personal", "project", "machine"},
    "checks": {"base", "project"},
    "gates": {"base", "project"},
    "setup": {"base", "project"},
    "scm": {"base", "project"},
    "deploy": {"base", "project"},
    "agents": {"base", "personal", "project"},
    "modules": {"base", "personal", "machine"},
    "preferences": {"base", "personal", "machine"},
    "paths": {"machine"},
    "accounts": {"machine"},
    "target": {"machine"},
    "project": {"base", "project"},
    "contracts": {"base", "project"},
}


@dataclass
class Resolved:
    values: dict[str, Any]
    sources: dict[str, str]


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def read_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text())


def _validate(layer: str, data: dict[str, Any]) -> None:
    if layer not in {"base", "personal", "project", "machine"}:
        raise ValueError(f"unknown layer: {layer}")
    if data.get("schema") != SCHEMA:
        raise ValueError(f"{layer}: unsupported schema {data.get('schema')}; migrate explicitly")
    for field in data:
        if field not in SCOPES:
            raise ValueError(f"{layer}: unknown field {field}")
        if layer not in SCOPES[field]:
            raise ValueError(f"{layer}: cannot set {field}")
    # Machine overrides may select credentials/accounts, never executable provider behavior.
    if layer == "machine":
        for name, settings in data.get("providers", {}).items():
            for key in settings:
                if key not in {"account", "token_env", "vault_path", "sandbox_workspace"}:
                    raise ValueError(f"machine: cannot set providers.{name}.{key}")

    def secrets(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in {"token", "password", "secret", "api_key", "access_token"}:
                    raise ValueError(
                        f"{layer}: credential value prohibited at {path}{key}; use environment reference"
                    )
                secrets(child, path + key + ".")
        elif isinstance(value, list):
            for child in value:
                secrets(child, path)

    secrets(data)


def resolve_layers(layers: list[tuple[str, dict[str, Any]]]) -> Resolved:
    values: dict[str, Any] = {}
    sources: dict[str, str] = {}

    def stamp(value: Any, path: str, layer: str) -> None:
        for existing in list(sources):
            if existing == path or existing.startswith(path + "."):
                del sources[existing]
        if isinstance(value, dict) and value:
            for key, item in value.items():
                stamp(item, f"{path}.{key}" if path else key, layer)
        elif isinstance(value, list) and value:
            for index, item in enumerate(value):
                stamp(item, f"{path}.{index}", layer)
        else:
            sources[path] = layer

    def merge(old: Any, new: Any, path: str, layer: str) -> Any:
        if isinstance(new, dict) and ("add" in new or "remove" in new):
            if set(new) - {"add", "remove"}:
                raise ValueError(f"{layer}: invalid collection operation at {path}")
            added = new.get("add", [])
            removed = new.get("remove", [])
            ids = [x["id"] if isinstance(x, dict) else x for x in added]
            if set(ids) & set(removed):
                raise ValueError(f"{layer}: add/remove same ID at {path}")
            if len(set(ids)) != len(ids) or len(set(removed)) != len(removed):
                raise ValueError(f"{layer}: duplicate IDs at {path}")
            result = copy.deepcopy(old or [])
            if not isinstance(result, list):
                raise ValueError(f"{layer}: named collection expected at {path}")
            key = lambda item: item["id"] if isinstance(item, dict) else item
            retained = [
                (index, item)
                for index, item in enumerate(result)
                if key(item) not in removed and key(item) not in ids
            ]
            prior_sources = dict(sources)
            result = [item for _, item in retained]
            result.extend(copy.deepcopy(added))
            stamp(result, path, layer)
            for new_index, (old_index, _) in enumerate(retained):
                old_prefix = f"{path}.{old_index}"
                for source_path, origin in prior_sources.items():
                    if source_path == old_prefix or source_path.startswith(old_prefix + "."):
                        sources[f"{path}.{new_index}" + source_path[len(old_prefix) :]] = origin
            return result
        if isinstance(new, dict):
            result = copy.deepcopy(old) if isinstance(old, dict) else {}
            for key, value in new.items():
                child_path = f"{path}.{key}" if path else key
                result[key] = merge(result.get(key), value, child_path, layer)
            return result
        stamp(new, path, layer)
        return copy.deepcopy(new)

    previous = -1
    order = ["base", "personal", "project", "machine"]
    for layer, data in layers:
        _validate(layer, data)
        index = order.index(layer)
        if index < previous:
            raise ValueError("layers must be base → personal → project → machine")
        previous = index
        values = merge(values, data, "", layer)
    return Resolved(values, sources)


def load_project(root: Path) -> dict[str, Any]:
    return resolve_layers([("project", read_toml(root / "ai-dlc.toml"))]).values


def resolve_files(
    base: Path | None = None,
    personal: Path | None = None,
    project: Path | None = None,
    machine: Path | None = None,
) -> Resolved:
    return resolve_layers(
        [
            (name, read_toml(path))
            for name, path in [
                ("base", base),
                ("personal", personal),
                ("project", project),
                ("machine", machine),
            ]
            if path
        ]
    )
