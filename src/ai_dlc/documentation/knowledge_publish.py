"""Capture dedupe for vault notes: the sha256 of a captured transcript or thread.

ADR 0003's reviewed one-way publish of a vault note is retired (KAN-430). The git
knowledge repository is canonical and ``ai-dlc knowledge render`` is the only writer
to the wiki (:mod:`ai_dlc.documentation.knowledge_render`).
"""

import hashlib
from pathlib import Path

from ai_dlc.documentation import knowledge_notes


def _vault(vault: Path | str) -> Path:
    root = Path(vault).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("knowledge unavailable: existing vault path is required")
    return root


def source_sha256(data: bytes) -> str:
    """Digest of captured text; line endings are normalized so a re-export matches."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def captured(vault: Path | str, sha256: str) -> list[str]:
    """Vault notes whose ``source.sha256`` is ``sha256``; read-only."""
    root = _vault(vault)
    found = []
    for path in sorted(root.rglob("*.md")):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            continue
        try:
            data, _raw, _body = knowledge_notes.split(
                knowledge_notes.strip_markers(path.read_text(errors="replace"))
            )
        except ValueError:
            continue
        source = (data or {}).get("source")
        if isinstance(source, dict) and source.get("sha256") == sha256:
            found.append(str(path.relative_to(root)))
    return found


def check_source(vault: Path | str, source: Path) -> dict:
    """``new`` or ``captured`` for a transcript or pasted thread saved to ``source``."""
    digest = source_sha256(source.read_bytes())
    notes = captured(vault, digest)
    return {"status": "captured" if notes else "new", "sha256": digest, "notes": notes}
