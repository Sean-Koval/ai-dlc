"""Explicit local directory mounts; private Knowledge traversal remains independent."""

import hashlib
import json
import os
import re
import stat
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from ai_dlc.documentation.document_files import (
    create_document,
    directory,
    read_document,
    validate_parent,
)


@dataclass(frozen=True)
class VaultMountResult:
    project_root: str
    project_name: str
    vault_path: str
    link_path: str
    binding_path: str
    binding_action: str
    binding_content: dict
    mounts: list[dict[str, str]]
    missing_sources: list[str]
    created_link: bool = False
    status: str = "planned"
    mode: str = "mount"

    def as_dict(self) -> dict:
        return asdict(self)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise ValueError(
            "Mounts require a stable Git checkout with ignored .ai-dlc/local/ bindings."
        )
    return result.stdout.strip()


def _canonical_directory(path: Path) -> Path:
    raw = path.expanduser().absolute()
    # Check lexical components before collapsing '..', which could conceal a link.
    cursor = Path(raw.anchor)
    for part in raw.parts[1:]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"Mount directory traverses a symlink: {cursor}")
    normalized = Path(os.path.abspath(raw))
    with directory(normalized):
        pass
    return normalized.resolve()


def _inaccessible(exc: OSError) -> None:
    raise ValueError(f"Mount inspection encountered an inaccessible directory: {exc}") from exc


def _source(path: Path) -> None:
    with directory(path):
        pass
    # A mounted tree must not silently grant access through another symlink.
    for parent, dirs, files in os.walk(path, followlinks=False, onerror=_inaccessible):
        for name in dirs + files:
            child = Path(parent) / name
            mode = child.lstat().st_mode
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise ValueError(
                    f"Mount source contains unsafe nested traversal or special file: {child}"
                )


def mount_vault(root: Path, vault: Path, name: str | None, *, adopt: bool, apply: bool):
    root, vault = _canonical_directory(root), _canonical_directory(vault)
    name = root.name if name is None else name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", name):
        raise ValueError("Project name must be one safe filename.")
    with directory(root), directory(vault):
        pass
    if not (root / ".git").is_dir() or (root / ".git").is_symlink():
        raise ValueError("Mount sources require a stable checkout, not a linked Git worktree.")
    if Path(_git(root, "rev-parse", "--show-toplevel")).resolve() != root.resolve():
        raise ValueError("Mount source must be the stable checkout root.")
    if root.is_relative_to(vault) or vault.is_relative_to(root):
        raise ValueError("Project and vault must not overlap or form a loop.")
    target = vault / "Projects" / name
    validate_parent(target / "docs")
    key = hashlib.sha256(str(target).encode()).hexdigest()
    binding = root / ".ai-dlc/local/vault-mounts" / f"{key}.json"
    validate_parent(binding)
    _git(root, "check-ignore", "-q", str(binding))
    body = (
        json.dumps(
            {
                "schema": 1,
                "project_root": str(root),
                "vault_path": str(vault),
                "project_name": name,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode()
    owned = binding.exists() or binding.is_symlink()
    if owned and read_document(binding) != body:
        raise ValueError("Mount binding conflicts; preserve it and inspect the local binding.")
    mounts: list[dict[str, str]] = []
    missing: list[str] = []
    for part in ("docs", "openspec"):
        source = root / part
        destination = target / part
        if not source.exists() and not source.is_symlink():
            if part == "docs":
                raise ValueError("Project docs are missing; initialize them before mounting.")
            if destination.exists() or destination.is_symlink():
                raise ValueError(f"Mount destination conflicts with missing source: {destination}")
            missing.append(part)
            continue
        _source(source)
        action = "create"
        if destination.is_symlink():
            if Path(os.path.abspath(target / os.readlink(destination))) != source:
                raise ValueError(f"Mount target conflicts: {destination}")
            if not owned and not adopt:
                raise ValueError("Matching unowned links require explicit --adopt.")
            action = "unchanged" if owned else "adopt"
        elif destination.exists():
            raise ValueError(f"Mount target conflicts: {destination}")
        mounts.append({"source": str(source), "path": str(destination), "action": action})
    expected = {Path(item["path"]) for item in mounts}
    for parent, dirs, files in os.walk(vault, followlinks=False, onerror=_inaccessible):
        for entry in dirs + files:
            other = Path(parent) / entry
            if not other.is_symlink() or other in expected:
                continue
            try:
                other_source = other.resolve()
            except (OSError, RuntimeError) as exc:
                raise ValueError(f"Unsafe vault link: {other}") from exc
            for item in mounts:
                source = Path(item["source"])
                if other_source.is_relative_to(source) or source.is_relative_to(other_source):
                    raise ValueError(f"Mount targets overlap existing vault link: {other}")
    result = VaultMountResult(
        str(root),
        name,
        str(vault),
        str(target),
        str(binding),
        "unchanged" if owned else "create",
        json.loads(body),
        mounts,
        missing,
    )
    if not apply:
        return result
    retained: list[str] = []
    try:
        if not owned:
            if not create_document(binding, body):
                raise ValueError("Binding appeared during setup; inspect and retry.")
            retained.append(str(binding))
        for item in mounts:
            source = Path(item["source"])
            _source(source)
            with directory(target, create=True) as parent:
                if item["action"] == "create":
                    os.symlink(str(source), source.name, target_is_directory=True, dir_fd=parent)
                    retained.append(item["path"])
                elif os.readlink(source.name, dir_fd=parent) != str(source):
                    # Relative matching links are allowed, but recheck without following parents.
                    actual = os.readlink(source.name, dir_fd=parent)
                    if Path(os.path.abspath(target / actual)) != source:
                        raise ValueError("Existing mount changed during setup; inspect and retry.")
    except (OSError, ValueError) as exc:
        raise ValueError(f"Mount setup stopped; retained output {retained}. {exc}") from exc
    return VaultMountResult(
        str(root),
        name,
        str(vault),
        str(target),
        str(binding),
        result.binding_action,
        result.binding_content,
        mounts,
        missing,
        any(item["action"] == "create" for item in mounts),
        "applied",
    )


def read_mount_bindings(root: Path | str) -> list[dict]:
    """Read machine-local binding identities for diagnostics without following links."""
    base = Path(root).absolute() / ".ai-dlc/local/vault-mounts"
    try:
        with directory(base) as parent:
            names = sorted(os.listdir(parent))
    except FileNotFoundError:
        return []
    results = []
    for name in names:
        if not name.endswith(".json"):
            continue
        path = base / name
        body = json.loads(read_document(path))
        if (
            not isinstance(body, dict)
            or body.get("schema") != 1
            or any(
                not isinstance(body.get(key), str)
                for key in ("project_root", "vault_path", "project_name")
            )
        ):
            raise ValueError(f"Malformed mount binding: {path}")
        results.append({**body, "binding_path": str(path)})
    return results
