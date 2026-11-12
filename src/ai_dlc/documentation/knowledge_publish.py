"""Capture dedupe and the reviewed one-way publish of a vault note (ADR 0003).

ai-dlc never calls Confluence here. The agent reads and writes the page through the
client's approved Atlassian connection; these functions are the deterministic guard
around that call. ``plan`` refuses before anything leaves the machine, and ``record``
writes the page binding back into the note afterwards.

Each vault declares its own target in ``<vault>/.ai-dlc/publish.toml``::

    origin = "work"                 # work | home: the vault this is
    site = "example.atlassian.net"  # the only site this vault may publish to
    space = "ENG"
    parent = "123456"               # optional parent page id

There is no default: a vault without the file cannot publish, and a note whose
``origin`` or ``publish.site`` differs from the vault's is refused.
"""

import hashlib
import re
import tomllib
from pathlib import Path

from ai_dlc.documentation import knowledge_notes
from ai_dlc.documentation.knowledge import _note_lock
from ai_dlc.files import atomic_write, inside

TARGET_FILE = ".ai-dlc/publish.toml"
_MARKERS = re.compile(r"\A((?:<!-- ai-dlc:[^\n]*-->\n)*)")
_TITLE = re.compile(r"^# +(.+?)\s*$", re.MULTILINE)


def _vault(vault: Path | str) -> Path:
    root = Path(vault).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("knowledge unavailable: existing vault path is required")
    return root


def _refused(reason: str, **extra) -> dict:
    return {"status": "refused", "reason": reason, **extra}


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


def vault_target(vault: Path | str) -> dict:
    """The vault's declared origin and publish target; raises when undeclared."""
    path = _vault(vault) / TARGET_FILE
    if not path.is_file():
        raise ValueError(f"no publish target: create {TARGET_FILE} in this vault")
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"{TARGET_FILE} is not valid TOML: {exc}") from exc
    if data.get("origin") not in {"work", "home"}:
        raise ValueError(f"{TARGET_FILE}: origin must be work or home")
    for key in ("site", "space"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{TARGET_FILE}: {key} is required")
    if not re.fullmatch(knowledge_notes.SITE_PATTERN, data["site"]):
        raise ValueError(f"{TARGET_FILE}: site must be a bare host name")
    parent = data.get("parent")
    if parent is not None and (not isinstance(parent, str) or not parent.strip()):
        raise ValueError(f"{TARGET_FILE}: parent must be a page id")
    return {
        "origin": data["origin"],
        "site": data["site"],
        "space": data["space"],
        "parent": parent,
    }


def _read(root: Path, note: str) -> tuple[Path, str, dict, str]:
    path = inside(root, note)
    if path.suffix != ".md" or not path.is_file():
        raise ValueError(f"note not found: {note}")
    text = path.read_text()
    prefix = _MARKERS.match(text)
    markers = prefix.group(1) if prefix else ""
    data, _raw, body = knowledge_notes.split(text[len(markers) :])
    if data is None:
        raise ValueError("note has no knowledge-note frontmatter")
    return path, markers, data, body


def _guard(root: Path, data: dict) -> tuple[dict | None, dict]:
    """``(refusal, target)``; the refusal is ``None`` when the note may leave."""
    problems = knowledge_notes.errors(data)
    if problems:
        return _refused("invalid frontmatter", errors=problems), {}
    try:
        target = vault_target(root)
    except ValueError as exc:
        return _refused(str(exc)), {}
    if data["kind"] == "daily":
        return _refused("daily notes stay in the vault; publish a meeting or note"), target
    if data.get("origin") != target["origin"]:
        return _refused(
            f"origin mismatch: note is {data.get('origin')}, vault is {target['origin']}"
        ), target
    bound = data.get("publish") or {}
    if bound.get("site", target["site"]) != target["site"]:
        return _refused(
            f"site mismatch: note names {bound['site']}, vault publishes to {target['site']}"
        ), target
    return None, target


def _body(markdown: str) -> str:
    return re.sub(r"\n?<!-- ai-dlc:[^\n]*-->\n?", "\n", markdown).strip() + "\n"


def plan(vault: Path | str, note: str, remote_version: int | None = None) -> dict:
    """The exact page payload to show for confirmation, or a refusal. Writes nothing.

    For a note already bound to a page, ``remote_version`` is the page's current
    version as read from Confluence; any other value than the recorded one means the
    page changed since the last publish, which is refused rather than overwritten.
    """
    root = _vault(vault)
    _path, _markers, data, markdown = _read(root, note)
    refusal, target = _guard(root, data)
    if refusal:
        return {**refusal, "note": note}
    bound = data.get("publish") or {}
    page_id, version = bound.get("page_id"), bound.get("version")
    if page_id is not None:
        if remote_version is None:
            return _refused("read the page's current version first", note=note, page_id=page_id)
        if remote_version != version:
            return _refused(
                "version conflict: the page changed since it was published",
                note=note,
                page_id=page_id,
                recorded_version=version,
                remote_version=remote_version,
            )
    body = _body(markdown)
    title = _TITLE.search(body)
    return {
        "status": "ready",
        "action": "update" if page_id else "create",
        "note": note,
        "site": target["site"],
        "space": bound.get("space", target["space"]),
        "parent": bound.get("parent", target["parent"]),
        "page_id": page_id,
        "expected_version": version,
        "title": title.group(1) if title else Path(note).stem,
        "body": body,
    }


def record(vault: Path | str, note: str, page_id: str, version: int) -> dict:
    """Write the published page's id and version into the note's ``publish`` block."""
    if not re.fullmatch(r"[0-9]+", page_id) or version < 1:
        raise ValueError("page_id must be numeric and version at least 1")
    root = _vault(vault)
    with _note_lock(root):
        path, markers, data, body = _read(root, note)
        refusal, target = _guard(root, data)
        if refusal:
            return {**refusal, "note": note}
        bound = dict(data.get("publish") or {})
        if bound.get("page_id") not in {None, page_id}:
            return _refused(
                "page binding conflict: the note is bound to another page",
                note=note,
                page_id=bound["page_id"],
            )
        if bound.get("page_id") == page_id and bound.get("version") == version:
            return {"status": "unchanged", "note": note, "page_id": page_id, "version": version}
        if bound.get("version") is not None and version <= bound["version"]:
            return _refused(
                "version conflict: the recorded version is newer",
                note=note,
                recorded_version=bound["version"],
            )
        bound.setdefault("site", target["site"])
        bound.setdefault("space", target["space"])
        if target["parent"] is not None:
            bound.setdefault("parent", target["parent"])
        bound.update(page_id=page_id, version=version)
        updated = {**data, "publish": bound}
        problems = knowledge_notes.errors(updated)
        if problems:
            return _refused("invalid frontmatter", note=note, errors=problems)
        atomic_write(path, markers + "---\n" + knowledge_notes.dump(updated) + "---\n" + body)
    return {"status": "recorded", "note": note, "page_id": page_id, "version": version}
