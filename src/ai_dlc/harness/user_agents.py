"""Conflict-aware user-level MCP configuration for supported agent clients."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from ai_dlc.files import atomic_write, inside

_CLIENTS = {"claude-code", "codex"}
_ENV_NAME = re.compile(r"[A-Z_][A-Z0-9_]*")
_CODEX_START = "# ai-dlc:user-agents:begin "
_CODEX_END = "# ai-dlc:user-agents:end"
_CODEX_SECTION = re.compile(
    re.escape(_CODEX_START) + r"([0-9a-f]{64})\n(.*?)" + re.escape(_CODEX_END) + r"\n?",
    re.DOTALL,
)


class UserAgentOwnershipConflict(ValueError):
    """A persisted client configuration prevents AI-DLC from safely changing it."""


def render_user_agents(
    config: dict[str, Any],
    home: Path,
    apply: bool = False,
    client: str | None = None,
) -> dict[str, Any]:
    """Plan or apply personal MCP servers without replacing authored settings."""
    clients = [client] if client else ["claude-code", "codex"]
    if set(clients) - _CLIENTS:
        raise ValueError("unsupported user agent client")

    servers = _servers(config)
    home = home.resolve()
    state_path = inside(home, ".local/state/ai-dlc/user-agent-ownership.json")
    previous = _read_state(state_path)
    ownership = copy.deepcopy(previous)
    ownership["schema"] = 1
    owned_clients = ownership.setdefault("clients", {})

    planned: dict[Path, str] = {}
    removed: set[Path] = set()
    for selected in clients:
        prior = previous.get("clients", {}).get(selected, {})
        if selected == "claude-code":
            _plan_claude(home, servers, prior, planned, removed, owned_clients)
        else:
            _plan_codex(home, servers, prior, planned, removed, owned_clients)

    owned_clients = {name: value for name, value in owned_clients.items() if value.get("servers")}
    if owned_clients:
        ownership["clients"] = owned_clients
        planned[state_path] = json.dumps(ownership, indent=2, sort_keys=True) + "\n"
    else:
        ownership.pop("clients", None)
        if state_path.exists():
            removed.add(state_path)

    changed = sorted(
        {
            str(path.relative_to(home))
            for path, text in planned.items()
            if not path.exists() or path.read_text() != text
        }
        | {str(path.relative_to(home)) for path in removed if path.exists()}
    )
    if apply:
        _apply_changes(home, changed, planned, removed)
    return {"clean": not changed, "changed": changed, "applied": apply}


def _servers(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    agents = config.get("agents", {})
    if not isinstance(agents, dict):
        raise TypeError("agents configuration must be a table")
    configured = agents.get("servers", [])
    if not isinstance(configured, list):
        raise TypeError("agents.servers must be a list")

    servers: dict[str, dict[str, Any]] = {}
    for server in configured:
        if not isinstance(server, dict):
            raise TypeError("agent server configuration must be a table")
        server_id = server.get("id")
        if not isinstance(server_id, str) or not server_id:
            raise ValueError("agent server requires a nonempty id")
        if server_id in servers:
            raise ValueError(f"duplicate agent server: {server_id}")
        if ("command" in server) == ("url" in server):
            raise ValueError(f"agent server {server_id} requires exactly one command or URL")
        command, url = server.get("command"), server.get("url")
        if "command" in server:
            allowed = {"id", "command", "args", "env"}
            if not isinstance(command, str) or not command.strip():
                raise ValueError(f"agent server {server_id} requires a nonempty command")
        else:
            allowed = {"id", "url", "bearer_token_env_var", "env_http_headers"}
            if not isinstance(url, str) or not url.strip():
                raise ValueError(f"agent server {server_id} requires a nonempty URL")
        unknown = set(server) - allowed
        if unknown:
            raise ValueError(f"agent server {server_id} has unsupported fields: {sorted(unknown)}")
        args = server.get("args", [])
        if not isinstance(args, list) or not all(isinstance(value, str) for value in args):
            raise ValueError("agent server args must be a list of strings")
        env = server.get("env", [])
        if not isinstance(env, list) or not all(
            isinstance(value, str) and _ENV_NAME.fullmatch(value) for value in env
        ):
            raise ValueError(
                "agent server environment must list variable names; literal values are unsupported"
            )
        token_env = server.get("bearer_token_env_var")
        if token_env is not None and (
            not isinstance(token_env, str) or not _ENV_NAME.fullmatch(token_env)
        ):
            raise ValueError("bearer token must be an environment variable name")
        headers = server.get("env_http_headers", {})
        if not isinstance(headers, dict) or not all(
            isinstance(name, str) and name and isinstance(value, str) and _ENV_NAME.fullmatch(value)
            for name, value in headers.items()
        ):
            raise ValueError("HTTP headers must reference environment variable names")
        if command and (token_env or headers):
            raise ValueError("HTTP credential environment references are unsupported for commands")
        servers[server_id] = {
            **({"command": command} if command else {"url": url}),
            **({"args": args} if args else {}),
            **({"env": env} if env else {}),
            **({"bearer_token_env_var": token_env} if token_env else {}),
            **({"env_http_headers": headers} if headers else {}),
        }
    return servers


def _definitions(servers: dict[str, dict[str, Any]], client: str) -> dict[str, dict[str, Any]]:
    rendered = {}
    for server_id, server in servers.items():
        if "command" in server:
            definition = {key: server[key] for key in ["command", "args"] if key in server}
            names = server.get("env", [])
            if names:
                definition["env" if client == "claude-code" else "env_vars"] = (
                    {name: "${" + name + "}" for name in names}
                    if client == "claude-code"
                    else names
                )
        else:
            definition = {"url": server["url"]}
            if client == "claude-code":
                definition["type"] = "http"
                headers = {
                    name: "${" + env_name + "}"
                    for name, env_name in server.get("env_http_headers", {}).items()
                }
                if token_env := server.get("bearer_token_env_var"):
                    headers["Authorization"] = "Bearer ${" + token_env + "}"
                if headers:
                    definition["headers"] = headers
            else:
                for key in ["bearer_token_env_var", "env_http_headers"]:
                    if key in server:
                        definition[key] = server[key]
        rendered[server_id] = definition
    return rendered


def _plan_claude(
    home: Path,
    servers: dict[str, dict[str, Any]],
    prior: dict[str, Any],
    planned: dict[Path, str],
    removed: set[Path],
    clients: dict[str, Any],
) -> None:
    desired = _definitions(servers, "claude-code")
    old = prior.get("servers", {})
    if not desired and not old:
        return
    path = inside(home, ".claude.json")
    existed = path.exists()
    try:
        document = json.loads(path.read_text()) if existed else {}
    except (json.JSONDecodeError, OSError) as exc:
        raise UserAgentOwnershipConflict(
            "Claude user configuration conflict: invalid JSON"
        ) from exc
    if not isinstance(document, dict):
        raise UserAgentOwnershipConflict(
            "Claude user configuration conflict: root must be an object"
        )
    current = document.get("mcpServers", {})
    if not isinstance(current, dict):
        raise UserAgentOwnershipConflict(
            "Claude user configuration conflict: mcpServers must be an object"
        )
    _check_owned(current, old, "Claude")
    for server_id in old:
        current.pop(server_id)
    _check_unowned(current, desired, "Claude")
    current.update(desired)

    if current:
        document["mcpServers"] = current
    else:
        document.pop("mcpServers", None)
    clients["claude-code"] = {
        "created": prior.get("created", not existed),
        "servers": desired,
    }
    if not document and clients["claude-code"]["created"]:
        removed.add(path)
    else:
        planned[path] = json.dumps(document, indent=2, sort_keys=True) + "\n"


def _plan_codex(
    home: Path,
    servers: dict[str, dict[str, Any]],
    prior: dict[str, Any],
    planned: dict[Path, str],
    removed: set[Path],
    clients: dict[str, Any],
) -> None:
    desired = _definitions(servers, "codex")
    path = inside(home, ".codex/config.toml")
    existed = path.exists()
    current_text = path.read_text() if existed else ""
    section = _existing_codex_section(current_text)
    old = prior.get("servers", {})
    if section is not None and not old:
        raise UserAgentOwnershipConflict(
            "Codex user configuration conflict: orphaned managed section"
        )
    if not desired and not old:
        return
    try:
        document = tomllib.loads(current_text) if current_text else {}
    except tomllib.TOMLDecodeError as exc:
        raise UserAgentOwnershipConflict("Codex user configuration conflict: invalid TOML") from exc
    current = document.get("mcp_servers", {})
    if not isinstance(current, dict):
        raise UserAgentOwnershipConflict(
            "Codex user configuration conflict: mcp_servers must be a table"
        )
    if old and section is None:
        raise UserAgentOwnershipConflict(
            "Codex user configuration conflict: managed section is missing"
        )
    _check_owned(current, old, "Codex")
    unmanaged = {name: value for name, value in current.items() if name not in old}
    _check_unowned(unmanaged, desired, "Codex")

    body = tomli_w.dumps({"mcp_servers": desired}) if desired else ""
    separator_added = prior.get("separator_added", False)
    rendered = _replace_codex_section(current_text, section, body, separator_added)
    if rendered:
        try:
            tomllib.loads(rendered)
        except tomllib.TOMLDecodeError as exc:
            raise UserAgentOwnershipConflict(
                "Codex user configuration conflict: duplicate MCP tables"
            ) from exc
    clients["codex"] = {
        "created": prior.get("created", not existed),
        "separator_added": (
            separator_added
            if section is not None
            else bool(body and current_text and not current_text.endswith("\n"))
        ),
        "servers": desired,
    }
    if not rendered and clients["codex"]["created"]:
        removed.add(path)
    else:
        planned[path] = rendered


def _check_owned(current: dict, old: dict, label: str) -> None:
    for server_id, definition in old.items():
        if current.get(server_id) != definition:
            raise UserAgentOwnershipConflict(
                f"{label} user configuration conflict: managed server {server_id}"
            )


def _check_unowned(current: dict, desired: dict, label: str) -> None:
    collision = sorted(set(current) & set(desired))
    if collision:
        raise UserAgentOwnershipConflict(
            f"{label} user configuration conflict: unowned server {collision[0]}"
        )


def _existing_codex_section(text: str) -> re.Match[str] | None:
    matches = list(_CODEX_SECTION.finditer(text))
    if len(matches) > 1 or (_CODEX_START in text and not matches):
        raise UserAgentOwnershipConflict(
            "Codex user configuration conflict: malformed managed section"
        )
    if not matches:
        return None
    match = matches[0]
    if hashlib.sha256(match.group(2).encode()).hexdigest() != match.group(1):
        raise UserAgentOwnershipConflict(
            "Codex user configuration conflict: managed section was edited"
        )
    return match


def _replace_codex_section(
    current: str,
    existing: re.Match[str] | None,
    body: str,
    separator_added: bool,
) -> str:
    block = ""
    if body:
        block = (
            _CODEX_START
            + hashlib.sha256(body.encode()).hexdigest()
            + "\n"
            + body
            + _CODEX_END
            + "\n"
        )
    if existing:
        start = existing.start()
        if not block and separator_added and start and current[start - 1] == "\n":
            start -= 1
        return current[:start] + block + current[existing.end() :]
    if not block:
        return current
    separator = "" if not current or current.endswith("\n") else "\n"
    return current + separator + block


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"clients": {}}
    try:
        state = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise UserAgentOwnershipConflict("user agent ownership conflict: invalid state") from exc
    if state.get("schema") != 1 or not isinstance(state.get("clients"), dict):
        raise UserAgentOwnershipConflict("user agent ownership conflict: unsupported state")
    return state


def _apply_changes(
    home: Path,
    changed: list[str],
    planned: dict[Path, str],
    removed: set[Path],
) -> None:
    changed_paths = {inside(home, name) for name in changed}
    removals = [path for path in sorted(removed) if path in changed_paths]
    writes = [path for path in planned if path in changed_paths]
    operations = [("remove", path) for path in removals] + [("write", path) for path in writes]
    before = {
        path: (
            path.read_bytes() if path.exists() else None,
            path.stat().st_mode & 0o777 if path.exists() else None,
        )
        for _, path in operations
    }
    attempted: list[Path] = []
    try:
        for action, path in operations:
            attempted.append(path)
            if action == "remove":
                _unlink(path)
            else:
                atomic_write(path, planned[path])
    except BaseException as exc:
        rollback_errors = []
        for path in reversed(attempted):
            original, mode = before[path]
            try:
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    assert mode is not None
                    atomic_write(path, original.decode())
                    path.chmod(mode)
            except Exception as rollback_error:  # noqa: BLE001 -- continue restoring every file
                rollback_errors.append(f"{path}: {rollback_error}")
        if rollback_errors:
            exc.add_note("rollback incomplete: " + "; ".join(rollback_errors))
        raise


def _unlink(path: Path) -> None:
    path.unlink()
