"""Copier adoption and three-way updates, staged before any checkout mutation."""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import copier

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


def adopt(
    root: Path,
    preset: str = "generic",
    apply: bool = False,
    *,
    template_source: str | None = None,
    vcs_ref: str | None = None,
    capabilities: list[str] | None = None,
    initialize: bool = False,
) -> dict:
    if preset not in {"generic", "python", "node", "rust"}:
        raise ValueError("Unknown preset")
    capabilities = list(CAPABILITIES if capabilities is None else dict.fromkeys(capabilities))
    if set(capabilities) - set(CAPABILITIES):
        raise ValueError("Unknown role capability")
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
            "template_source": source,
            "local_source": "://" not in source,
        }


def sync(root: Path, apply: bool = False, *, vcs_ref: str | None = None) -> dict:
    root = Path(root).resolve()
    before = _files(root)
    if ".copier-answers.yml" not in before:
        raise ValueError("Adopt a versioned Copier template before sync")
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
