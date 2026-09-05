"""Machine recipes delegate installations; ordinary setup never requests upgrades."""

from __future__ import annotations

import difflib
import json
import os
import platform
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

import tomli_w

from ai_dlc.components import load_component_catalog, resolve_components
from ai_dlc.config import SCHEMA, read_toml, resolve_files
from ai_dlc.credentials import credential_status
from ai_dlc.files import assets, atomic_write


def _which(command: str, environ: Mapping[str, str] | None) -> str | None:
    if environ is None:
        return shutil.which(command)
    return shutil.which(command, path=environ.get("PATH", ""))


def machine_plan(
    profile: Path,
    headless: bool = False,
    system: str | None = None,
    architecture: str | None = None,
    home: Path | None = None,
    machine: Path | None = None,
    root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict:
    system = system or platform.system()
    architecture = architecture or platform.machine()
    if system not in {"Darwin", "Linux"} or architecture not in {
        "arm64",
        "aarch64",
        "x86_64",
        "amd64",
    }:
        raise ValueError(f"unsupported machine: {system}/{architecture}")
    selected_root = Path(root).resolve() if root is not None else None
    resolved = resolve_files(
        personal=profile,
        project=selected_root / "ai-dlc.toml" if selected_root is not None else None,
        machine=machine,
    )
    config = resolved.values
    catalog = read_toml(assets("modules") / "catalog.toml")
    chosen = config.get("modules", {}).get("include", ["core"])
    component_modules: list[dict[str, str]] = []
    if selected_root is not None:
        components = resolve_components(resolved, load_component_catalog(selected_root, config))
        if components["unresolved"]:
            raise ValueError(components["unresolved"][0]["reason"])
        for component in components["components"]:
            for module_id in component["modules"]:
                component_modules.append(
                    {
                        "id": module_id,
                        "provider": component["provider"],
                        "role": component["role"],
                        "reason": (
                            f"selected provider {component['provider']} for role {component['role']}"
                        ),
                    }
                )
        chosen = list(dict.fromkeys([*chosen, *(item["id"] for item in component_modules)]))
    headless = headless or config.get("preferences", {}).get("headless", False)
    commands, omitted, guidance, signins = [], [], [], []
    brew, casks, apt, runtimes = [], [], [], {}
    for name in chosen:
        if name not in catalog:
            raise ValueError(f"unknown module: {name}")
        module = catalog[name]
        if headless and module.get("desktop"):
            omitted.append({"id": name, "reason": "headless desktop capability unavailable"})
            continue
        brew.extend(module.get("brew", []))
        casks.extend(module.get("cask", []))
        apt.extend(module.get("apt", []))
        runtimes.update(module.get("mise", {}))
        signins.extend(module.get("signins", []))
        if system == "Linux" and module.get("linux_guidance"):
            guidance.append({"id": name, "instruction": module["linux_guidance"]})
    if system == "Darwin":
        brewfile = "".join(f'brew "{name}"\n' for name in dict.fromkeys(brew))
        brewfile += "".join(f'cask "{name}"\n' for name in dict.fromkeys(casks))
        commands.append(
            {
                "argv": ["brew", "bundle", "--no-upgrade", "--file", "{Brewfile}"],
                "content": brewfile,
            }
        )
    elif apt:
        commands.append(
            {"argv": ["sudo", "apt-get", "install", "--yes", "--no-upgrade", *dict.fromkeys(apt)]}
        )
    if runtimes:
        commands.append({"argv": ["mise", "install"], "mise": runtimes})
    from ai_dlc.user_agents import render_user_agents

    agent_configuration = render_user_agents(config, (home or Path.home()).resolve())
    result = {
        "system": system,
        "architecture": architecture,
        "commands": commands,
        "omitted": omitted,
        "guidance": guidance,
        "signins": signins,
        "headless": headless,
        "credentials": credential_status(config, environ),
        "agent_configuration": agent_configuration,
    }
    if selected_root is not None:
        result["component_modules"] = component_modules
    return result


def machine_apply(
    profile: Path,
    headless: bool = False,
    home: Path | None = None,
    machine: Path | None = None,
    root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict:
    plan = machine_plan(profile, headless, home=home, machine=machine, root=root, environ=environ)
    if plan["system"] == "Linux":
        release = platform.freedesktop_os_release()
        if release.get("ID") != "ubuntu" or release.get("VERSION_ID") not in {"24.04", "26.04"}:
            raise ValueError("supported Linux workstation releases are Ubuntu 24.04 and 26.04")
    home = (home or Path.home()).resolve()
    environment = os.environ if environ is None else environ
    workstation_root = (
        Path(environment.get("XDG_DATA_HOME", str(home / ".local/share"))) / "ai-dlc/workstation"
    )
    workstation_root.mkdir(parents=True, exist_ok=True)
    selected_root = Path(root).resolve() if root is not None else None
    config = resolve_files(
        personal=profile,
        project=selected_root / "ai-dlc.toml" if selected_root is not None else None,
        machine=machine,
    ).values
    from ai_dlc.user_agents import render_user_agents

    # Detect user-authored configuration conflicts before invoking package managers.
    render_user_agents(config, home)
    bootstrap_home = Path(
        environment.get(
            "AI_DLC_BOOTSTRAP_HOME",
            str(
                Path(environment.get("XDG_DATA_HOME", str(home / ".local/share")))
                / "ai-dlc/bootstrap"
            ),
        )
    )
    bootstrap_bin = bootstrap_home / "bin"
    mise = _which("mise", environ)
    if not mise and (bootstrap_bin / "mise").is_file():
        mise = str(bootstrap_bin / "mise")
    if not mise:
        raise RuntimeError("mise is required; run the standalone bootstrap first")
    brew = None
    if any(step["argv"][0] == "brew" for step in plan["commands"]):
        from ai_dlc.workstation import ensure_brew

        brew = ensure_brew(workstation_root, plan["architecture"], environ=environ)
    results = []
    runtimes = {}
    for step in plan["commands"]:
        argv = list(step["argv"])
        if argv[0] == "brew" and brew:
            argv[0] = brew
        elif argv[0] == "mise":
            argv[0] = mise
        elif not _which(argv[0], environ):
            raise RuntimeError(
                f"{argv[0]} is required; install the native package manager before applying this module"
            )
        if "content" in step:
            file = workstation_root / "Brewfile"
            atomic_write(file, step["content"])
            argv = [str(file) if x == "{Brewfile}" else x for x in argv]
        if "mise" in step:
            runtimes.update(step["mise"])
            atomic_write(workstation_root / ".mise.toml", tomli_w.dumps({"tools": step["mise"]}))
            subprocess.run(
                [mise, "trust", str(workstation_root / ".mise.toml")],
                cwd=workstation_root,
                check=True,
                env=environment,
            )
        subprocess.run(argv, cwd=workstation_root, check=True, env=environment)
        results.append(argv)
    source = config.get("preferences", {}).get("dotfiles_source")
    if source:
        # An explicit source only; chezmoi owns its conflict resolution.
        subprocess.run(
            ["chezmoi", "--source", str(Path(source).expanduser()), "apply", "--interactive"],
            check=True,
            env=environment,
        )
    from ai_dlc.workstation import activate_workstation

    workstation = activate_workstation(
        home,
        runtimes,
        mise,
        bootstrap_bin,
        brew=brew,
        shell=Path(environment.get("SHELL", "/bin/zsh")).name,
    )
    agent_configuration = render_user_agents(config, home, apply=True)
    return {
        **plan,
        "ready": workstation["ready"],
        "applied": results,
        "workstation": workstation,
        "agent_configuration": agent_configuration,
        "next": "Complete listed sign-ins and run doctor. Select each checkout explicitly for project setup.",
    }


def doctor(
    root: Path,
    target: str = "local",
    machine: Path | None = None,
    *,
    personal: Path | None = None,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict:
    capabilities = read_toml(assets("targets") / "capabilities.toml")
    if target not in capabilities:
        raise ValueError(f"unsupported execution target: {target}")
    environment = os.environ if environ is None else environ
    config = resolve_files(personal=personal, project=root / "ai-dlc.toml", machine=machine).values
    credentials = credential_status(config, environment)
    missing = [tool for tool in ["git", "mise"] if not _which(tool, environ)]
    runtime_drift = []
    if "mise" not in missing:
        result = subprocess.run(
            ["mise", "ls", "--json"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=environment,
        )
        if result.returncode:
            runtime_drift.append("mise could not resolve this project; run project setup")
        else:
            for tool, versions in json.loads(result.stdout).items():
                for version in versions:
                    if version.get("active") and not version.get("installed"):
                        runtime_drift.append(tool + "@" + version.get("version", "unknown"))
    signins = []
    configuration = []
    health = []
    roles = config.get("roles", {})
    providers = config.get("providers", {})

    def kind(role):
        name = roles.get(role)
        settings = providers.get(name, {})
        return settings.get("kind", settings.get("type", name))

    if kind("scm") in {"github", "github-scm"} or kind("tracker") == "github-issues":
        if _which("gh", environ):
            status = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                timeout=30,
                check=False,
                env=environment,
            )
            if status.returncode:
                signins.append("gh auth login")
        else:
            missing.append("gh")
        for key in ["repository", "workflow", "target_branch"]:
            if not config.get("scm", {}).get(key):
                configuration.append("scm." + key + " is required")
    if kind("tracker") == "github-issues" and not providers.get(roles["tracker"], {}).get(
        "repository"
    ):
        configuration.append("tracker repository is required")
    if kind("tracker") == "linear":
        settings = providers.get(roles["tracker"], {})
        if not settings.get("team_id"):
            configuration.append("tracker team_id is required for creation")
        for state in ["in_progress", "closed"]:
            if not settings.get("statuses", {}).get(state):
                configuration.append("tracker statuses." + state + " is required")
    from ai_dlc.providers import Registry

    registry = Registry(config, root=root, environ=environment)
    for name, settings in providers.items():
        if settings.get("health_reference"):
            try:
                registry.invoke(name, "read", {"reference": settings["health_reference"]})
                health.append({"provider": name, "ready": True})
            except Exception:  # noqa: BLE001 -- doctor must report provider failures
                health.append(
                    {
                        "provider": name,
                        "ready": False,
                        "reason": "provider health check failed",
                    }
                )
    from ai_dlc.agents import render_agents, target_hooks

    hooks = target_hooks(config, target)

    try:
        rendered = render_agents(root)
        conflicts = rendered["changed"]
    except ValueError as exc:
        conflicts = [str(exc)]
    vault = config.get("paths", {}).get("vault")
    knowledge = "available" if vault and Path(vault).expanduser().is_dir() else "unavailable"
    if personal is None:
        user_agents: dict[str, object] = {"clean": True, "changed": [], "applied": False}
    else:
        from ai_dlc.user_agents import UserAgentOwnershipConflict, render_user_agents

        try:
            user_agents = render_user_agents(
                config,
                (Path.home() if home is None else Path(home)).resolve(),
                apply=False,
            )
        except UserAgentOwnershipConflict as exc:
            user_agents = {
                "clean": False,
                "changed": [],
                "applied": False,
                "conflicts": [str(exc)],
            }
    for credential in credentials:
        if credential["present"]:
            continue
        variable = credential.get("variable")
        if isinstance(variable, str):
            signins.append(f"Set {variable} using your credential store")
        else:
            signins.append(f"Bind credential {credential['id']} in machine configuration")
    return {
        "ready": not (missing or runtime_drift or signins or conflicts or configuration)
        and hooks["ready"]
        and all(item["ready"] for item in health)
        and bool(user_agents["clean"]),
        "target": target,
        "capabilities": capabilities[target],
        "missing": missing,
        "runtime_drift": runtime_drift,
        "configuration": configuration,
        "provider_health": health,
        "signins": signins,
        "managed_conflicts": conflicts,
        "knowledge": knowledge,
        "hooks": hooks,
        "credentials": credentials,
        "user_agents": user_agents,
    }


def capture(profile: Path) -> dict:
    proposed = read_toml(profile)
    catalog = read_toml(assets("modules") / "catalog.toml")
    included = proposed.setdefault("modules", {}).setdefault("include", [])
    detected = []
    for name, module in catalog.items():
        commands = module.get("verify", [])
        if commands and all(shutil.which(command) for command in commands) and name not in included:
            detected.append(name)
    proposed["modules"]["include"] = included + detected
    patch = "".join(
        difflib.unified_diff(
            profile.read_text().splitlines(True),
            tomli_w.dumps(proposed).splitlines(True),
            fromfile=str(profile),
            tofile=str(profile),
        )
    )
    return {
        "proposed_modules": detected,
        "patch": patch,
        "source": "executable inventory; no shell history read",
        "applied": False,
    }


def migrate(path: Path, apply: bool = False) -> dict:
    data = read_toml(path)
    version = data.get("schema")
    if version not in {2, 3, SCHEMA}:
        raise ValueError(f"unknown schema {version}; explicit migration unavailable")
    if version == SCHEMA:
        return {"changed": False}
    data["schema"] = SCHEMA
    roles = data.get("roles", {})
    if "agents" in roles:
        roles["agent-client"] = roles.pop("agents")
    data.pop("extends", None)
    migrated = tomli_w.dumps(data)
    patch = "".join(
        difflib.unified_diff(
            path.read_text().splitlines(True),
            migrated.splitlines(True),
            fromfile=str(path),
            tofile=str(path),
        )
    )
    if apply:
        # Preserve original config so a migration can be reviewed and reverted.
        backup = path.with_suffix(path.suffix + f".v{version}.bak")
        if backup.exists():
            raise ValueError(f"migration backup exists: {backup}")
        backup.write_bytes(path.read_bytes())
        atomic_write(path, migrated)
    return {"changed": True, "applied": apply, "patch": patch}
