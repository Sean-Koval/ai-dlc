"""Resolve one Git profile file into a pinned, digest-verified cache."""

from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import shutil
import stat
import subprocess
import tempfile
import tomllib
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ai_dlc.config import resolve_layers
from ai_dlc.enrollment import EnrollmentLock, EnrollmentPaths

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")
_SCP_REMOTE = re.compile(
    r"^(?:(?P<username>[A-Za-z0-9._~-]+)@)?"
    r"(?P<host>\[[^\]]+\]|[^@:/\\]+):(?P<path>.+)$"
)
_GIT_TRANSPORT_HELPER = re.compile(r"^[^:/\\]+::")
_PERCENT_ENCODED_BYTE = re.compile(r"%([0-9A-Fa-f]{2})")
_SSH_USERNAME = re.compile(r"^[A-Za-z0-9._~-]+$")
_DNS_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_URL_SCHEMES = {"file", "https", "ssh"}
_STRUCTURAL_DELIMITERS = frozenset(":/\\@?#%")
_URI_ENCODED_DELIMITERS = frozenset(":/?#[]@!$&'()*+,;=%\\")
_GIT_TIMEOUT_SECONDS = 30
_REDACTED_SOURCE = "<redacted profile source>"
_INVALID_SOURCE = "profile source is invalid"


@dataclass(frozen=True)
class ProfileCandidate:
    profile_id: str
    source: str
    requested_ref: str
    resolved_commit: str
    content_sha256: str
    subdirectory: str
    profile_file: str
    cache_root: Path
    portable: bool


def _relative_path(value: str, *, field: str, allow_empty: bool) -> PurePosixPath:
    if not value:
        if allow_empty:
            return PurePosixPath()
        raise ValueError(f"{field} must be a non-empty relative path")
    if "\x00" in value:
        raise ValueError(f"{field} must be a relative normalized path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError(f"{field} must be a relative normalized path")
    return path


def _selected_path(subdirectory: str, profile_file: str) -> PurePosixPath:
    directory = _relative_path(subdirectory, field="subdirectory", allow_empty=True)
    filename = _relative_path(profile_file, field="profile_file", allow_empty=False)
    return directory / filename


def _run_git(
    repository: Path,
    *arguments: str,
    environ: Mapping[str, str] | None = None,
) -> str:
    if environ is None:
        command = "git"
    else:
        command = shutil.which("git", path=environ.get("PATH", ""))
        if command is None:
            raise RuntimeError("Git is required to resolve a profile source")
    try:
        result = subprocess.run(
            [command, "-C", str(repository), *arguments],
            capture_output=True,
            check=False,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            env=environ,
        )
    except FileNotFoundError as error:
        raise RuntimeError("Git is required to resolve a profile source") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Git profile source operation timed out") from error
    if result.returncode != 0:
        raise RuntimeError("Git profile source operation failed")
    return result.stdout.strip()


def _resolve_commit(
    repository: Path,
    source: str,
    requested_ref: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> str:
    _run_git(repository, "init", "--quiet", environ=environ)
    if requested_ref.startswith("refs/"):
        _run_git(repository, "check-ref-format", requested_ref, environ=environ)
    else:
        _run_git(repository, "check-ref-format", "--branch", requested_ref, environ=environ)
    advertised = _run_git(
        repository,
        "ls-remote",
        "--refs",
        "--",
        source,
        requested_ref,
        environ=environ,
    )
    matches = [line.split("\t", 1) for line in advertised.splitlines() if "\t" in line]
    if len(matches) != 1:
        raise RuntimeError("Git requested ref must identify exactly one advertised ref")
    fetch_ref = matches[0][1]
    _run_git(
        repository,
        "fetch",
        "--quiet",
        "--no-tags",
        "--",
        source,
        fetch_ref,
        environ=environ,
    )
    commit = _run_git(
        repository,
        "rev-parse",
        "--verify",
        "FETCH_HEAD^{commit}",
        environ=environ,
    )
    if not _COMMIT.fullmatch(commit):
        raise RuntimeError("Git returned an invalid resolved commit")
    _run_git(repository, "checkout", "--quiet", "--detach", commit, environ=environ)
    return commit


def _read_regular_file(root: Path, relative_path: PurePosixPath) -> bytes:
    root = root.resolve(strict=True)
    current = root
    parts = relative_path.parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError as error:
            raise ValueError(f"profile file does not exist: {relative_path.as_posix()}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"profile path cannot contain a symlink: {relative_path.as_posix()}")
        if index < len(parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"profile path is not a directory: {relative_path.as_posix()}")
    if not stat.S_ISREG(current.lstat().st_mode):
        raise ValueError(f"profile path must be a regular file: {relative_path.as_posix()}")
    try:
        current.resolve(strict=True).relative_to(root)
    except ValueError as error:
        raise ValueError(
            f"profile path escapes the repository: {relative_path.as_posix()}"
        ) from error
    return current.read_bytes()


def _validate_profile(content: bytes, profile_id: str, *, allow_legacy_identity: bool) -> None:
    try:
        document = tomllib.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ValueError("profile file must be valid UTF-8 TOML") from error
    declared_identity = document.get("profile_id")
    if declared_identity is None and not allow_legacy_identity:
        raise ValueError("profile_id is required in a personal profile")
    if declared_identity is not None and declared_identity != profile_id:
        raise ValueError("profile_id does not match the requested profile")
    resolve_layers([("personal", document)])


def _content_digest(relative_path: PurePosixPath, content: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(relative_path.as_posix().encode("utf-8"))
    digest.update(b"\x00")
    digest.update(str(len(content)).encode("ascii"))
    digest.update(b"\x00")
    digest.update(content)
    return digest.hexdigest()


def _verify_cache_tree(
    cache_root: Path, relative_path: PurePosixPath, expected_digest: str
) -> Path:
    try:
        root_metadata = cache_root.lstat()
    except FileNotFoundError as error:
        raise RuntimeError("cached profile is missing") from error
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        raise RuntimeError("cached profile is corrupt")

    expected_entries = {
        PurePosixPath(*relative_path.parts[:index]) for index in range(1, len(relative_path.parts))
    }
    expected_entries.add(relative_path)
    actual_entries: set[PurePosixPath] = set()
    for directory, directory_names, filenames in os.walk(cache_root, followlinks=False):
        parent = Path(directory)
        for name in [*directory_names, *filenames]:
            path = parent / name
            relative = PurePosixPath(path.relative_to(cache_root).as_posix())
            actual_entries.add(relative)
            if path.is_symlink():
                raise RuntimeError("cached profile is corrupt")
    if actual_entries != expected_entries:
        raise RuntimeError("cached profile is corrupt")

    try:
        content = _read_regular_file(cache_root, relative_path)
    except ValueError as error:
        raise RuntimeError("cached profile is corrupt") from error
    if _content_digest(relative_path, content) != expected_digest:
        raise RuntimeError("cached profile is corrupt")
    return cache_root.joinpath(*relative_path.parts)


def _materialize_cache(
    destination: Path,
    relative_path: PurePosixPath,
    content: bytes,
    expected_digest: str,
) -> None:
    if destination.exists() or destination.is_symlink():
        _verify_cache_tree(destination, relative_path, expected_digest)
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".ai-dlc-profile-", dir=destination.parent))
    try:
        staged_file = staged.joinpath(*relative_path.parts)
        staged_file.parent.mkdir(parents=True, exist_ok=True)
        staged_file.write_bytes(content)
        staged_file.chmod(0o600)
        _verify_cache_tree(staged, relative_path, expected_digest)
        try:
            os.rename(staged, destination)
        except OSError:
            if not (destination.exists() or destination.is_symlink()):
                raise
            _verify_cache_tree(destination, relative_path, expected_digest)
    finally:
        if staged.exists() or staged.is_symlink():
            shutil.rmtree(staged)


def _git_source(source: str, kind: str) -> str:
    """Normalize an existing local source without probing canonical URLs."""
    if kind == "local":
        source_path = Path(source)
        if source_path.exists():
            return str(source_path.resolve())
    return source


def source_portability(source: str) -> bool:
    """Classify source portability from syntax alone, never filesystem state."""
    return _source_kind(source) in {"https", "ssh", "scp"}


def source_lock_value(source: str) -> str:
    """Return the stable source representation stored in a new enrollment lock."""
    kind = _source_kind(source)
    if kind == "unsafe":
        raise ValueError(_INVALID_SOURCE) from None
    if kind in {"file", "https", "ssh", "scp"}:
        return source
    return _git_source(source, kind)


def redact_source(source: str) -> str:
    """Return a safe display value for a legacy source without ever raising."""
    return _REDACTED_SOURCE if _source_kind(source) == "unsafe" else source


def _source_kind(source: str) -> str:
    """Classify the accepted source grammar without consulting the filesystem."""
    if not _lexically_safe_source(source):
        return "unsafe"
    if _GIT_TRANSPORT_HELPER.match(source) is not None:
        return "unsafe"
    scheme_match = _SCHEME.match(source)
    if scheme_match is not None:
        scheme = scheme_match.group(1).lower()
        suffix = source[scheme_match.end() :]
        if scheme in _URL_SCHEMES:
            return _canonical_url_kind(source, scheme, suffix)
    if "://" in source:
        return "unsafe"
    if _WINDOWS_PATH.match(source):
        return "local"
    return _scp_or_local_kind(source)


def _canonical_url_kind(source: str, scheme: str, suffix: str) -> str:
    if not suffix.startswith("//"):
        return "unsafe"
    if "?" in suffix or "#" in suffix:
        return "unsafe"
    if "\\" in suffix or any(character.isspace() for character in source):
        return "unsafe"
    remainder = suffix[2:]
    authority = remainder.split("/", 1)[0]
    if not _valid_url_authority(authority, scheme):
        return "unsafe"
    return scheme


def _lexically_safe_source(source: str) -> bool:
    if not source or source != source.strip():
        return False
    if any(
        chr(int(match.group(1), 16)) in _URI_ENCODED_DELIMITERS
        for match in _PERCENT_ENCODED_BYTE.finditer(source)
    ):
        return False
    for character in source:
        codepoint = ord(character)
        category = unicodedata.category(character)
        if (
            codepoint < 32
            or codepoint == 127
            or category[0] == "C"
            or (character != " " and character.isspace())
        ):
            return False
        normalized = unicodedata.normalize("NFKC", character)
        if normalized != character and any(
            normalized_character in _STRUCTURAL_DELIMITERS
            or normalized_character.isspace()
            or unicodedata.category(normalized_character)[0] == "C"
            for normalized_character in normalized
        ):
            return False
    return True


def _valid_url_authority(authority: str, scheme: str) -> bool:
    if not authority:
        return scheme == "file"
    if (
        not authority.isascii()
        or "%" in authority
        or "\\" in authority
        or any(character.isspace() for character in authority)
    ):
        return False

    host_port = authority
    if "@" in authority:
        if scheme != "ssh" or authority.count("@") != 1:
            return False
        username, host_port = authority.split("@", 1)
        if _SSH_USERNAME.fullmatch(username) is None:
            return False

    return _valid_host_port(host_port, allow_port=scheme != "file")


def _valid_host_port(host_port: str, *, allow_port: bool) -> bool:
    if host_port.startswith("["):
        closing_bracket = host_port.find("]")
        if closing_bracket < 0:
            return False
        host = host_port[1:closing_bracket]
        remainder = host_port[closing_bracket + 1 :]
        try:
            ipaddress.IPv6Address(host)
        except ValueError:
            return False
        if not remainder:
            return True
        return allow_port and remainder.startswith(":") and _valid_port(remainder[1:])

    if host_port.count(":") > 1:
        return False
    if ":" in host_port:
        if not allow_port:
            return False
        host, port = host_port.rsplit(":", 1)
        if not _valid_port(port):
            return False
    else:
        host = host_port
    return _valid_host(host)


def _valid_host(host: str) -> bool:
    if not host or not host.isascii() or len(host) > 253:
        return False
    if all(character.isdigit() or character == "." for character in host) and "." in host:
        try:
            ipaddress.IPv4Address(host)
        except ValueError:
            return False
        return True
    normalized_host = host.removesuffix(".")
    return bool(normalized_host) and all(
        _DNS_LABEL.fullmatch(label) is not None for label in normalized_host.split(".")
    )


def _valid_port(port: str) -> bool:
    return port.isascii() and port.isdigit() and 1 <= len(port) <= 5 and 1 <= int(port) <= 65535


def _scp_or_local_kind(source: str) -> str:
    match = _SCP_REMOTE.fullmatch(source)
    if match is not None:
        host = match.group("host")
        path = match.group("path")
        if (
            _valid_scp_host(host)
            and "@" not in path
            and "\\" not in path
            and not any(character.isspace() for character in path)
        ):
            return "scp"
        return "unsafe"
    colon = source.find(":")
    first_separator = min(
        (index for index in (source.find("/"), source.find("\\")) if index >= 0),
        default=-1,
    )
    if colon >= 0 and (first_separator < 0 or colon < first_separator):
        return "unsafe"
    return "local"


def _valid_scp_host(host: str) -> bool:
    if host.startswith("[") and host.endswith("]"):
        try:
            ipaddress.IPv6Address(host[1:-1])
        except ValueError:
            return False
        return True
    return _valid_host(host)


def resolve_profile_source(
    source: str,
    profile_id: str,
    requested_ref: str,
    paths: EnrollmentPaths,
    *,
    subdirectory: str = "",
    profile_file: str = "ai-dlc-profile.toml",
    allow_legacy_identity: bool = False,
    environ: Mapping[str, str] | None = None,
) -> ProfileCandidate:
    """Resolve one requested Git ref and cache only its validated profile file."""
    kind = _source_kind(source)
    if kind == "unsafe":
        raise ValueError(_INVALID_SOURCE) from None
    relative_path = _selected_path(subdirectory, profile_file)
    fetch_source = _git_source(source, kind)
    portable = kind in {"https", "ssh", "scp"}
    environment = None if environ is None else dict(environ)
    paths.profile_root(profile_id, "0" * 40)
    paths.cache_root.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=".ai-dlc-profile-", dir=paths.cache_root.parent
    ) as temporary_directory:
        repository = Path(temporary_directory) / "repository"
        repository.mkdir()
        resolved_commit = _resolve_commit(
            repository,
            fetch_source,
            requested_ref,
            environ=environment,
        )
        content = _read_regular_file(repository, relative_path)
        _validate_profile(content, profile_id, allow_legacy_identity=allow_legacy_identity)
        content_sha256 = _content_digest(relative_path, content)

    cache_root = paths.profile_root(profile_id, resolved_commit)
    _materialize_cache(cache_root, relative_path, content, content_sha256)
    return ProfileCandidate(
        profile_id=profile_id,
        source=source,
        requested_ref=requested_ref,
        resolved_commit=resolved_commit,
        content_sha256=content_sha256,
        subdirectory=subdirectory,
        profile_file=profile_file,
        cache_root=cache_root,
        portable=portable,
    )


def verify_cached_profile(lock: EnrollmentLock, paths: EnrollmentPaths) -> Path:
    """Verify and return an enrolled cached profile without contacting its source."""
    relative_path = _selected_path(lock.subdirectory, lock.profile_file)
    cache_root = paths.profile_root(lock.profile_id, lock.resolved_commit)
    return _verify_cache_tree(cache_root, relative_path, lock.content_sha256)
