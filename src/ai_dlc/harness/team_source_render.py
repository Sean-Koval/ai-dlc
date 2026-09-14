"""Merge verified team declarations into existing owned render plans."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_dlc.environment.team_sources import SelectedSources
from ai_dlc.files import assets


def merge_source_items(
    selected: SelectedSources,
    config: dict[str, Any],
    skills: dict[str, str],
    bundles: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, str]]:
    names = set(skills) | set(
        json.loads((assets("agents") / "skills.lock.json").read_text())["skills"]
    )
    names.update(name for bundle in bundles.values() for name in bundle["manifest"]["skills"])
    servers = config.setdefault("agents", {}).setdefault("servers", [])
    server_names = {server["id"] for server in servers}
    source_skills: dict[str, str] = {}
    rule_names: set[str] = set()
    lines: list[str] = []
    hooks: set[str] = set()
    for source_id, item in selected.items:
        if item.kind == "skill":
            if item.name in names:
                raise ValueError(f"team source skill collision: {item.name}")
            names.add(item.name)
            skills[item.name] = item.body
            source_skills[item.name] = source_id
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
        if item.kind in {"skill", "rule"}:
            lines.extend([f"### Team {item.kind}: {item.name} ({source_id})", "", item.body, ""])
    for client in config.get("roles", {}).get("agent-client", []):
        if not hooks:
            break
        settings = config["agents"].setdefault("clients", {}).setdefault(client, {})
        settings["required_hooks"] = sorted(set(settings.get("required_hooks", [])) | hooks)
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
            relative_directory = str(directory.relative_to(root))
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
