"""Resolve, lock and select team content without implicitly activating updates."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_dlc.environment.enrollment import EnrollmentLock, EnrollmentPaths, read_lock
from ai_dlc.environment.profile_source import (
    resolve_git_source,
    source_lock_value,
    verify_cached_profile,
)
from ai_dlc.environment.source_content import SourceItem, content_digest, read_tree, source_items
from ai_dlc.environment.source_schema import SourceLock, subscriptions
from ai_dlc.files import run_git


@dataclass
class SelectedSources:
    items: list[tuple[str, SourceItem]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    enrolled: bool = False


def cache_root(paths: EnrollmentPaths, source: SourceLock) -> Path:
    return (
        paths.cache_root
        / "team-sources"
        / source.id
        / source.resolved_commit
        / source.content_sha256
    )


def _verify(source: SourceLock, paths: EnrollmentPaths) -> dict[str, str]:
    files = read_tree(cache_root(paths, source), cached=True)
    if content_digest(files) != source.content_sha256:
        raise ValueError(f"team source {source.id} cache digest mismatch")
    source_items(files, source)
    return files


def resolve_sources(
    config: dict[str, Any], paths: EnrollmentPaths, environ: Mapping[str, str]
) -> list[SourceLock]:
    result: list[SourceLock] = []
    for source in subscriptions(config.get("sources", [])):
        paths.cache_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".team-source-", dir=paths.cache_root) as temporary:
            repository = Path(temporary) / "repository"
            repository.mkdir()
            revision, _ = resolve_git_source(repository, source.git, source.ref, environ=environ)
            files = read_tree(repository)
            source_items(files, source)
            lock = SourceLock(
                **{**source.model_dump(), "git": source_lock_value(source.git)},
                resolved_commit=revision,
                content_sha256=content_digest(files),
            )
            destination = cache_root(paths, lock)
            if destination.exists() or destination.is_symlink():
                _verify(lock, paths)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                staged = Path(tempfile.mkdtemp(prefix=".source-", dir=destination.parent))
                try:
                    for name, body in files.items():
                        path = staged / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(body)
                        path.chmod(0o600)
                    if content_digest(read_tree(staged, cached=True)) != lock.content_sha256:
                        raise ValueError("team source cache changed while staging")
                    try:
                        os.rename(staged, destination)
                    except OSError:
                        if not destination.exists():
                            raise
                        _verify(lock, paths)
                finally:
                    if staged.exists():
                        shutil.rmtree(staged)
            result.append(lock)
    return result


def load_sources(
    lock: EnrollmentLock, paths: EnrollmentPaths, roles: list[str] | None = None
) -> SelectedSources:
    profile = tomllib.loads(verify_cached_profile(lock, paths).read_text())
    declared = subscriptions(profile.get("sources", []))
    expected = [{**entry.model_dump(), "git": source_lock_value(entry.git)} for entry in declared]
    actual = [
        entry.model_dump(exclude={"resolved_commit", "content_sha256"}) for entry in lock.sources
    ]
    if actual != expected:
        raise ValueError(
            "team source lock does not match enrolled profile; run ai-dlc machine sync"
        )
    selected = SelectedSources(enrolled=bool(lock.sources))
    for source in lock.sources:
        items, notes = source_items(_verify(source, paths), source)
        selected.notes.extend(f"team source {source.id}: {note}" for note in notes)
        active_roles = set(source.roles) | set(roles or [])
        for item in items:
            if (
                not (item.roles or item.tags)
                or active_roles.intersection(item.roles)
                or set(source.tags).intersection(item.tags)
            ):
                selected.items.append((source.id, item))
    return selected


def enrolled_sources(*, paths: EnrollmentPaths | None = None) -> SelectedSources:
    paths = paths or EnrollmentPaths.from_environment()
    lock = read_lock(paths)
    if lock is None:
        return SelectedSources()
    # Validate the machine layer independently; do not mix unrelated personal settings
    # into the project-owned render configuration.
    from ai_dlc.config import resolve_layers

    machine = paths.machine_file(lock.machine_id)
    if not machine.is_file():
        raise ValueError("active machine binding is missing")
    config = resolve_layers([("machine", tomllib.loads(machine.read_text()))]).values
    return load_sources(lock, paths, config.get("team_roles", []))


def source_update_notices(
    *, paths: EnrollmentPaths | None = None, environ: Mapping[str, str] | None = None
) -> list[str]:
    """Read advertised refs within a shared short deadline; never fetch or activate."""
    paths = paths or EnrollmentPaths.from_environment(environ=environ)
    result: list[str] = []
    deadline = time.monotonic() + 3
    try:
        lock = read_lock(paths)
        if lock is None:
            return []
        for source in lock.sources:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            # Revalidate the remote syntax before invoking Git, including edited locks.
            remote = source_lock_value(source.git)
            ref = source.ref
            refs = [ref] if ref.startswith("refs/") else [f"refs/heads/{ref}", f"refs/tags/{ref}"]
            output = run_git(
                None,
                "ls-remote",
                "--",
                remote,
                *refs,
                *(f"{ref}^{{}}" for ref in refs),
                environ=environ,
                timeout=remaining,
                context="Team source ref inspection failed",
            ).stdout
            advertised = dict(
                line.split("\t", 1)[::-1] for line in output.splitlines() if "\t" in line
            )
            matching = [ref for ref in refs if ref in advertised]
            if len(matching) == 1:
                ref = matching[0]
                revision = advertised.get(f"{ref}^{{}}", advertised[ref])
                if revision != source.resolved_commit:
                    result.append(
                        f"team source {source.id} has a newer revision; run `ai-dlc machine sync`"
                    )
    except (OSError, ValueError, RuntimeError):
        # The network is advisory: offline sessions remain usable without diagnostics
        # from external commands or credential-bearing transport errors.
        return result
    return result
