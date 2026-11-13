"""Read knowledge records from a directory tree: get, search and duplicate checks.

Format logic only; the ``knowledge`` providers (git repository, Obsidian vault) call it
on their own trees. Headers are validated by
:class:`~ai_dlc.documentation.knowledge_records.KnowledgeRecord`. A search reads
frontmatter only and opens a body only when ``text`` is given.

The duplicate check carries forward the capture dedupe of ADR 0003
(:func:`ai_dlc.documentation.knowledge_publish.source_sha256`): a record whose
``sources`` hash is ``sha256:<digest>`` was captured from that text.
"""

import tomllib
from collections.abc import Iterable, Iterator
from pathlib import Path

from ai_dlc.documentation import knowledge_records
from ai_dlc.documentation.knowledge_notes import split
from ai_dlc.documentation.knowledge_publish import source_sha256
from ai_dlc.documentation.knowledge_records import KnowledgeRecord

PIN_FILE = "knowledge.toml"
_DELIMITER = "---"


def _files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            continue
        yield path


def read_header(path: Path) -> dict | None:
    """The frontmatter mapping of ``path``, reading no line past its closing delimiter."""
    lines: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        if handle.readline().rstrip("\r\n") != _DELIMITER:
            return None
        for line in handle:
            if line.rstrip("\r\n") == _DELIMITER:
                break
            lines.append(line)
        else:
            return None
    data, _raw, _body = split(_DELIMITER + "\n" + "".join(lines) + _DELIMITER + "\n")
    return data


def _is_record(data: dict | None) -> bool:
    # Legacy knowledge notes carry ``kind``; plain pages carry no ``type``.
    return bool(data) and "type" in data and "kind" not in data  # type: ignore[operator]


def scan(root: Path) -> tuple[list[dict], list[dict]]:
    """``(records, invalid)``: valid record headers with paths, and refused files."""
    records, invalid = [], []
    for path in _files(root):
        relative = path.relative_to(root).as_posix()
        try:
            data = read_header(path)
        except ValueError as exc:
            invalid.append({"path": relative, "errors": [str(exc)]})
            continue
        if not _is_record(data):
            continue
        problems = knowledge_records.errors(data or {})
        if problems:
            invalid.append({"path": relative, "errors": problems})
            continue
        record = KnowledgeRecord.model_validate(data)
        records.append({"path": relative, "record": record})
    return records, invalid


def _item(entry: dict) -> dict:
    record: KnowledgeRecord = entry["record"]
    return {"id": record.id, "path": entry["path"], "header": record.model_dump(mode="json")}


def get(root: Path, record_id: str) -> dict:
    """The record whose id or alias is ``record_id``, with its body; raises when absent."""
    records, _invalid = scan(root)
    matches = [
        entry
        for entry in records
        if record_id in (entry["record"].id, *(entry["record"].aliases or ()))
    ]
    if not matches:
        raise LookupError(f"no knowledge record has id or alias {record_id}")
    if len(matches) > 1:
        paths = ", ".join(entry["path"] for entry in matches)
        raise ValueError(f"id or alias {record_id} is ambiguous: {paths}")
    entry = matches[0]
    _data, _raw, body = split((root / entry["path"]).read_text(errors="replace"))
    return {**_item(entry), "body": body}


def search(
    root: Path,
    type: str | None = None,
    scope: str | None = None,
    labels: Iterable[str] = (),
    status: str | None = None,
    text: str | None = None,
) -> dict:
    """Records matching every given filter; ``labels`` match ``tags`` or ``label``."""
    wanted = set(labels)
    needle = text.casefold() if text else None
    records, invalid = scan(root)
    found = []
    for entry in records:
        record: KnowledgeRecord = entry["record"]
        if type and record.type != type:
            continue
        if scope and record.scope != scope:
            continue
        if status and record.status != status:
            continue
        if wanted - {*(record.tags or ()), *([record.label] if record.label else [])}:
            continue
        if needle is not None:
            content = (root / entry["path"]).read_text(errors="replace")
            if needle not in content.casefold():
                continue
        found.append(_item(entry))
    return {"items": found, "invalid": invalid}


def hashes(record: KnowledgeRecord) -> set[str]:
    return {source.hash for source in record.sources if source.hash}


def captured(root: Path, digest: str) -> list[str]:
    """Paths of records with a ``sha256:<digest>`` source hash; read-only."""
    target = f"sha256:{digest}"
    records, _invalid = scan(root)
    return [entry["path"] for entry in records if target in hashes(entry["record"])]


def check_source(root: Path, source: Path) -> dict:
    """``new`` or ``captured`` for a transcript or pasted thread saved to ``source``."""
    digest = source_sha256(source.read_bytes())
    found = captured(root, digest)
    return {"status": "captured" if found else "new", "sha256": digest, "records": found}


def duplicates(existing: list[dict], proposed: list[dict]) -> list[str]:
    """Why each proposed record duplicates another, by path.

    A Source with a hash already on another Source was captured before; any two
    records of one type sharing a hash and a title are duplicates (KAN-423). A
    duplicate becomes a ``derived_from`` link, not a new record.
    """
    found = []
    seen = [entry for entry in existing if entry["path"] not in {p["path"] for p in proposed}]
    for entry in proposed:
        record: KnowledgeRecord = entry["record"]
        for other in seen:
            prior: KnowledgeRecord = other["record"]
            shared = hashes(record) & hashes(prior)
            if not shared or record.type != prior.type:
                continue
            if record.type == "source" or (record.title and record.title == prior.title):
                found.append(
                    f"{entry['path']}: duplicates {other['path']} ({min(shared)}); "
                    "link it with derived_from instead"
                )
        seen.append(entry)
    return found


def pin(root: Path) -> list[str]:
    """Problems with the tree's ``knowledge.toml`` format pin."""
    path = root / PIN_FILE
    if not path.is_file():
        return [f"{PIN_FILE}: missing; pin the record format with [format] version"]
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        return [f"{PIN_FILE}: not valid TOML: {exc}"]
    return [f"{PIN_FILE}: {problem}" for problem in knowledge_records.pin_errors(data)]
