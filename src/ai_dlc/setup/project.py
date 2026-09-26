"""Project preparation and checks run from one checked-in manifest."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ai_dlc import __version__
from ai_dlc.config import digest, load_project, read_toml
from ai_dlc.environment.bootstrap import bootstrap_bin
from ai_dlc.errors import RefusedError, UncertainError
from ai_dlc.files import run_git
from ai_dlc.setup.commands import (
    Command,
    CommandUnavailable,
    find_executable,
    parse_command,
    require_executable,
)


def state_file() -> Path:
    return (
        Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
        / "ai-dlc/state.db"
    )


def environment_digest(root: Path, config: dict[str, Any]) -> str:
    return digest({"mise": read_toml(root / ".mise.toml"), "setup": config.get("setup", {})})


class RuntimeUnavailable(UncertainError):
    """A configured runtime manager is absent, so no command can run reproducibly."""

    def __init__(self, executable: str) -> None:
        self.executable = executable
        self.remedy = [
            "Inspect installation and shell activation with `ai-dlc project workspace-check`.",
            "Open a new terminal or source the AI-DLC shell file to activate the bootstrap bin directory.",
            "Rerun the repository bootstrap if the bootstrap bin directory is absent.",
        ]
        super().__init__(f"{executable} is not on PATH; no check can run reproducibly")


def runtime_env(root: Path, use_mise: bool, *, notify: bool = True) -> dict[str, str]:
    env = dict(os.environ)
    env["UV_PYTHON_DOWNLOADS"] = "never"
    if use_mise:
        executable = find_executable("mise", root, env)
        if executable is None:
            directory = bootstrap_bin(env, Path(env.get("HOME") or Path.home()))
            candidate = directory / ("mise.exe" if os.name == "nt" else "mise")
            if not candidate.is_file() or not os.access(candidate, os.X_OK):
                raise RuntimeUnavailable("mise")
            executable = str(candidate)
            env["PATH"] = str(directory) + os.pathsep + env.get("PATH", "")
            if notify:
                print(
                    f"note: using bootstrap runtime at {directory}; add it to PATH permanently with `ai-dlc project workspace-init --shell --apply`",
                    file=sys.stderr,
                )
        # Explicitly forbid mise from installing tools as a side effect of checks.
        env["MISE_AUTO_INSTALL"] = "0"
        tools = read_toml(root / ".mise.toml").get("tools", {})
        if "python" in tools:
            result = subprocess.run(
                [executable, "which", "python"],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            env["UV_PYTHON"] = result.stdout.strip()
    return env


def run_command(
    root: Path, command: Any, *, use_mise: bool, timeout: int = 3600
) -> subprocess.CompletedProcess:
    parsed = parse_command(command)
    env = runtime_env(root, use_mise, notify=False)
    if use_mise and parsed.shell is None and Path(parsed.argv[0]).name == parsed.argv[0]:
        # Resolve native tools under mise before pinning the launch path, so managed
        # runtimes win over a different system executable and batch targets are checked.
        mise = find_executable("mise", root, env)
        if mise is None:
            raise RuntimeUnavailable("mise")
        resolved = subprocess.run(
            [mise, "which", parsed.argv[0]],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if resolved.returncode == 0 and resolved.stdout.strip():
            parsed = Command((resolved.stdout.strip(), *parsed.argv[1:]))
    executable = require_executable(parsed, root, env)
    argv = [executable, *parsed.argv[1:]]
    if use_mise:
        mise = find_executable("mise", root, env)
        if mise is None:
            raise RuntimeUnavailable("mise")
        argv = [mise, "exec", "--", *argv]
    try:
        return subprocess.run(
            argv,
            cwd=root,
            env=env,
            shell=False,
            text=True,
            stdout=sys.stderr,
            stderr=sys.stderr,
            timeout=timeout,
            check=False,
        )
    except OSError as exc:
        raise CommandUnavailable(
            f"cannot launch {parsed.argv[0]!r}: {exc.strerror}; verify the declared prerequisite"
        ) from exc


def check_definitions(config: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    """Validated required check IDs and their commands from project configuration."""
    checks = config.get("checks", {})
    if not isinstance(checks, dict):
        raise RefusedError("checks must be a table")
    required = checks.get("required", [])
    commands = checks.get("commands", {})
    if not isinstance(required, list) or not all(isinstance(x, str) for x in required):
        raise ValueError("checks.required must be a list of IDs")
    if not isinstance(commands, dict):
        raise RefusedError("checks.commands must be a table")
    if len(set(required)) != len(required):
        raise ValueError("duplicate required check IDs")
    for name in required:
        try:
            parse_command(commands.get(name))
        except ValueError as exc:
            raise ValueError(
                f"missing or invalid command for required check: {name}: {exc}"
            ) from exc
    return required, commands


def selected_check_ids(
    required: list[str],
    commands: dict[str, Any],
    *,
    required_only: bool,
    selected_checks: list[str] | None,
) -> list[str]:
    """Validate explicit selection before runtime resolution and preserve its order."""
    if selected_checks is None:
        chosen = required if required_only else list(commands)
        for name in chosen:
            try:
                parse_command(commands[name])
            except ValueError as exc:
                raise ValueError(
                    f"missing or invalid command for selected check: {name}: {exc}"
                ) from exc
        return chosen
    if not required_only:
        raise ValueError("explicit check selection cannot be combined with all-command mode")
    if not selected_checks:
        raise ValueError("explicit check selection must be nonempty")
    if any(not isinstance(name, str) or not name.strip() for name in selected_checks):
        raise ValueError("explicit check selection contains a blank ID")
    if len(set(selected_checks)) != len(selected_checks):
        raise ValueError("explicit check selection contains duplicate IDs")
    unknown = [name for name in selected_checks if name not in commands]
    if unknown:
        raise ValueError("unknown check ID: " + ", ".join(unknown))
    for name in selected_checks:
        try:
            parse_command(commands[name])
        except ValueError as exc:
            raise ValueError(
                f"missing or invalid command for selected check: {name}: {exc}"
            ) from exc
    return list(selected_checks)


def check_project(
    root: Path,
    target: str = "local",
    use_mise: bool = True,
    required_only: bool = True,
    *,
    selected_checks: list[str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    config = load_project(root)
    required, commands = check_definitions(config)
    check_ids = selected_check_ids(
        required,
        commands,
        required_only=required_only,
        selected_checks=selected_checks,
    )
    # Resolve the runtime before any check so a missing one cannot be reported as a check failure.
    runtime_env(root, use_mise)
    commit = run_git(root, "rev-parse", "HEAD").stdout.strip()
    status = run_git(root, "status", "--porcelain").stdout
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
    for name in check_ids:
        start = time.monotonic()
        reason = None
        try:
            result = run_command(root, commands[name], use_mise=use_mise)
            code, outcome = result.returncode, "passed" if result.returncode == 0 else "failed"
        except CommandUnavailable as exc:
            code, outcome = 127, "failed"
            reason = f"check {name}: {exc}"
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
                **({"reason": reason} if reason else {}),
            }
        )
        if outcome == "cancelled":
            break
    after = run_git(root, "status", "--porcelain").stdout
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
    parsed = parse_command(step["command"])
    # Scripts keep legacy dependency-command recognition. Native argv is inspected
    # as tokens, never split or reinterpreted as shell text.
    command = parsed.argv[-1] if parsed.shell else ""
    native = list(parsed.argv)
    if native:
        native[0] = Path(native[0]).name.removesuffix(".exe")
    paths: list[Path] = []
    if native[:2] == ["uv", "sync"] or re.search(r"\buv\s+sync\b", command):
        environment = Path(os.environ.get("UV_PROJECT_ENVIRONMENT", ".venv"))
        if not environment.is_absolute():
            environment = root / environment
        paths += [
            environment,
            environment / "pyvenv.cfg",
            environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python"),
        ]
    if native[:2] in (
        ["npm", "ci"],
        ["npm", "install"],
        ["pnpm", "install"],
        ["yarn", "install"],
    ) or re.search(r"\b(?:npm\s+(?:ci|install)|pnpm\s+install|yarn\s+install)\b", command):
        paths += [root / "node_modules", root / "node_modules/.package-lock.json"]
    if native[:2] == ["cargo", "fetch"] or re.search(r"\bcargo\s+fetch\b", command):
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


def setup_steps(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Preflight every setup declaration before installation, journaling or rendering."""
    setup = config.get("setup", {})
    if not isinstance(setup, dict) or not isinstance(setup.get("steps", []), list):
        raise RefusedError("setup.steps must be a list of step records")
    steps = setup.get("steps", [])
    ids: set[str] = set()
    for step in steps:
        if (
            not isinstance(step, dict)
            or not isinstance(step.get("id"), str)
            or not step["id"].strip()
        ):
            raise ValueError("setup steps require nonblank IDs")
        if step["id"] in ids:
            raise ValueError("duplicate setup step IDs")
        ids.add(step["id"])
        for field in ("command", "verify"):
            if field == "verify" and field not in step:
                continue
            try:
                parse_command(step.get(field))
            except ValueError as exc:
                raise ValueError(f"invalid setup step {step['id']} {field}: {exc}") from exc
        setup_inputs(root, step)
    return steps


def setup_project(
    root: Path, target: str = "local", state_path: Path | None = None, use_mise: bool = True
) -> dict[str, Any]:
    if os.name == "nt":
        from ai_dlc._windows_storage import guarded_path

        # Resolve neither the root nor its ancestors before the native guard can
        # reject reparse redirects. Retain their identity through setup and render.
        with guarded_path(root):
            # The guard validates raw drive-relative/parent traversal syntax before
            # absolute normalization, as well as retaining the opened directories.
            return _setup_project(Path(os.path.abspath(root)), target, state_path, use_mise)
    return _setup_project(root.resolve(), target, state_path, use_mise)


def _setup_project(
    root: Path, target: str, state_path: Path | None, use_mise: bool
) -> dict[str, Any]:
    config = load_project(root)
    check_definitions(config)
    steps = setup_steps(root, config)
    from ai_dlc.files import assets
    from ai_dlc.harness.agents import render_agents, target_hooks

    targets = read_toml(assets("targets") / "capabilities.toml")
    if target not in targets:
        raise ValueError(f"unsupported execution target: {target}")
    hook_policy = target_hooks(config, target)
    if not hook_policy["ready"]:
        raise ValueError(f"required target hooks unavailable: {hook_policy['unavailable']}")
    # A bare install directory (only ai-dlc.toml, as the release runbook creates) declares
    # no tools; activating mise there would fail on the absent file, not on a real problem.
    if use_mise and (root / ".mise.toml").is_file():
        subprocess.run(["mise", "trust", str(root / ".mise.toml")], cwd=root, check=True)
        subprocess.run(["mise", "install"], cwd=root, check=True)
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
        raise ValueError(
            "generated project files are stale; render and commit before CI: "
            + ", ".join(generated["changed"])
        )
    return {
        "target": target,
        "steps": completed,
        "ready": True,
        "agent_configuration": generated,
        "hook_policy": hook_policy,
    }
