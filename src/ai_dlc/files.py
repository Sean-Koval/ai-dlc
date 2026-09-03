"""Filesystem boundaries shared by renderers and knowledge storage."""

import os
import tempfile
from pathlib import Path


def inside(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"path escapes root/vault: {relative}")
    candidate = root / path
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"path escapes root/vault: {relative}")
    for parent in [candidate, *candidate.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError(f"symlink not managed in root/vault: {relative}")
    return candidate


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".ai-dlc-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def assets(name: str) -> Path:
    bundled = Path(__file__).parent / "assets" / name
    if bundled.is_dir():
        return bundled
    checkout = Path(__file__).resolve().parents[2]
    return checkout / ("templates" if name == "legacy" else name)
