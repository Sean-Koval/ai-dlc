"""One install for a teammate: the team harness, the knowledge repository and its hook.

``install`` checks the tools it needs and names any that are missing before it writes
anything. It then runs team-harness ``scripts/install_local.py`` for one harness channel
in user scope, which owns the guarantee that the person's own skills, hooks and
settings under ``~/.claude`` are never overwritten. Next it clones ``KNOWLEDGE_REPO``
and adds the knowledge pre-commit hook only where the clone has no hook of its own.

Settings come from environment variables (:data:`SETTINGS`). A missing one is asked
for only when a prompt is given (a terminal); otherwise the install stops and names
it. What is stored, in ``<config root>/knowledge-install.toml``, is names, paths and
URLs without credentials. A URL that carries a user name or password is refused.

``uninstall`` asks install_local to remove what it installed, removes the hook only
while it is unchanged, and removes the stored settings. It never deletes the clone,
which may hold the person's own work.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from ai_dlc.environment.enrollment import EnrollmentPaths
from ai_dlc.errors import RefusedError
from ai_dlc.files import atomic_write, run_git

# Tools the install needs on PATH. Python is the interpreter running this.
PREREQUISITES = ("claude", "uv", "gh", "git")

# (variable, default, what it is). None as default means it must be given.
SETTINGS = (
    ("KNOWLEDGE_REPO", None, "the knowledge repository: a git URL or a local clone"),
    ("TEAM_HARNESS_REPO", None, "the team-harness repository: a git URL or a local checkout"),
    ("TEAM_HARNESS", "suite-default", "the harness to install, under harnesses/"),
    ("TEAM_HARNESS_CHANNEL", "stable", "the channels.yaml channel to install"),
    ("KNOWLEDGE_CHECKOUT", "", "where to clone the knowledge repository"),
)
SETTINGS_FILE = "knowledge-install.toml"
# A hook that blocked every commit when ai-dlc is not on git's PATH (a GUI client, a
# Windows shell) would be worse than none; CI runs the same check.
HOOK = (
    "#!/bin/sh\n"
    "# Installed by `ai-dlc knowledge install`; `--uninstall` removes it while unchanged.\n"
    "if command -v ai-dlc >/dev/null 2>&1; then exec ai-dlc knowledge check .; fi\n"
    'echo "ai-dlc is not on PATH: knowledge check skipped; run it before you push" >&2\n'
)
_URL = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_USERINFO = re.compile(r"^[a-z][a-z0-9+.-]*://([^/@]*)@", re.IGNORECASE)
_HARNESS = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")

Prompt = Callable[[str, str], str]
Runner = Callable[..., subprocess.CompletedProcess]


def is_url(value: str) -> bool:
    return bool(_URL.match(value)) or (
        "@" in value and ":" in value.split("@", 1)[1] and not Path(value).exists()
    )


def carries_credentials(url: str) -> bool:
    """A URL with a password, or a user other than ssh's usual ``git``, in it."""
    found = _USERINFO.match(url)
    return bool(found) and (":" in found.group(1) or found.group(1) != "git")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class Install:
    home: Path
    config_root: Path
    cache_root: Path

    @classmethod
    def for_home(cls, home: Path, environ: Mapping[str, str]) -> "Install":
        paths = EnrollmentPaths.from_environment(home, environ)
        return cls(home=home, config_root=paths.config_root, cache_root=paths.cache_root)

    @property
    def settings_path(self) -> Path:
        return self.config_root / SETTINGS_FILE

    @property
    def manifest_path(self) -> Path:
        return self.home / ".claude" / "team-harness.json"


def missing_prerequisites(environ: Mapping[str, str]) -> list[str]:
    path = environ.get("PATH", os.defpath)
    return [tool for tool in PREREQUISITES if shutil.which(tool, path=path) is None]


def resolve_settings(
    home: Path, environ: Mapping[str, str], prompt: Prompt | None = None
) -> dict[str, str]:
    """The settings from the environment, asking only for absent ones when ``prompt`` is given."""
    values: dict[str, str] = {}
    for name, default, about in SETTINGS:
        value = environ.get(name, "").strip()
        if not value and default is None:
            if prompt is None:
                raise RefusedError(f"set {name} ({about}); nothing was installed")
            value = prompt(name, about).strip()
            if not value:
                raise RefusedError(f"{name} is required ({about}); nothing was installed")
        values[name] = value or (default or "")
    for name in ("KNOWLEDGE_REPO", "TEAM_HARNESS_REPO"):
        if carries_credentials(values[name]):
            raise RefusedError(
                f"{name} carries a user name or password; give a URL without credentials "
                "and let git's credential helper sign in"
            )
    if not _HARNESS.fullmatch(values["TEAM_HARNESS"]):
        raise RefusedError("TEAM_HARNESS must be one harness directory name")
    if not values["KNOWLEDGE_CHECKOUT"]:
        values["KNOWLEDGE_CHECKOUT"] = str(_default_checkout(home, values["KNOWLEDGE_REPO"]))
    return values


def _default_checkout(home: Path, source: str) -> Path:
    if not is_url(source):
        return Path(source).expanduser().resolve()
    name = re.split(r"[/:]", source.rstrip("/"))[-1].removesuffix(".git") or "knowledge"
    return home / "knowledge" / name


def _origin(checkout: Path, environ: Mapping[str, str]) -> str | None:
    result = run_git(checkout, "remote", "get-url", "origin", environ=environ, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _same_remote(left: str, right: str) -> bool:
    def norm(value: str) -> str:
        return re.sub(r"\.git/?$", "", value.strip().rstrip("/")).casefold()

    return norm(left) == norm(right)


def ensure_clone(
    source: str, checkout: Path, environ: Mapping[str, str], *, full: bool = False
) -> Path:
    """A clone of ``source`` at ``checkout``; an existing clone of it is reused, never replaced."""
    if not is_url(source):
        local = Path(source).expanduser().resolve()
        if not (local / ".git").exists():
            raise RefusedError(f"{source} is not a git checkout")
        return local
    if checkout.exists() and any(checkout.iterdir()):
        origin = _origin(checkout, environ) if (checkout / ".git").exists() else None
        if origin is None or not _same_remote(origin, source):
            raise RefusedError(
                f"{checkout} already exists and is not a clone of that repository; "
                "set KNOWLEDGE_CHECKOUT to another directory"
            )
        run_git(checkout, "fetch", "--quiet", "origin", environ=environ, check=False)
        return checkout
    checkout.parent.mkdir(parents=True, exist_ok=True)
    args = ["clone", "--quiet"] + ([] if full else ["--filter=blob:none"]) + [source, str(checkout)]
    run_git(None, *args, environ=environ, context="Clone failed")
    return checkout


def team_harness_checkout(install: Install, source: str, environ: Mapping[str, str]) -> Path:
    """The team-harness checkout: the given one, or a full clone in the cache.

    The clone is full because install_local finds a channel's lock in git history.
    """
    if not is_url(source):
        return ensure_clone(source, Path(source), environ)
    key = digest(source.strip().rstrip("/"))[:16]
    checkout = install.cache_root / "team-harness" / key
    ensure_clone(source, checkout, environ, full=True)
    run_git(checkout, "merge", "--ff-only", "--quiet", "@{upstream}", environ=environ, check=False)
    return checkout


def known_harness_checkout(install: Install, source: str) -> Path | None:
    """The team-harness checkout an install used, if it is still there; no network."""
    if not source:
        return None
    if is_url(source):
        path = install.cache_root / "team-harness" / digest(source.strip().rstrip("/"))[:16]
    else:
        path = Path(source).expanduser()
    return path if (path / "scripts" / "install_local.py").is_file() else None


def hook_path(checkout: Path, environ: Mapping[str, str]) -> Path | None:
    """The clone's own pre-commit hook, or None when git would run one from elsewhere.

    With ``core.hooksPath`` set (often a global directory of shared hooks), a hook
    written there would run in every repository, so none is installed.
    """
    configured = run_git(
        checkout, "config", "--get", "core.hooksPath", environ=environ, check=False
    )
    if configured.returncode == 0 and configured.stdout.strip():
        return None
    found = run_git(checkout, "rev-parse", "--git-path", "hooks/pre-commit", environ=environ)
    path = Path(found.stdout.strip())
    path = path if path.is_absolute() else checkout / path
    git_dir = run_git(checkout, "rev-parse", "--absolute-git-dir", environ=environ).stdout.strip()
    return path if path.resolve().is_relative_to(Path(git_dir).resolve()) else None


def harness_command(checkout: Path, harness: str, channel: str, home: Path, mode: str) -> list[str]:
    command = [
        sys.executable,
        str(checkout / "scripts" / "install_local.py"),
        str(Path("harnesses") / harness),
        "--scope",
        "user",
        "--home",
        str(home),
    ]
    if mode != "--uninstall":
        command += ["--channel", channel]
    return command + [mode]


def _run(runner: Runner, command: list[str], cwd: Path, environ: Mapping[str, str], step: str):
    result = runner(command, cwd=cwd, env=dict(environ), text=True, capture_output=True)
    if result.returncode != 0:
        detail = (result.stdout or "") + (result.stderr or "")
        raise RefusedError(f"{step} failed (exit {result.returncode}):\n{detail.strip()}")
    return result


def _write_settings(
    install: Install, values: Mapping[str, str], hook: str | None, preinstalled: bool
) -> None:
    lines = ["# Written by `ai-dlc knowledge install`. Names, paths and URLs only.\n"]
    for name, _default, _about in SETTINGS:
        lines.append(f"{name} = {_toml(values[name])}\n")
    if hook:
        lines.append(f"hook_sha256 = {_toml(hook)}\n")
    # A harness the person installed before this is theirs: uninstall leaves it.
    lines.append(f"harness_preinstalled = {'true' if preinstalled else 'false'}\n")
    atomic_write(install.settings_path, "".join(lines), mode=0o600)


def _toml(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def read_settings(install: Install) -> dict[str, str] | None:
    try:
        return tomllib.loads(install.settings_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def install(
    home: Path,
    environ: Mapping[str, str],
    *,
    prompt: Prompt | None = None,
    dry_run: bool = False,
    runner: Runner = subprocess.run,
) -> dict:
    """Install the harness channel, the knowledge clone and its hook; return what was done."""
    missing = missing_prerequisites(environ)
    if missing:
        raise RefusedError(
            "install " + ", ".join(missing) + " and put it on PATH; nothing was installed"
        )
    target = Install.for_home(home, environ)
    values = resolve_settings(home, environ, prompt)
    steps: list[str] = []
    if dry_run:
        return {"status": "planned", "settings": values, "steps": steps}
    # Recorded first, so an install that stops part way can still be uninstalled. A
    # re-install keeps the earlier record until it succeeds, then keeps what that
    # record says about the hook and about a harness installed before ai-dlc's.
    earlier = read_settings(target) or {}
    kept_hook = earlier.get("hook_sha256") if isinstance(earlier.get("hook_sha256"), str) else None
    preinstalled = (
        bool(earlier["harness_preinstalled"])
        if "harness_preinstalled" in earlier
        else target.manifest_path.exists()
    )
    if not earlier:
        _write_settings(target, values, None, preinstalled)
    harness = team_harness_checkout(target, values["TEAM_HARNESS_REPO"], environ)
    command = harness_command(
        harness, values["TEAM_HARNESS"], values["TEAM_HARNESS_CHANNEL"], home, "--apply"
    )
    _run(runner, command, harness, environ, "the team harness install")
    steps.append(f"harness {values['TEAM_HARNESS']}@{values['TEAM_HARNESS_CHANNEL']} installed")
    checkout = ensure_clone(values["KNOWLEDGE_REPO"], Path(values["KNOWLEDGE_CHECKOUT"]), environ)
    values = {**values, "KNOWLEDGE_CHECKOUT": str(checkout)}
    steps.append(f"knowledge repository at {checkout}")
    hook = hook_path(checkout, environ)
    written: str | None = kept_hook
    if hook is None:
        steps.append(
            "pre-commit hook not installed: core.hooksPath is set; add "
            "`ai-dlc knowledge check .` to your hooks there"
        )
    elif hook.exists():
        current = hook.read_text(encoding="utf-8", errors="replace")
        if current == HOOK:
            written = digest(HOOK)
            steps.append("pre-commit hook already installed")
        else:
            steps.append(f"pre-commit hook left alone: {hook} is your own")
    else:
        atomic_write(hook, HOOK, mode=0o755)
        written = digest(HOOK)
        steps.append(f"pre-commit hook installed at {hook}")
    _write_settings(target, values, written, preinstalled)
    steps.append(f"settings written to {target.settings_path}")
    return {"status": "installed", "settings": values, "steps": steps}


def uninstall(home: Path, environ: Mapping[str, str], *, runner: Runner = subprocess.run) -> dict:
    """Remove what ``install`` added; keep the knowledge clone and anything the person changed."""
    target = Install.for_home(home, environ)
    stored = read_settings(target)
    if stored is None:
        raise RefusedError(f"no install recorded at {target.settings_path}; nothing was removed")
    steps: list[str] = []
    if stored.get("harness_preinstalled"):
        steps.append("harness kept: it was installed before `ai-dlc knowledge install`")
    elif target.manifest_path.exists():
        harness = known_harness_checkout(target, str(stored.get("TEAM_HARNESS_REPO", "")))
        if harness is None:
            raise RefusedError(
                "the team-harness checkout is gone; run its scripts/install_local.py "
                "--scope user --uninstall, then rerun this"
            )
        command = harness_command(harness, str(stored["TEAM_HARNESS"]), "", home, "--uninstall")
        _run(runner, command, harness, environ, "the team harness uninstall")
        steps.append("harness removed")
    checkout = Path(str(stored.get("KNOWLEDGE_CHECKOUT") or ""))
    hook = None
    if stored.get("hook_sha256") and (checkout / ".git").exists():
        hook = hook_path(checkout, environ)
    if hook is not None:
        if hook.exists() and digest(hook.read_text(encoding="utf-8")) == stored["hook_sha256"]:
            hook.unlink()
            steps.append("pre-commit hook removed")
        elif hook.exists():
            steps.append(f"pre-commit hook kept: {hook} was changed")
    target.settings_path.unlink()
    steps.append(f"knowledge repository kept at {checkout}")
    return {"status": "uninstalled", "steps": steps}
