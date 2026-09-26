"""Bounded native workstation recipes; account and profile activation stay explicit."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ai_dlc.environment.bootstrap import bootstrap_bin
from ai_dlc.setup.commands import find_executable


def _version(argv: list[str], environment: dict[str, str], home: Path, tool: str) -> str | None:
    try:
        result = subprocess.run(
            argv, cwd=home, env=environment, capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    prefixes = {"git": "git version", "gh": "gh version", "python": "Python", "uv": "uv"}
    match = re.match(re.escape(prefixes[tool]) + r" (\d+\.\d+\.\d+)(?:\b|$)", result.stdout)
    return match[1] if match else None


def _core_tools(catalog: dict, environment: dict[str, str], home: Path) -> list[dict]:
    tools = []
    manager = find_executable("winget.exe", home, environment)
    for recipe in catalog["core"]["windows"]["packages"]:
        tool = recipe["command"]
        executable = find_executable(tool + ".exe", home, environment)
        observed = (
            _version([executable, "--version"], environment, home, tool) if executable else None
        )
        adequate = observed is not None and tuple(map(int, observed.split("."))) >= tuple(
            map(int, recipe["minimum"].split("."))
        )
        package = {key: recipe[key] for key in ("id", "version", "source", "scope", "manifest")}
        package["architecture"] = "x64"
        package["availability"] = "not-probed"
        # The reviewed manifest is informative, not permission to launch an elevated installer.
        # Neither current reviewed package establishes an unattended non-elevating route.
        requested = [
            "winget.exe",
            "install",
            "--id",
            recipe["id"],
            "--exact",
            "--source",
            recipe["source"],
            "--version",
            recipe["version"],
            "--scope",
            "user",
            "--architecture",
            "x64",
            "--no-upgrade",
            "--disable-interactivity",
        ]
        reason = recipe["limitation"]
        if observed is not None and not adequate:
            reason = f"Installed {tool} {observed} is below required {recipe['minimum']}; preserved without upgrade"
        elif executable and observed is None:
            reason = (
                f"Installed {tool} version could not be verified; preserved without replacement"
            )
        if not manager:
            reason += "; winget.exe is unavailable"
        tools.append(
            {
                "id": tool,
                "executable": executable,
                "observed_version": observed,
                "minimum_version": recipe["minimum"],
                "status": "ready"
                if adequate
                else "missing"
                if not executable
                else "incompatible"
                if observed
                else "unverified",
                "package": package,
                "installation_plan": requested,
                "automatic_install": False,
                "reason": "adequate installed executable preserved" if adequate else reason,
                "next_action": "none"
                if adequate
                else f"Use a policy-approved manual native installation of {recipe['id']} ({recipe['version']}) or a compatible existing executable; add it to this session's PATH and rerun setup. No elevation or upgrade is requested.",
            }
        )
    return tools


def _runtime_observation(
    mise: str | None, tool: str, required: str, environment: dict[str, str], home: Path
) -> tuple[str | None, list[str]]:
    if mise is None:
        return None, []
    try:
        located = subprocess.run(
            [mise, "which", tool, "--tool", f"{tool}@{required}"],
            cwd=home,
            env=environment,
            capture_output=True,
            text=True,
            # mise emits UTF-8 paths even when Windows' pipe locale is CP1252.
            encoding="utf-8",
            errors="strict",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return None, []
    executable = located.stdout.strip()
    if (
        located.returncode
        or not executable
        or "\n" in executable
        or "\0" in executable
        or not Path(executable).is_absolute()
        or Path(executable).suffix.lower() != ".exe"
    ):
        return None, []
    argv = [executable, "--version"]
    return _version(argv, environment, home, tool), argv


def _runtime_tools(
    catalog: dict, environment: dict[str, str], home: Path
) -> tuple[list[dict], list[dict]]:
    directory = bootstrap_bin(environment, home)
    mise = find_executable("mise.exe", home, environment)
    if mise is None:
        mise = find_executable(str(directory / "mise.exe"), home, environment)
    tools, commands = [], []
    selections = [f"{tool}@{version}" for tool, version in catalog["python"]["mise"].items()]
    for tool, required in catalog["python"]["mise"].items():
        observed, argv = _runtime_observation(mise, tool, required, environment, home)
        tools.append(
            {
                "id": tool,
                "observed_version": observed,
                "required_version": required,
                "status": "ready" if observed == required else "missing" if mise else "blocked",
                "verification": argv,
                "mise": mise,
                "reason": "exact runtime verified"
                if observed == required
                else "pinned runtime is unavailable"
                if mise
                else "bootstrap mise.exe is unavailable",
                "next_action": "none"
                if observed == required
                else "Run explicit setup to prepare the declared runtime; run native bootstrap first if mise.exe is missing.",
            }
        )
    if mise and any(item["status"] != "ready" for item in tools):
        commands.append({"argv": [mise, "install", *selections], "owner": "python"})
    return tools, commands


def native_plan(
    chosen: list[str],
    catalog: dict,
    component_modules: list[dict],
    config: dict,
    home: Path,
    environment: dict[str, str],
) -> dict:
    """Read versions without installing; unsupported selected modules remain blockers."""
    environment = {**environment, "MISE_AUTO_INSTALL": "false", "UV_PYTHON_DOWNLOADS": "never"}
    unsupported = [
        {
            "id": module,
            "reason": "no qualified native Windows recipe",
            "required_by": [
                {"provider": item["provider"], "role": item["role"]}
                for item in component_modules
                if item["id"] == module
            ],
            "next_action": "Choose a supported module or prepare and qualify this module manually; selection remains incomplete.",
        }
        for module in chosen
        if module not in {"core", "python"}
    ]
    if config.get("preferences", {}).get("dotfiles_source"):
        unsupported.append(
            {
                "id": "dotfiles_source",
                "reason": "native dotfile application is not supported",
                "required_by": [],
                "next_action": "Manage the selected dotfiles source explicitly.",
            }
        )
    if config.get("agents", {}).get("servers"):
        unsupported.append(
            {
                "id": "personal-agent-configuration",
                "reason": "native personal client configuration is not part of minimal provisioning",
                "required_by": [],
                "next_action": "Use the separately qualified client configuration service.",
            }
        )
    tools = _core_tools(catalog, environment, home) if "core" in chosen else []
    commands = []
    if "python" in chosen:
        runtimes, commands = _runtime_tools(catalog, environment, home)
        tools.extend(runtimes)
    return {
        "system": "Windows",
        "architecture": "x86_64",
        "selected": list(chosen),
        "ready": not unsupported and all(tool["status"] == "ready" for tool in tools),
        "tools": tools,
        "unsupported": unsupported,
        "commands": commands,
        "omitted": [],
        "guidance": [
            {"id": item["id"], "instruction": item["next_action"]}
            for item in [*unsupported, *tools]
            if item.get("status") != "ready"
        ],
        "signins": [],
        "authentication": "not-assessed",
        "qualification": "not-assessed",
        "agent_configuration": {
            "applied": False,
            "clean": not config.get("agents", {}).get("servers"),
            "qualification": "not-assessed",
        },
    }


def native_apply(plan: dict, home: Path, environment: dict[str, str]) -> dict:
    """Only install the explicitly pinned mise runtimes, then require version readback."""
    environment = {**environment, "MISE_AUTO_INSTALL": "false", "UV_PYTHON_DOWNLOADS": "never"}
    applied, failures = [], []
    for step in plan["commands"]:
        try:
            result = subprocess.run(
                step["argv"],
                cwd=home,
                env=environment,
                capture_output=True,
                text=True,
                timeout=3600,
                check=False,
            )
            if result.returncode:
                failures.append(
                    {
                        "id": step["owner"],
                        "reason": "runtime installation failed",
                        "exit_code": result.returncode,
                    }
                )
            else:
                applied.append(step["argv"])
        except (OSError, subprocess.TimeoutExpired):
            failures.append(
                {"id": step["owner"], "reason": "runtime installation unavailable or timed out"}
            )
    for tool in plan["tools"]:
        if tool.get("mise"):
            observed, argv = _runtime_observation(
                tool["mise"], tool["id"], tool["required_version"], environment, home
            )
            tool["verification"] = argv
            ready = observed == tool["required_version"]
            tool.update(
                observed_version=observed,
                status="ready" if ready else "missing",
                reason="exact runtime verified" if ready else "pinned runtime readback failed",
                next_action="none"
                if ready
                else "Inspect the native runtime installation and rerun setup; no readiness is claimed before exact version readback.",
            )
    from ai_dlc.setup.workstation import activate_workstation

    workstation = activate_workstation(
        home, {}, "mise.exe", bootstrap_bin(environment, home), shell="powershell"
    )
    return {
        **plan,
        "ready": not failures
        and not plan["unsupported"]
        and all(tool["status"] == "ready" for tool in plan["tools"]),
        "guidance": [
            {"id": item["id"], "instruction": item["next_action"]}
            for item in [*plan["unsupported"], *plan["tools"]]
            if item.get("status") != "ready"
        ],
        "applied": applied,
        "failures": failures,
        "workstation": workstation,
        "next": "Verify local tools; preview explicit --powershell-profile $PROFILE activation separately. Provider authentication is not assessed.",
    }
