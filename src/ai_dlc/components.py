"""Verified, non-executable component metadata."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from ai_dlc.config import read_toml
from ai_dlc.files import assets, inside

_CATALOG_FIELDS = {"schema", "components"}
_COMPONENT_FIELDS = {"id", "roles", "modules", "guidance", "required_config"}
_COMPONENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_CONFIG_PATH = re.compile(r"^[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROLES = {"specs", "tracker", "knowledge", "scm", "deploy"}


def _relative_path(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a relative normalized path")
    path = PurePosixPath(value)
    if (
        "\\" in value
        or value != path.as_posix()
        or path.is_absolute()
        or PureWindowsPath(value).drive != ""
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"{field} must be a relative normalized path")
    return path.as_posix()


def _regular_file(root: Path, relative: str, *, field: str) -> Path:
    path = inside(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{field} must name an existing regular file: {relative}")
    return path


def _string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a string list")
    if len(value) != len(set(value)):
        raise ValueError(f"{field} must not contain duplicates")
    return value


def _validate_catalog(
    data: Any, *, module_ids: set[str], guidance_root: Path, source: str
) -> list[dict[str, Any]]:
    if (
        not isinstance(data, dict)
        or set(data) != _CATALOG_FIELDS
        or type(data.get("schema")) is not int
        or data["schema"] != 1
    ):
        raise ValueError(f"{source}: expected component catalog schema 1")
    if not isinstance(data["components"], list):
        raise TypeError(f"{source}: components must be a list")

    declared_ids = [
        entry.get("id")
        for entry in data["components"]
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    ]
    if len(declared_ids) != len(set(declared_ids)):
        raise ValueError(f"{source}: duplicate component ID")

    components: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, entry in enumerate(data["components"]):
        prefix = f"{source}: components[{index}]"
        if not isinstance(entry, dict) or set(entry) != _COMPONENT_FIELDS:
            raise ValueError(f"{prefix} has unknown or missing fields")
        component_id = entry["id"]
        if not isinstance(component_id, str) or not _COMPONENT_ID.fullmatch(component_id):
            raise ValueError(f"{prefix}.id must be a stable slug")
        if component_id in ids:
            raise ValueError(f"{source}: duplicate component ID: {component_id}")
        ids.add(component_id)

        roles = _string_list(entry["roles"], field=f"{prefix}.roles")
        if not roles or set(roles) - _ROLES:
            raise ValueError(f"{prefix}.roles contains an incompatible role")

        modules = _string_list(entry["modules"], field=f"{prefix}.modules")
        unknown_modules = sorted(set(modules) - module_ids)
        if unknown_modules:
            raise ValueError(f"{prefix}.modules names unknown module: {unknown_modules[0]}")

        guidance = _string_list(entry["guidance"], field=f"{prefix}.guidance")
        for guidance_path in guidance:
            relative = _relative_path(guidance_path, field=f"{prefix}.guidance")
            if not relative.endswith(".md"):
                raise ValueError(f"{prefix}.guidance must name Markdown files")
            _regular_file(guidance_root, relative, field=f"{prefix}.guidance")

        required_config = _string_list(entry["required_config"], field=f"{prefix}.required_config")
        if any(not _CONFIG_PATH.fullmatch(path) for path in required_config):
            raise ValueError(f"{prefix}.required_config must contain configuration paths")

        components.append(
            {
                "id": component_id,
                "roles": roles,
                "modules": modules,
                "guidance": guidance,
                "required_config": required_config,
            }
        )
    return components


def _custom_manifests(root: Path, config: dict) -> list[tuple[str, bytes]]:
    providers = config.get("providers", {})
    if not isinstance(providers, dict):
        raise TypeError("providers must be a table")
    manifests: list[tuple[str, bytes]] = []
    for provider_id, settings in providers.items():
        if not isinstance(settings, dict):
            raise TypeError(f"providers.{provider_id} must be a table")
        manifest = settings.get("component_manifest")
        digest = settings.get("component_manifest_sha256")
        if manifest is None and digest is None:
            continue
        if manifest is None or digest is None:
            raise ValueError(
                f"providers.{provider_id} component manifests require a SHA-256 digest"
            )
        relative = _relative_path(manifest, field=f"providers.{provider_id}.component_manifest")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise ValueError(f"providers.{provider_id}.component_manifest_sha256 must be SHA-256")
        path = _regular_file(root, relative, field=f"providers.{provider_id}.component_manifest")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError(f"providers.{provider_id} component manifest digest mismatch")
        manifests.append((str(provider_id), content))
    return manifests


def load_component_catalog(root: Path, config: dict) -> dict:
    """Load built-in and explicitly digest-verified repository component manifests."""
    if not isinstance(config, dict):
        raise TypeError("component configuration must be a table")
    root = Path(root).resolve()
    module_ids = set(read_toml(assets("modules") / "catalog.toml"))
    components = _validate_catalog(
        json.loads((assets("modules") / "components.json").read_text()),
        module_ids=module_ids,
        guidance_root=assets("agents"),
        source="packaged component catalog",
    )
    ids = {component["id"] for component in components}
    for provider_id, manifest_bytes in _custom_manifests(root, config):
        additions = _validate_catalog(
            json.loads(manifest_bytes),
            module_ids=module_ids,
            guidance_root=root,
            source=f"providers.{provider_id}.component_manifest",
        )
        for component in additions:
            if component["id"] in ids:
                raise ValueError(f"duplicate component ID: {component['id']}")
            ids.add(component["id"])
            components.append(component)
    return {"schema": 1, "components": sorted(components, key=lambda component: component["id"])}
