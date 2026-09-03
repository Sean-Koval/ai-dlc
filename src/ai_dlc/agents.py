"""Deterministic project guidance and client-owned configuration sections."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import tomli_w

from ai_dlc.config import load_project
from ai_dlc.files import assets, atomic_write, inside


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


def render_agents(
    root: Path, apply: bool = False, client: str | None = None, target: str = "local"
) -> dict[str, Any]:
    config = load_project(root)
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
    ownership: dict[str, Any] = dict(previous)
    ownership["schema"] = 2
    owned_files = dict(previous.get("files", {}))
    removed = []
    for selected_client in clients:
        directory = ".agents" if selected_client == "codex" else ".claude"
        prefix = directory + "/skills/"
        desired = {prefix + name + "/SKILL.md": body for name, body in skill_sources.items()}
        for name, old_digest in list(owned_files.items()):
            if not name.startswith(prefix):
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
    ownership["files"] = owned_files
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
        if not inside(root, name).exists() or inside(root, name).read_text() != text
    ]
    changed.extend(removed)
    if apply:
        for name in removed:
            inside(root, name).unlink()
        for name in changed:
            if name in removed:
                continue
            atomic_write(inside(root, name), planned[name])
    return {"clean": not changed, "changed": changed, "applied": apply}


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
