"""Reviewed native role bindings into project-owned configuration, without login."""

import copy
import hashlib
import json
import re
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

import tomli_w

from ai_dlc.config import digest, resolve_layers, resolve_runtime
from ai_dlc.connections import (
    apply_exact_patch,
    load_saved_plan,
    save_exclusive_plan,
    snapshot_work,
)
from ai_dlc.files import inside
from ai_dlc.provider_definitions import DEFINITIONS
from ai_dlc.provider_onboarding import _comment_suffix, _structural_lines, _table_paths

_ROLES = {"specs", "tracker", "knowledge", "scm", "deploy"}
_ALIAS = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
_FIELDS = {"role", "provider", "server", "account", "url", "command", "args", "env"}
_PLAN_FIELDS = {
    "schema",
    "kind",
    "bindings_path",
    "input_digest",
    "before_digest",
    "runtime_digest",
    "work_digest",
    "bindings",
    "patch",
}
_ACCOUNT_NOTICE = (
    "An account is a declared expectation, not verified native authentication. "
    "An alias does not switch an endpoint-shared OAuth cache; inspect and authenticate "
    "the intended account in each native client."
)


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and value.isprintable()


def _binding(row, config):
    if (
        not isinstance(row, dict)
        or set(row) - _FIELDS
        or not {"role", "provider", "server", "account"} <= set(row)
    ):
        raise ValueError(
            "Native binding requires role, provider, server and account with only supported transport fields"
        )
    if not all(_text(row[key]) for key in ("role", "provider", "server", "account")):
        raise ValueError("Native binding identity fields must be nonempty printable strings")
    role, provider = row["role"], row["provider"]
    if role not in _ROLES or config.get("roles", {}).get(role) != provider:
        raise ValueError("Native binding must match the effective selected role and provider")
    settings = config.get("providers", {}).get(provider, {})
    definition = DEFINITIONS.get(settings.get("kind", settings.get("type", provider)))
    if definition is not None and role not in definition.roles:
        raise ValueError("Native binding role is incompatible with its trusted provider definition")
    if settings.get("account") is not None and settings["account"] != row["account"]:
        raise ValueError(
            "Native account expectation differs from the effective provider account reference"
        )
    if not _ALIAS.fullmatch(row["server"]):
        raise ValueError("Native server alias must be a stable name")
    server = {"id": row["server"], "account": row["account"]}
    if ("url" in row) == ("command" in row):
        raise ValueError("Native binding requires one unambiguous URL or command transport")
    if "url" in row:
        if set(row) & {"args", "env"} or not _text(row["url"]):
            raise ValueError(
                "Native URL transport does not accept command arguments or environment overrides"
            )
        try:
            parsed = urlsplit(row["url"])
            valid = (
                parsed.scheme in {"http", "https"}
                and parsed.hostname
                and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
            )
            _ = parsed.port  # Validate explicit port syntax/range.
        except ValueError:
            valid = False
        if not valid:
            raise ValueError(
                "Native URL must be HTTP(S) without embedded credentials, query or fragment"
            )
        server["url"] = row["url"]
    else:
        args, env = row.get("args", []), row.get("env", [])
        if (
            not _text(row["command"])
            or not isinstance(args, list)
            or not all(isinstance(arg, str) for arg in args)
        ):
            raise ValueError("Native command and arguments must be explicit strings")
        if any(item.startswith(("/Users/", "/home/")) for item in [row["command"], *args]):
            raise ValueError("Personal paths cannot appear in shared native configuration")
        if (
            not isinstance(env, list)
            or not all(
                isinstance(name, str) and re.fullmatch(r"[A-Z_][A-Z0-9_]*", name) for name in env
            )
            or len(set(env)) != len(env)
        ):
            raise ValueError(
                "Native env must contain unique environment variable names, never values"
            )
        server.update(command=row["command"], args=list(args), env=list(env))
    return server


def compose_native_connections(config: dict, bindings: list) -> dict:
    """Pure role/account/transport validation; no URL or credential probing."""
    if not isinstance(bindings, list) or not bindings:
        raise ValueError("Reviewed native bindings must be a nonempty list")
    existing = config.get("agents", {}).get("servers", [])
    if not isinstance(existing, list) or not all(
        isinstance(row, dict) and _text(row.get("id")) for row in existing
    ):
        raise ValueError("Existing native servers must be a list of named definitions")
    by_id = {}
    for server in existing:
        if server["id"] in by_id:
            raise ValueError("Existing duplicate native alias must be reviewed before composition")
        by_id[server["id"]] = server
    servers = copy.deepcopy(existing)
    roles = {}
    for row in bindings:
        server = _binding(row, config)
        roles[row["role"]] = row["provider"]
        previous = by_id.get(server["id"])
        if previous is not None:
            # Omitted empty args/env are semantically identical to explicit empty lists.
            normalized = copy.deepcopy(previous)
            if "command" in normalized:
                normalized.setdefault("args", [])
                normalized.setdefault("env", [])
            if normalized != server:
                raise ValueError(
                    "Native server alias has conflicting account or transport identity"
                )
        else:
            by_id[server["id"]] = server
            servers.append(server)
    return {"servers": servers, "roles": dict(sorted(roles.items()))}


def _inline(value):
    if isinstance(value, dict):
        return (
            "{"
            + ", ".join(json.dumps(key) + " = " + _inline(item) for key, item in value.items())
            + "}"
        )
    if isinstance(value, list):
        return "[" + ", ".join(_inline(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def render_native_patch(text, _alias, patch):
    """Append array tables or replace one supported inline assignment, retaining authorship."""
    original = tomllib.loads(text)
    existing = original.get("agents", {}).get("servers", [])
    servers = patch["servers"]
    if servers[: len(existing)] != existing:
        raise ValueError("Native composition cannot rewrite existing manual entries")
    if servers == existing:
        return text
    expected = copy.deepcopy(original)
    expected.setdefault("agents", {})["servers"] = servers
    lines = text.splitlines(keepends=True)
    paths = _table_paths(text)
    structural = _structural_lines(lines)
    section = None
    rendered = None
    assignment = re.compile(r'^(\s*(?:servers|"servers"|\'servers\')\s*=\s*)(.*?)(\r?\n)?$')
    for index, line in enumerate(lines):
        if paths[index] is not None:
            section = paths[index]
        if section != ("agents",) or not structural[index]:
            continue
        match = assignment.match(line)
        if not match:
            continue
        # Find the complete authored assignment, including multiline arrays/comments.
        for end in range(index, len(lines)):
            fragment = "".join(lines[index : end + 1])
            try:
                parsed = tomllib.loads(fragment)
            except tomllib.TOMLDecodeError:
                continue
            if parsed != {"servers": existing}:
                break
            last = lines[end]
            comment = _comment_suffix(last.rstrip("\r\n"))
            meaningful = last[: len(last.rstrip("\r\n")) - len(comment)]
            closing = meaningful.rfind("]")
            if closing < 0:
                break
            additions = ", ".join(_inline(server) for server in servers[len(existing) :])
            # Either an existing trailing comma or this inserted separator is needed.
            for separator in ("", ","):
                candidate_lines = list(lines)
                candidate_lines[end] = last[:closing] + separator + additions + last[closing:]
                candidate = "".join(candidate_lines)
                try:
                    valid = tomllib.loads(candidate) == expected
                except tomllib.TOMLDecodeError:
                    valid = False
                if valid:
                    rendered = candidate
                    break
            break
        if rendered is None:
            raise ValueError("Native server TOML representation cannot be edited safely")
        break
    if rendered is None:
        rendered = (
            text.rstrip()
            + "\n\n"
            + "\n".join(
                "[[agents.servers]]\n" + tomli_w.dumps(server)
                for server in servers[len(existing) :]
            )
        )
    try:
        actual = tomllib.loads(rendered)
    except tomllib.TOMLDecodeError:
        raise ValueError("Native server TOML representation cannot be edited safely") from None
    if actual != expected:
        raise ValueError("Native server TOML representation cannot be edited safely")
    return rendered


def _input(root, requested):
    requested = Path(requested)
    if requested.is_absolute():
        try:
            requested = requested.relative_to(root)
        except ValueError:
            raise ValueError("Reviewed native bindings must stay in the project") from None
    path = inside(root, requested.as_posix())
    if not path.is_file():
        raise ValueError("Reviewed native bindings must be a regular file")
    content = path.read_bytes()
    data = tomllib.loads(content.decode())
    if (
        not isinstance(data, dict)
        or set(data) != {"schema", "bindings"}
        or type(data["schema"]) is not int
        or data["schema"] != 1
    ):
        raise ValueError("Expected reviewed native binding schema 1")
    return path.relative_to(root).as_posix(), content, data["bindings"]


def _snapshot(root, bindings_path):
    relative, content, _ = _input(root, bindings_path)
    return {
        "work": snapshot_work(root),
        "bindings": {relative: hashlib.sha256(content).hexdigest()},
    }


def _result(status, roles):
    return {
        "status": status,
        "roles": roles,
        "rendering": "pending",
        "authentication": "unverified",
        "account_notice": _ACCOUNT_NOTICE,
    }


def plan_native_connections(root, bindings_path, *, environ, save_plan=None):
    root = Path(root).resolve()
    path = inside(root, "ai-dlc.toml")
    before = path.read_bytes()
    runtime = resolve_runtime(root, environ=environ).values
    relative, content, bindings = _input(root, bindings_path)
    project_composition = copy.deepcopy(runtime)
    # Effective roles/accounts validate the request; only project-owned server entries
    # may be persisted. Personal defaults are never copied into shared configuration.
    project_composition["agents"] = tomllib.loads(before.decode()).get("agents", {})
    composed = compose_native_connections(project_composition, bindings)
    patch = {"servers": composed["servers"]}
    rendered = render_native_patch(before.decode(), None, patch)
    resolve_layers([("project", tomllib.loads(rendered))])
    plan = {
        "schema": 1,
        "kind": "native-tool-composition",
        "bindings_path": relative,
        "input_digest": hashlib.sha256(content).hexdigest(),
        "before_digest": hashlib.sha256(before).hexdigest(),
        "runtime_digest": digest(runtime),
        "work_digest": _snapshot(root, relative),
        "bindings": copy.deepcopy(bindings),
        "patch": patch,
    }
    result = {**_result("planned", composed["roles"]), "plan": plan}
    if save_plan is not None:
        result["plan_file"] = save_exclusive_plan(root, Path(save_plan), plan)
    return result


def apply_native_connections(root, plan_file, *, environ):
    root = Path(root).resolve()
    saved = load_saved_plan(root, Path(plan_file))
    if (
        not isinstance(saved, dict)
        or set(saved) != _PLAN_FIELDS
        or type(saved["schema"]) is not int
        or saved["schema"] != 1
        or saved["kind"] != "native-tool-composition"
    ):
        raise ValueError("Invalid native composition plan")
    fresh = plan_native_connections(root, saved["bindings_path"], environ=environ)
    if fresh["plan"] != saved:
        raise ValueError(
            "Native plan drift: reviewed input, source, roles, provider or account changed"
        )
    apply_exact_patch(
        root,
        None,
        saved,
        environ=environ,
        snapshot=lambda current: _snapshot(current, saved["bindings_path"]),
        render=render_native_patch,
        label="Native tool",
        stage_prefix=".ai-dlc-native-",
    )
    return _result("applied", fresh["roles"])
