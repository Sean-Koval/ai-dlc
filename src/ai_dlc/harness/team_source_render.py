"""Merge verified team declarations into existing owned render plans."""

from __future__ import annotations

import json
import string
import unicodedata
from pathlib import Path
from typing import Any

from ai_dlc.environment.team_sources import SelectedSources
from ai_dlc.files import assets
from ai_dlc.providers.teamai import yaml_document

_DESCRIPTION_FALLBACK = "Read the linked skill for its instructions."
_MARKDOWN_PUNCTUATION = frozenset(string.punctuation) - {"&", "<", ">", '"', "'"}
_MAX_DESCRIPTION_CHARACTERS = 240


def _escaped_description(value: str) -> str:
    normalized = "".join(
        " "
        if character.isspace()
        else ""
        if unicodedata.category(character).startswith("C")
        else character
        for character in value
    )
    normalized = " ".join(normalized.split())
    if not normalized:
        return _DESCRIPTION_FALLBACK
    escaped = []
    for character in normalized:
        if character == "&":
            escaped.append("&amp;")
        elif character == "<":
            escaped.append("&lt;")
        elif character == ">":
            escaped.append("&gt;")
        elif character == '"':
            escaped.append("&quot;")
        elif character == "'":
            escaped.append("&#x27;")
        elif character in _MARKDOWN_PUNCTUATION:
            escaped.append("\\" + character)
        else:
            escaped.append(character)
    if sum(map(len, escaped)) <= _MAX_DESCRIPTION_CHARACTERS:
        return "".join(escaped)
    bounded: list[str] = []
    length = 0
    for chunk in escaped:
        if length + len(chunk) + 1 > _MAX_DESCRIPTION_CHARACTERS:
            break
        bounded.append(chunk)
        length += len(chunk)
    return "".join(bounded) + "…"


def _skill_description(body: str) -> str:
    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        return _DESCRIPTION_FALLBACK
    metadata, separator, _ = normalized[4:].partition("\n---\n")
    if not separator:
        if not normalized.endswith("\n---"):
            return _DESCRIPTION_FALLBACK
        metadata = normalized[4:-4]
    try:
        value = yaml_document(metadata, "team skill frontmatter").get("description")
    except (TypeError, ValueError):
        return _DESCRIPTION_FALLBACK
    return _escaped_description(value) if isinstance(value, str) else _DESCRIPTION_FALLBACK


def _skill_links(name: str, clients: list[str], directories: dict[str, str]) -> str:
    destinations: dict[str, set[str]] = {}
    for client in clients:
        path = f"{directories[client]}/skills/{name}/SKILL.md"
        destinations.setdefault(path, set()).add(client)
    return ", ".join(
        f"[{', '.join(sorted(labels))}](<{path}>)" for path, labels in sorted(destinations.items())
    )


def merge_source_items(
    selected: SelectedSources,
    config: dict[str, Any],
    skills: dict[str, str],
    bundles: dict[str, dict[str, Any]],
    clients: list[str],
    directories: dict[str, str],
) -> tuple[str, dict[str, str]]:
    names = set(skills) | set(
        json.loads((assets("agents") / "skills.lock.json").read_text(encoding="utf-8"))["skills"]
    )
    names.update(name for bundle in bundles.values() for name in bundle["manifest"]["skills"])
    servers = config.setdefault("agents", {}).setdefault("servers", [])
    server_names = {server["id"] for server in servers}
    source_skills: dict[str, str] = {}
    rule_names: set[str] = set()
    lines: list[str] = []
    skill_entries: list[str] = []
    hooks: set[str] = set()
    for source_id, item in selected.items:
        if item.kind == "skill":
            if item.name in names:
                raise ValueError(f"team source skill collision: {item.name}")
            names.add(item.name)
            skills[item.name] = item.body
            source_skills[item.name] = source_id
            if clients:
                skill_entries.append(
                    f"- `{item.name}` (source `{source_id}`): {_skill_description(item.body)} — "
                    f"{_skill_links(item.name, clients, directories)}"
                )
        elif item.kind == "rule":
            if item.name in rule_names:
                raise ValueError(f"team source rule collision: {item.name}")
            rule_names.add(item.name)
        elif item.kind == "mcp":
            if item.name in server_names:
                raise ValueError(f"team source MCP server collision: {item.name}")
            server_names.add(item.name)
            servers.append(item.server)
        elif item.kind == "hook":
            hooks.add(item.name)
        if item.kind == "rule" or (item.kind == "skill" and not clients):
            lines.extend([f"### Team {item.kind}: {item.name} ({source_id})", "", item.body, ""])
    for client in config.get("roles", {}).get("agent-client", []):
        if not hooks:
            break
        settings = config["agents"].setdefault("clients", {}).setdefault(client, {})
        settings["required_hooks"] = sorted(set(settings.get("required_hooks", [])) | hooks)
    if skill_entries:
        lines = [
            (
                "Read a linked `SKILL.md` before using an applicable team skill. Use these "
                "links as the manual fallback when native skill discovery is unavailable or "
                "unverified."
            ),
            "",
            "### Team skills",
            "",
            *skill_entries,
            "",
            *lines,
        ]
    return ("\n## Team sources\n\n" + "\n".join(lines) if lines else ""), source_skills


def check_source_skill_destinations(
    root: Path,
    read,
    clients: list[str],
    directories: dict[str, str],
    source_skills: dict[str, str],
    previous: dict[str, Any],
) -> tuple[dict[str, str], dict[str, str]]:
    prior = previous.get("source_skills", {})
    owned_directories = dict(previous.get("source_directories", {}))
    if not isinstance(prior, dict):
        raise ValueError("invalid team source skill ownership")  # noqa: TRY004 -- reject untrusted document content
    ownership = dict(prior)
    for client in clients:
        prefix = directories[client] + "/skills/"
        for path in list(ownership):
            if path.startswith(prefix):
                del ownership[path]
        for name, source_id in source_skills.items():
            path = prefix + name + "/SKILL.md"
            current = read(path)
            directory = (root / path).parent
            relative_directory = directory.relative_to(root).as_posix()
            if current is not None:
                conflict = prior.get(path) != source_id or path not in previous.get("files", {})
            else:
                # Transactional retirement retains recovery backups in this directory.
                # Its recorded provenance permits restoring the absent SKILL.md without
                # touching those backups or claiming a genuinely authored directory.
                conflict = (
                    directory.exists() and owned_directories.get(relative_directory) != source_id
                )
            if conflict:
                raise ValueError(f"team source skill conflict with local ownership: {path}")
            ownership[path] = source_id
            owned_directories[relative_directory] = source_id
    return ownership, owned_directories
