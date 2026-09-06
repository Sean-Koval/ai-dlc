"""Validation for portable, non-executable Markdown workflow bundles."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import tempfile
import tomllib
import unicodedata
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Self

from ai_dlc.config import resolve_layers
from ai_dlc.locking import project_write_lock
from ai_dlc.profile_source import resolve_git_source, source_portability

_MANIFEST_FIELDS = {"schema", "id", "skills", "templates", "files"}
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")

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
_LOCK_FIELDS = {
    "schema",
    "id",
    "source",
    "ref",
    "resolved_commit",
    "manifest_sha256",
    "files",
}

_Identity = tuple[int, int, int, int, int, int]
_TreeSnapshot = tuple[_Identity, dict[str, _Identity]]
_DirectoryRoot = Path | int


@dataclass(frozen=True)
class BundleCandidate:
    """A validated, temporary bundle checkout pinned to one advertised ref."""

    source: str
    ref: str
    bundle_id: str
    resolved_commit: str
    root: Path
    manifest: dict[str, Any]
    manifest_sha256: str
    file_hashes: dict[str, str]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


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
def _directory_descriptor(root: _DirectoryRoot) -> Iterator[int]:
    descriptor = os.dup(root) if isinstance(root, int) else os.open(root, _DIRECTORY_FLAGS)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("bundle root must be an existing directory, not a symlink")
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def _file_descriptor(root: _DirectoryRoot, relative: PurePosixPath) -> Iterator[int]:
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


def _regular_file_bytes(root: _DirectoryRoot, relative: PurePosixPath, *, maximum: int) -> bytes:
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
        if _identity(before) != _identity(after):
            raise ValueError("bundle checkout changed during validation")
        return content


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("bundle.json contains duplicate JSON key")
        result[key] = value
    return result


def _decode_json_object(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        document = json.loads(content.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} must be valid UTF-8 JSON") from error
    if type(document) is not dict:
        raise ValueError(f"{label} must contain a JSON object")
    return document


def _load_manifest_with_bytes(root: _DirectoryRoot) -> tuple[bytes, dict[str, Any]]:
    try:
        content = _regular_file_bytes(
            root, PurePosixPath("bundle.json"), maximum=_MAX_MANIFEST_BYTES
        )
    except OSError:
        raise ValueError(_FILESYSTEM_ERROR) from None
    return content, _decode_json_object(content, label="bundle.json")


def load_bundle_manifest(root: Path) -> dict[str, Any]:
    """Load a bounded UTF-8 ``bundle.json`` without accepting duplicate keys."""
    return _load_manifest_with_bytes(root)[1]


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


def _expected_tree(payload_paths: set[str], metadata_paths: set[str] | None = None) -> set[str]:
    expected = {"bundle.json", *(metadata_paths or set()), *payload_paths}
    for value in payload_paths:
        path = PurePosixPath(value)
        expected.update(
            PurePosixPath(*path.parts[:index]).as_posix() for index in range(1, len(path.parts))
        )
    return expected


def _checkout_tree(root: _DirectoryRoot, *, ignore_root_git: bool = True) -> _TreeSnapshot:
    entries: dict[str, _Identity] = {}

    def scan(descriptor: int, relative_directory: PurePosixPath) -> None:
        directory_before = os.fstat(descriptor)
        with os.scandir(descriptor) as children:
            names = [child.name for child in children]
        for name in names:
            relative = relative_directory / name
            if ignore_root_git and relative_directory == PurePosixPath() and name == ".git":
                continue
            if len(relative.parts) > _MAX_PATH_SEGMENTS:
                raise ValueError("bundle checkout tree paths must contain at most 16 path segments")
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


def _validate_bundle(root: _DirectoryRoot, manifest: dict, *, metadata_paths: set[str]) -> dict:
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

    expected_tree = _expected_tree(set(files), metadata_paths)
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


def validate_bundle(root: Path, manifest: dict) -> dict:
    """Validate and normalize an already parsed schema-1 bundle and its complete tree."""
    return _validate_bundle(Path(root), manifest, metadata_paths=set())


def _candidate_bytes(candidate: BundleCandidate) -> tuple[dict[str, Any], bytes, dict[str, bytes]]:
    if (
        type(candidate.source) is not str
        or not source_portability(candidate.source)
        or type(candidate.bundle_id) is not str
        or _SLUG.fullmatch(candidate.bundle_id) is None
        or type(candidate.resolved_commit) is not str
        or _COMMIT.fullmatch(candidate.resolved_commit) is None
        or type(candidate.manifest_sha256) is not str
        or _SHA256.fullmatch(candidate.manifest_sha256) is None
        or not isinstance(candidate.ref, str)
        or not candidate.ref
    ):
        raise ValueError("bundle candidate metadata is invalid")
    manifest_bytes, raw_manifest = _load_manifest_with_bytes(candidate.root)
    manifest = validate_bundle(candidate.root, raw_manifest)
    if manifest["id"] != candidate.bundle_id:
        raise ValueError("bundle manifest id does not match the requested bundle id")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if (
        manifest != candidate.manifest
        or manifest_sha256 != candidate.manifest_sha256
        or manifest["files"] != candidate.file_hashes
    ):
        raise ValueError("bundle candidate changed after resolution")
    payload = {
        relative: _regular_file_bytes(
            candidate.root, PurePosixPath(relative), maximum=_MAX_PAYLOAD_BYTES
        )
        for relative in manifest["files"]
    }
    latest_manifest_bytes, latest_raw_manifest = _load_manifest_with_bytes(candidate.root)
    if latest_manifest_bytes != manifest_bytes or latest_raw_manifest != raw_manifest:
        raise ValueError("bundle checkout changed during validation")
    for relative, content in payload.items():
        if hashlib.sha256(content).hexdigest() != manifest["files"][relative]:
            raise ValueError(f"bundle payload digest mismatch: {relative}")
    return manifest, manifest_bytes, payload


def resolve_bundle(
    source: str,
    ref: str,
    bundle_id: str,
    *,
    environ: Mapping[str, str] | None,
) -> BundleCandidate:
    """Resolve and validate one portable Git bundle in temporary storage."""
    if not source_portability(source):
        raise ValueError("bundle source must be a portable Git source")
    if _SLUG.fullmatch(bundle_id) is None:
        raise ValueError("requested bundle id must be a lowercase ASCII slug")
    try:
        temporary = Path(tempfile.mkdtemp(prefix=".ai-dlc-bundle-"))
    except OSError:
        raise ValueError(_FILESYSTEM_ERROR) from None
    try:
        resolved_commit, portable = resolve_git_source(
            temporary,
            source,
            ref,
            portable_only=True,
            environ=environ,
        )
        if not portable:
            raise ValueError("bundle source must be a portable Git source")
        manifest_bytes, raw_manifest = _load_manifest_with_bytes(temporary)
        manifest = validate_bundle(temporary, raw_manifest)
        if manifest["id"] != bundle_id:
            raise ValueError("bundle manifest id does not match the requested bundle id")
        latest_manifest_bytes, latest_raw_manifest = _load_manifest_with_bytes(temporary)
        if latest_manifest_bytes != manifest_bytes or latest_raw_manifest != raw_manifest:
            raise ValueError("bundle checkout changed during validation")
        return BundleCandidate(
            source=source,
            ref=ref,
            bundle_id=bundle_id,
            resolved_commit=resolved_commit,
            root=temporary,
            manifest=manifest,
            manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
            file_hashes=dict(manifest["files"]),
        )
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def validate_bundle_project(root: Path) -> Path:
    """Return a lexical absolute project root after no-follow config validation."""
    absolute = Path(os.path.abspath(root))
    try:
        metadata = absolute.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError
        with _directory_descriptor(absolute) as descriptor:
            opened = os.fstat(descriptor)
            if not _same_object(metadata, opened):
                raise ValueError
            content = _regular_file_bytes(
                descriptor, PurePosixPath("ai-dlc.toml"), maximum=_MAX_MANIFEST_BYTES
            )
            _validate_project_document(content)
            named_after = absolute.lstat()
            if not _same_object(named_after, opened):
                raise ValueError
    except (OSError, TypeError, UnicodeDecodeError, ValueError, tomllib.TOMLDecodeError):
        raise ValueError("bundle import requires a valid project root") from None
    return absolute


def _validate_project_document(content: bytes) -> None:
    try:
        document = tomllib.loads(content.decode("utf-8"))
        resolve_layers([("project", document)])
    except (TypeError, UnicodeDecodeError, ValueError, tomllib.TOMLDecodeError):
        raise ValueError("bundle import requires a valid project root") from None


def _lock_document(candidate: BundleCandidate, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": 1,
        "id": candidate.bundle_id,
        "source": candidate.source,
        "ref": candidate.ref,
        "resolved_commit": candidate.resolved_commit,
        "manifest_sha256": candidate.manifest_sha256,
        "files": dict(sorted(manifest["files"].items())),
    }


def _lock_bytes(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _relative_bundle_path(bundle_id: str, relative: str = "") -> str:
    base = f".ai-dlc/bundles/{bundle_id}"
    return f"{base}/{relative}" if relative else base


def _load_existing_lock(destination: _DirectoryRoot, bundle_id: str) -> dict[str, Any]:
    content = _regular_file_bytes(
        destination, PurePosixPath("bundle.lock.json"), maximum=_MAX_MANIFEST_BYTES
    )
    lock = _decode_json_object(content, label="bundle.lock.json")
    if (
        set(lock) != _LOCK_FIELDS
        or type(lock.get("schema")) is not int
        or lock.get("schema") != 1
        or lock.get("id") != bundle_id
    ):
        raise ValueError("invalid lock")
    if (
        type(lock.get("source")) is not str
        or not source_portability(lock["source"])
        or type(lock.get("ref")) is not str
        or not lock["ref"]
        or type(lock.get("resolved_commit")) is not str
        or _COMMIT.fullmatch(lock["resolved_commit"]) is None
        or type(lock.get("manifest_sha256")) is not str
        or _SHA256.fullmatch(lock["manifest_sha256"]) is None
    ):
        raise ValueError("invalid lock")
    lock["files"] = _file_map(lock.get("files"))
    if content != _lock_bytes(lock):
        raise ValueError("invalid lock")
    return lock


def _owned_bundle_conflicts(destination: int, bundle_id: str) -> list[str]:
    base = _relative_bundle_path(bundle_id)
    lock_path = f"{base}/bundle.lock.json"
    try:
        lock = _load_existing_lock(destination, bundle_id)
    except (OSError, ValueError):
        try:
            os.stat("bundle.lock.json", dir_fd=destination, follow_symlinks=False)
        except OSError:
            return [f"{base}: existing bundle is not owned"]
        return [f"{lock_path}: existing bundle lock is invalid"]

    expected = _expected_tree(set(lock["files"]), {"bundle.lock.json"})
    try:
        actual = set(_checkout_tree(destination, ignore_root_git=False)[1])
    except (OSError, ValueError):
        return [f"{base}: existing bundle tree is invalid"]
    conflicts = [
        f"{_relative_bundle_path(bundle_id, relative)}: owned bundle path is missing"
        for relative in sorted(expected - actual)
    ]
    conflicts.extend(
        f"{_relative_bundle_path(bundle_id, relative)}: existing bundle contains an unowned path"
        for relative in sorted(actual - expected)
    )
    if conflicts:
        return sorted(conflicts)

    try:
        manifest_bytes, raw_manifest = _load_manifest_with_bytes(destination)
    except ValueError:
        return [f"{base}/bundle.json: existing bundle manifest is invalid"]
    if hashlib.sha256(manifest_bytes).hexdigest() != lock["manifest_sha256"]:
        return [f"{base}/bundle.json: existing bundle file has local edits"]
    try:
        if type(raw_manifest) is not dict or set(raw_manifest) != _MANIFEST_FIELDS:
            raise ValueError("invalid manifest")
        manifest_files = _file_map(raw_manifest["files"])
    except (KeyError, TypeError, ValueError):
        return [f"{base}/bundle.json: existing bundle manifest is invalid"]
    if raw_manifest.get("id") != bundle_id or manifest_files != lock["files"]:
        return [f"{lock_path}: existing bundle lock does not match its manifest"]
    edited = []
    for relative, expected_digest in lock["files"].items():
        try:
            content = _regular_file_bytes(
                destination, PurePosixPath(relative), maximum=_MAX_PAYLOAD_BYTES
            )
        except (OSError, ValueError):
            edited.append(relative)
            continue
        if hashlib.sha256(content).hexdigest() != expected_digest:
            edited.append(relative)
    if edited:
        return [
            f"{_relative_bundle_path(bundle_id, relative)}: existing bundle file has local edits"
            for relative in sorted(edited)
        ]
    try:
        _validate_bundle(destination, raw_manifest, metadata_paths={"bundle.lock.json"})
    except ValueError:
        return [f"{base}: existing bundle content is invalid"]
    return []


def _existing_conflicts(destination: Path, bundle_id: str) -> list[str]:
    base = _relative_bundle_path(bundle_id)
    if not destination.exists() and not destination.is_symlink():
        return []
    try:
        metadata = destination.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            return [f"{base}: existing bundle destination is not an owned directory"]
        with _directory_descriptor(destination) as descriptor:
            if not _same_object(metadata, os.fstat(descriptor)):
                return [f"{base}: existing bundle destination is invalid"]
            return _owned_bundle_conflicts(descriptor, bundle_id)
    except OSError:
        return [f"{base}: existing bundle destination is invalid"]


def _destination_parent_conflicts(root: Path, bundle_id: str) -> list[str]:
    current = root
    for relative in (".ai-dlc", ".ai-dlc/bundles"):
        current = root.joinpath(*PurePosixPath(relative).parts)
        if not current.exists() and not current.is_symlink():
            continue
        try:
            metadata = current.lstat()
        except OSError:
            return [f"{relative}: bundle destination parent is invalid"]
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            return [f"{relative}: bundle destination parent must be a directory"]
    return _existing_conflicts(root / ".ai-dlc/bundles" / bundle_id, bundle_id)


def _desired_files(
    candidate: BundleCandidate, manifest_bytes: bytes, payload: dict[str, bytes]
) -> dict[str, bytes]:
    lock = _lock_document(candidate, candidate.manifest)
    return {
        "bundle.json": manifest_bytes,
        "bundle.lock.json": _lock_bytes(lock),
        **dict(sorted(payload.items())),
    }


def _changed_paths(destination: Path, bundle_id: str, desired: dict[str, bytes]) -> list[str]:
    existing: dict[str, bytes] = {}
    if destination.is_dir() and not destination.is_symlink():
        for path in destination.rglob("*"):
            if path.is_file() and not path.is_symlink():
                existing[path.relative_to(destination).as_posix()] = path.read_bytes()
    return sorted(
        _relative_bundle_path(bundle_id, relative)
        for relative in existing.keys() | desired.keys()
        if existing.get(relative) != desired.get(relative)
    )


def _open_named_directory(parent: int, name: str) -> int:
    before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise OSError("directory link is invalid")
    descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent)
    if not _same_object(before, os.fstat(descriptor)):
        os.close(descriptor)
        raise OSError("directory link changed")
    return descriptor


def _ensure_named_directory(parent: int, name: str) -> tuple[int, bool]:
    created = False
    try:
        descriptor = _open_named_directory(parent, name)
    except FileNotFoundError:
        os.mkdir(name, dir_fd=parent)
        created = True
        descriptor = _open_named_directory(parent, name)
    return descriptor, created


def _verify_named_directory(parent: int, name: str, descriptor: int) -> None:
    named = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if stat.S_ISLNK(named.st_mode) or not _same_object(named, os.fstat(descriptor)):
        raise OSError("directory link changed")


def _mkdirs_at(root: int, relative: PurePosixPath) -> None:
    current = os.dup(root)
    try:
        for part in relative.parts:
            try:
                os.mkdir(part, dir_fd=current)
            except FileExistsError:
                pass
            following = _open_named_directory(current, part)
            os.close(current)
            current = following
    finally:
        os.close(current)


def _write_regular_file_at(root: int, relative: PurePosixPath, content: bytes) -> None:
    parts = list(relative.parts)
    if not parts:
        raise ValueError("bundle payload path must be non-empty")
    if len(parts) > 1:
        _mkdirs_at(root, PurePosixPath(*parts[:-1]))
    current = os.dup(root)
    try:
        for part in parts[:-1]:
            following = _open_named_directory(current, part)
            os.close(current)
            current = following
        descriptor = os.open(
            parts[-1],
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            0o644,
            dir_fd=current,
        )
        try:
            view = memoryview(content)
            while view:
                written = os.write(descriptor, view)
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(current)


def _stage_bundle_at(parent: int, bundle_id: str, desired: dict[str, bytes]) -> tuple[str, int]:
    suffix = secrets.token_hex(12)
    name = f".{bundle_id}.stage-{suffix}"
    os.mkdir(name, dir_fd=parent)
    descriptor = _open_named_directory(parent, name)
    try:
        for relative, content in desired.items():
            _write_regular_file_at(descriptor, PurePosixPath(relative), content)
        if _owned_bundle_conflicts(descriptor, bundle_id):
            raise ValueError("staged bundle failed integrity validation")
        return name, descriptor
    except BaseException:
        os.close(descriptor)
        _remove_tree_at(parent, name)
        raise


def _remove_tree_at(parent: int, name: str) -> None:
    descriptor = _open_named_directory(parent, name)
    try:
        with os.scandir(descriptor) as children:
            names = [child.name for child in children]
        for child in names:
            metadata = os.stat(child, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISDIR(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode):
                _remove_tree_at(descriptor, child)
            else:
                os.unlink(child, dir_fd=descriptor)
    finally:
        os.close(descriptor)
    os.rmdir(name, dir_fd=parent)


def _destination_descriptor(parent: int, bundle_id: str) -> int | None:
    try:
        return _open_named_directory(parent, bundle_id)
    except FileNotFoundError:
        return None


def _publish_bundle_tree(
    parent: int,
    bundle_id: str,
    staged_name: str,
    staged_descriptor: int,
    existing_descriptor: int | None,
) -> list[str]:
    backup_name = f".{bundle_id}.backup"
    try:
        os.stat(backup_name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise OSError("stale bundle transaction")

    if existing_descriptor is None:
        os.mkdir(bundle_id, dir_fd=parent)
        try:
            os.replace(staged_name, bundle_id, src_dir_fd=parent, dst_dir_fd=parent)
        except BaseException:
            os.rmdir(bundle_id, dir_fd=parent)
            raise
        _verify_named_directory(parent, bundle_id, staged_descriptor)
        return []

    named = os.stat(bundle_id, dir_fd=parent, follow_symlinks=False)
    if not _same_object(named, os.fstat(existing_descriptor)):
        return [f"{_relative_bundle_path(bundle_id)}: existing bundle destination changed"]
    conflicts = _owned_bundle_conflicts(existing_descriptor, bundle_id)
    if conflicts:
        return conflicts

    os.replace(bundle_id, backup_name, src_dir_fd=parent, dst_dir_fd=parent)
    try:
        _verify_named_directory(parent, backup_name, existing_descriptor)
        conflicts = _owned_bundle_conflicts(existing_descriptor, bundle_id)
        if conflicts:
            os.replace(backup_name, bundle_id, src_dir_fd=parent, dst_dir_fd=parent)
            return conflicts
        os.replace(staged_name, bundle_id, src_dir_fd=parent, dst_dir_fd=parent)
        _verify_named_directory(parent, bundle_id, staged_descriptor)
        try:
            _remove_tree_at(parent, backup_name)
        except BaseException:
            os.replace(bundle_id, staged_name, src_dir_fd=parent, dst_dir_fd=parent)
            os.replace(backup_name, bundle_id, src_dir_fd=parent, dst_dir_fd=parent)
            raise
    except BaseException:
        try:
            os.stat(backup_name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            try:
                os.stat(bundle_id, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                os.replace(backup_name, bundle_id, src_dir_fd=parent, dst_dir_fd=parent)
        raise
    return []


def _result(
    candidate: BundleCandidate,
    *,
    applied: bool,
    changed: list[str],
    conflicts: list[str],
) -> dict[str, Any]:
    return {
        "applied": applied,
        "changed": sorted(changed),
        "conflicts": sorted(conflicts),
        "source": candidate.source,
        "ref": candidate.ref,
        "bundle_id": candidate.bundle_id,
        "resolved_commit": candidate.resolved_commit,
        "manifest_sha256": candidate.manifest_sha256,
        "skills": dict(sorted(candidate.manifest["skills"].items())),
        "templates": dict(sorted(candidate.manifest["templates"].items())),
        "files": dict(sorted(candidate.file_hashes.items())),
    }


def import_bundle(
    root: Path,
    candidate: BundleCandidate,
    *,
    apply: bool = False,
    expected_commit: str | None = None,
) -> dict[str, Any]:
    """Preview or transactionally vendor an unchanged, reviewed bundle candidate."""
    if not apply and expected_commit is not None:
        raise ValueError("bundle expected commit requires apply")
    if apply and (type(expected_commit) is not str or _COMMIT.fullmatch(expected_commit) is None):
        raise ValueError("bundle apply requires a 40-character expected commit")
    if apply and expected_commit != candidate.resolved_commit:
        raise ValueError("bundle resolved commit does not match the reviewed commit")
    try:
        root = validate_bundle_project(root)
        _, manifest_bytes, payload = _candidate_bytes(candidate)
        desired = _desired_files(candidate, manifest_bytes, payload)
        conflicts = _destination_parent_conflicts(root, candidate.bundle_id)
        destination = root / ".ai-dlc/bundles" / candidate.bundle_id
        if conflicts:
            return _result(candidate, applied=False, changed=[], conflicts=conflicts)
        changed = _changed_paths(destination, candidate.bundle_id, desired)
        if not apply:
            return _result(candidate, applied=False, changed=changed, conflicts=[])

        with project_write_lock(root):
            _, manifest_bytes, payload = _candidate_bytes(candidate)
            desired = _desired_files(candidate, manifest_bytes, payload)
            conflicts = _destination_parent_conflicts(root, candidate.bundle_id)
            if conflicts:
                return _result(candidate, applied=False, changed=[], conflicts=conflicts)
            changed = _changed_paths(destination, candidate.bundle_id, desired)
            if not changed:
                return _result(candidate, applied=True, changed=[], conflicts=[])
            root_descriptor = metadata_descriptor = bundles_descriptor = None
            metadata_created = bundles_created = False
            staged_name: str | None = None
            staged_descriptor: int | None = None
            existing_descriptor: int | None = None
            try:
                root_descriptor = os.open(root, _DIRECTORY_FLAGS)
                project_bytes = _regular_file_bytes(
                    root_descriptor, PurePosixPath("ai-dlc.toml"), maximum=_MAX_MANIFEST_BYTES
                )
                _validate_project_document(project_bytes)
                metadata_descriptor, metadata_created = _ensure_named_directory(
                    root_descriptor, ".ai-dlc"
                )
                bundles_descriptor, bundles_created = _ensure_named_directory(
                    metadata_descriptor, "bundles"
                )
                staged_name, staged_descriptor = _stage_bundle_at(
                    bundles_descriptor, candidate.bundle_id, desired
                )
                _candidate_bytes(candidate)
                changed = _changed_paths(destination, candidate.bundle_id, desired)
                _verify_named_directory(root_descriptor, ".ai-dlc", metadata_descriptor)
                _verify_named_directory(metadata_descriptor, "bundles", bundles_descriptor)
                try:
                    existing_descriptor = _destination_descriptor(
                        bundles_descriptor, candidate.bundle_id
                    )
                except OSError:
                    return _result(
                        candidate,
                        applied=False,
                        changed=[],
                        conflicts=[
                            (
                                f"{_relative_bundle_path(candidate.bundle_id)}: "
                                "existing bundle destination is not an owned directory"
                            )
                        ],
                    )
                if existing_descriptor is not None:
                    conflicts = _owned_bundle_conflicts(existing_descriptor, candidate.bundle_id)
                    if conflicts:
                        return _result(candidate, applied=False, changed=[], conflicts=conflicts)
                if not changed:
                    return _result(candidate, applied=True, changed=[], conflicts=[])
                conflicts = _publish_bundle_tree(
                    bundles_descriptor,
                    candidate.bundle_id,
                    staged_name,
                    staged_descriptor,
                    existing_descriptor,
                )
                if conflicts:
                    return _result(candidate, applied=False, changed=[], conflicts=conflicts)
                staged_name = None
            finally:
                if existing_descriptor is not None:
                    os.close(existing_descriptor)
                if staged_name is not None and bundles_descriptor is not None:
                    try:
                        _remove_tree_at(bundles_descriptor, staged_name)
                    except OSError:
                        pass
                if staged_descriptor is not None:
                    os.close(staged_descriptor)
                if bundles_descriptor is not None:
                    os.close(bundles_descriptor)
                if bundles_created and metadata_descriptor is not None:
                    try:
                        os.rmdir("bundles", dir_fd=metadata_descriptor)
                    except OSError:
                        pass
                if metadata_descriptor is not None:
                    os.close(metadata_descriptor)
                if metadata_created and root_descriptor is not None:
                    try:
                        os.rmdir(".ai-dlc", dir_fd=root_descriptor)
                    except OSError:
                        pass
                if root_descriptor is not None:
                    os.close(root_descriptor)
        return _result(candidate, applied=True, changed=changed, conflicts=[])
    except OSError:
        raise ValueError(_FILESYSTEM_ERROR) from None
