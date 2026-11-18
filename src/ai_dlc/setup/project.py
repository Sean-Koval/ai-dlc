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
            "Open a new terminal or source the ai-dlc shell file to activate the bootstrap bin directory.",
            "Rerun the repository bootstrap if the bootstrap bin directory is absent.",
        ]
        super().__init__(f"{executable} is not on PATH; no check can run reproducibly")


def _mise_skipped_note(reason: str) -> str:
    return (
        f"note: {reason}; mise skipped, running with the tools on PATH. "
        "Results may differ from the versions pinned in .mise.toml."
    )


def _find_mise(root: Path, env: dict[str, str]) -> tuple[str | None, Path | None]:
    """The mise executable on PATH, else in the bootstrap bin (returned as the second item)."""
    executable = find_executable("mise", root, env)
    if executable is not None:
        return executable, None
    directory = bootstrap_bin(env, Path(env.get("HOME") or Path.home()))
    candidate = directory / ("mise.exe" if os.name == "nt" else "mise")
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate), directory
    return None, None


class RuntimeEnv(dict[str, str]):
    """A check environment; ``mise`` is the mise executable, or None when checks run on PATH."""

    mise: str | None = None


def runtime_env(
    root: Path, use_mise: bool, *, notify: bool = True, target: str = "local"
) -> dict[str, str]:
    """The check environment, carrying the mise executable when mise runs the checks.

    Locally, an absent or unprepared mise is skipped visibly and the tools on PATH run the
    checks (KAN-354). CI receipts are completion evidence, so the github-actions target
    still refuses to run without the pinned runtime.
    """
    env = RuntimeEnv(os.environ)
    env["UV_PYTHON_DOWNLOADS"] = "never"
    if not use_mise:
        return env
    executable, directory = _find_mise(root, env)
    if executable is None:
        if target != "local":
            raise RuntimeUnavailable("mise")
        if notify:
            print(_mise_skipped_note("mise is not installed"), file=sys.stderr)
        return env
    mise_env = RuntimeEnv(env)
    if directory is not None:
        mise_env["PATH"] = str(directory) + os.pathsep + env.get("PATH", "")
    # Explicitly forbid mise from installing tools as a side effect of checks.
    mise_env["MISE_AUTO_INSTALL"] = "0"
    tools = read_toml(root / ".mise.toml").get("tools", {})
    if "python" in tools:
        result = subprocess.run(
            [executable, "which", "python"],
            cwd=root,
            env=mise_env,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            if target != "local":
                raise RuntimeUnavailable("python from .mise.toml")
            if notify:
                print(
                    _mise_skipped_note(
                        "mise has not installed the python in .mise.toml "
                        "(run `ai-dlc project setup` to install it)"
                    ),
                    file=sys.stderr,
                )
            return env
        mise_env["UV_PYTHON"] = result.stdout.strip()
    if directory is not None and notify:
        print(
            f"note: using bootstrap runtime at {directory}; add it to PATH permanently with `ai-dlc project workspace-init --shell --apply`",
            file=sys.stderr,
        )
    mise_env.mise = executable
    return mise_env


def run_command(
    root: Path,
    command: Any,
    *,
    use_mise: bool,
    timeout: int = 3600,
    target: str = "local",
) -> subprocess.CompletedProcess:
    parsed = parse_command(command)
    env = runtime_env(root, use_mise, notify=False, target=target)
    mise = getattr(env, "mise", None)
    if mise is not None and parsed.shell is None and Path(parsed.argv[0]).name == parsed.argv[0]:
        # Resolve native tools under mise before pinning the launch path, so managed
        # runtimes win over a different system executable and batch targets are checked.
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
    if mise is not None:
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
    mise = getattr(runtime_env(root, use_mise, target=target), "mise", None)
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
        # "path" records that mise was skipped and the checks ran with the tools on PATH.
        "runtime": "mise" if mise is not None else "path",
        "outcomes": [],
    }
    for name in check_ids:
        start = time.monotonic()
        reason = None
        try:
            result = run_command(root, commands[name], use_mise=use_mise, target=target)
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
    from ai_dlc.harness.agents import render_agents, target_hooks
    from ai_dlc.setup.targets import execution_target

    execution_target(target)
    hook_policy = target_hooks(config, target)
    if not hook_policy["ready"]:
        raise ValueError(f"required target hooks unavailable: {hook_policy['unavailable']}")
    # A bare install directory (only ai-dlc.toml, as the release runbook creates) declares
    # no tools; activating mise there would fail on the absent file, not on a real problem.
    mise = _find_mise(root, dict(os.environ))[0] if use_mise else None
    skipped: list[str] = []
    declared = root / ".mise.toml"
    tools = sorted(read_toml(declared).get("tools", {})) if declared.is_file() else []
    if use_mise and mise is None and tools:
        missing = (
            f"mise is not installed, so the tools in .mise.toml ({', '.join(tools)}) "
            "were not installed"
        )
        if target != "local":
            raise RuntimeError(
                f"{missing}; install mise (`sh scripts/bootstrap.sh` provides it), "
                "then rerun `ai-dlc project setup`"
            )
        print(
            f"note: {missing}. Setup steps run with the tools on PATH; install those tools "
            "yourself, or install mise and rerun `ai-dlc project setup`.",
            file=sys.stderr,
        )
        skipped = tools
    if mise is not None and (root / ".mise.toml").is_file():
        subprocess.run([mise, "trust", str(root / ".mise.toml")], cwd=root, check=True)
        try:
            subprocess.run([mise, "install"], cwd=root, check=True)
        except subprocess.CalledProcessError as exc:
            # Name the failure as setup steps do; mise has already printed which tool
            # and download failed, and nothing was journaled, so a rerun resumes.
            raise RuntimeError(
                f"mise could not install the tools in .mise.toml (exit {exc.returncode}); "
                "check access to the tool downloads mise printed above (behind a shared "
                "or proxied network, set GITHUB_TOKEN for mise's GitHub downloads), then "
                "rerun `ai-dlc project setup` to resume"
            ) from exc
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
                or run_command(root, step["verify"], use_mise=use_mise, target=target).returncode
                == 0
            ):
                completed.append({"id": step["id"], "status": "unchanged"})
                continue
            result = run_command(root, step["command"], use_mise=use_mise, target=target)
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
    generated = render_agents(root, apply=target != "github-actions")
    if target == "github-actions" and not generated["clean"]:
        raise ValueError("generated project files are stale; render and commit before CI")
    return {
        "target": target,
        "steps": completed,
        "ready": True,
        "agent_configuration": generated,
        "hook_policy": hook_policy,
        **({"mise_skipped": skipped} if skipped else {}),
    }
