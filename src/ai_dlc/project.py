"""Project preparation and checks run from one checked-in manifest."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ai_dlc import __version__
from ai_dlc.config import digest, load_project, read_toml


def state_file() -> Path:
    return (
        Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
        / "ai-dlc/state.db"
    )


def environment_digest(root: Path, config: dict[str, Any]) -> str:
    return digest({"mise": read_toml(root / ".mise.toml"), "setup": config.get("setup", {})})


def runtime_env(root: Path, use_mise: bool) -> dict[str, str]:
    env = dict(os.environ)
    if use_mise:
        if not shutil.which("mise"):
            raise RuntimeError("mise unavailable; run the repository bootstrap first")
        # Explicitly forbid mise from installing tools as a side effect of checks.
        env["MISE_AUTO_INSTALL"] = "0"
        tools = read_toml(root / ".mise.toml").get("tools", {})
        if "python" in tools:
            result = subprocess.run(
                ["mise", "which", "python"],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            env["UV_PYTHON"] = result.stdout.strip()
            env["UV_PYTHON_DOWNLOADS"] = "never"
    return env


def run_command(
    root: Path, command: str, *, use_mise: bool, timeout: int = 3600
) -> subprocess.CompletedProcess:
    argv = ["sh", "-c", command]
    if use_mise:
        argv = ["mise", "exec", "--", *argv]
    return subprocess.run(
        argv,
        cwd=root,
        env=runtime_env(root, use_mise),
        text=True,
        stdout=sys.stderr,
        stderr=sys.stderr,
        timeout=timeout,
        check=False,
    )


def _check_definitions(config: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
    checks = config.get("checks", {})
    required = checks.get("required", [])
    commands = checks.get("commands", {})
    if not isinstance(required, list) or not all(isinstance(x, str) for x in required):
        raise ValueError("checks.required must be a list of IDs")
    if len(set(required)) != len(required):
        raise ValueError("duplicate required check IDs")
    for name in required:
        if not isinstance(commands.get(name), str) or not commands[name].strip():
            raise ValueError(f"missing command for required check: {name}")
    return required, commands


def check_project(
    root: Path, target: str = "local", use_mise: bool = True, required_only: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    config = load_project(root)
    required, commands = _check_definitions(config)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True)
    receipt: dict[str, Any] = {
        "schema": 1,
        "commit": commit,
        "checks_digest": digest(config.get("checks", {})),
        "environment_digest": environment_digest(root, config),
        "engine_version": __version__,
        "target": target,
        "required": required,
        "dirty": bool(status),
        "outcomes": [],
    }
    for name in required if required_only else commands:
        start = time.monotonic()
        try:
            result = run_command(root, commands[name], use_mise=use_mise)
            code, outcome = result.returncode, "passed" if result.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            code, outcome = 124, "cancelled"
        except KeyboardInterrupt:
            code, outcome = 130, "cancelled"
        receipt["outcomes"].append(
            {
                "id": name,
                "status": outcome,
                "exit_code": code,
                "duration_seconds": time.monotonic() - start,
            }
        )
        if outcome == "cancelled":
            break
    after = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True)
    receipt["dirty"] = receipt["dirty"] or bool(after)
    return receipt


# Files that change dependency resolution, including workspace-member manifests.
_DEPENDENCY_NAMES = {
    "pyproject.toml",
    "uv.lock",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "setup.py",
    "setup.cfg",
    "package.json",
    "package-lock.json",
    "npm-shrinkwrap.json",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "Cargo.toml",
    "Cargo.lock",
    ".npmrc",
    ".yarnrc",
    ".yarnrc.yml",
    "rust-toolchain",
    "rust-toolchain.toml",
    ".python-version",
}
_DEPENDENCY_GLOBS = ("requirements*.txt", "requirements*.in", "constraints*.txt")
_SETUP_IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "target",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def setup_inputs(root: Path, step: dict[str, Any]) -> dict[str, str]:
    """Hash dependency inputs, adding optional repository-relative input globs.

    Examples: inputs = ["schema/*.json", "scripts/prepare.sh"]. Missing/new/deleted
    matches change the snapshot. Generated dependency trees are not traversed.
    """
    paths: set[Path] = set()
    for directory, subdirs, names in os.walk(root, followlinks=False):
        subdirs[:] = [name for name in subdirs if name not in _SETUP_IGNORED_DIRS]
        for name in names:
            if name in _DEPENDENCY_NAMES or any(
                fnmatch.fnmatch(name, pattern) for pattern in _DEPENDENCY_GLOBS
            ):
                paths.add(Path(directory) / name)
    declared = step.get("inputs", [])
    if not isinstance(declared, list) or any(
        not isinstance(p, str) or not p.strip() for p in declared
    ):
        raise ValueError("setup step inputs must be a list of relative paths or globs")
    for pattern in declared:
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise ValueError("setup step inputs must remain inside the project")
        for match in root.glob(pattern):
            paths.update(
                p for p in match.rglob("*") if p.is_file()
            ) if match.is_dir() else paths.add(match)
    snapshot = {}
    for path in sorted(paths):
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"setup input escapes project: {path.relative_to(root)}")
        snapshot[str(path.relative_to(root))] = (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        )
    return snapshot


def setup_outputs(root: Path, step: dict[str, Any]) -> dict[str, Any]:
    """Cheap environment-presence markers supplement (never replace) input hashes."""
    command = step["command"]
    paths: list[Path] = []
    if re.search(r"\buv\s+sync\b", command):
        environment = Path(os.environ.get("UV_PROJECT_ENVIRONMENT", ".venv"))
        if not environment.is_absolute():
            environment = root / environment
        paths += [environment, environment / "pyvenv.cfg", environment / "bin/python"]
    if re.search(r"\b(?:npm\s+(?:ci|install)|pnpm\s+install|yarn\s+install)\b", command):
        paths += [root / "node_modules", root / "node_modules/.package-lock.json"]
    if re.search(r"\bcargo\s+fetch\b", command):
        home = Path(os.environ.get("CARGO_HOME", str(Path.home() / ".cargo")))
        paths += [home / "registry", home / "git"]
    return {str(path): {"exists": path.exists(), "directory": path.is_dir()} for path in paths}


def setup_key(root: Path, target: str, config: dict[str, Any], step: dict[str, Any]) -> str:
    return digest(
        {
            "root": str(root),
            "target": target,
            "environment": environment_digest(root, config),
            "step": step,
            "dependency_inputs": setup_inputs(root, step),
            "environment_outputs": setup_outputs(root, step),
        }
    )


def setup_project(
    root: Path, target: str = "local", state_path: Path | None = None, use_mise: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    config = load_project(root)
    _check_definitions(config)
    from ai_dlc.agents import render_agents, target_hooks
    from ai_dlc.files import assets

    targets = read_toml(assets("targets") / "capabilities.toml")
    if target not in targets:
        raise ValueError(f"unsupported execution target: {target}")
    hook_policy = target_hooks(config, target)
    if not hook_policy["ready"]:
        raise ValueError(f"required target hooks unavailable: {hook_policy['unavailable']}")
    if use_mise:
        subprocess.run(["mise", "trust", str(root / ".mise.toml")], cwd=root, check=True)
        subprocess.run(["mise", "install"], cwd=root, check=True)
    steps = config.get("setup", {}).get("steps", [])
    ids = [step["id"] for step in steps]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate setup step IDs")
    db_path = state_path or state_file()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    completed = []
    with sqlite3.connect(db_path) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS setup_state (key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL)"
        )
        for step in steps:
            key = setup_key(root, target, config, step)
            identity = digest({"root": str(root), "target": target, "step_id": step["id"]})
            previous = db.execute(
                "SELECT fingerprint FROM setup_state WHERE key=?", (identity,)
            ).fetchone()
            done = previous is not None and previous[0] == key
            # Both dependency content and environment presence must match; a lock-only
            # verify command cannot hide changed inputs or a removed environment.
            if done and (
                not step.get("verify")
                or run_command(root, step["verify"], use_mise=use_mise).returncode == 0
            ):
                completed.append({"id": step["id"], "status": "unchanged"})
                continue
            result = run_command(root, step["command"], use_mise=use_mise)
            if result.returncode:
                raise RuntimeError(
                    f"setup step {step['id']} failed ({result.returncode}); retry to resume"
                )
            # A setup command may create/update a lockfile or its environment. Journal
            # the resulting state so the next identical invocation is a cache hit.
            post_key = setup_key(root, target, config, step)
            db.execute("INSERT OR REPLACE INTO setup_state VALUES (?,?)", (identity, post_key))
            db.commit()
            completed.append({"id": step["id"], "status": "completed"})
    generated = render_agents(
        root, apply=target not in {"github-actions", "codex-cloud", "claude-cloud"}
    )
    if target == "github-actions" and not generated["clean"]:
        raise ValueError("generated project files are stale; render and commit before CI")
    return {
        "target": target,
        "steps": completed,
        "ready": True,
        "agent_configuration": generated,
        "hook_policy": hook_policy,
    }
