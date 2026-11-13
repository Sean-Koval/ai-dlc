"""Small, file-based knowledge operations; no vault plugins or sync assumptions."""

import hashlib
import os
import re
from contextlib import contextmanager
from datetime import UTC, date, datetime
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


def _note_metadata(body: str) -> dict | None:
    """Record or knowledge-note frontmatter (marker lines skipped); ``None`` for older notes."""
    from ai_dlc.documentation.knowledge_notes import split, strip_markers

    try:
        data, _raw, _rest = split(strip_markers(body))
    except ValueError:
        return None
    return data if data and ("kind" in data or "type" in data) else None


def _as_date(value) -> date | None:
    """A date, or a datetime's UTC date (``stale_after`` carries a timezone)."""
    if isinstance(value, str) and "T" in value:
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


class Knowledge:
    def __init__(self, vault_path: Path | str):
        self.root = Path(vault_path).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError("knowledge unavailable: existing vault path is required")

    def get(self, id: str) -> dict:
        """The knowledge record in this vault whose id or alias is ``id``."""
        from ai_dlc.documentation import record_index

        return record_index.get(self.root, id)

    def search(
        self,
        type: str | None = None,
        scope: str | None = None,
        labels: list[str] | None = None,
        status: str | None = None,
        text: str | None = None,
    ) -> dict:
        """Knowledge records in this vault matching every given filter."""
        from ai_dlc.documentation import record_index

        return record_index.search(self.root, type, scope, labels or (), status, text)

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

    def recall(self, terms: list[str], limit: int = 5, today: date | None = None) -> list[dict]:
        """Return learning paths, a first content line and provenance, without writing.

        Notes with record or knowledge-note frontmatter whose ``valid_to`` has passed are
        skipped; ``stale`` marks a passed ``stale_after`` (a record) or ``review_by`` (a
        note, read until KAN-453). Notes without frontmatter recall as before.
        """
        today = today or datetime.now(UTC).date()
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
            meta = _note_metadata(body)
            valid_to = _as_date(meta.get("valid_to")) if meta else None
            if valid_to and valid_to < today:
                continue
            if lines[:1] == ["---"] and "---" in lines[1:]:
                lines = lines[lines.index("---", 1) + 1 :]
            found: dict[str, object] = {
                "path": str(path.relative_to(self.root)),
                "first_line": lines[0] if lines else "",
            }
            if meta and "kind" in meta:
                review_by = _as_date(meta.get("review_by"))
                found.update(
                    kind=meta.get("kind"),
                    author=meta.get("author"),
                    review_by=review_by.isoformat() if review_by else None,
                    stale=bool(review_by and review_by < today),
                )
            elif meta:
                stale_after = _as_date(meta.get("stale_after"))
                found.update(
                    type=meta.get("type"),
                    author=meta.get("author"),
                    stale_after=stale_after.isoformat() if stale_after else None,
                    stale=bool(stale_after and stale_after < today),
                )
            results.append(found)
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
