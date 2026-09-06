"""Deterministic project guidance and client-owned configuration sections."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import tomli_w

from ai_dlc.components import load_component_catalog, resolve_components
from ai_dlc.config import load_project
from ai_dlc.files import assets, atomic_write, inside
from ai_dlc.locking import project_write_lock
from ai_dlc.workflow_bundles import MissingBundlePath, load_vendored_bundle

_BUNDLE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BUNDLE_PREFIXES = (".agents/skills/", ".claude/skills/", "docs/templates/")


def _section(current: str, body: str, toml: bool = False) -> str:
    start = "# ai-dlc:begin " if toml else "<!-- ai-dlc:begin "
    end = "# ai-dlc:end" if toml else "<!-- ai-dlc:end -->"
    suffix = "" if toml else " -->"
    pattern = re.compile(
        re.escape(start) + r"([0-9a-f]{64})" + re.escape(suffix) + r"\n(.*?)" + re.escape(end),
        re.DOTALL,
    )
    matches = list(pattern.finditer(current))
    if len(matches) > 1 or (start in current and not matches):
        raise ValueError("managed section conflict: malformed markers")
    new = start + hashlib.sha256(body.encode()).hexdigest() + suffix + "\n" + body + end
    if matches:
        match = matches[0]
        if hashlib.sha256(match.group(2).encode()).hexdigest() != match.group(1):
            raise ValueError(
                "managed section conflict: preserve user edit and resolve before apply"
            )
        return current[: match.start()] + new + current[match.end() :]
    return current.rstrip() + ("\n\n" if current else "") + new + "\n"


def provider_index(resolved: dict) -> tuple[str, dict[str, str]]:
    """Build portable links and owned copies from validated component requirements."""
    base = assets("agents")
    builtins = {
        item["id"]
        for item in json.loads((assets("modules") / "components.json").read_text())["components"]
    }
    lines = [(base / "templates/provider-index.md").read_text().rstrip(), ""]
    copies = {}
    for component in resolved["components"]:
        links = []
        for guidance in component["guidance"]:
            if component["id"] in builtins:
                destination = ".ai-dlc/" + guidance
                copies[destination] = inside(base, guidance).read_text()
            else:
                destination = guidance
            links.append(f"[{guidance}](<{destination}>)")
        modules = ", ".join(component["modules"]) or "none"
        lines.append(
            f"- {component['role']}: {component['provider']} (modules: {modules}); "
            + (", ".join(links) or "no component instructions declared")
        )
    for item in resolved["unresolved"]:
        lines.append(f"- {item['role']}: {item['provider']}; unsupported: {item['reason']}")
    return "\n".join(lines) + "\n", copies


def provider_guidance_ready(root: Path, index: str, copies: dict[str, str], client: str) -> bool:
    """Check that the supported harness can reach intact configured instructions."""
    try:
        for filename, expected in [
            ("AGENTS.md", index),
            *([("CLAUDE.md", "@AGENTS.md\n")] if client == "claude-code" else []),
        ]:
            current = inside(root, filename).read_text()
            if (
                current.count("<!-- ai-dlc:begin ") != 1
                or current.count("<!-- ai-dlc:end -->") != 1
            ):
                return False
            match = re.search(
                r"<!-- ai-dlc:begin ([0-9a-f]{64}) -->\n(.*?)<!-- ai-dlc:end -->",
                current,
                re.DOTALL,
            )
            if not match or expected not in match.group(2):
                return False
            if hashlib.sha256(match.group(2).encode()).hexdigest() != match.group(1):
                return False
        for name, body in copies.items():
            if inside(root, name).read_text() != body:
                return False
    except (OSError, ValueError):
        return False
    return True


def _selected_bundle_ids(config: dict[str, Any]) -> list[str]:
    selected = config.get("agents", {}).get("bundles", [])
    if not isinstance(selected, list) or not all(
        isinstance(bundle_id, str) and _BUNDLE_ID.fullmatch(bundle_id) for bundle_id in selected
    ):
        raise ValueError("agents.bundles must be a list of bundle-ID slugs")
    if len(set(selected)) != len(selected):
        raise ValueError("agents.bundles must not contain duplicate IDs")
    return sorted(selected)


def _load_selected_bundles(root: Path, bundle_ids: list[str]) -> dict[str, dict[str, Any]]:
    bundles: dict[str, dict[str, Any]] = {}
    for bundle_id in bundle_ids:
        try:
            bundles[bundle_id] = load_vendored_bundle(root, bundle_id)
        except ValueError as exc:
            raise ValueError(f"selected bundle {bundle_id} is invalid: {exc}") from exc
    return bundles


def _shipped_skill_names() -> set[str]:
    lock = json.loads((assets("agents") / "skills.lock.json").read_text())
    return set(lock["skills"])


def _bundle_collision_details(bundles: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    details = {bundle_id: [] for bundle_id in bundles}
    claims: dict[str, list[tuple[str, str]]] = {}
    shipped = _shipped_skill_names()
    for bundle_id, bundle in bundles.items():
        manifest = bundle["manifest"]
        for kind in ("skills", "templates"):
            for name in manifest[kind]:
                claims.setdefault(name, []).append((bundle_id, kind[:-1]))
                if kind == "skills" and name in shipped:
                    details[bundle_id].append(
                        f"bundle skill export collision with shipped skill: {name}"
                    )
    for name, owners in claims.items():
        if len(owners) < 2:
            continue
        claimants = ", ".join(sorted(bundle_id for bundle_id, _ in owners))
        for bundle_id, _ in owners:
            details[bundle_id].append(
                f"bundle export collision for {name} among selected bundles: {claimants}"
            )
    return {bundle_id: sorted(set(items)) for bundle_id, items in details.items()}


def _raise_bundle_collisions(bundles: dict[str, dict[str, Any]]) -> None:
    collisions = _bundle_collision_details(bundles)
    messages = [
        f"{bundle_id}: {detail}"
        for bundle_id in sorted(collisions)
        for detail in collisions[bundle_id]
    ]
    if messages:
        raise ValueError("bundle collision: " + "; ".join(messages))


def _bundle_index(bundles: dict[str, dict[str, Any]]) -> str:
    if not bundles:
        return ""
    lines = ["## Workflow bundles", ""]
    for bundle_id, bundle in sorted(bundles.items()):
        manifest = bundle["manifest"]
        for kind in ("skills", "templates"):
            for name, payload_path in sorted(manifest[kind].items()):
                destination = (
                    f".ai-dlc/bundles/{bundle_id}/{payload_path}"
                    if kind == "skills"
                    else f"docs/templates/{name}.md"
                )
                lines.append(f"- {bundle_id} {kind[:-1]}: [{name}](<{destination}>)")
    return "\n".join(lines) + "\n"


def _bundle_outputs(
    bundles: dict[str, dict[str, Any]], clients: list[str]
) -> dict[str, tuple[str, str]]:
    outputs: dict[str, tuple[str, str]] = {}
    for bundle_id, bundle in sorted(bundles.items()):
        manifest = bundle["manifest"]
        payload = bundle["payload"]
        for name, relative in sorted(manifest["skills"].items()):
            for client in clients:
                directory = ".agents" if client == "codex" else ".claude"
                outputs[f"{directory}/skills/{name}/SKILL.md"] = (
                    bundle_id,
                    payload[relative],
                )
        for name, relative in sorted(manifest["templates"].items()):
            outputs[f"docs/templates/{name}.md"] = (bundle_id, payload[relative])
    return outputs


def _prior_bundle_files(previous: Any) -> dict[str, dict[str, str]]:
    if not isinstance(previous, dict):
        raise TypeError("bundle ownership document must be an object")
    if previous.get("schema") != 3:
        return {}
    files = previous.get("files")
    bundle_files = previous.get("bundle_files")
    if not isinstance(files, dict) or not isinstance(bundle_files, dict):
        raise TypeError("bundle ownership schema 3 is invalid")
    normalized: dict[str, dict[str, str]] = {}
    for path, entry in bundle_files.items():
        if (
            not isinstance(path, str)
            or not path.startswith(_BUNDLE_PREFIXES)
            or not isinstance(entry, dict)
            or set(entry) != {"owner", "sha256"}
            or not isinstance(entry["owner"], str)
            or _BUNDLE_ID.fullmatch(entry["owner"]) is None
            or not isinstance(entry["sha256"], str)
            or _SHA256.fullmatch(entry["sha256"]) is None
            or files.get(path) != entry["sha256"]
        ):
            raise ValueError("bundle ownership schema 3 is invalid")
        normalized[path] = dict(entry)
    return normalized


def _managed_bundle_path(path: str, clients: list[str], *, full_render: bool) -> bool:
    if path.startswith("docs/templates/") or full_render:
        return True
    return (path.startswith(".agents/skills/") and "codex" in clients) or (
        path.startswith(".claude/skills/") and "claude-code" in clients
    )


def _plan_bundle_files(
    root: Path,
    bundles: dict[str, dict[str, Any]],
    clients: list[str],
    *,
    full_render: bool,
    owned_files: dict[str, str],
    bundle_files: dict[str, dict[str, str]],
    planned: dict[str, str],
    removed: list[str],
) -> None:
    desired = _bundle_outputs(bundles, clients)
    for path, ownership in list(bundle_files.items()):
        if not _managed_bundle_path(path, clients, full_render=full_render):
            continue
        destination = inside(root, path)
        if (
            destination.exists()
            and hashlib.sha256(destination.read_bytes()).hexdigest() != ownership["sha256"]
        ):
            raise ValueError(f"managed bundle output conflict: {path}")
        if path not in desired:
            if destination.exists():
                removed.append(path)
            bundle_files.pop(path)
            owned_files.pop(path, None)

    for path, (bundle_id, body) in desired.items():
        destination = inside(root, path)
        prior = bundle_files.get(path)
        if prior is None:
            if destination.exists() or path in owned_files:
                raise ValueError(f"bundle destination collision: {path}")
        elif prior["owner"] != bundle_id:
            raise ValueError(f"bundle destination collision: {path} is owned by {prior['owner']}")
        elif (
            destination.exists()
            and hashlib.sha256(destination.read_bytes()).hexdigest() != prior["sha256"]
        ):
            raise ValueError(f"managed bundle output conflict: {path}")
        digest = hashlib.sha256(body.encode()).hexdigest()
        planned[path] = body
        owned_files[path] = digest
        bundle_files[path] = {"owner": bundle_id, "sha256": digest}


def _apply_render_transaction(
    root: Path,
    planned: dict[str, str],
    removed: list[str],
    changed: list[str],
) -> None:
    paths = {name: inside(root, name) for name in changed}
    before = {
        name: (path.read_bytes(), path.stat().st_mode & 0o777) if path.exists() else None
        for name, path in paths.items()
    }
    try:
        for name in removed:
            paths[name].unlink()
        for name in changed:
            if name not in removed:
                atomic_write(paths[name], planned[name])
    except BaseException:
        for name, snapshot in before.items():
            path = paths[name]
            if snapshot is None:
                path.unlink(missing_ok=True)
                continue
            content, mode = snapshot
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ai-dlc-")
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary, mode)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        raise


def _managed_section_state(path: Path, required: str) -> str:
    if not path.exists():
        return "missing"
    if path.is_symlink() or not path.is_file():
        return "blocked"
    try:
        current = path.read_text()
    except OSError:
        return "blocked"
    matches = list(
        re.finditer(
            r"<!-- ai-dlc:begin ([0-9a-f]{64}) -->\n(.*?)<!-- ai-dlc:end -->",
            current,
            re.DOTALL,
        )
    )
    if len(matches) != 1:
        return "blocked"
    match = matches[0]
    if hashlib.sha256(match.group(2).encode()).hexdigest() != match.group(1):
        return "blocked"
    return "ready" if required in match.group(2) else "missing"


def inspect_bundle_guidance(root: Path, config: dict, clients: list[str]) -> list[dict]:
    """Inspect selected vendored guidance and rendered outputs without source access."""
    bundle_ids = _selected_bundle_ids(config)
    if not bundle_ids:
        return []
    states: dict[str, dict[str, list[str]]] = {
        bundle_id: {"blocked": [], "missing": []} for bundle_id in bundle_ids
    }
    bundles: dict[str, dict[str, Any]] = {}
    for bundle_id in bundle_ids:
        path = root / ".ai-dlc" / "bundles" / bundle_id
        if not path.exists() and not path.is_symlink():
            states[bundle_id]["missing"].append("vendored bundle path is missing")
            continue
        try:
            bundles[bundle_id] = load_vendored_bundle(root, bundle_id)
        except MissingBundlePath as exc:
            states[bundle_id]["missing"].append(f"vendored bundle path is missing: {exc.path}")
        except ValueError as exc:
            states[bundle_id]["blocked"].append(str(exc))

    collisions = _bundle_collision_details(bundles)
    for bundle_id, details in collisions.items():
        states[bundle_id]["blocked"].extend(details)

    ownership_path = root / ".ai-dlc" / "agent-ownership.json"
    previous: dict[str, Any] = {}
    prior_bundle_files: dict[str, dict[str, str]] = {}
    if ownership_path.exists():
        try:
            previous = json.loads(ownership_path.read_text())
            prior_bundle_files = _prior_bundle_files(previous)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            for bundle_id in bundle_ids:
                states[bundle_id]["blocked"].append(f"bundle ownership is invalid: {exc}")

    desired = _bundle_outputs(bundles, clients)
    for path, (bundle_id, body) in desired.items():
        try:
            destination = inside(root, path)
        except ValueError:
            states[bundle_id]["blocked"].append(f"rendered bundle output is a symlink: {path}")
            continue
        ownership = prior_bundle_files.get(path)
        if ownership is not None and ownership["owner"] != bundle_id:
            detail = (
                f"bundle destination collision between {bundle_id} and {ownership['owner']}: {path}"
            )
            states[bundle_id]["blocked"].append(detail)
            if ownership["owner"] in states:
                states[ownership["owner"]]["blocked"].append(detail)
            continue
        if not destination.exists():
            states[bundle_id]["missing"].append(f"rendered bundle output is missing: {path}")
            continue
        if not destination.is_file():
            states[bundle_id]["blocked"].append(
                f"owned bundle output is not a regular file: {path}"
            )
            continue
        if ownership is None:
            states[bundle_id]["blocked"].append(
                f"bundle destination collision with unowned file: {path}"
            )
            continue
        try:
            current_digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        except OSError:
            states[bundle_id]["blocked"].append(f"owned bundle output cannot be read: {path}")
            continue
        if current_digest != ownership["sha256"]:
            states[bundle_id]["blocked"].append(f"owned bundle output has local edits: {path}")
        elif current_digest != hashlib.sha256(body.encode()).hexdigest():
            states[bundle_id]["missing"].append(f"rendered bundle output is stale: {path}")

    desired_paths = set(desired)
    for path, ownership in prior_bundle_files.items():
        bundle_id = ownership["owner"]
        if bundle_id not in states or path in desired_paths:
            continue
        try:
            destination = inside(root, path)
        except ValueError:
            states[bundle_id]["blocked"].append(f"obsolete bundle output is a symlink: {path}")
            continue
        if destination.exists() and not destination.is_file():
            states[bundle_id]["blocked"].append(
                f"obsolete bundle output is not a regular file: {path}"
            )
            continue
        try:
            current_digest = (
                hashlib.sha256(destination.read_bytes()).hexdigest()
                if destination.exists()
                else None
            )
        except OSError:
            states[bundle_id]["blocked"].append(f"obsolete bundle output cannot be read: {path}")
            continue
        if current_digest is not None and current_digest != ownership["sha256"]:
            states[bundle_id]["blocked"].append(f"obsolete bundle output has local edits: {path}")
        else:
            states[bundle_id]["missing"].append(f"obsolete bundle output requires removal: {path}")

    index_state = _managed_section_state(root / "AGENTS.md", _bundle_index(bundles))
    if index_state != "ready":
        for bundle_id in bundles:
            states[bundle_id][index_state].append("managed workflow-bundle index is unavailable")
    if "claude-code" in clients:
        claude_state = _managed_section_state(root / "CLAUDE.md", "@AGENTS.md\n")
        if claude_state != "ready":
            for bundle_id in bundles:
                states[bundle_id][claude_state].append("CLAUDE.md does not reference AGENTS.md")

    results = []
    for bundle_id in bundle_ids:
        blocked = sorted(set(states[bundle_id]["blocked"]))
        missing = sorted(set(states[bundle_id]["missing"]))
        if blocked:
            status = "blocked"
            reason = blocked[0]
            action = (
                "Resolve bundle guidance conflicts or restore exact vendored and owned bytes, "
                "then run a full ai-dlc agents render --apply."
            )
        elif missing:
            status = "missing"
            reason = missing[0]
            action = "Restore missing vendored content if needed, then run a full ai-dlc agents render --apply."
        else:
            status = "ready"
            reason = "bundle guidance is intact and rendered for configured clients"
            action = "No action required."
        results.append(
            {
                "bundle_id": bundle_id,
                "status": status,
                "reason": reason,
                "next_action": action,
            }
        )
    return results


def _render_agents(
    root: Path, apply: bool = False, client: str | None = None, target: str = "local"
) -> dict[str, Any]:
    root = Path(root).resolve()
    config = load_project(root)
    bundle_ids = _selected_bundle_ids(config)
    bundles = _load_selected_bundles(root, bundle_ids)
    _raise_bundle_collisions(bundles)
    clients = (
        [client]
        if client
        else config.get("roles", {}).get("agent-client", ["claude-code", "codex"])
    )
    if isinstance(clients, str):
        clients = [clients]
    if set(clients) - {"claude-code", "codex"}:
        raise ValueError("unsupported agent client; register a client adapter before rendering")
    for selected_client in clients:
        settings = config.get("agents", {}).get("clients", {}).get(selected_client, {})
        readiness = hook_readiness(
            selected_client,
            settings.get("version", ""),
            "local",
            settings.get("required_hooks", []),
        )
        if not readiness["ready"]:
            raise ValueError(
                f"unsupported required hooks for {selected_client}: {readiness['unavailable']}"
            )
    skill_sources = _skill_sources(config)
    try:
        components = resolve_components(config, load_component_catalog(root, config))
    except TypeError as exc:
        raise ValueError(f"invalid component metadata: {exc}") from exc
    index, provider_copies = provider_index(components)
    referenced_guidance = {
        guidance for component in components["components"] for guidance in component["guidance"]
    }
    checks = config.get("checks", {})
    lines = [
        "# Shared project guidance",
        "",
        "Read ai-dlc.toml and the active .ai-dlc/work record before work.",
        "Use specification artifacts for implementation tasks and the tracker for priority/status.",
        "Finalize required specifications before review. Complete work through ai-dlc work finish.",
        "Store architecture, design, decisions and runbooks in docs/. Keep personal notes in knowledge.",
        "",
        "## Verification",
        "",
    ]
    for name in checks.get("required", []):
        lines.append(f"- {name}: `{checks.get('commands', {}).get(name, 'MISSING COMMAND')}`")
    lines.extend(
        ["", "Run `ai-dlc project check --required` in the prepared project environment.", ""]
    )
    lines.append(index)
    bundle_index = _bundle_index(bundles)
    if bundle_index:
        lines.append(bundle_index)
    planned: dict[str, str] = {}
    for filename, body in [("AGENTS.md", "\n".join(lines)), ("CLAUDE.md", "@AGENTS.md\n")]:
        if filename == "CLAUDE.md" and "claude-code" not in clients:
            continue
        path = inside(root, filename)
        planned[filename] = _section(path.read_text() if path.exists() else "", body)
    servers = {}
    codex = {}
    for server in config.get("agents", {}).get("servers", []):
        sid = server["id"]
        if sid in servers:
            raise ValueError(f"duplicate MCP server: {sid}")
        definition = {k: server[k] for k in ["command", "args", "url"] if k in server}
        if "command" not in definition and "url" not in definition:
            raise ValueError(f"MCP server {sid} requires command or URL")
        if any(
            str(x).startswith(("/Users/", "/home/"))
            for x in [definition.get("command", ""), *definition.get("args", [])]
        ):
            raise ValueError("personal paths cannot appear in shared MCP configuration")
        env_names = server.get("env", [])
        if not isinstance(env_names, list) or not all(
            re.fullmatch(r"[A-Z_][A-Z0-9_]*", x) for x in env_names
        ):
            raise ValueError(
                "MCP env must list environment variable names, never credential values"
            )
        servers[sid] = {
            **definition,
            **({"env": {x: "${" + x + "}" for x in env_names}} if env_names else {}),
        }
        codex[sid] = {**definition, **({"env_vars": env_names} if env_names else {})}
    manifest_path = inside(root, ".ai-dlc/agent-ownership.json")
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"mcp": {}}
    prior_bundle_files = _prior_bundle_files(previous)
    bundle_participates = bool(bundle_ids or prior_bundle_files or previous.get("schema") == 3)
    ownership: dict[str, Any] = dict(previous)
    ownership["schema"] = 3 if bundle_participates else 2
    owned_files = dict(previous.get("files", {}))
    bundle_files = dict(prior_bundle_files)
    removed = []
    for name, old_digest in list(owned_files.items()):
        if not name.startswith(".ai-dlc/providers/"):
            continue
        path = inside(root, name)
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != old_digest:
            raise ValueError(f"managed provider guidance conflict: {name}")
        if name not in provider_copies:
            if path.exists():
                removed.append(name)
            del owned_files[name]
    for name, body in provider_copies.items():
        path = inside(root, name)
        if name not in owned_files and path.exists() and path.read_bytes() != body.encode():
            raise ValueError(f"authored provider guidance conflict: {name}")
        planned[name] = body
        owned_files[name] = hashlib.sha256(body.encode()).hexdigest()
    for selected_client in clients:
        directory = ".agents" if selected_client == "codex" else ".claude"
        prefix = directory + "/skills/"
        desired = {prefix + name + "/SKILL.md": body for name, body in skill_sources.items()}
        for name, old_digest in list(owned_files.items()):
            if not name.startswith(prefix):
                continue
            if name in prior_bundle_files:
                continue
            path = inside(root, name)
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != old_digest:
                raise ValueError(f"managed skill conflict: {name}")
            if name not in desired:
                if path.exists():
                    removed.append(name)
                del owned_files[name]
        for name, body in desired.items():
            path = inside(root, name)
            if name not in owned_files and path.exists() and path.read_bytes() != body.encode():
                raise ValueError(f"authored skill conflict: {name}")
            planned[name] = body
            owned_files[name] = hashlib.sha256(body.encode()).hexdigest()
        _plan_hooks(root, config, selected_client, previous, ownership, planned)
    _plan_bundle_files(
        root,
        bundles,
        clients,
        full_render=client is None,
        owned_files=owned_files,
        bundle_files=bundle_files,
        planned=planned,
        removed=removed,
    )
    ownership["files"] = owned_files
    if bundle_participates:
        ownership["bundle_files"] = bundle_files
    if "claude-code" in clients:
        ownership["mcp"] = servers
        path = inside(root, ".mcp.json")
        document = json.loads(path.read_text()) if path.exists() else {}
        existing = document.setdefault("mcpServers", {})
        for sid, old in previous.get("mcp", {}).items():
            if sid in existing and existing[sid] != old:
                raise ValueError(f"MCP server conflict: {sid}")
            existing.pop(sid, None)
        for sid, definition in servers.items():
            if sid in existing and existing[sid] != definition:
                raise ValueError(f"MCP server conflict: {sid}")
            existing[sid] = definition
        planned[".mcp.json"] = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if "codex" in clients:
        path = inside(root, ".codex/config.toml")
        current = path.read_text() if path.exists() else ""
        body = (
            tomli_w.dumps({"mcp_servers": codex})
            if codex
            else "# No project MCP servers configured.\n"
        )
        planned[".codex/config.toml"] = _section(current, body, toml=True)
        # Validate duplicate tables or invalid unmanaged text before writing any file.
        import tomllib

        tomllib.loads(planned[".codex/config.toml"])
    planned[".ai-dlc/agent-ownership.json"] = json.dumps(ownership, indent=2, sort_keys=True) + "\n"
    changed = [
        name
        for name, text in planned.items()
        if not inside(root, name).exists() or inside(root, name).read_bytes() != text.encode()
    ]
    changed.extend(removed)
    for name in removed:
        if name in referenced_guidance:
            raise ValueError(
                f"managed provider guidance conflict: {name} is still referenced; "
                "copy the instructions to a project-owned path and update the component manifest"
            )
    if apply:
        if bundle_participates:
            _apply_render_transaction(root, planned, removed, changed)
        else:
            for name in removed:
                inside(root, name).unlink()
            for name in changed:
                if name in removed:
                    continue
                atomic_write(inside(root, name), planned[name])
    return {"clean": not changed, "changed": changed, "applied": apply}


def render_agents(
    root: Path, apply: bool = False, client: str | None = None, target: str = "local"
) -> dict[str, Any]:
    """Render project guidance, transactionally when bundle outputs participate."""
    absolute = Path(root).resolve()
    if not apply:
        return _render_agents(absolute, apply=False, client=client, target=target)
    config = load_project(absolute)
    selected = bool(_selected_bundle_ids(config))
    ownership_path = absolute / ".ai-dlc" / "agent-ownership.json"
    previous: dict[str, Any] = {}
    if ownership_path.exists():
        previous = json.loads(ownership_path.read_text())
    participates = selected or previous.get("schema") == 3
    if participates:
        with project_write_lock(absolute):
            return _render_agents(absolute, apply=True, client=client, target=target)
    return _render_agents(absolute, apply=True, client=client, target=target)


def _skill_sources(config: dict) -> dict[str, str]:
    base = assets("agents")
    lock = json.loads((base / "skills.lock.json").read_text())
    available = {p.parent.name: p for p in (base / "skills").glob("*/SKILL.md")}
    if set(available) != set(lock["skills"]):
        raise ValueError("skill digest lock does not match shipped collection")
    # Verify the whole package before planning any project writes.
    content = {}
    for name, path in sorted(available.items()):
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != lock["skills"][name]["sha256"]:
            raise ValueError(f"skill digest mismatch: {name}")
        content[name] = data.decode("utf-8")
    selected = config.get("agents", {}).get("skills", sorted(content))
    if not isinstance(selected, list) or not all(isinstance(name, str) for name in selected):
        raise ValueError("agents.skills must be a list of shipped skill names")
    if set(selected) - set(content):
        raise ValueError("unknown selected skill")
    return {name: content[name] for name in sorted(set(selected))}


def hook_readiness(client: str, version: str, target: str, required: list[str]) -> dict:
    import tomllib

    matrix = tomllib.loads((assets("agents") / "capabilities.toml").read_text())
    supported = set()
    for fixture in matrix["fixtures"]:
        if (fixture["client"], fixture["version"], fixture["target"]) == (client, version, target):
            supported.update(fixture["hooks"])
    unavailable = sorted(set(required) - supported)
    return {
        "ready": not unavailable,
        "unavailable": unavailable,
        "supported": sorted(supported),
        "coverage": matrix["coverage"],
    }


def target_hooks(config: dict, target: str) -> dict:
    clients = config.get("agents", {}).get("clients", {})
    results = {
        name: hook_readiness(
            name, settings.get("version", ""), target, settings.get("required_hooks", [])
        )
        for name, settings in clients.items()
    }
    return {
        "ready": all(result["ready"] for result in results.values()),
        "clients": results,
        "unavailable": [
            f"{name}:{hook}" for name, result in results.items() for hook in result["unavailable"]
        ],
    }


def _plan_hooks(
    root: Path, config: dict, client: str, previous: dict, ownership: dict, planned: dict
) -> None:
    settings = config.get("agents", {}).get("clients", {}).get(client, {})
    required = settings.get("required_hooks", [])
    old = previous.get("hooks", {}).get(client, {})
    if not required and not old:
        return
    name = ".codex/hooks.json" if client == "codex" else ".claude/settings.json"
    path = inside(root, name)
    document = json.loads(path.read_text()) if path.exists() else {}
    hooks = document.setdefault("hooks", {})
    for event, entries in old.items():
        current = hooks.get(event, [])
        for entry in entries:
            if entry not in current:
                raise ValueError(f"managed hook conflict: {client}/{event}")
            current.remove(entry)
        if not current:
            hooks.pop(event, None)
    rendered = {}
    events = {
        "bound-push": ("PreToolUse", "pre-tool"),
        "session-context": ("SessionStart", "session-start"),
        "stop-reminder": ("Stop", "stop"),
    }
    for feature in sorted(set(required)):
        event, action = events[feature]
        entry: dict[str, Any] = {
            "hooks": [
                {
                    "type": "command",
                    "command": f'ai-dlc hook {action} --root "$(git rev-parse --show-toplevel)"',
                    "timeout": 10,
                }
            ]
        }
        if event == "PreToolUse":
            entry["matcher"] = "Bash|exec_command"
        hooks.setdefault(event, []).append(entry)
        rendered.setdefault(event, []).append(entry)
    ownership["hooks"] = dict(ownership.get("hooks", {}))
    ownership["hooks"][client] = rendered
    planned[name] = json.dumps(document, indent=2, sort_keys=True) + "\n"
