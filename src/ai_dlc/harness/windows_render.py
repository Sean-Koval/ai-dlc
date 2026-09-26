"""Native handle-backed render transactions; retained backups are never blindly deleted."""

from __future__ import annotations

import json
import os
import secrets
import tomllib
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from ai_dlc.config import resolve_layers

Snapshot = tuple[bytes, tuple[int, int, int]]


def _storage():
    from ai_dlc import _windows_storage

    return _windows_storage


@dataclass
class _Change:
    name: str
    before: Snapshot | None
    backup: Path | None = None
    stage: Path | None = None
    published: Snapshot | None = None


class WindowsRenderState:
    """Retain ancestor guards and bind every destination to its observed file identity."""

    def __init__(self, root: Path):
        self.root = Path(os.path.abspath(root))
        self.storage = _storage()
        self.stack = ExitStack()
        self.directories: set[Path] = set()
        self.missing: set[Path] = set()
        self.snapshots: dict[str, Snapshot | None] = {}

    def __enter__(self):
        self.stack.enter_context(self.storage.guarded_path(self.root))
        self.directories.add(self.root)
        return self

    def __exit__(self, *args):
        return self.stack.__exit__(*args)

    def _path(self, name: str) -> Path:
        self.storage.validate_relative(name)
        relative = PurePosixPath(name)
        if name != relative.as_posix():
            raise ValueError("invalid render destination path")
        return self.root.joinpath(*relative.parts)

    def _parent(self, name: str, *, create: bool = False) -> bool:
        path = self._path(name)
        parent = self.root
        for part in path.relative_to(self.root).parts[:-1]:
            parent = parent / part
            if parent in self.directories:
                continue
            exists = os.path.lexists(parent)
            if parent in self.missing and exists:
                raise ValueError("render destination ancestor changed after planning")
            if not exists and not create:
                self.missing.add(parent)
                return False
            self.stack.enter_context(self.storage.guarded_path(parent, create_parents=create))
            self.directories.add(parent)
            self.missing.discard(parent)
        return True

    def _snapshot(self, name: str) -> Snapshot | None:
        if not self._parent(name):
            return None
        try:
            return self.storage.safe_snapshot(self._path(name))
        except FileNotFoundError:
            return None

    def read(self, name: str) -> bytes | None:
        if name not in self.snapshots:
            self.snapshots[name] = self._snapshot(name)
        value = self.snapshots[name]
        return value[0] if value is not None else None

    def verify_files(self) -> None:
        for name, expected in self.snapshots.items():
            if self._snapshot(name) != expected:
                raise ValueError(f"render destination changed after planning: {name}")

    def _move(self, source: Path, target: Path, snapshot: Snapshot) -> None:
        self.storage.move_owned(source, target, expected=snapshot[0], expected_identity=snapshot[1])

    def _temporary(self, target: Path) -> Path:
        return target.with_name(f".ai-dlc-{secrets.token_hex(12)}")

    def _restore(self, change: _Change) -> None:
        target = self._path(change.name)
        if change.published is not None:
            try:
                current = self.storage.safe_snapshot(target)
            except FileNotFoundError:
                current = None
            if current != change.published:
                raise ValueError("render recovery preserved a late authored edit or deletion")
            retained = self._temporary(target)
            self._move(target, retained, change.published)
            change.stage = retained
            change.published = None
        if change.backup is not None and change.before is not None:
            try:
                self._move(change.backup, target, change.before)
            except FileNotFoundError:
                # An attempted capture may have failed before moving the original.
                if self.storage.safe_snapshot(target) != change.before:
                    raise
            change.backup = None

    def apply(self, planned: dict[str, bytes], removed: list[str], changed: list[str]) -> list[str]:
        names = list(dict.fromkeys([*removed, *changed]))
        for name in names:
            self.read(name)
        self.verify_files()
        changes: list[_Change] = []
        try:
            # All existing ancestors stay open until the complete transaction exits.
            for name in names:
                self._parent(name, create=True)
            self.verify_files()
            for name in names:
                target = self._path(name)
                change = _Change(name, self.snapshots[name])
                changes.append(change)
                staged: Snapshot | None = None
                if name not in removed:
                    change.stage = self._temporary(target)
                    if change.before is None:
                        staged = self.storage.create_owned(change.stage, planned[name])
                    else:
                        staged = self.storage.create_owned(
                            change.stage,
                            planned[name],
                            security_source=target,
                            security_identity=change.before[1],
                            security_expected=change.before[0],
                        )
                    if self.storage.safe_snapshot(change.stage) != staged:
                        raise ValueError("render stage changed before publication")
                if change.before is not None:
                    change.backup = self._temporary(target)
                    self._move(target, change.backup, change.before)
                if change.stage is not None and staged is not None:
                    self._move(change.stage, target, staged)
                    change.published = staged
                    change.stage = None
                if self._snapshot(name) != change.published:
                    raise ValueError(f"render destination changed during publication: {name}")
            for change in changes:
                if self._snapshot(change.name) != change.published:
                    raise ValueError(
                        f"render destination changed during publication: {change.name}"
                    )
                if (
                    change.backup is not None
                    and self.storage.safe_snapshot(change.backup) != change.before
                ):
                    raise ValueError("render backup changed during publication")
        except BaseException as original:
            for change in reversed(changes):
                try:
                    self._restore(change)
                except (OSError, ValueError) as recovery:
                    original.add_note(f"Render recovery preserved {change.name}: {recovery}")
                for retained in (change.backup, change.stage):
                    if retained is not None:
                        original.add_note(
                            "Render recovery retained "
                            f"{retained.relative_to(self.root).as_posix()}; inspect before removal."
                        )
            raise
        return sorted(
            change.backup.relative_to(self.root).as_posix()
            for change in changes
            if change.backup is not None
        )


def render_windows(
    root: Path, apply: bool = False, client: str | None = None, target: str = "local"
) -> dict[str, Any]:
    from ai_dlc.harness.agents import _render_agents, _selected_bundle_ids
    from ai_dlc.locking import project_write_lock

    # Native guards receive lexical paths so junctions cannot disappear through resolve().
    with project_write_lock(root), WindowsRenderState(root) as state:
        raw = state.read("ai-dlc.toml")
        config = resolve_layers([("project", tomllib.loads((raw or b"").decode()))]).values
        ownership = json.loads(state.read(".ai-dlc/agent-ownership.json") or b"{}")
        if _selected_bundle_ids(config) or ownership.get("bundle_files"):
            raise ValueError("vendored workflow bundles are not supported on native Windows")
        result = _render_agents(state.root, apply=apply, client=client, target=target, state=state)
        if not apply:
            state.verify_files()
        return result
