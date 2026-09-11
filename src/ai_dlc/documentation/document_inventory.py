"""Read-only Git-scoped Markdown discovery without following filesystem links."""

import os
import stat
from pathlib import Path

from ai_dlc.documentation.document_files import directory
from ai_dlc.documentation.document_impact import _git


def inventory_documents(root: Path | str) -> dict:
    """List paths, not bodies; Git ignores prune discovery but never hide tracked files."""
    root = Path(root).absolute()
    documents: set[str] = set()
    omitted: dict[str, str] = {}
    with directory(root) as root_fd:
        candidates = {
            os.fsdecode(p)
            for p in _git(
                root, "ls-files", "--cached", "--others", "--exclude-standard", "-z"
            ).split(b"\0")
            if p
        }
        ignored = {
            os.fsdecode(p)
            for p in _git(
                root, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z"
            ).split(b"\0")
            if p
        }
        excluded = {p: "Git ignored" for p in ignored}
        excluded[".git"] = "Git metadata"
        visited: set[str] = set()

        def walk(fd: int, prefix: str) -> None:
            try:
                with os.scandir(fd) as scan:
                    names = sorted(entry.name for entry in scan)
            except OSError:
                omitted[prefix.rstrip("/") or "."] = "inaccessible directory"
                return
            if prefix and ".git" in names:
                excluded[prefix.rstrip("/")] = "nested Git repository"
                return
            for name in names:
                relative = prefix + name
                if name == ".git":
                    excluded[relative] = "Git metadata"
                    continue
                if relative in ignored or relative + "/" in ignored:
                    continue
                try:
                    info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                    if stat.S_ISLNK(info.st_mode):
                        omitted[relative] = "symlink not followed"
                    elif stat.S_ISDIR(info.st_mode):
                        child = os.open(
                            name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
                        )
                        try:
                            walk(child, relative + "/")
                        finally:
                            os.close(child)
                    elif relative in candidates and Path(name).suffix.lower() == ".md":
                        visited.add(relative)
                        if stat.S_ISREG(info.st_mode):
                            documents.add(relative)
                        else:
                            omitted[relative] = "not a regular file"
                except OSError:
                    omitted[relative] = "inaccessible or changed path"

        walk(root_fd, "")
        for relative in sorted(candidates):
            if Path(relative).suffix.lower() == ".md" and relative not in documents | visited:
                omitted.setdefault(relative, "missing or inaccessible path")
    return {
        "schema": 1,
        "documents": sorted(documents),
        "excluded": [{"path": p, "reason": excluded[p]} for p in sorted(excluded)],
        "omitted": [{"path": p, "reason": omitted[p]} for p in sorted(omitted)],
        "constraints": [
            "Tracked and nonignored .md paths only; no document bodies read.",
            "Symlinks are not followed. Excluded and unavailable content remains unreviewed.",
        ],
    }
