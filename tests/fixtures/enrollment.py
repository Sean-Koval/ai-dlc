"""Digest-verified enrollment cache and lock fixtures."""

from __future__ import annotations

import hashlib


def write_enrollment(
    paths, *, content: bytes, machine_id: str = "workstation-01", machine: str = "schema = 4\n"
) -> None:
    """Create a real, digest-verified cache and its active enrollment lock."""
    from ai_dlc.environment.enrollment import EnrollmentLock, write_lock

    profile_id = "personal-profile"
    resolved_commit = "a" * 40
    profile_file = "ai-dlc-profile.toml"
    digest = hashlib.sha256(
        profile_file.encode("utf-8") + b"\0" + str(len(content)).encode("ascii") + b"\0" + content
    ).hexdigest()
    cached_profile = paths.profile_root(profile_id, resolved_commit) / profile_file
    cached_profile.parent.mkdir(parents=True)
    cached_profile.write_bytes(content)
    paths.machine_file(machine_id).parent.mkdir(parents=True)
    paths.machine_file(machine_id).write_text(machine)
    write_lock(
        paths,
        EnrollmentLock(
            profile_id=profile_id,
            source="https://example.test/profiles.git",
            requested_ref="main",
            resolved_commit=resolved_commit,
            content_sha256=digest,
            machine_id=machine_id,
        ),
    )
