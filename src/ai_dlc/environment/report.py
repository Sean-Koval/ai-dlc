"""Read-only local collection into the closed, explicitly nonsecret report schema."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_dlc import __version__
from ai_dlc.config import Resolved, resolve_layers
from ai_dlc.environment.credentials import credential_status
from ai_dlc.environment.enrollment import EnrollmentLock, EnrollmentPaths
from ai_dlc.environment.profile_source import verify_cached_profile
from ai_dlc.environment.report_schema import finalize_report
from ai_dlc.environment.team_sources import _verify, cache_root
from ai_dlc.environment.version_probes import find_executable, probe_version, supports_probe
from ai_dlc.files import assets
from ai_dlc.harness.agents import read_managed_section
from ai_dlc.harness.components import (
    MissingComponentGuidance,
    load_component_catalog,
    resolve_components,
)

_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_CONSTRAINT = re.compile(
    r"(?:(?:==|>=|>|<=|<)?[0-9]+(?:\.[0-9]+)*)(?:,(?:==|>=|>|<=|<)[0-9]+(?:\.[0-9]+)*)*"
)
_FAILURES = (OSError, ValueError, TypeError, KeyError, RuntimeError, AttributeError)
# Executable observations and recipe keys are distinct namespaces.
_RECIPES = {
    "rust": ("cargo", "rustc"),
    "npm:@openai/codex": ("codex",),
    "npm:@anthropic-ai/claude-code": ("claude",),
    "npm:@fission-ai/openspec": ("openspec",),
    "npm:wrangler": ("wrangler",),
}
_CLIENT_EXECUTABLES = {"codex": "codex", "claude-code": "claude"}


def _identifier(value: Any) -> str | None:
    return value if isinstance(value, str) and _ID.fullmatch(value) else None


def _read(path: Path) -> str:
    # Avoid locale-dependent metadata interpretation and unbounded authored files.
    with path.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("Local metadata exceeds report inspection bound.")
    return raw.decode("utf-8")


def _toml(path: Path) -> dict:
    return tomllib.loads(_read(path))


def _source(identifier=None, commit=None, *, state="unknown", reason="not-assessed") -> dict:
    return {
        "id": _identifier(identifier),
        "commit": commit,
        "content_sha256": None,
        "state": state,
        "reasons": {
            "id": None
            if _identifier(identifier)
            else "not-applicable"
            if state == "not-applicable"
            else "identifier-redacted",
            "commit": None if commit else reason,
            "content_sha256": "not-applicable"
            if state == "not-applicable"
            else "safe-digest-unavailable",
        },
    }


def _engine(observation: dict) -> dict:
    return {
        "package_version": observation["observed"],
        "installation_kind": "unknown",
        "source_revision": None,
        "source_dirty": None,
        "artifact_sha256": None,
        "state": observation["state"],
        "reasons": {
            "package_version": observation["reason"],
            "source_revision": "provenance-unavailable",
            "source_dirty": "provenance-unavailable",
            "artifact_sha256": "provenance-unavailable",
        },
    }


class _Collector:
    def __init__(self, root: Path, home: Path | None, environ: Mapping[str, str], probes: bool):
        self.root = root
        self.paths = EnrollmentPaths.from_environment(home=home, environ=environ)
        self.environ = environ
        self.probes = probes
        self.limitations: list[dict] = []
        self.observations: dict[str, dict] = {}
        self.component_selection: list[dict] = []

    def limit(self, field: str, reason: str, required: bool = True) -> None:
        item = {"field": field, "reason_code": reason, "required": required}
        if item not in self.limitations:
            self.limitations.append(item)

    def constraint(self, value: Any, field: str) -> str | None:
        if value is None:
            return None
        if isinstance(value, str) and len(value) <= 64 and _CONSTRAINT.fullmatch(value):
            return value
        self.limit(field, "unsupported-version")
        return None

    def observe(self, executable: str) -> dict:
        if executable not in self.observations:
            try:
                if not supports_probe(executable):
                    result = {"observed": None, "state": "unsupported", "reason": "not-assessed"}
                elif self.probes:
                    result = probe_version(executable, environ=self.environ)
                elif find_executable(executable, self.environ) is None:
                    result = {"observed": None, "state": "missing", "reason": "not-found"}
                else:
                    result = {"observed": None, "state": "unknown", "reason": "not-assessed"}
            except _FAILURES:
                result = {"observed": None, "state": "unknown", "reason": "collection-failed"}
            self.observations[executable] = result
        return dict(self.observations[executable])

    def layers(self) -> tuple[Resolved, dict, list[dict], str]:
        layers = []
        profile = _source(state="not-applicable", reason="not-applicable")
        sources = []
        lock = None
        personal = None
        try:
            layers.append(("base", _toml(assets("profiles") / "base.toml")))
        except _FAILURES:
            self.limit("project", "collection-failed")
        try:
            if self.paths.lock_file.exists():
                # Preserve the existing model validation boundary; only decoding differs.
                lock = EnrollmentLock.model_validate(_toml(self.paths.lock_file))
        except _FAILURES:
            profile = _source(reason="invalid-configuration")
            self.limit("profile", "invalid-configuration")
            self.limit("sources", "collection-failed")
        if lock is not None:
            profile = _source(lock.profile_id, lock.resolved_commit)
            try:
                personal = _toml(verify_cached_profile(lock, self.paths))
                resolve_layers([("personal", personal)])
                layers.append(("personal", personal))
                profile["state"] = "known"
            except _FAILURES:
                personal = None
                self.limit("profile", "cache-corrupt")
            sources = self.sources(lock, personal)
        project_state = "known"
        try:
            project = _toml(self.root / "ai-dlc.toml")
            resolve_layers([("project", project)])
            layers.append(("project", project))
        except FileNotFoundError:
            project_state = "missing"
            self.limit("project", "not-found")
        except _FAILURES:
            project_state = "unknown"
            self.limit("project", "invalid-configuration")
        if lock is not None:
            try:
                machine = _toml(self.paths.machine_file(lock.machine_id))
                resolve_layers([("machine", machine)])
                layers.append(("machine", machine))
            except _FAILURES:
                self.limit("profile", "invalid-configuration")
        # Validate each merge independently; retain prior successfully resolved layers.
        accepted: list[tuple[str, dict]] = []
        for layer in layers:
            try:
                resolve_layers([*accepted, layer])
                accepted.append(layer)
            except _FAILURES:
                self.limit(
                    "project" if layer[0] in {"project", "base"} else "profile",
                    "invalid-configuration",
                )
                if layer[0] == "project":
                    project_state = "unknown"
        return resolve_layers(accepted), profile, sources, project_state

    def sources(self, lock: EnrollmentLock, personal: dict | None) -> list[dict]:
        if personal is None:
            self.limit("sources", "collection-failed")
        else:
            declared = personal.get("sources", [])
            locked = [
                entry.model_dump(exclude={"resolved_commit", "content_sha256"})
                for entry in lock.sources
            ]
            # No URL/path normalization or fetching: declarations must match verbatim.
            from ai_dlc.environment.source_schema import subscriptions

            if [entry.model_dump() for entry in subscriptions(declared)] != locked:
                self.limit("sources", "conflicting-declarations")
        records = {}
        for entry in lock.sources[:16]:
            record = _source(entry.id, entry.resolved_commit)
            try:
                _verify(entry, self.paths)
                record["state"] = "known"
            except _FAILURES:
                missing = not cache_root(self.paths, entry).exists()
                record["state"] = "missing" if missing else "unknown"
                self.limit("sources", "cache-missing" if missing else "cache-corrupt")
            if record["id"] in records:
                self.limit(
                    "sources",
                    "identifier-redacted" if record["id"] is None else "invalid-configuration",
                )
            records[record["id"]] = record
        if len(lock.sources) > 16:
            self.limit("sources", "invalid-configuration")
        return list(records.values())

    def selections(self, resolved: Resolved) -> tuple[list[dict], list[dict], set[str]]:
        roles = []
        components: dict[str | None, dict] = {}
        modules: set[str] = set()
        try:
            catalog = load_component_catalog(self.root, resolved.values)
        except MissingComponentGuidance as error:
            catalog = error.catalog
            self.limit("project.guidance", "not-found")
        except _FAILURES:
            catalog = {"components": []}
            self.limit("project.components", "collection-failed")
        try:
            selection = resolve_components(resolved, catalog)
            self.component_selection = selection["components"]
            for entry in selection["components"]:
                provider, component = _identifier(entry["provider"]), _identifier(entry["id"])
                roles.append({"role": entry["role"], "provider": provider, "component": component})
                components[component] = {
                    "id": component,
                    "platform_support": {"os": None, "architecture": None, "shell_family": None},
                }
                modules.update(entry["modules"])
            for entry in selection["unresolved"]:
                roles.append(
                    {
                        "role": entry["role"],
                        "provider": _identifier(entry["provider"]),
                        "component": None,
                    }
                )
                self.limit("project.roles", "invalid-configuration")
        except _FAILURES:
            self.limit("project.roles", "invalid-configuration")
        for field, records, keys in (
            ("project.roles", roles, ("provider", "component")),
            ("project.components", list(components.values()), ("id",)),
        ):
            if any(item[key] is None for item in records for key in keys):
                self.limit(field, "identifier-redacted")
        return roles, list(components.values()), modules

    def tools(self, config: dict, modules: set[str]) -> tuple[list[dict], list[dict]]:
        try:
            catalog = _toml(assets("modules") / "catalog.toml")
        except _FAILURES:
            catalog = {}
            self.limit("runtimes", "collection-failed")
        try:
            selected = config.get("modules", {}).get("include", ["core"])
            if not isinstance(selected, list) or not all(
                isinstance(item, str) for item in selected
            ):
                raise TypeError
            modules.update(selected)
        except _FAILURES:
            self.limit("runtimes", "invalid-configuration")
        try:
            client_ids = config.get("roles", {}).get("agent-client", [])
            client_ids = [client_ids] if isinstance(client_ids, str) else client_ids
            if not isinstance(client_ids, list):
                raise TypeError
        except _FAILURES:
            client_ids = []
            self.limit("clients", "invalid-configuration")
        modules.update(c for c in client_ids if isinstance(c, str) and c in catalog)
        pins: dict[str, Any] = {}
        executables = set()
        for module in modules:
            if module not in catalog:
                self.limit("runtimes", "invalid-configuration")
                continue
            entry = catalog[module]
            executables.update(entry.get("verify", []))
            for recipe, pin in entry.get("mise", {}).items():
                for executable in _RECIPES.get(recipe, (recipe,)):
                    pins[executable] = pin
        explicit: dict[str, Any] = {}
        try:
            if (self.root / ".mise.toml").exists():
                tools = _toml(self.root / ".mise.toml").get("tools", {})
                if not isinstance(tools, dict):
                    raise TypeError
                for recipe, pin in tools.items():
                    for executable in _RECIPES.get(recipe, (recipe,)):
                        explicit[executable] = pin
                pins.update(explicit)
                executables.update(explicit)
        except _FAILURES:
            self.limit("runtimes", "invalid-configuration")
        runtimes = {}
        for executable in sorted(executables):
            identifier = _identifier(executable)
            if identifier is None:
                self.limit("runtimes", "identifier-redacted")
            version = {
                "intended": self.constraint(pins.get(executable), "runtimes"),
                **self.observe(executable),
            }
            runtimes[identifier] = {"id": identifier, "required": True, "version": version}
        clients = {}
        for raw_id in client_ids[:16]:
            identifier = _identifier(raw_id)
            executable = _CLIENT_EXECUTABLES.get(identifier or "")
            intended = pins.get(executable) if executable else None
            try:
                client_pin = (
                    config.get("agents", {}).get("clients", {}).get(raw_id, {}).get("version")
                )
                if client_pin is not None:
                    if executable in explicit and client_pin != explicit[executable]:
                        intended = None
                        self.limit("clients", "conflicting-declarations")
                        if executable in runtimes:
                            runtimes[executable]["version"]["intended"] = None
                            self.limit("runtimes", "conflicting-declarations")
                    else:
                        intended = client_pin
                        if executable in runtimes:
                            runtimes[executable]["version"]["intended"] = self.constraint(
                                client_pin, "runtimes"
                            )
            except _FAILURES:
                intended = None
                self.limit("clients", "invalid-configuration")
            observed = (
                self.observe(executable)
                if executable
                else {"observed": None, "state": "unsupported", "reason": "not-assessed"}
            )
            clients[identifier] = {
                "id": identifier,
                "edition": "cli" if executable and observed["state"] == "observed" else None,
                "version": {"intended": self.constraint(intended, "clients"), **observed},
                "configured": "yes",
                "rendered": "unknown",
                "recognized": "unknown",
                "authenticated": "unknown",
                "reasons": {
                    "id": None if identifier else "identifier-redacted",
                    "edition": None
                    if executable and observed["state"] == "observed"
                    else "not-assessed",
                    "configured": None,
                    "rendered": "not-assessed",
                    "recognized": "not-assessed",
                    "authenticated": "not-assessed",
                },
            }
        if len(runtimes) > 128:
            self.limit("runtimes", "invalid-configuration")
        if len(client_ids) > 16:
            self.limit("clients", "invalid-configuration")
        return list(runtimes.values())[:128], list(clients.values())

    def guidance(self, config: dict, clients: list[dict]) -> list[dict]:
        records = []
        ownership = {}
        try:
            path = self.root / ".ai-dlc/agent-ownership.json"
            if path.exists():
                ownership = json.loads(self.project_text(".ai-dlc/agent-ownership.json")).get(
                    "files", {}
                )
                if not isinstance(ownership, dict):
                    raise TypeError
        except _FAILURES:
            ownership = {}
            self.limit("project.guidance", "invalid-configuration")
        if clients:
            try:
                builtins = {
                    item["id"]
                    for item in json.loads(_read(assets("modules") / "components.json"))[
                        "components"
                    ]
                }
                for component in self.component_selection:
                    paths = [
                        (".ai-dlc/" if component["id"] in builtins else "") + path
                        for path in component["guidance"]
                    ]
                    states = [self.owned_state(path, ownership) for path in paths]
                    record_state = (
                        "mismatch"
                        if "mismatch" in states
                        else "missing"
                        if "missing" in states
                        else "unknown"
                    )
                    records.append(
                        self.guidance_record(
                            _identifier("provider." + component["id"]), "provider", record_state
                        )
                    )
                agents = config.get("agents", {})
                skills = agents.get("skills")
                if skills is None:
                    skills = list(
                        json.loads(_read(assets("agents") / "skills.lock.json"))["skills"]
                    )
                if not isinstance(skills, list):
                    raise TypeError
                prefixes = {"codex": ".agents", "claude-code": ".claude", "antigravity": ".agents"}
                for skill in skills:
                    identifier = _identifier(skill)
                    states = (
                        [
                            self.owned_state(
                                f"{prefixes[c['id']]}/skills/{identifier}/SKILL.md", ownership
                            )
                            for c in clients
                            if c["id"] in prefixes
                        ]
                        if identifier
                        else []
                    )
                    record_state = (
                        "mismatch"
                        if "mismatch" in states
                        else "missing"
                        if "missing" in states
                        else "unknown"
                    )
                    records.append(
                        self.guidance_record(
                            _identifier("skill." + identifier) if identifier else None,
                            "skill",
                            record_state,
                        )
                    )
                for bundle in agents.get("bundles", []):
                    identifier = _identifier(bundle)
                    records.append(
                        self.guidance_record(
                            _identifier("bundle." + identifier) if identifier else None,
                            "skill",
                            "unknown",
                        )
                    )
            except _FAILURES:
                self.limit("project.guidance", "collection-failed")
            state = self.managed_state("AGENTS.md")
            records.append(self.guidance_record("agents", "instruction", state))
            if any(client["id"] == "claude-code" for client in clients):
                records.append(
                    self.guidance_record("claude", "instruction", self.managed_state("CLAUDE.md"))
                )
            for client in clients:
                if state in {"missing", "mismatch"} or any(
                    g["state"] in {"missing", "mismatch"}
                    for g in records
                    if g["id"] != "claude" or client["id"] == "claude-code"
                ):
                    client["rendered"] = "no"
                    client["reasons"]["rendered"] = None
        try:
            servers = config.get("agents", {}).get("servers", [])
            if not isinstance(servers, list):
                raise TypeError
            for server in servers:
                if not isinstance(server, dict):
                    raise TypeError
                alias = _identifier(server.get("id"))
                provider = _identifier(server.get("provider"))
                transport = server.get("transport", server.get("type"))
                if "command" in server and "url" in server:
                    transport = None
                    self.limit("project.guidance", "conflicting-declarations")
                elif transport not in {"stdio", "http", "sse"}:
                    transport = (
                        "stdio" if "command" in server else "http" if "url" in server else None
                    )
                item = self.guidance_record(
                    _identifier("native." + alias) if alias else None, "native-server", "unknown"
                )
                item["native_server"] = {
                    "alias": alias,
                    "provider": provider,
                    "transport": transport,
                    "recipe_identity": None,
                    "reasons": {
                        "alias": None if alias else "identifier-redacted",
                        "provider": None if provider else "identifier-redacted",
                        "transport": None if transport else "not-assessed",
                        "recipe_identity": "safe-digest-unavailable",
                    },
                }
                records.append(item)
        except _FAILURES:
            self.limit("project.guidance", "invalid-configuration")
        # Unknown IDs aggregate, with no hash or ordinal derived from private values.
        unique = {}
        for record in records:
            if record["id"] in unique:
                self.limit("project.guidance", "conflicting-declarations")
            unique[record["id"]] = record
        if len(unique) > 512:
            self.limit("project.guidance", "invalid-configuration")
        return list(unique.values())[:512]

    def project_text(self, relative: str) -> str:
        path = self.root / relative
        path.resolve().relative_to(self.root.resolve())
        if path.is_symlink():
            raise ValueError("Guidance symlink is not an owned regular file.")
        return _read(path)

    def owned_state(self, relative: str, ownership: dict) -> str:
        try:
            content = self.project_text(relative)
            previous = ownership.get(relative)
            # Integrity detects known edits only. This private checksum never
            # becomes exported provenance or an input to report identities.
            if (
                previous is not None
                and hashlib.sha256(content.encode("utf-8")).hexdigest() != previous
            ):
                return "mismatch"
            return "unknown"
        except FileNotFoundError:
            return "missing"
        except _FAILURES:
            self.limit("project.guidance", "collection-failed")
            return "unknown"

    def managed_state(self, relative: str) -> str:
        try:
            path = self.root / relative
            if path.is_symlink():
                return "mismatch"
            state = read_managed_section(self.project_text(relative))["state"]
            return {"absent": "missing", "malformed": "mismatch", "modified": "mismatch"}.get(
                state, "unknown"
            )
        except FileNotFoundError:
            return "missing"
        except _FAILURES:
            self.limit("project.guidance", "collection-failed")
            return "unknown"

    @staticmethod
    def guidance_record(identifier: str | None, kind: str, state: str) -> dict:
        return {
            "id": identifier,
            "kind": kind,
            "state": state,
            "expected_sha256": None,
            "observed_sha256": None,
            "native_server": None,
            "reasons": {
                "id": None if identifier else "identifier-redacted",
                "expected_sha256": "safe-digest-unavailable",
                "observed_sha256": "safe-digest-unavailable",
            },
        }

    def auth(self, config: dict, roles: list[dict], clients: list[dict]) -> list[dict]:
        try:
            credentials = credential_status(config, self.environ)
        except _FAILURES:
            credentials = []
            self.limit("auth", "collection-failed", False)
        records = {}
        for kind, identifier in [("provider", role["provider"]) for role in roles] + [
            ("client", client["id"]) for client in clients
        ]:
            applicable = [
                entry
                for entry in credentials
                if identifier
                and isinstance(required_by := entry.get("required_by"), list)
                and f"{kind}.{identifier}" in required_by
            ]
            presence = (
                "unknown"
                if not applicable
                else "present"
                if all(entry["present"] for entry in applicable)
                else "missing"
            )
            # A redacted identity cannot denote independent accounts safely.
            key = (kind, identifier) if identifier else ("provider", None)
            records[key] = {
                "kind": key[0],
                "id": identifier,
                "credential_presence": presence,
                "verification": "not-assessed",
                "verified_at": None,
                "evidence_identity": None,
                "reasons": {
                    "id": None if identifier else "identifier-redacted",
                    "verified_at": "not-assessed",
                    "evidence_identity": "not-assessed",
                },
            }
        return list(records.values())


def collect_report(
    root: Path,
    *,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
    probe_versions: bool = False,
) -> dict:
    """Collect local safe facts without mutations or execution unless explicitly opted in."""
    collector = _Collector(
        Path(root), home, os.environ if environ is None else environ, probe_versions
    )
    resolved, profile, sources, state = collector.layers()
    roles, components, modules = collector.selections(resolved)
    runtimes, clients = collector.tools(resolved.values, modules)
    if any(item["field"] == "profile" for item in collector.limitations):
        client_origins = [
            origin
            for key, origin in resolved.sources.items()
            if key == "roles.agent-client" or key.startswith("roles.agent-client.")
        ]
        if not client_origins or any(origin == "base" for origin in client_origins):
            for client in clients:
                client["configured"] = "unknown"
                client["reasons"]["configured"] = "collection-failed"
    guidance = collector.guidance(resolved.values, clients)
    engine_constraint = None
    try:
        raw_constraint = resolved.values.get("engine", {}).get("version")
        engine_constraint = collector.constraint(raw_constraint, "project.engine_constraint")
        constraint_reason = (
            "unsupported-version"
            if raw_constraint is not None and engine_constraint is None
            else None
        )
    except _FAILURES:
        constraint_reason = "invalid-configuration"
    current = _engine({"observed": __version__, "state": "observed", "reason": None})
    selected = _engine(collector.observe("ai-dlc"))
    system = {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}.get(platform.system())
    architecture = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "i386": "x86",
        "i686": "x86",
        "x86": "x86",
        "armv7l": "arm",
    }.get(platform.machine().lower())
    collector.limit("project", "excluded-fields", False)
    return finalize_report(
        {
            "schema_version": 1,
            "observed_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "engine": {
                **{key: value for key, value in current.items() if key not in {"state", "reasons"}},
                "current_process": current,
                "path_selected": selected,
            },
            "platform": {
                "os": system,
                "architecture": architecture,
                "shell_family": None,
                "reasons": {
                    "os": None if system else "unsupported-platform",
                    "architecture": None if architecture else "unsupported-platform",
                    "shell_family": "not-assessed",
                },
            },
            "profile": profile,
            "sources": sources,
            "runtimes": runtimes,
            "clients": clients,
            "project": {
                "engine_constraint": engine_constraint,
                "roles": roles,
                "components": components,
                "client_ids": [client["id"] for client in clients],
                "configuration_sha256": None,
                "guidance": guidance,
                "state": state,
                "reasons": {"engine_constraint": constraint_reason},
            },
            "auth": collector.auth(resolved.values, roles, clients),
            "limitations": collector.limitations,
            "configuration_identity": None,
            "observation_identity": None,
        }
    )
