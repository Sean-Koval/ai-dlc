"""Validation for portable, non-executable Markdown workflow bundles."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
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
_FILESYSTEM_ERROR = "bundle filesystem operation failed"
_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_FILE_FLAGS = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
_READ_CHUNK_BYTES = 64 * 1024

_Identity = tuple[int, int, int, int, int, int]
_TreeSnapshot = tuple[_Identity, dict[str, _Identity]]


def _identity(metadata: os.stat_result) -> _Identity:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _same_object(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev,
        left.st_ino,
        stat.S_IFMT(left.st_mode),
    ) == (
        right.st_dev,
        right.st_ino,
        stat.S_IFMT(right.st_mode),
    )


@contextmanager
def _directory_descriptor(root: Path) -> Iterator[int]:
    descriptor = os.open(root, _DIRECTORY_FLAGS)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("bundle root must be an existing directory, not a symlink")
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def _file_descriptor(root: Path, relative: PurePosixPath) -> Iterator[int]:
    with _directory_descriptor(root) as root_descriptor:
        current = os.dup(root_descriptor)
        try:
            for part in relative.parts[:-1]:
                before = os.stat(part, dir_fd=current, follow_symlinks=False)
                if stat.S_ISLNK(before.st_mode):
                    raise ValueError(f"bundle path cannot contain a symlink: {relative.as_posix()}")
                if not stat.S_ISDIR(before.st_mode):
                    raise ValueError(
                        f"bundle path component must be a directory: {relative.as_posix()}"
                    )
                following = os.open(part, _DIRECTORY_FLAGS, dir_fd=current)
                after = os.fstat(following)
                if not _same_object(before, after):
                    os.close(following)
                    raise ValueError("bundle checkout changed during validation")
                os.close(current)
                current = following

            leaf = relative.parts[-1]
            before = os.stat(leaf, dir_fd=current, follow_symlinks=False)
            if stat.S_ISLNK(before.st_mode):
                raise ValueError(f"bundle path cannot contain a symlink: {relative.as_posix()}")
            if not stat.S_ISREG(before.st_mode):
                raise ValueError(f"bundle path must be a regular file: {relative.as_posix()}")
            descriptor = os.open(leaf, _FILE_FLAGS, dir_fd=current)
            try:
                after = os.fstat(descriptor)
                if not _same_object(before, after):
                    raise ValueError("bundle checkout changed during validation")
                yield descriptor
                named_after = os.stat(leaf, dir_fd=current, follow_symlinks=False)
                opened_after = os.fstat(descriptor)
                if not _same_object(named_after, opened_after):
                    raise ValueError("bundle checkout changed during validation")
            finally:
                os.close(descriptor)
        finally:
            os.close(current)


def _regular_file_bytes(root: Path, relative: PurePosixPath, *, maximum: int) -> bytes:
    with _file_descriptor(root, relative) as descriptor:
        before = os.fstat(descriptor)
        if before.st_size > maximum:
            limit = "1 MiB" if maximum == _MAX_MANIFEST_BYTES else "2 MiB"
            raise ValueError(f"bundle path must be at most {limit}: {relative.as_posix()}")

        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(_READ_CHUNK_BYTES, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        if len(content) > maximum or after.st_size > maximum:
            limit = "1 MiB" if maximum == _MAX_MANIFEST_BYTES else "2 MiB"
            raise ValueError(f"bundle path must be at most {limit}: {relative.as_posix()}")
        if not _same_object(before, after):
            raise ValueError("bundle checkout changed during validation")
        return content


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("bundle.json contains duplicate JSON key")
        result[key] = value
    return result


def load_bundle_manifest(root: Path) -> dict[str, Any]:
    """Load a bounded UTF-8 ``bundle.json`` without accepting duplicate keys."""
    try:
        content = _regular_file_bytes(
            Path(root), PurePosixPath("bundle.json"), maximum=_MAX_MANIFEST_BYTES
        )
    except OSError:
        raise ValueError(_FILESYSTEM_ERROR) from None
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


def _checkout_tree(root: Path) -> _TreeSnapshot:
    entries: dict[str, _Identity] = {}

    def scan(descriptor: int, relative_directory: PurePosixPath) -> None:
        directory_before = os.fstat(descriptor)
        with os.scandir(descriptor) as children:
            names = [child.name for child in children]
        for name in names:
            relative = relative_directory / name
            if relative_directory == PurePosixPath() and name == ".git":
                continue
            relative_string = relative.as_posix()
            child_before = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISLNK(child_before.st_mode):
                raise ValueError(f"bundle checkout tree contains a symlink: {relative_string}")
            entries[relative_string] = _identity(child_before)
            if stat.S_ISDIR(child_before.st_mode):
                child_descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=descriptor)
                try:
                    child_after = os.fstat(child_descriptor)
                    if not _same_object(child_before, child_after):
                        raise ValueError("bundle checkout changed during validation")
                    scan(child_descriptor, relative)
                finally:
                    os.close(child_descriptor)
            elif not stat.S_ISREG(child_before.st_mode):
                raise ValueError(
                    f"bundle checkout tree entry must be a regular file: {relative_string}"
                )
        directory_after = os.fstat(descriptor)
        if _identity(directory_before) != _identity(directory_after):
            raise ValueError("bundle checkout changed during validation")

    with _directory_descriptor(root) as root_descriptor:
        root_before = os.fstat(root_descriptor)
        scan(root_descriptor, PurePosixPath())
        root_after = os.fstat(root_descriptor)
        if _identity(root_before) != _identity(root_after):
            raise ValueError("bundle checkout changed during validation")
    return _identity(root_after), entries


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
        or any(
            unicodedata.category(character).startswith("C")
            or unicodedata.category(character) in {"Zl", "Zp"}
            for character in description
        )
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
    expected_tree = _expected_tree(set(files))
    try:
        initial_snapshot = _checkout_tree(root)
        actual_tree = set(initial_snapshot[1])
        if actual_tree != expected_tree:
            missing = sorted(expected_tree - actual_tree)
            extra = sorted(actual_tree - expected_tree)
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

        final_snapshot = _checkout_tree(root)
        if final_snapshot != initial_snapshot:
            raise ValueError("bundle checkout changed during validation")
    except OSError:
        raise ValueError(_FILESYSTEM_ERROR) from None

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
