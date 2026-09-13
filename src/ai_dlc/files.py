"""Filesystem boundaries shared by renderers and knowledge storage."""

import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path

GIT_TIMEOUT_SECONDS = 30


class GitError(ValueError, RuntimeError):
    """A git invocation failed, timed out or could not start.

    The message carries the context the caller supplied and git's stderr. It derives from
    both ValueError and RuntimeError so every existing handler keeps catching it until a
    single application error base exists.
    """

    def __init__(self, message: str, *, stderr: str = "", returncode: int | None = None):
        super().__init__(message)
        self.stderr = stderr
        self.returncode = returncode


def run_git(
    root: Path | str | None,
    *args: str,
    environ: Mapping[str, str] | None = None,
    timeout: float = GIT_TIMEOUT_SECONDS,
    check: bool = True,
    text: bool = True,
    context: str = "Git operation failed",
) -> subprocess.CompletedProcess:
    """Run git with a bounded timeout and one error type.

    ``environ`` scopes both the executable lookup and the child environment so callers
    that resolve sources under a controlled PATH cannot pick up an ambient git.
    """
    if environ is None:
        command = "git"
    else:
        command = shutil.which("git", path=environ.get("PATH", ""))
        if command is None:
            raise GitError(f"{context}: git is not available on the configured PATH")
    try:
        result = subprocess.run(
            [command, *args],
            cwd=None if root is None else str(root),
            capture_output=True,
            text=text,
            timeout=timeout,
            check=False,
            env=None if environ is None else dict(environ),
        )
    except FileNotFoundError as error:
        raise GitError(f"{context}: git is not available") from error
    except subprocess.TimeoutExpired as error:
        raise GitError(f"{context}: timed out after {timeout:g}s") from error
    if check and result.returncode:
        stderr = result.stderr if text else result.stderr.decode(errors="replace")
        detail = stderr.strip() or f"git exited with status {result.returncode}"
        raise GitError(f"{context}: {detail}", stderr=stderr, returncode=result.returncode)
    return result


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


def atomic_write(path: Path, data: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    final_mode = (
        mode if mode is not None else path.stat().st_mode & 0o777 if path.exists() else 0o644
    )
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".ai-dlc-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, final_mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def atomic_create(path: Path, data: str, mode: int) -> bool:
    """Create a file from a private staging file without replacing an existing path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=".ai-dlc-")
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        try:
            os.link(name, path)
        except FileExistsError:
            return False
        return True
    finally:
        if os.path.exists(name):
            os.unlink(name)


def assets(name: str) -> Path:
    bundled = Path(__file__).parent / "assets" / name
    if bundled.is_dir():
        return bundled
    checkout = Path(__file__).resolve().parents[2]
    return checkout / ("templates" if name == "legacy" else name)
