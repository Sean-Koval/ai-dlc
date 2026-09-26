"""Read-only consumer routing; recommendations are never executed or previewed."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shlex
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from ai_dlc import __version__
from ai_dlc.config import load_project, read_toml
from ai_dlc.environment.enrollment import EnrollmentPaths, read_lock
from ai_dlc.environment.profile_source import source_lock_value, verify_cached_profile
from ai_dlc.files import assets
from ai_dlc.harness.agents import read_managed_section
from ai_dlc.harness.components import (
    MissingComponentGuidance,
    load_component_catalog,
    resolve_components,
)
from ai_dlc.provider_definitions import DEFINITIONS
from ai_dlc.setup.commands import find_executable, parse_command
from ai_dlc.setup.project import check_definitions
from ai_dlc.setup.templates import plan_toolset

_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SUPPORTED_SHELLS = {"sh", "bash", "zsh"}
_SUPPORTED_ARCHITECTURES = {"arm64", "aarch64", "x86_64", "amd64"}


def _selection(source, ref, profile_id, machine_id, agent_clients, preset):
    if preset is not None and preset not in {"generic", "python"}:
        raise ValueError("preset must be generic or python")
    for field, value in (("profile_id", profile_id), ("machine_id", machine_id)):
        if value is not None and (not isinstance(value, str) or not _STABLE_ID.fullmatch(value)):
            raise ValueError(f"{field} must be a stable lowercase ID")
    if ref is not None and (
        not isinstance(ref, str)
        or not ref
        or ref.startswith(("-", "/", "."))
        or ref.endswith(("/", ".", ".lock"))
        or any(character.isspace() or ord(character) < 32 for character in ref)
        or any(token in ref for token in ("..", "@{", "//", "~", "^", ":", "?", "*", "[", "\\"))
    ):
        raise ValueError("ref must be an explicit valid Git revision or ref")
    if source is not None:
        if not isinstance(source, str):
            raise ValueError("profile source is invalid")
        source = source_lock_value(source)
    if agent_clients is not None:
        if (
            not isinstance(agent_clients, list)
            or not agent_clients
            or not all(isinstance(client, str) for client in agent_clients)
        ):
            raise ValueError("agent_clients must be a nonempty list of supported clients")
        agent_clients = plan_toolset(capabilities=["agent-client"], agent_clients=agent_clients)[
            "roles"
        ]["agent-client"]
    return source, agent_clients


def _target_file(root: Path, name: str) -> Path:
    """Ownership metadata must never send inspection outside the selected target."""
    relative = Path(name)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError("invalid managed path")
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError("managed path is a symbolic link")
    return current


def _guidance_conflicts(root: Path) -> bool:
    """Compare stored ownership, not desired output: stale is different from edited."""
    try:
        for name in ("AGENTS.md", "CLAUDE.md", ".codex/config.toml"):
            path = _target_file(root, name)
            if path.exists() and read_managed_section(
                path.read_text(), toml=name.endswith(".toml")
            )["state"] in {"modified", "malformed"}:
                return True
        ownership = _target_file(root, ".ai-dlc/agent-ownership.json")
        if not ownership.exists():
            return False
        metadata = json.loads(ownership.read_text())
        if not isinstance(metadata, dict):
            return True
        files = metadata.get("files", {})
        bundles = metadata.get("bundle_files", {})
        if not isinstance(files, dict) or not isinstance(bundles, dict):
            return True
        digests = dict(files)
        for name, item in bundles.items():
            if not isinstance(item, dict):
                return True
            digests[name] = item.get("sha256")
        for name, expected in digests.items():
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                return True
            path = _target_file(root, name)
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                return True
    except (OSError, ValueError, TypeError):
        return True
    return False


def _engine_checkout(root: Path) -> bool:
    if not (root / "src/ai_dlc/__init__.py").is_file():
        return False
    try:
        data = tomllib.loads((root / "pyproject.toml").read_text())
        return data.get("project", {}).get("name") == "ai-dlc"
    except (OSError, ValueError, TypeError):
        return False


def _headless_preference(profile: Path, machine: Path) -> bool | None:
    """Read one preference only after the caller verifies the explicit enrollment."""
    value = False
    try:
        for path in (profile, machine):
            preferences = read_toml(path).get("preferences", {})
            if not isinstance(preferences, dict):
                return None
            if "headless" in preferences:
                selected = preferences["headless"]
                if type(selected) is not bool:
                    return None
                value = selected
    except (OSError, ValueError, TypeError):
        return None
    return value


def _component_limits(root: Path, config: dict, headless: bool | None) -> list[dict]:
    """Inspect only declared module/optional-viewer support, not general readiness."""
    try:
        try:
            catalog = load_component_catalog(root, config)
        except MissingComponentGuidance as exc:
            # Missing guidance does not invalidate authenticated support metadata.
            catalog = exc.catalog
        components = resolve_components(config, catalog)["components"]
        modules = read_toml(assets("modules") / "catalog.toml")
    except (OSError, ValueError, TypeError):
        return [
            {
                "code": "component-support-unverified",
                "component": "project",
                "reason": "Selected component support could not be inspected from local metadata; use the explicit offline readiness operation.",
                "blocking": False,
            }
        ]
    limitations = []
    for component in components:
        definition = DEFINITIONS.get(component["id"])
        if definition is not None and definition.optional_viewer:
            unavailable = headless is True
            limitations.append(
                {
                    "code": "optional-viewer-unavailable"
                    if unavailable
                    else "optional-viewer-unverified",
                    "component": component["provider"],
                    "reason": (
                        f"Optional {definition.optional_viewer} desktop viewer is unavailable in the explicitly selected headless enrollment; note storage does not require it."
                        if unavailable
                        else f"Optional {definition.optional_viewer} desktop viewer support is unverified; note storage does not require it."
                    ),
                    "blocking": False,
                }
            )
        if headless is True:
            for module_id in component["modules"]:
                if modules[module_id].get("desktop"):
                    limitations.append(
                        {
                            "code": "component-headless-unavailable",
                            "component": component["provider"],
                            "reason": f"Selected component requires desktop module {module_id}, which is unavailable in the explicitly selected headless enrollment. Review that selection or use a non-headless environment before target qualification.",
                            "blocking": True,
                        }
                    )
    return limitations


def plan_onboarding(
    root: Path,
    *,
    source: str | None = None,
    ref: str | None = None,
    profile_id: str | None = None,
    machine_id: str | None = None,
    agent_clients: list[str] | None = None,
    preset: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict:
    """Observe local target metadata and return an ordered, reviewable schema-1 plan.

    Availability means the operation is supported after its listed dependencies,
    not that it ran. Neither this interpreter's version nor PATH presence proves
    the feature set of a different installed ``ai-dlc`` executable.
    """
    source, agent_clients = _selection(source, ref, profile_id, machine_id, agent_clients, preset)
    supplied_environment = os.environ if environ is None else environ
    # Only routing metadata is needed; never enumerate credential-bearing values.
    environment = {
        key: value
        for key in ("PATH", "SHELL", "HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME")
        if (value := supplied_environment.get(key)) is not None
    }
    # An explicitly empty environment must not silently use the process PATH.
    environment.setdefault("PATH", "")
    system, architecture = platform.system(), platform.machine()
    shell = Path(environment.get("SHELL", "")).name or "unknown"
    supported_host = system in {"Darwin", "Linux"} and architecture in _SUPPORTED_ARCHITECTURES
    supported_shell = shell in _SUPPORTED_SHELLS and supported_host
    findings: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "schema": 1,
        "target": str(root),
        "platform": {"os": system, "architecture": architecture, "shell": shell},
        "clients": [],
        "engine": {
            "version": __version__,
            "source": "unknown",
            "executable_features": "not-assessed",
        },
        "enrollment": {"status": "unselected"},
        "state": "actionable",
        "findings": findings,
        "actions": actions,
        "qualification": "not-assessed",
    }
    severity = {"actionable": 0, "input-required": 1, "blocked": 2, "unsupported": 3}

    def finding(code, component, reason, next_action_id=None, state=None):
        findings.append(
            {
                "code": code,
                "component": component,
                "reason": reason,
                "next_action_id": next_action_id,
            }
        )
        if state is not None and severity[state] > severity[result["state"]]:
            result["state"] = state

    try:
        root = Path(root).resolve(strict=True)
        if not root.is_dir() or not os.access(root, os.R_OK | os.X_OK):
            raise OSError("unreadable target")
        # Opening the directory proves readability without enumerating user files.
        with os.scandir(root):
            pass
    except (OSError, RuntimeError, TypeError, ValueError):
        finding(
            "target-required",
            "target",
            "Select an existing readable target directory.",
            state="input-required",
        )
        return result
    result["target"] = str(root)
    if _engine_checkout(root):
        finding(
            "engine-checkout-target",
            "target",
            "This is the AI-DLC engine checkout. Select the downstream work repository; engine contribution has its own verification route.",
            state="blocked",
        )
        return result

    adopted = (root / "ai-dlc.toml").exists()
    try:
        config = load_project(root) if adopted else {}
        roles = config.get("roles", {})
        if not isinstance(roles, dict):
            raise TypeError("roles must be a table")
        configured_clients = roles.get("agent-client", [])
        if isinstance(configured_clients, str):
            configured_clients = [configured_clients]
        if not isinstance(configured_clients, list) or not all(
            isinstance(item, str) for item in configured_clients
        ):
            raise ValueError("invalid target clients")
        if configured_clients:
            configured_clients = plan_toolset(
                capabilities=["agent-client"], agent_clients=configured_clients
            )["roles"]["agent-client"]
        required, commands = check_definitions(config)
    except (OSError, ValueError, TypeError, AttributeError):
        raise ValueError(
            "configuration-invalid: review the target ai-dlc.toml and its declared clients/checks"
        ) from None
    clients = configured_clients if adopted and agent_clients is None else agent_clients or []
    result["clients"] = clients
    selection_blocked = False
    if adopted and agent_clients is not None and set(agent_clients) != set(configured_clients):
        finding(
            "selection-conflict",
            "clients",
            "Explicit clients conflict with the target configuration; review the target choices before replanning.",
            state="blocked",
        )
        selection_blocked = True
    if adopted and preset is not None:
        try:
            answers = yaml.safe_load(_target_file(root, ".copier-answers.yml").read_text())
            previous_preset = answers.get("preset") if isinstance(answers, dict) else None
        except (OSError, ValueError, yaml.YAMLError):
            previous_preset = None
        if previous_preset != preset:
            finding(
                "selection-conflict",
                "preset",
                "The explicit preset does not match recorded target adoption. Review its existing configuration before selecting a preset.",
                state="blocked",
            )
            selection_blocked = True
    if not clients:
        finding(
            "client-selection-required",
            "clients",
            "Select at least one supported agent client for the target project.",
            state="input-required",
        )
        selection_blocked = True
    if not supported_host:
        finding(
            "unsupported-platform",
            "platform",
            "Native onboarding requires Darwin or Linux on arm64/aarch64 or x86_64/amd64; this host has no supported execution route.",
            state="unsupported",
        )
    if not supported_shell:
        finding(
            "unsupported-shell",
            "shell",
            "No supported shell presentation is available. Activation and copyable command text are omitted; argument arrays remain authoritative.",
        )

    executable = find_executable("ai-dlc", root, environment)
    result["engine"]["executable"] = executable
    finding(
        "engine-source-unverified",
        "engine",
        "The running planner is available; current source revision and feature parity of other installations are unknown. The version string alone does not establish historical release features. Action availability is conditional on the PATH executable providing the current planner's operations; use the same reviewed engine environment that ran this planner.",
    )
    if not executable:
        finding(
            "engine-feature-unavailable",
            "engine",
            "ai-dlc is unavailable on the selected PATH. Use the consumer installation documentation and an explicit reviewed source/release choice, then activate its environment and rerun onboarding.",
            state="blocked",
        )

    values = (source, ref, profile_id, machine_id)
    enrolled = False
    headless = None
    enrollment_selected = any(value is not None for value in values)
    if enrollment_selected:
        result["enrollment"] = {"status": "selected"}
        if not all(value is not None for value in values):
            missing = [
                name
                for name, value in zip(
                    ("source", "ref", "profile_id", "machine_id"), values, strict=True
                )
                if value is None
            ]
            finding(
                "source-selection-incomplete",
                "enrollment",
                "Enrollment selection requires explicit " + ", ".join(missing) + ".",
                state="input-required",
            )
            selection_blocked = True
        else:
            assert source is not None and ref is not None
            assert profile_id is not None and machine_id is not None
            result["enrollment"].update(
                {
                    "source": source,
                    "requested_ref": ref,
                    "profile_id": profile_id,
                    "machine_id": machine_id,
                }
            )
            paths = EnrollmentPaths.from_environment(
                home=Path(environment["HOME"]) if "HOME" in environment else None,
                environ=environment,
            )
            try:
                lock = read_lock(paths)
                if lock is not None:
                    if (
                        lock.source,
                        lock.requested_ref,
                        lock.profile_id,
                        lock.machine_id,
                    ) != values:
                        finding(
                            "selection-conflict",
                            "enrollment",
                            "The explicitly selected enrollment differs from the active local lock. Review enrollment replacement through the existing enrollment preview.",
                            "enroll-preview",
                            "blocked",
                        )
                        selection_blocked = True
                    else:
                        selected_profile = verify_cached_profile(lock, paths)
                        if not paths.machine_file(lock.machine_id).is_file():
                            raise ValueError("machine binding missing")
                        enrolled = True
                        headless = _headless_preference(
                            selected_profile, paths.machine_file(lock.machine_id)
                        )
                        result["enrollment"].update(
                            {
                                "status": "verified",
                                "resolved_commit": lock.resolved_commit,
                                "content_sha256": lock.content_sha256,
                            }
                        )
            except (OSError, ValueError, TypeError, RuntimeError):
                finding(
                    "enrollment-unverified",
                    "enrollment",
                    "The selected local enrollment metadata/cache cannot be verified. Review the existing enrollment preview; no cache was repaired or fetched.",
                    "enroll-preview",
                )

    machine_supported = True
    if enrollment_selected and all(value is not None for value in values) and system == "Linux":
        try:
            release = platform.freedesktop_os_release()
        except OSError:
            release = {}
        if not release.get("ID") or not release.get("VERSION_ID"):
            machine_supported = False
            finding(
                "machine-platform-unverified",
                "machine",
                "Local Linux release metadata is unavailable or incomplete. Selected machine provisioning support is unresolved; project-only Linux onboarding remains supported.",
                "machine-preview",
                "blocked",
            )
        # This is the bounded native-release contract owned by provision.machine_apply.
        elif release["ID"] != "ubuntu" or release["VERSION_ID"] not in {"24.04", "26.04"}:
            machine_supported = False
            finding(
                "machine-platform-unsupported",
                "machine",
                "Selected native machine provisioning supports Ubuntu 24.04 and 26.04 only. This Linux release is unsupported for machine apply; project-only Linux onboarding remains supported.",
                "machine-preview",
                "blocked",
            )
    component_blocked = False
    for limitation in _component_limits(root, config, headless):
        component_blocked = component_blocked or limitation["blocking"]
        finding(
            limitation["code"],
            limitation["component"],
            limitation["reason"],
            "project-readiness",
            "blocked" if limitation["blocking"] else None,
        )

    usable = supported_host and executable is not None and not selection_blocked

    def add(identifier, stage, argv, effects, *, depends_on=(), review=False, available=True):
        dependencies = list(depends_on)
        prior = {item["id"]: item for item in actions}
        item = {
            "id": identifier,
            "stage": stage,
            "depends_on": dependencies,
            "operation": " ".join(argv[1:3]) if argv else "input-required",
            "argv": argv,
            "effects": effects,
            "requires_review": review,
            "available": bool(
                usable
                and available
                and argv
                and all(prior[name]["available"] for name in dependencies)
            ),
        }
        if supported_shell and item["available"]:
            item["command"] = shlex.join(argv)
        actions.append(item)
        return [identifier]

    dependency = []
    if enrollment_selected and all(value is not None for value in values):
        if not enrolled:
            enroll_argv = [
                "ai-dlc",
                "machine",
                "enroll",
                source,
                "--ref",
                ref,
                "--profile-id",
                profile_id,
                "--machine-id",
                machine_id,
            ]
            dependency = add(
                "enroll-preview",
                "enrollment",
                enroll_argv,
                ["May fetch the selected source and populate an inactive local cache."],
                review=True,
            )
            dependency = add(
                "enroll-apply",
                "enrollment",
                [*enroll_argv, "--apply"],
                ["Activates the reviewed enrollment and local machine bindings."],
                depends_on=dependency,
                review=True,
            )
        dependency = add(
            "machine-preview",
            "machine",
            ["ai-dlc", "machine", "plan", "--root", str(root)],
            ["Inspects selected enrollment and previews machine changes."],
            depends_on=dependency,
        )
        dependency = add(
            "machine-apply",
            "machine",
            ["ai-dlc", "machine", "apply", "--root", str(root)],
            ["Installs selected tools and updates user machine/client configuration."],
            depends_on=dependency,
            review=True,
            available=machine_supported,
        )
    if not adopted:
        adoption = [
            "ai-dlc",
            "project",
            "adopt",
            "--root",
            str(root),
            "--preset",
            preset or "generic",
            "--capability",
            "agent-client",
        ]
        for client in clients:
            adoption.extend(["--agent-client", client])
        # Missing selections have no executable recommendation, even with availability false.
        if not clients:
            adoption = []
        dependency = add(
            "adopt-preview",
            "adoption",
            adoption,
            ["Stages a temporary adoption preview and reports authored-file conflicts."],
            depends_on=dependency,
        )
        dependency = add(
            "adopt-apply",
            "adoption",
            [*adoption, "--apply"] if adoption else [],
            ["Writes reviewed scaffold files only through the adoption service."],
            depends_on=dependency,
            review=True,
        )
    dependency = add(
        "project-setup",
        "setup",
        ["ai-dlc", "project", "setup", "--root", str(root)],
        ["Runs the target's declared setup and may install project dependencies."],
        depends_on=dependency,
        review=True,
    )
    conflict = _guidance_conflicts(root)
    if conflict:
        finding(
            "guidance-conflict",
            "guidance",
            "Owned guidance has edits, unsafe paths or invalid ownership metadata. Use the existing render preview to inspect the conflict and preserve authored content before applying.",
            "render-preview",
            "blocked",
        )
    dependency = add(
        "render-preview",
        "render",
        ["ai-dlc", "agents", "render", "--root", str(root)],
        ["Previews generated guidance through the existing ownership service."],
        depends_on=dependency,
    )
    dependency = add(
        "render-apply",
        "render",
        ["ai-dlc", "agents", "render", "--root", str(root), "--apply"],
        ["Writes reviewed owned guidance after existing ownership checks."],
        depends_on=dependency,
        review=True,
        available=not conflict,
    )
    dependency = add(
        "project-readiness",
        "readiness",
        ["ai-dlc", "project", "readiness", "--root", str(root)],
        [
            "Inspects offline project requirements; native recognition and authentication remain unassessed."
        ],
        depends_on=dependency,
    )
    finding(
        "readiness-not-assessed",
        "readiness",
        "Offline project readiness has not been run; execute its explicit operation after setup and rendering.",
        "project-readiness",
    )
    check_argv = []
    management_only = bool(required) and all(
        name in {"generated", "work-records", "documentation"}
        and parse_command(commands[name]).argv
        in {
            ("sh", "-c", "ai-dlc agents render --check"),
            ("sh", "-c", "ai-dlc work validate --all"),
            ("sh", "-c", "ai-dlc docs gate"),
        }
        for name in required
    )
    check_available = bool(required) and not management_only
    if check_available:
        check_argv = ["ai-dlc", "project", "check", "--root", str(root), "--required"]
        missing_runtime = any(
            find_executable(parse_command(commands[name]).argv[0], root, environment) is None
            for name in required
        )
        if missing_runtime:
            check_available = False
            finding(
                "target-runtime-unavailable",
                "checks",
                "At least one required target check executable or declared shell is unavailable. Run target setup or install its declared prerequisite, then rerun onboarding.",
                "project-setup",
                "blocked",
            )
        finding(
            "target-check-not-run",
            "checks",
            "Required target checks are recommendations, not observed passes or proof of behavioral quality. Review whether they cover the target's acceptance behavior.",
            "target-check",
        )
    else:
        finding(
            "target-check-required",
            "checks",
            "Add or select a meaningful target acceptance check in ai-dlc.toml checks.required, then rerun onboarding. Scaffold/default checks do not establish target acceptance.",
            "target-check",
            "input-required",
        )
    add(
        "target-check",
        "checks",
        check_argv,
        ["Executes the target project's declared checks; their commands may have effects."],
        depends_on=dependency,
        review=True,
        available=check_available and not component_blocked,
    )
    return result
