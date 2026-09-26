"""Small, file-based knowledge operations; no vault plugins or sync assumptions."""

import hashlib
import os
import re
from contextlib import contextmanager
from pathlib import Path

from ai_dlc.files import atomic_write, inside
from ai_dlc.locking import project_write_lock


@contextmanager
def _note_lock(root: Path):
    if os.name == "nt":
        with project_write_lock(root):
            yield
        return
    import fcntl

    with (root / ".ai-dlc.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


class Knowledge:
    def __init__(self, vault_path: Path | str):
        self.root = Path(vault_path).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError("knowledge unavailable: existing vault path is required")

    def find(self, query: str, limit: int = 20) -> list[dict]:
        results = []
        for path in sorted(self.root.rglob("*.md")):
            if path.is_symlink() or not path.resolve().is_relative_to(self.root):
                continue
            body = path.read_text(errors="replace")
            if query.casefold() in (path.stem + "\n" + body).casefold():
                results.append({"path": str(path.relative_to(self.root)), "title": path.stem})
                if len(results) >= limit:
                    break
        return results

    def recall(self, terms: list[str], limit: int = 5) -> list[dict]:
        """Return only learning paths and a first content line, without writing."""
        limit = min(5, max(0, limit))
        terms = [term.casefold() for term in terms if term.strip()]
        if not limit or not terms:
            return []
        results = []
        for path in sorted((self.root / "learnings").rglob("*.md")):
            if path.is_symlink() or not path.resolve().is_relative_to(self.root):
                continue
            body = path.read_text(errors="replace")
            if not any(
                term in (str(path.relative_to(self.root)) + "\n" + body).casefold()
                for term in terms
            ):
                continue
            lines = [
                line.strip()
                for line in body.splitlines()
                if line.strip() and not line.strip().startswith("<!-- ai-dlc:")
            ]
            if lines[:1] == ["---"] and "---" in lines[1:]:
                lines = lines[lines.index("---", 1) + 1 :]
            results.append(
                {"path": str(path.relative_to(self.root)), "first_line": lines[0] if lines else ""}
            )
            if len(results) >= limit:
                break
        return results

    def note(self, path: str, body: str, operation_id: str) -> dict:
        target = inside(self.root, path)
        if target.exists() and f"<!-- ai-dlc:{operation_id}:" not in target.read_text():
            raise ValueError(f"note exists; use append: {path}")
        return self.append(path, body, operation_id)

    def append(self, path: str, body: str, operation_id: str) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", operation_id):
            raise ValueError("invalid note operation ID")
        target = inside(self.root, path)
        if target.suffix != ".md":
            raise ValueError("vault notes must use .md")
        marker = f"<!-- ai-dlc:{operation_id}:{hashlib.sha256(body.encode()).hexdigest()} -->"
        # Serialize local writers; atomic replacement preserves original notes on failure.
        with _note_lock(self.root):
            current = target.read_text() if target.exists() else ""
            if f"<!-- ai-dlc:{operation_id}:" in current:
                if marker not in current:
                    raise ValueError("note operation conflict: ID reused with different content")
                return {"path": path, "created": False, "url": target.as_uri()}
            addition = "\n" + marker + "\n" + body.rstrip() + "\n"
            if not current:
                addition = body.rstrip() + "\n" + marker + "\n"
            atomic_write(target, current + addition)
        return {"path": path, "created": True, "url": target.as_uri()}
