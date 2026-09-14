"""Read the supported Tencent teamai repository format; never run teamai."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

import yaml

from ai_dlc.environment.source_content import (
    SourceItem,
    command_server,
    reject_values,
    selectors,
    slug,
)


def yaml_document(content: str, path: str) -> dict[str, Any]:
    """Parse bounded data without aliases, duplicate keys or executable YAML tags."""
    if len(content.encode()) > 1024 * 1024:
        raise ValueError(f"source YAML exceeds 1 MiB: {path}")

    class StrictLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            mapping = {}
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                if not isinstance(key, str) or key in mapping:
                    raise ValueError(f"duplicate or invalid YAML key: {path}")
                mapping[key] = self.construct_object(value_node, deep=deep)
            return mapping

    try:
        depth = 0
        for event in yaml.parse(content, Loader=StrictLoader):
            if isinstance(event, yaml.AliasEvent):
                raise ValueError(f"source YAML aliases prohibited: {path}")  # noqa: TRY004 -- reject untrusted document content
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                if depth > 32:
                    raise ValueError(f"source YAML nesting exceeds 32: {path}")
            if isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
        value = yaml.load(content, Loader=StrictLoader)
    except yaml.YAMLError:
        raise ValueError(f"invalid source YAML: {path}") from None
    if not isinstance(value, dict):
        raise ValueError(f"source YAML must be a mapping: {path}")  # noqa: TRY004 -- reject untrusted document content
    reject_values(value, path)
    return value


def _frontmatter(body: str, path: str) -> dict[str, Any]:
    if not body.startswith("---\n"):
        return {}
    _, separator, _ = body[4:].partition("\n---\n")
    if not separator:
        raise ValueError(f"unterminated source frontmatter: {path}")
    return yaml_document(body[4:].split("\n---\n", 1)[0], path)


def _tag_map(value: Any, path: str) -> dict[str, dict[str, tuple[str, ...]]]:
    if not isinstance(value, dict):
        raise ValueError(f"source tags must be a mapping: {path}")  # noqa: TRY004 -- reject untrusted document content
    result: dict[str, dict[str, tuple[str, ...]]] = {}
    for kind in ("skills", "rules"):
        entries = value.get(kind, {})
        if not isinstance(entries, dict):
            raise ValueError(f"source tags.{kind} must be a mapping: {path}")  # noqa: TRY004 -- reject untrusted document content
        result[kind] = {name: selectors(tags, path) for name, tags in entries.items()}
    return result


def _role_map(value: Any, path: str) -> dict[str, set[str]]:
    if not isinstance(value, list):
        raise ValueError(f"source roles must be a list: {path}")  # noqa: TRY004 -- reject untrusted document content
    result: dict[str, set[str]] = {}
    seen: set[str] = set()
    for role in value:
        if not isinstance(role, dict):
            raise ValueError(f"source role must be a mapping: {path}")  # noqa: TRY004 -- reject untrusted document content
        role_id = selectors([role.get("id")], path)[0]
        if role_id in seen:
            raise ValueError(f"duplicate source role: {path}")
        seen.add(role_id)
        resources = role.get("resources", {})
        if not isinstance(resources, dict):
            raise ValueError(f"source role resources must be a mapping: {path}")  # noqa: TRY004 -- reject untrusted document content
        for namespace in selectors(resources.get("skills", []), path):
            result.setdefault(namespace, set()).add(role_id)
    return result


def teamai_items(files: dict[str, str]) -> tuple[list[SourceItem], list[str]]:
    config = yaml_document(files["teamai.yaml"], "teamai.yaml") if "teamai.yaml" in files else {}
    tag_maps = [_tag_map(config.get("tags", {}), "teamai.yaml")]
    if "tags.yaml" in files:
        tag_maps.append(_tag_map(yaml_document(files["tags.yaml"], "tags.yaml"), "tags.yaml"))
    role_map = _role_map(config.get("roles", []), "teamai.yaml")
    if "manifest/roles.yaml" in files:
        manifest = yaml_document(files["manifest/roles.yaml"], "manifest/roles.yaml")
        role_map = _role_map(manifest.get("roles"), "manifest/roles.yaml")
    items: list[SourceItem] = []
    notes: list[str] = []
    for path, body in sorted(files.items()):
        if path in {"teamai.yaml", "tags.yaml", "manifest/roles.yaml"}:
            continue
        parts = PurePosixPath(path).parts
        if parts[0] in {"hooks", "agents", "docs"}:
            if path.endswith((".yaml", ".yml")):
                yaml_document(body, path)
            notes.append(f"ignored {path}: teamai {parts[0]} semantics are not imported")
            continue
        if path == "mcp/mcp.yaml":
            document = yaml_document(body, path)
            if set(document) != {"servers"} or not isinstance(document["servers"], list):
                raise ValueError(f"teamai MCP requires a servers list: {path}")
            for entry in document["servers"]:
                server = command_server(entry, path, teamai=True)
                items.append(SourceItem("mcp", server["id"], path, server=server))
            continue
        if path == "culture.md":
            kind, name = "rule", "culture"
        elif parts[0] == "skills" and len(parts) in {3, 4} and parts[-1] == "SKILL.md":
            kind, name = "skill", slug(parts[-2], path)
        elif parts[0] == "rules" and len(parts) == 2 and path.endswith(".md"):
            kind, name = "rule", slug(PurePosixPath(path).stem, path)
        else:
            raise ValueError(f"unsupported teamai source path: {path}")
        if not body.strip():
            raise ValueError(f"source Markdown must not be empty: {path}")
        metadata = _frontmatter(body, path)
        if kind == "skill" and metadata.get("name", name) != name:
            raise ValueError(f"source skill name differs from directory: {path}")
        roles = set(selectors(metadata.get("roles", []), path))
        tags = set(selectors(metadata.get("tags", []), path))
        for tag_map in tag_maps:
            tags.update(tag_map[kind + "s"].get(name, ()))
            tags.update(tag_map[kind + "s"].get("/".join(parts[1:-1]), ()))
        if kind == "skill" and len(parts) == 4:
            namespace = selectors([parts[1]], path)[0]
            # Unknown namespaces stay restricted, never accidentally universal.
            roles.update(role_map.get(namespace, {namespace}))
        items.append(SourceItem(kind, name, path, tuple(sorted(roles)), tuple(sorted(tags)), body))
    names = [(item.kind, item.name) for item in items]
    if len(set(names)) != len(names):
        raise ValueError("duplicate teamai source item name")
    return items, notes
