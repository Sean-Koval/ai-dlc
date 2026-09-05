"""Scoped configuration resolution; project files never depend on personal state."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_dlc.enrollment import EnrollmentPaths

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
    "profile_id": {"personal"},
    "credentials": {"personal", "machine"},
}

_CREDENTIAL_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_ENVIRONMENT_VARIABLE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_SENSITIVE_FIELD_TOKENS = {"token", "password", "passwd", "secret"}
_SENSITIVE_FIELD_PAIRS = {
    ("api", "key"),
    ("access", "key"),
    ("client", "key"),
    ("private", "key"),
}
_SENSITIVE_COMPACT_FIELDS = {
    "apikey",
    "apitoken",
    "accesskey",
    "accesstoken",
    "clientkey",
    "clientsecret",
    "privatekey",
}
_BENIGN_INTEGER_TOKEN_FIELDS = {
    ("max", "token"),
    ("token", "count"),
}
_COMPONENT_PROVIDER_FIELDS = {
    "component",
    "component_manifest",
    "component_manifest_sha256",
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


def _field_tokens(field: str) -> tuple[str, ...]:
    separated = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", field)
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", separated)
    tokens = [token.lower() for token in re.split(r"[^A-Za-z0-9]+", separated) if token]
    singular = {
        "tokens": "token",
        "passwords": "password",
        "secrets": "secret",
        "keys": "key",
    }
    return tuple(singular.get(token, token) for token in tokens)


def _is_sensitive_field(tokens: tuple[str, ...]) -> bool:
    if _SENSITIVE_FIELD_TOKENS.intersection(tokens):
        return True
    if "".join(tokens) in _SENSITIVE_COMPACT_FIELDS:
        return True
    adjacent = set(pairwise(tokens))
    return bool(_SENSITIVE_FIELD_PAIRS.intersection(adjacent))


def _is_environment_reference(tokens: tuple[str, ...], value: Any) -> bool:
    suffix_length = 2 if tokens[-2:] == ("env", "var") else 1 if tokens[-1:] == ("env",) else 0
    return bool(
        suffix_length
        and _is_sensitive_field(tokens[:-suffix_length])
        and isinstance(value, str)
        and _ENVIRONMENT_VARIABLE.fullmatch(value)
    )


def _is_benign_integer_token_field(tokens: tuple[str, ...], value: Any) -> bool:
    return tokens in _BENIGN_INTEGER_TOKEN_FIELDS and type(value) is int


def _validate_credentials(layer: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{layer}: credentials must be a table")
    for credential_id, entry in value.items():
        if not isinstance(credential_id, str) or not _CREDENTIAL_ID.fullmatch(credential_id):
            raise ValueError(f"{layer}: credential ID must be a stable slug: {credential_id!r}")
        if not isinstance(entry, dict):
            raise TypeError(f"{layer}: credentials.{credential_id} must be a table")
        if layer == "personal":
            if "source" in entry or "variable" in entry:
                invalid = "source" if "source" in entry else "variable"
                raise ValueError(f"personal: cannot set credentials.{credential_id}.{invalid}")
            if not isinstance(entry.get("description"), str):
                raise ValueError(
                    f"personal: credentials.{credential_id}.description must be a string"
                )
            required_by = entry.get("required_by")
            if not isinstance(required_by, list) or not all(
                isinstance(provider, str) for provider in required_by
            ):
                raise ValueError(
                    f"personal: credentials.{credential_id}.required_by must be a string list"
                )
        elif layer == "machine":
            if set(entry) != {"source", "variable"}:
                invalid = next((key for key in entry if key not in {"source", "variable"}), None)
                if invalid is not None:
                    raise ValueError(f"machine: cannot set credentials.{credential_id}.{invalid}")
                raise ValueError(
                    f"machine: credentials.{credential_id} must contain source and variable"
                )
            if entry.get("source") != "environment":
                raise ValueError(f"machine: credentials.{credential_id}.source must be environment")
            variable = entry.get("variable")
            if not isinstance(variable, str) or not _ENVIRONMENT_VARIABLE.fullmatch(variable):
                raise ValueError(
                    f"machine: credentials.{credential_id}.variable must be an environment variable"
                )


def validate_provider_metadata(value: Any, *, layer: str | None = None) -> None:
    prefix = f"{layer}: " if layer is not None else ""
    if not isinstance(value, dict):
        raise TypeError(f"{prefix}providers must be a table")
    for provider_id, settings in value.items():
        if not isinstance(settings, dict):
            raise TypeError(f"{prefix}providers.{provider_id} must be a table")
        for field in _COMPONENT_PROVIDER_FIELDS.intersection(settings):
            if not isinstance(settings[field], str):
                raise TypeError(f"{prefix}providers.{provider_id}.{field} must be a string")
        if layer == "machine":
            forbidden = sorted(_COMPONENT_PROVIDER_FIELDS.intersection(settings))
            if forbidden:
                raise ValueError(f"machine: cannot set providers.{provider_id}.{forbidden[0]}")
        has_manifest = "component_manifest" in settings
        has_digest = "component_manifest_sha256" in settings
        if has_manifest != has_digest:
            raise ValueError(
                f"{prefix}providers.{provider_id} must set component manifest "
                "and component_manifest_sha256 together"
            )


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

    def secrets(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                tokens = _field_tokens(key)
                if (
                    _is_sensitive_field(tokens)
                    and not _is_environment_reference(tokens, child)
                    and not _is_benign_integer_token_field(tokens, child)
                ):
                    raise ValueError(
                        f"{layer}: credential value prohibited at {path}{key}; use environment reference"
                    )
                secrets(child, path + key + ".")
        elif isinstance(value, list):
            for child in value:
                secrets(child, path)

    secrets(data)
    if "credentials" in data:
        _validate_credentials(layer, data["credentials"])
    if "providers" in data:
        validate_provider_metadata(data["providers"], layer=layer)
    # Machine overrides may select credentials/accounts, never executable provider behavior.
    if layer == "machine":
        for name, settings in data.get("providers", {}).items():
            for key in settings:
                if key not in {"account", "token_env", "vault_path", "sandbox_workspace"}:
                    raise ValueError(f"machine: cannot set providers.{name}.{key}")


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


def resolve_runtime(
    root: Path | None = None,
    *,
    base: Path | None = None,
    personal: Path | None = None,
    project: Path | None = None,
    machine: Path | None = None,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
    enrollment_paths: EnrollmentPaths | None = None,
) -> Resolved:
    """Resolve the packaged base plus any active, verified enrollment layers."""
    from ai_dlc.enrollment import EnrollmentPaths, read_lock
    from ai_dlc.files import assets
    from ai_dlc.profile_source import verify_cached_profile

    paths = enrollment_paths or EnrollmentPaths.from_environment(home=home, environ=environ)
    enrolled_personal: Path | None = None
    enrolled_machine: Path | None = None
    if personal is None or machine is None:
        lock = read_lock(paths)
        if lock is not None:
            if personal is None:
                enrolled_personal = verify_cached_profile(lock, paths)
            if machine is None:
                enrolled_machine = paths.machine_file(lock.machine_id)

    project_file = project
    if project_file is None and root is not None and (root / "ai-dlc.toml").exists():
        project_file = root / "ai-dlc.toml"
    return resolve_files(
        base=base or assets("profiles") / "base.toml",
        personal=personal or enrolled_personal,
        project=project_file,
        machine=machine or enrolled_machine,
    )
