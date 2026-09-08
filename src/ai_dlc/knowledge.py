"""Small, file-based knowledge operations; no vault plugins or sync assumptions."""

import fcntl
import hashlib
import re
import os
from pathlib import Path

from ai_dlc.files import atomic_write, inside


class Knowledge:
    def __init__(self, vault_path: Path | str):
        self.root = Path(vault_path).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError("knowledge unavailable: existing vault path is required")

    def find(self, query: str, limit: int = 20) -> list[dict]:
        results: list[dict] = []
        seen_paths: set[str] = set()

        def search_file(file_path: Path, relative_display: str):
            if relative_display in seen_paths:
                return
            seen_paths.add(relative_display)
            try:
                body = file_path.read_text(errors="replace")
            except OSError:
                return
            if query.casefold() in (file_path.stem + "\n" + body).casefold():
                results.append({"path": relative_display, "title": file_path.stem})

        for path in sorted(self.root.rglob("*.md")):
            if path.is_symlink() or not path.resolve().is_relative_to(self.root):
                continue
            search_file(path, str(path.relative_to(self.root)))
            if len(results) >= limit:
                return results

        projects_dir = self.root / "Projects"
        if projects_dir.is_dir():
            for entry in sorted(projects_dir.iterdir()):
                if entry.is_symlink() and entry.is_dir():
                    try:
                        target = entry.resolve()
                    except OSError:
                        continue
                    if not target.is_dir() or target == self.root or self.root.is_relative_to(target):
                        continue
                    for root_dir, _, filenames in os.walk(target, followlinks=False):
                        root_path = Path(root_dir)
                        for fname in sorted(filenames):
                            if fname.endswith(".md"):
                                md_file = root_path / fname
                                if md_file.is_file() and not md_file.is_symlink():
                                    try:
                                        rel_within_project = md_file.relative_to(target)
                                        virtual_rel = str(Path("Projects") / entry.name / rel_within_project)
                                        search_file(md_file, virtual_rel)
                                        if len(results) >= limit:
                                            return results
                                    except ValueError:
                                        continue
        return results

    def note(self, path: str, body: str, operation_id: str) -> dict:
        target = inside(self.root, path, allow_project_symlinks=True)
        if target.exists() and f"<!-- ai-dlc:{operation_id}:" not in target.read_text():
            raise ValueError(f"note exists; use append: {path}")
        return self.append(path, body, operation_id)

    def append(self, path: str, body: str, operation_id: str) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", operation_id):
            raise ValueError("invalid note operation ID")
        target = inside(self.root, path, allow_project_symlinks=True)
        if target.suffix != ".md":
            raise ValueError("vault notes must use .md")
        marker = f"<!-- ai-dlc:{operation_id}:{hashlib.sha256(body.encode()).hexdigest()} -->"
        # Serialize local writers; atomic replacement preserves original notes on failure.
        with (self.root / ".ai-dlc.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            current = target.read_text() if target.exists() else ""
            if f"<!-- ai-dlc:{operation_id}:" in current:
                if marker not in current:
                    raise ValueError("note operation conflict: ID reused with different content")
                return {"path": path, "created": False, "url": target.as_uri()}
            atomic_write(target, current + "\n" + marker + "\n" + body.rstrip() + "\n")
        return {"path": path, "created": True, "url": target.as_uri()}
