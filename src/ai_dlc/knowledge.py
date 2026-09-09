"""Small, file-based knowledge operations; no vault plugins or sync assumptions."""

import fcntl
import hashlib
import re
from pathlib import Path

from ai_dlc.files import atomic_write, inside


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
        with (self.root / ".ai-dlc.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            current = target.read_text() if target.exists() else ""
            if f"<!-- ai-dlc:{operation_id}:" in current:
                if marker not in current:
                    raise ValueError("note operation conflict: ID reused with different content")
                return {"path": path, "created": False, "url": target.as_uri()}
            atomic_write(target, current + "\n" + marker + "\n" + body.rstrip() + "\n")
        return {"path": path, "created": True, "url": target.as_uri()}
