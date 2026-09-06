"""Validation for portable, non-executable Markdown workflow bundles."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import unicodedata
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

_MANIFEST_FIELDS = {"schema", "id", "skills", "templates", "files"}
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_MAX_MANIFEST_BYTES = 1024 * 1024
_MAX_PAYLOAD_FILES = 1024
_MAX_PATH_SEGMENTS = 16
_MAX_PAYLOAD_BYTES = 2 * 1024 * 1024
_MAX_TOTAL_PAYLOAD_BYTES = 10 * 1024 * 1024
_MAX_DESCRIPTION_CHARACTERS = 1024


def _regular_file_bytes(root: Path, relative: PurePosixPath, *, maximum: int) -> bytes:
    try:
        root_metadata = root.lstat()
    except FileNotFoundError as error:
        raise ValueError("bundle root must be an existing directory") from error
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        raise ValueError("bundle root must be an existing directory, not a symlink")

    current = root
    for index, part in enumerate(relative.parts):
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError as error:
            raise ValueError(f"bundle path is missing: {relative.as_posix()}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"bundle path cannot contain a symlink: {relative.as_posix()}")
        if index < len(relative.parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"bundle path component must be a directory: {relative.as_posix()}")

    metadata = current.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"bundle path must be a regular file: {relative.as_posix()}")
    if metadata.st_size > maximum:
        limit = "1 MiB" if maximum == _MAX_MANIFEST_BYTES else "2 MiB"
        raise ValueError(f"bundle path must be at most {limit}: {relative.as_posix()}")
    return current.read_bytes()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"bundle.json contains duplicate JSON key: {key}")
        result[key] = value
    return result


def load_bundle_manifest(root: Path) -> dict[str, Any]:
    """Load a bounded UTF-8 ``bundle.json`` without accepting duplicate keys."""
    content = _regular_file_bytes(
        Path(root), PurePosixPath("bundle.json"), maximum=_MAX_MANIFEST_BYTES
    )
    try:
        document = json.loads(content.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("bundle.json must be valid UTF-8 JSON") from error
    if type(document) is not dict:
        raise ValueError("bundle.json must contain a JSON object")
    return document


def _slug(value: Any, *, field: str) -> str:
    if type(value) is not str or _SLUG.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase ASCII slug")
    return value


def _payload_path(value: Any, *, field: str) -> str:
    if type(value) is not str or not value or _SAFE_PATH.fullmatch(value) is None:
        raise ValueError(f"{field} must be a relative normalized safe ASCII path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or PureWindowsPath(value).drive
        or value != path.as_posix()
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError(f"{field} must be a relative normalized safe ASCII path")
    if len(path.parts) > _MAX_PATH_SEGMENTS:
        raise ValueError(f"{field} must contain at most 16 path segments")
    return path.as_posix()


def _export_map(value: Any, *, field: str) -> dict[str, str]:
    if type(value) is not dict:
        raise ValueError(f"{field} must be an object")
    exports: dict[str, str] = {}
    for raw_name, raw_path in value.items():
        name = _slug(raw_name, field=f"{field} name")
        path = _payload_path(raw_path, field=f"{field}.{name}")
        if field == "skills" and not path.endswith("SKILL.md"):
            raise ValueError("skills paths must end in SKILL.md")
        if field == "templates" and not path.endswith(".md"):
            raise ValueError("templates paths must end in .md")
        exports[name] = path
    return dict(sorted(exports.items()))


def _file_map(value: Any) -> dict[str, str]:
    if type(value) is not dict:
        raise ValueError("files must be an object")
    if len(value) > _MAX_PAYLOAD_FILES:
        raise ValueError("bundle must contain at most 1024 payload files")
    files: dict[str, str] = {}
    for raw_path, raw_digest in value.items():
        path = _payload_path(raw_path, field="files path")
        if type(raw_digest) is not str or _SHA256.fullmatch(raw_digest) is None:
            raise ValueError(f"files.{path} must be a 64-character lowercase SHA-256 digest")
        files[path] = raw_digest
    return dict(sorted(files.items()))


def _expected_tree(payload_paths: set[str]) -> set[str]:
    expected = {"bundle.json", *payload_paths}
    for value in payload_paths:
        path = PurePosixPath(value)
        expected.update(
            PurePosixPath(*path.parts[:index]).as_posix() for index in range(1, len(path.parts))
        )
    return expected


def _checkout_tree(root: Path) -> set[str]:
    try:
        metadata = root.lstat()
    except FileNotFoundError as error:
        raise ValueError("bundle root must be an existing directory") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("bundle root must be an existing directory, not a symlink")

    entries: set[str] = set()
    pending = [(root, PurePosixPath())]
    while pending:
        directory, relative_directory = pending.pop()
        with os.scandir(directory) as children:
            for child in children:
                relative = relative_directory / child.name
                if relative_directory == PurePosixPath() and child.name == ".git":
                    continue
                relative_string = relative.as_posix()
                child_metadata = child.stat(follow_symlinks=False)
                if stat.S_ISLNK(child_metadata.st_mode):
                    raise ValueError(f"bundle checkout tree contains a symlink: {relative_string}")
                entries.add(relative_string)
                if stat.S_ISDIR(child_metadata.st_mode):
                    pending.append((Path(child.path), relative))
                elif not stat.S_ISREG(child_metadata.st_mode):
                    raise ValueError(
                        f"bundle checkout tree entry must be a regular file: {relative_string}"
                    )
    return entries


def _validate_skill(content: str, export_name: str) -> None:
    lines = content.split("\n", 4)
    if (
        len(lines) != 5
        or lines[0] != "---"
        or not lines[1].startswith("name: ")
        or not lines[2].startswith("description: ")
        or lines[3] != "---"
    ):
        raise ValueError(f"skill {export_name} must start with exact four-line frontmatter")

    name = lines[1].removeprefix("name: ")
    if name != export_name:
        raise ValueError(f"skill {export_name} frontmatter name must equal its export")
    description = lines[2].removeprefix("description: ")
    if (
        not description
        or description != description.strip()
        or len(description) > _MAX_DESCRIPTION_CHARACTERS
        or any(unicodedata.category(character) in {"Cc", "Zl", "Zp"} for character in description)
    ):
        raise ValueError(f"skill {export_name} frontmatter description is invalid")
    if not lines[4].strip():
        raise ValueError(f"skill {export_name} body must be non-empty")


def validate_bundle(root: Path, manifest: dict) -> dict:
    """Validate and normalize an already parsed schema-1 bundle and its complete tree."""
    if type(manifest) is not dict:
        raise ValueError("bundle manifest must be a JSON object")
    if set(manifest) != _MANIFEST_FIELDS:
        raise ValueError(
            "bundle manifest must contain exactly schema, id, skills, templates, and files"
        )
    if type(manifest["schema"]) is not int or manifest["schema"] != 1:
        raise ValueError("bundle schema must be 1")

    bundle_id = _slug(manifest["id"], field="bundle id")
    skills = _export_map(manifest["skills"], field="skills")
    templates = _export_map(manifest["templates"], field="templates")
    files = _file_map(manifest["files"])

    if not skills and not templates:
        raise ValueError("bundle must export at least one skill or template")
    if set(skills) & set(templates):
        raise ValueError("skill and template export names must be unique")

    export_paths = [*skills.values(), *templates.values()]
    if len(export_paths) != len(set(export_paths)):
        raise ValueError("each payload path may have only one export")
    if set(files) != set(export_paths):
        raise ValueError("files keys must equal the export paths exactly")

    root = Path(root)
    actual_tree = _checkout_tree(root)
    if actual_tree != _expected_tree(set(files)):
        missing = sorted(_expected_tree(set(files)) - actual_tree)
        extra = sorted(actual_tree - _expected_tree(set(files)))
        detail = f"missing {missing[0]}" if missing else f"undeclared {extra[0]}"
        raise ValueError(f"bundle checkout tree does not match its manifest: {detail}")

    total_size = 0
    decoded: dict[str, str] = {}
    for relative, expected_digest in files.items():
        content = _regular_file_bytes(root, PurePosixPath(relative), maximum=_MAX_PAYLOAD_BYTES)
        total_size += len(content)
        if total_size > _MAX_TOTAL_PAYLOAD_BYTES:
            raise ValueError("bundle payload must be at most 10 MiB total")
        if hashlib.sha256(content).hexdigest() != expected_digest:
            raise ValueError(f"bundle payload digest mismatch: {relative}")
        try:
            decoded[relative] = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"bundle payload must be UTF-8 Markdown: {relative}") from error

    for name, relative in skills.items():
        _validate_skill(decoded[relative], name)
    for name, relative in templates.items():
        if not decoded[relative].strip():
            raise ValueError(f"template body must be non-empty: {name}")

    return {
        "schema": 1,
        "id": bundle_id,
        "skills": skills,
        "templates": templates,
        "files": files,
    }
