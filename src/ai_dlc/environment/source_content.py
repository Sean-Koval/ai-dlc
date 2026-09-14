"""Bounded source content validation, independent of selection and transport."""

from __future__ import annotations

import re
import stat
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from ai_dlc.config import _field_tokens, _is_sensitive_field, digest
from ai_dlc.environment.source_schema import SourceSubscription

FEATURES = {"session-context", "bound-push", "stop-reminder"}


@dataclass(frozen=True)
class SourceItem:
    kind: str
    name: str
    path: str
    roles: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    body: str = ""
    server: dict[str, Any] = field(default_factory=dict)


def slug(value: Any, path: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[a-z0-9][a-z0-9-]*", value) is None:
        raise ValueError(f"source name must be a lowercase slug: {path}")
    return value


def selectors(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"source roles/tags must be a list: {path}")  # noqa: TRY004 -- reject untrusted document content
    if not all(
        isinstance(entry, str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]*", entry) for entry in value
    ):
        raise ValueError(f"source roles/tags must be safe lowercase identifiers: {path}")
    values = tuple(value)
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate source role/tag: {path}")
    return values


def reject_values(value: Any, path: str) -> None:
    """Reject structured credentials and common credential assignments, without echoing values."""
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                not isinstance(key, str)
                or _is_sensitive_field(_field_tokens(key))
                or key
                in {
                    "env",
                    "environment",
                    "headers",
                }
            ):
                raise ValueError(f"source environment or credential value prohibited: {path}")
            reject_values(child, path)
    elif isinstance(value, list):
        for child in value:
            reject_values(child, path)
    elif isinstance(value, str) and re.search(
        r"(?i)(?:token|password|passwd|secret|api[_-]?key|authorization)\s*[=:]|"
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
        r"https?://[^/\s]*@|(?:gh[pousr]_|sk-)[A-Za-z0-9]{12,}",
        value,
    ):
        raise ValueError(f"source credential value prohibited: {path}")


def read_tree(root: Path, *, cached: bool = False) -> dict[str, str]:
    # Reuse descriptor-bound bundle reads, including no-follow and mutation checks.
    from ai_dlc.harness import workflow_bundles as fs

    try:
        before = fs._checkout_tree(root, ignore_root_git=not cached)
        entries = before[1]
        regular = [name for name, identity in entries.items() if stat.S_ISREG(identity[2])]
        if len(regular) > 1024 or len(entries) > 4096:
            raise ValueError("source tree exceeds 1024 files or 4096 entries")
        result: dict[str, str] = {}
        total = 0
        for name, identity in sorted(entries.items()):
            fs._payload_path(name, field="source path")
            if "env" in PurePosixPath(name).parts:
                unsafe = next((entry for entry in regular if entry.startswith(name + "/")), name)
                raise ValueError(f"source env/ content prohibited: {unsafe}")
            if stat.S_ISDIR(identity[2]):
                continue
            if identity[2] & 0o111:
                raise ValueError(f"source executable prohibited: {name}")
            data = fs._regular_file_bytes(root, PurePosixPath(name), maximum=2 * 1024 * 1024)
            total += len(data)
            if total > 10 * 1024 * 1024:
                raise ValueError(f"source exceeds 10 MiB: {name}")
            try:
                result[name] = data.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError(f"source must be UTF-8: {name}") from None
            reject_values(result[name], name)
            if "<!-- ai-dlc:" in result[name]:
                raise ValueError(f"source cannot contain render ownership markers: {name}")
        if fs._checkout_tree(root, ignore_root_git=not cached) != before:
            raise ValueError("source tree changed during validation")
        return result
    except OSError:
        raise ValueError("source filesystem validation failed") from None


def content_digest(files: dict[str, str]) -> str:
    return digest(files)


def toml_document(files: dict[str, str], path: str) -> dict[str, Any]:
    if path not in files:
        raise ValueError(f"source file missing: {path}")
    if len(files[path].encode()) > 1024 * 1024:
        raise ValueError(f"source manifest exceeds 1 MiB: {path}")
    try:
        value = tomllib.loads(files[path])
    except tomllib.TOMLDecodeError:
        raise ValueError(f"invalid source TOML: {path}") from None
    reject_values(value, path)
    return value


def command_server(value: Any, path: str, *, teamai: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"source MCP server must be a mapping: {path}")  # noqa: TRY004 -- reject untrusted document content
    reject_values(value, path)
    allowed = (
        {"name", "transport", "description", "command", "args"}
        if teamai
        else {"id", "command", "args"}
    )
    if set(value) - allowed:
        raise ValueError(f"unsupported source MCP fields: {path}")
    if teamai and value.get("transport", "stdio") != "stdio":
        raise ValueError(f"source MCP supports command declarations only: {path}")
    name = slug(value.get("name" if teamai else "id"), path)
    command = value.get("command")
    # Single executable name only; no shell text, local path or environment expansion.
    if (
        not isinstance(command, str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", command) is None
    ):
        raise ValueError(f"source MCP command must be an executable name: {path}")
    args = value.get("args", [])
    if not isinstance(args, list) or not all(
        isinstance(arg, str)
        and not any(ord(c) < 32 for c in arg)
        and not arg.startswith(("/", "~", "file:"))
        and "${" not in arg
        for arg in args
    ):
        raise ValueError(f"source MCP arguments must be portable strings: {path}")
    for arg in args:
        option = arg.lstrip("-").split("=", 1)[0]
        if (
            arg.startswith("-")
            and (_is_sensitive_field(_field_tokens(option)) or option in {"env", "environment"})
        ) or re.match(r"[A-Z_][A-Z0-9_]*=", arg):
            # Inspect option names even when the value is the next argv element.
            raise ValueError(f"source MCP credential or environment argument prohibited: {path}")
    return {"id": name, "command": command, "args": args}


def native_items(files: dict[str, str]) -> tuple[list[SourceItem], list[str]]:
    manifest = toml_document(files, "manifest.toml")
    if (
        set(manifest) != {"schema", "items"}
        or manifest["schema"] != 1
        or not isinstance(manifest["items"], list)
    ):
        raise ValueError("manifest.toml requires schema=1 and an items list")
    items: list[SourceItem] = []
    declared = {"manifest.toml"}
    seen: set[tuple[str, str]] = set()
    for entry in manifest["items"]:
        if not isinstance(entry, dict) or set(entry) - {"kind", "name", "path", "roles", "tags"}:
            raise ValueError("invalid source item: manifest.toml")
        kind, path = entry.get("kind"), entry.get("path")
        name = slug(entry.get("name"), "manifest.toml")
        expected = {
            "skill": f"skills/{name}/SKILL.md",
            "rule": f"rules/{name}.md",
            "hook": "hooks/hooks.toml",
            "mcp": "mcp/servers.toml",
        }
        if kind not in expected or path != expected[kind]:
            raise ValueError(f"invalid source item layout: manifest.toml ({name})")
        if (kind, name) in seen:
            raise ValueError(f"duplicate source item: manifest.toml ({name})")
        seen.add((kind, name))
        if path not in files:
            raise ValueError(f"source file missing: {path}")
        declared.add(path)
        server = {}
        if kind == "mcp":
            document = toml_document(files, path)
            if set(document) != {"servers"} or not isinstance(document["servers"], list):
                raise ValueError(f"source MCP requires a servers list: {path}")
            servers = [command_server(value, path) for value in document["servers"]]
            matches = [value for value in servers if value["id"] == name]
            if len(matches) != 1 or len({value["id"] for value in servers}) != len(servers):
                raise ValueError(f"source MCP name missing or duplicated: {path}")
            server = matches[0]
        if kind == "hook":
            document = toml_document(files, path)
            if (
                set(document) != {"features"}
                or not isinstance(document["features"], list)
                or not all(
                    isinstance(feature, str) and feature in FEATURES
                    for feature in document["features"]
                )
                or name not in document["features"]
            ):
                raise ValueError(f"source hooks must name supported AI-DLC features: {path}")
        if kind in {"skill", "rule"} and not files[path].strip():
            raise ValueError(f"source Markdown must not be empty: {path}")
        items.append(
            SourceItem(
                kind,
                name,
                path,
                selectors(entry.get("roles", []), path),
                selectors(entry.get("tags", []), path),
                files[path],
                server,
            )
        )
    extra = sorted(set(files) - declared)
    if extra:
        raise ValueError(f"undeclared source file: {extra[0]}")
    return items, []


def source_items(
    files: dict[str, str], source: SourceSubscription
) -> tuple[list[SourceItem], list[str]]:
    if source.layout == "teamai":
        from ai_dlc.providers.teamai import teamai_items

        return teamai_items(files)
    return native_items(files)
