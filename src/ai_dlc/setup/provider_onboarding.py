"""Shared connection-plan path boundaries and the common connection entry point."""

import os
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path


def _connection_plan_path(root: Path, requested: Path) -> Path:
    root = Path(root).resolve()
    local = root / ".ai-dlc/local"
    candidate = requested if requested.is_absolute() else root / requested
    candidate = Path(os.path.abspath(candidate))
    if not candidate.is_relative_to(local):
        raise ValueError("Connection plan must stay under .ai-dlc/local")

    relative = candidate.relative_to(root)
    current = root
    for index, part in enumerate(relative.parts):
        current /= part
        if current.is_symlink():
            raise ValueError("Connection plan must stay under .ai-dlc/local without symlinks")
        if current.exists() and index < len(relative.parts) - 1 and not current.is_dir():
            raise ValueError("Connection plan must stay under .ai-dlc/local")
    return candidate


@contextmanager
def _connection_plan_parent(root: Path, requested: Path, *, create: bool):
    """Open the plan parent without following any path component symlinks."""
    root = Path(root).resolve()
    path = _connection_plan_path(root, requested)
    parts = path.relative_to(root).parts
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            try:
                child = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=descriptor,
                )
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, mode=0o700, dir_fd=descriptor)
                child = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=descriptor,
                )
            except OSError:
                raise ValueError(
                    "Connection plan must stay under .ai-dlc/local without symlinks"
                ) from None
            os.close(descriptor)
            descriptor = child
        yield path, descriptor, parts[-1]
    finally:
        os.close(descriptor)


def connect_provider(root: Path, *, name: str, environ: Mapping[str, str], **options) -> dict:
    """Compatibility entry point for the common connection service."""
    from ai_dlc.setup.connections import connect_provider as connect

    return connect(root, name=name, environ=environ, **options)
