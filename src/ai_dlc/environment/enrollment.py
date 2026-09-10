"""Validated, machine-local enrollment metadata and XDG paths."""

import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

import tomli_w
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_dlc.files import atomic_create, atomic_write

_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _stable_id(value: str, field: str) -> str:
    if not _STABLE_ID.fullmatch(value):
        raise ValueError(f"{field} must be a stable lowercase ID")
    return value


def _commit(value: str) -> str:
    if not _COMMIT.fullmatch(value):
        raise ValueError("resolved_commit must be a 40-character lowercase Git commit")
    return value


def _sha256(value: str) -> str:
    if not _SHA256.fullmatch(value):
        raise ValueError("content_sha256 must be a 64-character lowercase SHA-256 digest")
    return value


def _relative_path(value: str, *, allow_empty: bool) -> str:
    if value == "":
        if allow_empty:
            return value
        raise ValueError("path cannot be empty")
    path = PurePosixPath(value)
    components = value.split("/")
    if path.is_absolute() or any(component in {"", ".", ".."} for component in components):
        raise ValueError("path must be relative and normalized")
    return value


class EnrollmentLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = Field(default=1, alias="schema")
    profile_id: str
    source: str
    requested_ref: str
    resolved_commit: str
    content_sha256: str
    machine_id: str
    subdirectory: str = ""
    profile_file: str = "ai-dlc-profile.toml"

    @property
    def schema(self) -> Literal[1]:
        return self.schema_version

    @field_validator("profile_id", "machine_id")
    @classmethod
    def stable_ids(cls, value: str, info) -> str:
        return _stable_id(value, info.field_name)

    @field_validator("resolved_commit")
    @classmethod
    def commit(cls, value: str) -> str:
        return _commit(value)

    @field_validator("content_sha256")
    @classmethod
    def digest(cls, value: str) -> str:
        return _sha256(value)

    @field_validator("subdirectory")
    @classmethod
    def relative_subdirectory(cls, value: str) -> str:
        return _relative_path(value, allow_empty=True)

    @field_validator("profile_file")
    @classmethod
    def relative_profile_file(cls, value: str) -> str:
        return _relative_path(value, allow_empty=False)


@dataclass(frozen=True)
class EnrollmentPaths:
    config_root: Path
    cache_root: Path
    state_root: Path

    @classmethod
    def from_environment(
        cls, home: Path | None = None, environ: Mapping[str, str] | None = None
    ) -> "EnrollmentPaths":
        environment = os.environ if environ is None else environ
        user_home = Path.home() if home is None else Path(home)
        config_home = Path(environment.get("XDG_CONFIG_HOME", user_home / ".config"))
        cache_home = Path(environment.get("XDG_CACHE_HOME", user_home / ".cache"))
        state_home = Path(environment.get("XDG_STATE_HOME", user_home / ".local/state"))
        return cls(
            config_root=config_home / "ai-dlc",
            cache_root=cache_home / "ai-dlc",
            state_root=state_home / "ai-dlc",
        )

    @property
    def lock_file(self) -> Path:
        return self.config_root / "enrollment.toml"

    def machine_file(self, machine_id: str) -> Path:
        return self.config_root / "machines" / f"{_stable_id(machine_id, 'machine_id')}.toml"

    def profile_root(self, profile_id: str, resolved_commit: str) -> Path:
        return (
            self.cache_root
            / "profiles"
            / _stable_id(profile_id, "profile_id")
            / _commit(resolved_commit)
        )


def read_lock(paths: EnrollmentPaths) -> EnrollmentLock | None:
    if not paths.lock_file.exists():
        return None
    return EnrollmentLock.model_validate(tomllib.loads(paths.lock_file.read_text()))


def write_lock(paths: EnrollmentPaths, lock: EnrollmentLock) -> Path:
    atomic_write(paths.lock_file, tomli_w.dumps(lock.model_dump(by_alias=True)), mode=0o600)
    return paths.lock_file


def ensure_machine_file(paths: EnrollmentPaths, machine_id: str) -> Path:
    path = paths.machine_file(machine_id)
    atomic_create(path, tomli_w.dumps({"schema": 4}), mode=0o600)
    return path


def active_profile_file(paths: EnrollmentPaths, lock: EnrollmentLock) -> Path:
    return (
        paths.profile_root(lock.profile_id, lock.resolved_commit)
        / lock.subdirectory
        / lock.profile_file
    )
