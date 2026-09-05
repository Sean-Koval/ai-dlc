"""Preview-first enrollment and offline status for portable machine profiles."""

from __future__ import annotations

import difflib
import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NoReturn

from ai_dlc.config import resolve_layers
from ai_dlc.credentials import credential_status
from ai_dlc.enrollment import (
    EnrollmentLock,
    EnrollmentPaths,
    ensure_machine_file,
    read_lock,
    write_lock,
)
from ai_dlc.profile_source import (
    ProfileCandidate,
    redact_source,
    resolve_profile_source,
    source_lock_value,
    source_portability,
    verify_cached_profile,
)
from ai_dlc.user_agents import UserAgentOwnershipConflict, render_user_agents


class MachineManager:
    """Compose enrollment metadata with the existing profile and readiness services."""

    def __init__(
        self,
        *,
        home: Path | None = None,
        environ: Mapping[str, str] | None = None,
        paths: EnrollmentPaths | None = None,
    ) -> None:
        self.home = (Path.home() if home is None else Path(home)).resolve()
        self.environ = os.environ if environ is None else environ
        self.paths = paths or EnrollmentPaths.from_environment(home=self.home, environ=self.environ)

    def enroll(
        self,
        source: str,
        profile_id: str,
        machine_id: str,
        *,
        requested_ref: str = "main",
        subdirectory: str = "",
        apply: bool = False,
    ) -> dict[str, object]:
        candidate = self._candidate(
            source,
            profile_id,
            requested_ref,
            subdirectory=subdirectory,
        )
        return self._enrollment_preview(candidate, machine_id, apply=apply)

    def migrate(
        self,
        source: str,
        profile_file: str,
        profile_id: str,
        machine_id: str,
        *,
        requested_ref: str = "main",
        subdirectory: str = "",
        apply: bool = False,
    ) -> dict[str, object]:
        candidate = self._candidate(
            source,
            profile_id,
            requested_ref,
            subdirectory=subdirectory,
            profile_file=profile_file,
            allow_legacy_identity=True,
        )
        return self._enrollment_preview(candidate, machine_id, apply=apply)

    def status(self, root: Path | None = None) -> dict[str, object]:
        """Report only local enrollment state; never contact the profile source."""
        del root
        lock = read_lock(self.paths)
        if lock is None:
            return {
                "enrolled": False,
                "ready": False,
                "next": "Enroll a profile with ai-dlc machine enroll <source> --profile-id <id> --machine-id <id>.",
            }

        profile = self._profile_summary_from_lock(lock)
        machine_file = self.paths.machine_file(lock.machine_id)
        machine = {
            "id": lock.machine_id,
            "path": str(machine_file),
            "exists": machine_file.is_file(),
        }
        drift: list[str] = []
        if not machine["exists"]:
            drift.append("machine binding is missing")

        try:
            profile_file = verify_cached_profile(lock, self.paths)
        except RuntimeError:
            drift.append("cache is corrupt")
            return {
                "enrolled": True,
                "ready": False,
                "profile": profile,
                "cache": "corrupt",
                "machine": machine,
                "credentials": [],
                "drift": drift,
            }

        try:
            config = self._resolved_config(
                profile_file, machine_file if machine["exists"] else None
            )
        except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError):
            drift.append("machine binding is invalid")
            config = self._personal_config(profile_file)

        credentials = credential_status(config, self.environ)
        missing_credentials = (
            [entry for entry in credentials if not entry["present"]]
            if machine["exists"] and "machine binding is invalid" not in drift
            else []
        )
        for entry in missing_credentials:
            credential_id = entry["id"]
            variable = entry.get("variable")
            if isinstance(variable, str):
                drift.append(f"credential {credential_id} is missing: {variable}")
            else:
                drift.append(f"credential {credential_id} is not bound")
        return {
            "enrolled": True,
            "ready": not drift,
            "profile": profile,
            "cache": "healthy",
            "machine": machine,
            "credentials": credentials,
            "drift": drift,
        }

    def plan(
        self,
        *,
        headless: bool = False,
        profile: Path | None = None,
        root: Path | None = None,
    ) -> dict[str, object]:
        """Preview reconciliation from the active machine and selected personal profile."""
        from ai_dlc import provision

        lock, profile_file, machine_file = self._active_files(profile=profile)
        if root is None:
            result = provision.machine_plan(
                profile_file,
                headless=headless,
                home=self.home,
                machine=machine_file,
                environ=self.environ,
            )
        else:
            result = provision.machine_plan(
                profile_file,
                headless=headless,
                home=self.home,
                machine=machine_file,
                root=root,
                environ=self.environ,
            )
        return self._with_lock(result, lock)

    def apply(
        self,
        *,
        headless: bool = False,
        profile: Path | None = None,
        root: Path | None = None,
    ) -> dict[str, object]:
        """Reconcile the active machine and selected personal profile without mutation."""
        from ai_dlc import provision

        lock, profile_file, machine_file = self._active_files(profile=profile)
        if root is None:
            result = provision.machine_apply(
                profile_file,
                headless=headless,
                home=self.home,
                machine=machine_file,
                environ=self.environ,
            )
        else:
            result = provision.machine_apply(
                profile_file,
                headless=headless,
                home=self.home,
                machine=machine_file,
                root=root,
                environ=self.environ,
            )
        return self._with_lock(result, lock)

    def sync(self, *, apply: bool = False, headless: bool = False) -> dict[str, object]:
        """Resolve a candidate ref and activate it only after successful reconciliation."""
        from ai_dlc import provision

        lock = read_lock(self.paths)
        if lock is None:
            raise RuntimeError("machine is not enrolled")
        prior_lock_bytes = self.paths.lock_file.read_bytes()
        try:
            active_profile = verify_cached_profile(lock, self.paths)
            machine_file = self._active_machine_file(lock)
        except Exception as exc:  # noqa: BLE001 -- every failure must preserve the lock
            self._raise_sync_failure("active state validation", prior_lock_bytes, exc)

        try:
            candidate = self._candidate(
                lock.source,
                lock.profile_id,
                lock.requested_ref,
                subdirectory=lock.subdirectory,
                profile_file=lock.profile_file,
                allow_legacy_identity=(
                    "profile_id" not in tomllib.loads(active_profile.read_text())
                ),
            )
        except Exception as exc:  # noqa: BLE001 -- every failure must preserve the lock
            self._raise_sync_failure("candidate resolution", prior_lock_bytes, exc)

        candidate_lock = self._lock_from_candidate(candidate, lock.machine_id)
        candidate_profile = candidate.cache_root / candidate.subdirectory / candidate.profile_file
        configuration_diff = "".join(
            difflib.unified_diff(
                active_profile.read_text().splitlines(True),
                candidate_profile.read_text().splitlines(True),
                fromfile=lock.resolved_commit,
                tofile=candidate.resolved_commit,
            )
        )
        changes = {
            "resolved_commit": {
                "from": lock.resolved_commit,
                "to": candidate.resolved_commit,
            },
            "content_sha256": {
                "from": lock.content_sha256,
                "to": candidate.content_sha256,
            },
            "configuration": configuration_diff,
        }
        try:
            config = self._resolved_config(candidate_profile, machine_file)
            credentials = credential_status(config, self.environ)
        except Exception as exc:  # noqa: BLE001 -- every failure must preserve the lock
            self._raise_sync_failure("candidate readiness", prior_lock_bytes, exc)
        idempotent = candidate_lock == lock
        base_result: dict[str, object] = {
            "applied": False,
            "idempotent": idempotent,
            "lock": candidate_lock.model_dump(by_alias=True),
            "changes": changes,
            "readiness": {
                "ready": all(bool(entry["present"]) for entry in credentials),
                "credentials": credentials,
            },
        }
        if idempotent:
            return base_result

        try:
            plan = provision.machine_plan(
                candidate_profile,
                headless=headless,
                home=self.home,
                machine=machine_file,
                environ=self.environ,
            )
        except Exception as exc:  # noqa: BLE001 -- every failure must preserve the lock
            self._raise_sync_failure("candidate planning", prior_lock_bytes, exc)
        base_result["plan"] = plan
        if not apply:
            return base_result

        try:
            reconciliation = provision.machine_apply(
                candidate_profile,
                headless=headless,
                home=self.home,
                machine=machine_file,
                environ=self.environ,
            )
        except Exception as exc:  # noqa: BLE001 -- every failure must preserve the lock
            self._raise_sync_failure(
                "reconciliation",
                prior_lock_bytes,
                exc,
                package_side_effects=True,
            )
        try:
            write_lock(self.paths, candidate_lock)
        except Exception as exc:  # noqa: BLE001 -- every failure must preserve the lock
            self._raise_sync_failure(
                "lock activation",
                prior_lock_bytes,
                exc,
                package_side_effects=True,
            )
        return {
            **base_result,
            "applied": True,
            "reconciliation": reconciliation,
        }

    def doctor(
        self, root: Path, *, target: str = "local", machine: Path | None = None
    ) -> dict[str, object]:
        """Combine enrollment state with shared project and provider diagnostics."""
        from ai_dlc import provision

        lock = read_lock(self.paths)
        profile_file: Path | None = None
        machine_file: Path | None = None
        unavailable: list[str] = []
        if machine is None:
            machine_status = self.status(root)
            if lock is None:
                unavailable.extend(["verified profile cache", "machine binding"])
            else:
                try:
                    profile_file = verify_cached_profile(lock, self.paths)
                except RuntimeError:
                    unavailable.append("verified profile cache")
                selected_machine = self.paths.machine_file(lock.machine_id)
                drift = machine_status.get("drift", [])
                machine_invalid = isinstance(drift, list) and "machine binding is invalid" in drift
                if selected_machine.is_file() and not machine_invalid:
                    machine_file = selected_machine
                else:
                    unavailable.append("machine binding")
        elif lock is not None:
            try:
                profile_file = verify_cached_profile(lock, self.paths)
            except RuntimeError:
                unavailable.append("verified profile cache")
        if machine is not None:
            machine_file = machine
        needs_user_agent_readiness = (
            machine is None and (profile_file is None or machine_file is None)
        ) or (machine is not None and lock is not None and profile_file is None)
        if needs_user_agent_readiness:
            unavailable.append("complete user-agent readiness")
        checks = provision.doctor(
            root,
            target=target,
            personal=profile_file,
            machine=machine_file,
            home=self.home,
            environ=self.environ,
        )
        if machine is not None:
            effective_ready = (
                bool(checks["ready"])
                and machine.is_file()
                and (lock is None or profile_file is not None)
            )
            machine_status = {
                "enrolled": lock is not None,
                "ready": effective_ready,
                "machine": {
                    "path": str(machine),
                    "exists": machine.is_file(),
                    "override": True,
                },
                "drift": unavailable,
            }
        else:
            effective_ready = bool(machine_status["ready"]) and bool(checks["ready"])
        return {
            **checks,
            "ready": effective_ready,
            "machine_status": machine_status,
            "machine_checks": {
                "available": not unavailable,
                "unavailable": unavailable,
            },
        }

    def _candidate(
        self,
        source: str,
        profile_id: str,
        requested_ref: str,
        *,
        subdirectory: str,
        profile_file: str = "ai-dlc-profile.toml",
        allow_legacy_identity: bool = False,
    ) -> ProfileCandidate:
        return resolve_profile_source(
            source,
            profile_id,
            requested_ref,
            self.paths,
            subdirectory=subdirectory,
            profile_file=profile_file,
            allow_legacy_identity=allow_legacy_identity,
            environ=self.environ,
        )

    def _active_files(
        self, *, profile: Path | None = None
    ) -> tuple[EnrollmentLock | None, Path, Path | None]:
        lock = read_lock(self.paths)
        if lock is None:
            if profile is None:
                raise RuntimeError("machine is not enrolled")
            return None, profile, None
        return (
            lock,
            profile or verify_cached_profile(lock, self.paths),
            self._active_machine_file(lock),
        )

    @staticmethod
    def _with_lock(result: dict[str, object], lock: EnrollmentLock | None) -> dict[str, object]:
        if lock is None:
            return result
        return {**result, "lock": lock.model_dump(by_alias=True)}

    def _active_machine_file(self, lock: EnrollmentLock) -> Path:
        machine_file = self.paths.machine_file(lock.machine_id)
        if not machine_file.is_file():
            raise RuntimeError("active machine binding is missing")
        return machine_file

    @staticmethod
    def _lock_from_candidate(candidate: ProfileCandidate, machine_id: str) -> EnrollmentLock:
        return EnrollmentLock(
            profile_id=candidate.profile_id,
            source=source_lock_value(candidate.source),
            requested_ref=candidate.requested_ref,
            resolved_commit=candidate.resolved_commit,
            content_sha256=candidate.content_sha256,
            machine_id=machine_id,
            subdirectory=candidate.subdirectory,
            profile_file=candidate.profile_file,
        )

    def _raise_sync_failure(
        self,
        step: str,
        prior_lock_bytes: bytes,
        error: Exception,
        *,
        package_side_effects: bool = False,
    ) -> NoReturn:
        try:
            lock_unchanged = self.paths.lock_file.read_bytes() == prior_lock_bytes
        except OSError:
            lock_unchanged = False
        if not lock_unchanged:
            raise RuntimeError(
                f"machine sync failed during {step}; active lock changed unexpectedly"
            ) from error
        partial = "; package-side effects may be partial" if package_side_effects else ""
        raise RuntimeError(
            f"machine sync failed during {step}; active lock preserved{partial}"
        ) from error

    def _enrollment_preview(
        self, candidate: ProfileCandidate, machine_id: str, *, apply: bool
    ) -> dict[str, object]:
        lock = self._lock_from_candidate(candidate, machine_id)
        current = read_lock(self.paths)
        machine_file = self.paths.machine_file(machine_id)
        config = self._resolved_config(
            candidate.cache_root / candidate.subdirectory / candidate.profile_file,
            machine_file if machine_file.is_file() else None,
        )
        agent_preview, conflicts = self._agent_preview(config)
        profile_change = (
            {"from": current.profile_id, "to": lock.profile_id}
            if current is not None and current.profile_id != lock.profile_id
            else None
        )
        idempotent = current == lock and machine_file.is_file()
        result: dict[str, object] = {
            "applied": apply,
            "idempotent": idempotent,
            "profile": {
                "id": candidate.profile_id,
                "source": candidate.source,
                "requested_ref": candidate.requested_ref,
                "resolved_commit": candidate.resolved_commit,
                "content_sha256": candidate.content_sha256,
                "portable": candidate.portable,
                "profile_file": candidate.profile_file,
            },
            "lock": lock.model_dump(by_alias=True),
            "machine": {
                "id": machine_id,
                "path": str(machine_file),
                "exists": machine_file.is_file() or apply,
            },
            "modules": self._selected_modules(config),
            "credentials": credential_status(config, self.environ),
            "user_agents": agent_preview,
            "ownership_conflicts": conflicts,
            "profile_change": profile_change,
        }
        if apply:
            ensure_machine_file(self.paths, machine_id)
            # The cache, binding, and complete result are validated before active-state mutation.
            write_lock(self.paths, lock)
        return result

    def _agent_preview(self, config: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        try:
            return render_user_agents(config, self.home, apply=False), []
        except UserAgentOwnershipConflict as error:
            return {"clean": False, "changed": [], "applied": False}, [str(error)]

    @staticmethod
    def _selected_modules(config: dict[str, Any]) -> list[str]:
        modules = config.get("modules", {})
        if not isinstance(modules, Mapping):
            raise TypeError("modules must be a table")
        selected = modules.get("include", ["core"])
        if not isinstance(selected, list) or not all(
            isinstance(module, str) for module in selected
        ):
            raise ValueError("modules.include must be a list of module IDs")
        return selected

    @staticmethod
    def _personal_config(profile_file: Path) -> dict[str, Any]:
        return tomllib.loads(profile_file.read_text())

    def _resolved_config(self, profile_file: Path, machine_file: Path | None) -> dict[str, Any]:
        layers: list[tuple[str, dict[str, Any]]] = [
            ("personal", self._personal_config(profile_file))
        ]
        if machine_file is not None:
            layers.append(("machine", tomllib.loads(machine_file.read_text())))
        return resolve_layers(layers).values

    @staticmethod
    def _profile_summary_from_lock(lock: EnrollmentLock) -> dict[str, object]:
        source = redact_source(lock.source)
        return {
            "id": lock.profile_id,
            "source": source,
            "requested_ref": lock.requested_ref,
            "resolved_commit": lock.resolved_commit,
            "portable": source_portability(lock.source),
        }
