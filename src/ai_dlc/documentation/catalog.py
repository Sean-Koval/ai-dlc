"""The documentation catalog: ``docs/catalog.toml`` plus one fragment per new document.

Two pull requests that each add a page used to conflict on ``docs/catalog.toml``. A
page added now brings its own ``docs/catalog.d/<id>.toml`` (KAN-486), which no other
pull request touches. Every file has the same shape: ``schema = 1`` and a
``[[documents]]`` array. Entries are read in order: ``catalog.toml`` first, then the
fragments sorted by name. Duplicate ids and paths across files are the callers' to
report, as they were within one file.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from ai_dlc.documentation.document_files import read_document
from ai_dlc.files import inside

CATALOG = "docs/catalog.toml"
FRAGMENTS = "docs/catalog.d"


def catalog_files(root: Path) -> list[str]:
    """Repository-relative catalog files: the catalog, then its fragments by name."""
    directory = inside(root, FRAGMENTS)
    if directory.is_symlink():
        raise ValueError(f"{FRAGMENTS} cannot be a symlink")
    names = [p.name for p in directory.glob("*.toml")] if directory.is_dir() else []
    # Editors leave hidden lock and backup files (``.#x.toml``) beside the one being edited.
    fragments = sorted(name for name in names if not name.startswith("."))
    return [CATALOG, *(f"{FRAGMENTS}/{name}" for name in fragments)]


def load_catalog(root: Path) -> list[dict]:
    """Every catalog entry. A missing ``docs/catalog.toml`` raises ``FileNotFoundError``."""
    entries: list[dict] = []
    for relative in catalog_files(root):
        raw = tomllib.loads(read_document(inside(root, relative)).decode())
        documents = raw.get("documents", [])
        if (
            raw.get("schema") != 1
            or not isinstance(documents, list)
            or not all(isinstance(e, dict) for e in documents)
        ):
            raise ValueError(f"{relative}: expected schema = 1 and a documents array")
        entries.extend(documents)
    return entries
