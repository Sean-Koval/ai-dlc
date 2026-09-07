"""Copier adoption and three-way updates, staged before any checkout mutation."""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import copier
import yaml

from ai_dlc.files import assets, inside

RUNTIME_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".cache",
}
CAPABILITIES = ["specs", "tracker", "knowledge", "scm", "deploy", "agent-client"]


def _ignore(root: Path):
    ignored = set()
    if root.is_dir():
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "--directory",
                *[f"--exclude={name}/" for name in sorted(RUNTIME_DIRS)],
                "--exclude=.ai-dlc/local/",
                "-z",
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        if result.returncode == 0:
            ignored = {
                os.fsdecode(value).rstrip("/") for value in result.stdout.split(b"\0") if value
            }

    def exclude(directory, names):
        parent = Path(directory).relative_to(root)
        return {
            name
            for name in names
            if name in RUNTIME_DIRS
            or (parent / name).as_posix() == ".ai-dlc/local"
            or (parent / name).as_posix() in ignored
        }

    return exclude


def _files(root: Path) -> dict[str, bytes]:
    result = {}
    exclude = _ignore(root)
    for directory, dirs, names in os.walk(root, followlinks=False):
        excluded = exclude(directory, dirs + names)
        dirs[:] = [name for name in dirs if name not in excluded]
        for name in names:
            path = Path(directory) / name
            if name not in excluded and not path.is_symlink() and path.is_file():
                result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def _apply(root: Path, before: dict, after: dict) -> list[str]:
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    # Recheck the checkout after staging, before writing anything.
    if _files(root) != before:
        raise ValueError("Checkout changed during template staging; retry")
    for name in changed:
        inside(root, name)
    try:
        for name in changed:
            path = root / name
            if name in after:
                path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    dir=path.parent, prefix=".ai-dlc-", delete=False
                ) as stream:
                    temp = Path(stream.name)
                    stream.write(after[name])
                temp.chmod(path.stat().st_mode & 0o777 if path.exists() else 0o644)
                temp.replace(path)
            else:
                path.unlink()
    except Exception:
        for name in changed:
            path = root / name
            if name in before:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(before[name])
            else:
                path.unlink(missing_ok=True)
        raise
    return changed


def plan_toolset(*, capabilities=None, providers=None, agent_clients=None) -> dict:
    """Pure declared selection; no account identity, remote access or destination writes."""
    from ai_dlc.agents import CLIENT_SKILL_DIRECTORIES
    from ai_dlc.provider_definitions import DEFINITIONS

    capabilities = list(CAPABILITIES if capabilities is None else dict.fromkeys(capabilities))
    if set(capabilities) - set(CAPABILITIES):
        raise ValueError("Unknown role capability")
    providers = providers or {}
    if set(providers) - {"tracker", "knowledge"}:
        raise ValueError("Only tracker and knowledge scaffold selections are supported")
    for role, provider in providers.items():
        if role not in capabilities:
            raise ValueError(f"{role.title()} selection requires the {role} capability")
        definition = DEFINITIONS.get(provider)
        if definition is None or role not in definition.roles:
            raise ValueError(
                f"Unsupported {role} scaffold: {provider}; custom providers remain configurable"
            )
    if agent_clients is not None and "agent-client" not in capabilities:
        raise ValueError("Client selection requires the agent-client capability")
    clients = list(
        dict.fromkeys(["claude-code", "codex"] if agent_clients is None else agent_clients)
    )
    if set(clients) - set(CLIENT_SKILL_DIRECTORIES):
        raise ValueError("Unsupported agent client")
    defaults = {
        "specs": "openspec",
        "tracker": "linear",
        "knowledge": "obsidian",
        "scm": "github",
        "deploy": "none",
    }
    roles: dict = {
        role: providers.get(role, default)
        for role, default in defaults.items()
        if role in capabilities
    }
    if "agent-client" in capabilities:
        roles["agent-client"] = clients
    settings = {}
    limitations = []
    for role in ("tracker", "knowledge"):
        if role not in roles:
            continue
        definition = DEFINITIONS[roles[role]]
        if role == "tracker" or definition.scaffold_defaults:
            settings[definition.kind] = dict(definition.scaffold_defaults) or {
                "kind": definition.kind
            }
        if not definition.lifecycle_available:
            limitations.append(
                f"{definition.kind}: AI-DLC {role} lifecycle adapter is unavailable; native tools do not enable tracked-work operations."
            )
    return {"roles": roles, "providers": settings, "limitations": limitations}


def adopt(
    root: Path,
    preset: str = "generic",
    apply: bool = False,
    *,
    template_source: str | None = None,
    vcs_ref: str | None = None,
    capabilities: list[str] | None = None,
    initialize: bool = False,
    providers: dict[str, str] | None = None,
    agent_clients: list[str] | None = None,
) -> dict:
    if preset not in {"generic", "python", "node", "rust"}:
        raise ValueError("Unknown preset")
    capabilities = list(CAPABILITIES if capabilities is None else dict.fromkeys(capabilities))
    if set(capabilities) - set(CAPABILITIES):
        raise ValueError("Unknown role capability")
    toolset = plan_toolset(
        capabilities=capabilities, providers=providers, agent_clients=agent_clients
    )
    tracker = toolset["roles"].get("tracker", "linear")
    root = Path(root).resolve()
    source = template_source or str(assets("project-templates"))
    before = _files(root)
    with tempfile.TemporaryDirectory(prefix="ai-dlc-adopt-") as temporary:
        stage = Path(temporary).resolve() / "project"
        copier.run_copy(
            source,
            stage,
            data={
                "preset": preset,
                "tracker": tracker,
                "tracker_settings": toolset["providers"].get(tracker, {}),
                "knowledge": toolset["roles"].get("knowledge", "obsidian"),
                "agent_clients": toolset["roles"].get("agent-client", []),
                "capabilities": capabilities,
                "initialize": initialize,
                "project_name": "project-"
                + (re.sub(r"[^a-z0-9]+", "-", root.name.lower()).strip("-")[:60] or "app"),
            },
            vcs_ref=vcs_ref,
            defaults=True,
            quiet=True,
            skip_tasks=True,
        )
        rendered = _files(stage)
        conflicts = []
        for name in rendered:
            path = root / name
            if (
                path.exists()
                or path.is_symlink()
                or any(
                    parent.is_symlink() or parent.is_file()
                    for parent in path.parents
                    if parent != root and parent.is_relative_to(root)
                )
            ):
                conflicts.append(name)
        conflicts.sort()
        if conflicts:
            return {"status": "conflict", "conflicts": conflicts}
        changes = sorted(rendered)
        if apply:
            _apply(root, before, {**before, **rendered})
        return {
            "status": "applied" if apply else "planned",
            "files": changes,
            "toolset": toolset,
            "template_source": source,
            "local_source": "://" not in source,
        }


def _validate_toolset_answers(content: bytes) -> None:
    """Check retained and staged selections before Copier can publish destination changes."""
    try:
        answers = yaml.safe_load(content)
    except yaml.YAMLError:
        raise ValueError("Copier answers must contain valid selection data") from None
    if not isinstance(answers, dict):
        raise ValueError("Copier answers must contain a mapping")
    capabilities = answers.get("capabilities", CAPABILITIES)
    if not isinstance(capabilities, list) or not all(
        isinstance(value, str) for value in capabilities
    ):
        raise ValueError("Copier capabilities must be a string list")
    plan_toolset(capabilities=capabilities)
    providers = {role: answers[role] for role in ("tracker", "knowledge") if role in answers}
    if not all(isinstance(value, str) for value in providers.values()):
        raise ValueError("Copier provider selections must be strings")
    clients = answers.get("agent_clients")
    if "agent_clients" in answers and (
        not isinstance(clients, list) or not all(isinstance(value, str) for value in clients)
    ):
        raise ValueError("Copier client selections must be a string list")
    # Answers retain defaults even for disabled capabilities; validate the declared
    # choices without treating those retained defaults as new capability requests.
    selected = plan_toolset(providers=providers, agent_clients=clients)
    if "tracker_settings" in answers:
        settings = answers["tracker_settings"]
        tracker = selected["roles"]["tracker"]
        if settings != selected["providers"][tracker] and not (
            "tracker" not in capabilities and settings == {}
        ):
            raise ValueError(
                "Copier tracker defaults differ from the trusted provider definition; review a fresh scaffold selection"
            )


def sync(root: Path, apply: bool = False, *, vcs_ref: str | None = None) -> dict:
    root = Path(root).resolve()
    before = _files(root)
    if ".copier-answers.yml" not in before:
        raise ValueError("Adopt a versioned Copier template before sync")
    _validate_toolset_answers(before[".copier-answers.yml"])
    with tempfile.TemporaryDirectory(prefix="ai-dlc-sync-") as temporary:
        stage = Path(temporary).resolve() / "project"
        shutil.copytree(root, stage, ignore=_ignore(root), symlinks=True)
        for args in [
            ("init",),
            ("add", "."),
            (
                "-c",
                "user.name=AI-DLC",
                "-c",
                "user.email=ai-dlc@localhost",
                "commit",
                "-m",
                "Staged project",
            ),
        ]:
            subprocess.run(["git", "-C", str(stage), *args], check=True, capture_output=True)
        copier.run_update(
            stage,
            vcs_ref=vcs_ref,
            defaults=True,
            overwrite=True,
            quiet=True,
            skip_tasks=True,
            conflict="inline",
        )
        after = _files(stage)
        if ".copier-answers.yml" not in after:
            raise ValueError("Updated template must retain its Copier answers")
        _validate_toolset_answers(after[".copier-answers.yml"])
        conflicts = sorted(
            name
            for name in after
            if (name.endswith(".rej") and name not in before)
            or (b"<<<<<<<" in after[name] and after[name] != before.get(name))
        )
        if conflicts:
            return {"status": "conflict", "conflicts": conflicts}
        changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
        if apply:
            _apply(root, before, after)
        return {"status": "applied" if apply else "planned", "files": changed}
