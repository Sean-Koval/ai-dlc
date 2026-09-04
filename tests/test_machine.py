import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from ai_dlc import profile_source
from ai_dlc.enrollment import EnrollmentLock, EnrollmentPaths, read_lock, write_lock

PROFILE = """\
schema = 4
profile_id = "portable-development"

[modules]
include = ["core", "codex"]

[credentials.linear-sandbox]
description = "Linear sandbox access"
required_by = ["provider.linear-sandbox"]

[[agents.servers]]
id = "notes"
command = "notes-mcp"
args = ["serve"]
env = ["LINEAR_SANDBOX_TOKEN"]
"""

LEGACY_PROFILE = PROFILE.replace('profile_id = "portable-development"\n', "")


def git(repository: Path, *arguments: str) -> str:
    """Run one controlled Git command for a disposable profile source."""
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        check=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def disposable_profile(
    tmp_path: Path,
    *,
    manifest: str = PROFILE,
    profile_file: str = "ai-dlc-profile.toml",
) -> tuple[Path, str]:
    repository = tmp_path / "profile-source"
    repository.mkdir(parents=True)
    git(repository, "init", "-b", "main")
    git(repository, "config", "user.name", "AI-DLC Test")
    git(repository, "config", "user.email", "ai-dlc@example.test")
    path = repository / profile_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest)
    git(repository, "add", "--", profile_file)
    git(repository, "commit", "-m", "add profile")
    return repository, git(repository, "rev-parse", "HEAD")


def manager(tmp_path: Path, environ: dict[str, str] | None = None):
    from ai_dlc.machine import MachineManager

    home = tmp_path / "home"
    paths = EnrollmentPaths.from_environment(home=home, environ={})
    selected_environment = (
        None if environ is None else {"PATH": os.environ.get("PATH", ""), **environ}
    )
    return MachineManager(home=home, environ=selected_environment, paths=paths), paths


def fake_git_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, str], Path]:
    real_git = shutil.which("git")
    assert real_git is not None
    injected_home = tmp_path / "git-home"
    injected_home.mkdir(parents=True)
    injected = {"PATH": os.environ["PATH"], "HOME": str(injected_home)}
    ambient_bin = tmp_path / "ambient-bin"
    ambient_bin.mkdir()
    marker = tmp_path / "ambient-git-invoked"
    fake_git = ambient_bin / "git"
    fake_git.write_text('#!/bin/sh\nprintf invoked > "$FAKE_GIT_MARKER"\nexit 97\n')
    fake_git.chmod(0o755)
    monkeypatch.setenv("PATH", str(ambient_bin))
    monkeypatch.setenv("FAKE_GIT_MARKER", str(marker))
    return injected, marker


def test_enroll_preview_reports_the_candidate_without_activating_it(tmp_path: Path):
    """Would fail if preview wrote a lock, machine file, or omitted plan facts."""
    source, commit = disposable_profile(tmp_path)
    service, paths = manager(tmp_path, {"LINEAR_SANDBOX_TOKEN": "test-value-never-returned"})

    preview = service.enroll(str(source), "portable-development", "laptop")

    assert preview["applied"] is False
    assert preview["profile"] == {
        "id": "portable-development",
        "source": str(source),
        "requested_ref": "main",
        "resolved_commit": commit,
        "content_sha256": "624a0af6afbff788318d5f9d2ae4bc7d3259aa6dda98fa4a84b962fb1b2d045a",
        "portable": False,
        "profile_file": "ai-dlc-profile.toml",
    }
    assert preview["lock"]["machine_id"] == "laptop"
    assert preview["modules"] == ["core", "codex"]
    assert preview["credentials"] == [
        {
            "id": "linear-sandbox",
            "description": "Linear sandbox access",
            "required_by": ["provider.linear-sandbox"],
            "configured": False,
            "present": False,
        }
    ]
    assert preview["user_agents"]["changed"]
    assert preview["ownership_conflicts"] == []
    assert not paths.lock_file.exists()
    assert not paths.machine_file("laptop").exists()
    assert "test-value-never-returned" not in repr(preview)


def test_enroll_apply_creates_a_machine_skeleton_before_activating_an_idempotent_lock(
    tmp_path: Path,
):
    """Would fail if apply activated before creating bindings or changed a stable enrollment."""
    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)

    applied = service.enroll(str(source), "portable-development", "laptop", apply=True)
    first_lock = paths.lock_file.read_bytes()
    repeated = service.enroll(str(source), "portable-development", "laptop", apply=True)

    assert applied["applied"] is True
    assert tomllib.loads(paths.machine_file("laptop").read_text()) == {"schema": 4}
    assert read_lock(paths).machine_id == "laptop"
    assert paths.lock_file.read_bytes() == first_lock
    assert repeated["idempotent"] is True
    assert not (paths.config_root.parent.parent / ".claude.json").exists()
    assert not (paths.config_root.parent.parent / ".codex").exists()


def test_enroll_uses_only_the_injected_git_environment(tmp_path: Path, monkeypatch):
    """Would fail if enrollment launched Git from the ambient PATH."""
    source, commit = disposable_profile(tmp_path)
    injected, ambient_marker = fake_git_environment(tmp_path, monkeypatch)
    service, paths = manager(tmp_path, injected)

    result = service.enroll(str(source), "portable-development", "laptop", apply=True)

    assert result["lock"]["resolved_commit"] == commit
    assert read_lock(paths).resolved_commit == commit
    assert (paths.profile_root("portable-development", commit) / "ai-dlc-profile.toml").is_file()
    assert not ambient_marker.exists()


def test_sync_uses_only_the_injected_git_environment(tmp_path: Path, monkeypatch):
    """Would fail if synchronization launched Git from the ambient PATH."""
    from ai_dlc.machine import MachineManager

    source, old_commit = disposable_profile(tmp_path)
    enrolled, paths = manager(tmp_path, {"PATH": os.environ["PATH"]})
    enrolled.enroll(str(source), "portable-development", "laptop", apply=True)
    new_commit = advance_profile(source, suffix="python")
    old_lock = paths.lock_file.read_bytes()
    injected, ambient_marker = fake_git_environment(tmp_path / "sync-environment", monkeypatch)
    service = MachineManager(home=enrolled.home, environ=injected, paths=paths)

    result = service.sync()

    assert result["lock"]["resolved_commit"] == new_commit
    assert result["changes"]["resolved_commit"] == {"from": old_commit, "to": new_commit}
    assert paths.lock_file.read_bytes() == old_lock
    assert (
        paths.profile_root("portable-development", new_commit) / "ai-dlc-profile.toml"
    ).is_file()
    assert not ambient_marker.exists()


def test_sync_with_an_explicit_empty_environment_never_invokes_ambient_git(
    tmp_path: Path, monkeypatch
):
    """Would fail if empty PATH fell through to ambient Git during synchronization."""
    from ai_dlc.machine import MachineManager

    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    old_lock = paths.lock_file.read_bytes()
    _, ambient_marker = fake_git_environment(tmp_path / "empty-environment", monkeypatch)
    isolated = MachineManager(home=service.home, environ={}, paths=paths)

    with pytest.raises(RuntimeError, match="candidate resolution.*active lock preserved"):
        isolated.sync()

    assert paths.lock_file.read_bytes() == old_lock
    assert not ambient_marker.exists()


def test_enroll_without_an_environment_retains_ambient_git_compatibility(
    tmp_path: Path, monkeypatch
):
    """Would fail if the optional environment changed existing direct behavior."""
    from ai_dlc.machine import MachineManager

    source, commit = disposable_profile(tmp_path)
    ambient_path = os.environ["PATH"]
    monkeypatch.setenv("PATH", ambient_path)
    home = tmp_path / "ambient-home"
    paths = EnrollmentPaths.from_environment(home=home, environ={})
    service = MachineManager(home=home, paths=paths)

    result = service.enroll(str(source), "portable-development", "laptop")

    assert result["lock"]["resolved_commit"] == commit


def test_enroll_preview_reports_and_apply_allows_an_explicit_profile_replacement(tmp_path: Path):
    """Would fail if a different profile silently replaced the active profile."""
    first_source, _ = disposable_profile(tmp_path / "first")
    second_source, _ = disposable_profile(
        tmp_path / "second", manifest=PROFILE.replace("portable-development", "portable-work")
    )
    service, paths = manager(tmp_path)
    service.enroll(str(first_source), "portable-development", "laptop", apply=True)

    preview = service.enroll(str(second_source), "portable-work", "laptop")
    applied = service.enroll(str(second_source), "portable-work", "laptop", apply=True)

    assert preview["profile_change"] == {
        "from": "portable-development",
        "to": "portable-work",
    }
    assert applied["profile_change"] == preview["profile_change"]
    assert read_lock(paths).profile_id == "portable-work"


def test_enroll_rejects_a_declared_identity_mismatch_before_writing_active_state(tmp_path: Path):
    """Would fail if a mismatched source could create or replace an active binding."""
    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)

    with pytest.raises(ValueError, match="profile_id"):
        service.enroll(str(source), "other-profile", "laptop", apply=True)

    assert not paths.lock_file.exists()
    assert not paths.machine_file("laptop").exists()


def test_migrate_requires_a_relative_legacy_file_and_preserves_that_source_file(tmp_path: Path):
    """Would fail if migration accepted an unpinned path or rewrote the user's legacy file."""
    source, commit = disposable_profile(
        tmp_path, manifest=LEGACY_PROFILE, profile_file="profiles/personal.toml"
    )
    original = (source / "profiles/personal.toml").read_bytes()
    service, paths = manager(tmp_path)

    with pytest.raises(ValueError, match="relative|normalized"):
        service.migrate(str(source), "/profiles/personal.toml", "portable-development", "laptop")
    preview = service.migrate(
        str(source), "profiles/personal.toml", "portable-development", "laptop"
    )
    assert not paths.lock_file.exists()
    applied = service.migrate(
        str(source), "profiles/personal.toml", "portable-development", "laptop", apply=True
    )

    assert preview["applied"] is False
    assert preview["profile"]["resolved_commit"] == commit
    assert preview["lock"]["profile_file"] == "profiles/personal.toml"
    assert applied["applied"] is True
    assert read_lock(paths).profile_file == "profiles/personal.toml"
    assert (source / "profiles/personal.toml").read_bytes() == original


def test_status_reports_an_actionable_unenrolled_machine(tmp_path: Path):
    """Would fail if status treated a new machine as an exception instead of a next action."""
    service, _ = manager(tmp_path)

    status = service.status()

    assert status == {
        "enrolled": False,
        "ready": False,
        "next": "Enroll a profile with ai-dlc machine enroll <source> --profile-id <id> --machine-id <id>.",
    }


def test_status_reports_cached_identity_readiness_and_drift_without_environment_values(
    tmp_path: Path,
):
    """Would fail if status omitted enrollment health or leaked a credential value."""
    source, commit = disposable_profile(tmp_path)
    marker = "credential-value-that-must-not-escape"
    service, paths = manager(tmp_path, {"LINEAR_SANDBOX_TOKEN": marker})
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    paths.machine_file("laptop").write_text(
        'schema = 4\n[credentials.linear-sandbox]\nsource = "environment"\nvariable = "LINEAR_SANDBOX_TOKEN"\n'
    )

    status = service.status()

    assert status["enrolled"] is True
    assert status["ready"] is True
    assert status["profile"] == {
        "id": "portable-development",
        "source": str(source),
        "requested_ref": "main",
        "resolved_commit": commit,
        "portable": False,
    }
    assert status["cache"] == "healthy"
    assert status["machine"] == {
        "id": "laptop",
        "path": str(paths.machine_file("laptop")),
        "exists": True,
    }
    assert status["credentials"][0]["id"] == "linear-sandbox"
    assert status["credentials"][0]["variable"] == "LINEAR_SANDBOX_TOKEN"
    assert status["credentials"][0]["present"] is True
    assert status["drift"] == []
    assert marker not in repr(status)


def test_status_reports_missing_machine_and_credential_bindings_as_drift(tmp_path: Path):
    """Would fail if absent local prerequisites were hidden rather than actionable drift."""
    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    paths.machine_file("laptop").unlink()

    missing_machine = service.status()
    paths.machine_file("laptop").parent.mkdir(parents=True, exist_ok=True)
    paths.machine_file("laptop").write_text(
        'schema = 4\n[credentials.linear-sandbox]\nsource = "environment"\nvariable = "LINEAR_SANDBOX_TOKEN"\n'
    )
    missing_credential = service.status()

    assert missing_machine["ready"] is False
    assert missing_machine["drift"] == ["machine binding is missing"]
    assert missing_credential["credentials"][0]["id"] == "linear-sandbox"
    assert missing_credential["credentials"][0]["variable"] == "LINEAR_SANDBOX_TOKEN"
    assert missing_credential["credentials"][0]["present"] is False
    assert missing_credential["ready"] is False


def test_status_stays_offline_for_corrupt_cache_and_unavailable_source(tmp_path: Path):
    """Would fail if status fetched a source or treated cache corruption as healthy."""
    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    source.rename(tmp_path / "source-offline")

    offline = service.status()
    active = read_lock(paths)
    (
        paths.profile_root(active.profile_id, active.resolved_commit) / active.profile_file
    ).write_text("corrupt\n")
    corrupt = service.status()

    assert offline["cache"] == "healthy"
    assert offline["enrolled"] is True
    assert corrupt["cache"] == "corrupt"
    assert corrupt["ready"] is False
    assert "cache is corrupt" in corrupt["drift"]


@pytest.mark.parametrize(
    "source",
    [
        " https://profile-user:synthetic-credential@example.test/profile.git",
        "https://profile-user:synthetic-credential@example.test/profile.git ",
        "https://profile-user:synthetic-credential@example.test/profile.git",
        "https://profile-user@example.test/synthetic-credential.git",
        "http://profile-user@example.test/synthetic-credential.git",
        "ssh://profile-user:synthetic-credential@example.test/profile.git",
        "https://example.test/profile.git?access_token=synthetic-credential",
        "https://example.test/profile.git#access_token=synthetic-credential",
        "https://profile-user%3Asynthetic-credential@example.test/profile.git",
        "https://profile-user%3Asynthetic-credential%40example.test/profile.git",
        "https://synthetic-credential／example.test/profile.git",
        "https:profile-user:synthetic-credential@example.test/profile.git",
        "https://example.test%3Fsynthetic-credential/profile.git",
        "https://example.test%23synthetic-credential/profile.git",
        "https://example.test%2Fsynthetic-credential/profile.git",
        "https://example.test%EF%BC%8Fsynthetic-credential/profile.git",
        "https://:443/synthetic-credential.git",
        "ssh://git@/synthetic-credential.git",
        "https://example_test/synthetic-credential.git",
        "https://example.test\\synthetic-credential.git",
        "https：//profile-user:synthetic-credential@example.test/profile.git",
        "git:profile-user:synthetic-credential@example.test/profile.git",
    ],
)
def test_enroll_rejects_unsafe_source_before_it_can_reach_local_state_or_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
):
    """Would fail if unsafe URL material reached Git, output, or local enrollment state."""
    service, paths = manager(tmp_path)
    git_calls: list[tuple[object, ...]] = []

    def record_git(*arguments: object) -> str:
        git_calls.append(arguments)
        return ""

    monkeypatch.setattr(profile_source, "_run_git", record_git)

    with pytest.raises(ValueError) as raised:
        service.enroll(source, "portable-development", "laptop", apply=True)

    stored_files = [
        path
        for root in [paths.config_root, paths.cache_root, paths.state_root]
        if root.exists()
        for path in root.rglob("*")
        if path.is_file()
    ]
    assert str(raised.value) == "profile source is invalid"
    assert "synthetic-credential" not in str(raised.value)
    assert profile_source.redact_source(source) == "<redacted profile source>"
    assert git_calls == []
    assert all("synthetic-credential" not in path.read_text() for path in stored_files)
    assert not paths.lock_file.exists()


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("credential-helper::synthetic-credential", id="git-transport-helper"),
        pytest.param(
            "https%3a//profile-user:synthetic-credential@example.test/profile.git",
            id="encoded-scheme-delimiter",
        ),
        pytest.param(
            "https://example.test/profile%2Fsynthetic-credential.git",
            id="encoded-path-delimiter",
        ),
    ],
)
def test_machine_rejects_ambiguous_sources_before_git_state_or_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
):
    """Would fail if public enrollment bypassed fail-closed source classification."""
    service, paths = manager(tmp_path)
    git_calls: list[tuple[object, ...]] = []

    def record_git(*arguments: object) -> str:
        git_calls.append(arguments)
        return ""

    monkeypatch.setattr(profile_source, "_run_git", record_git)

    with pytest.raises(ValueError) as raised:
        service.enroll(source, "portable-development", "laptop", apply=True)

    status = service.status()
    stored_files = [
        path
        for root in [paths.config_root, paths.cache_root, paths.state_root]
        if root.exists()
        for path in root.rglob("*")
        if path.is_file()
    ]
    assert str(raised.value) == "profile source is invalid"
    assert raised.value.__cause__ is None
    assert "synthetic-credential" not in repr((raised.value, status))
    assert profile_source.redact_source(source) == "<redacted profile source>"
    assert git_calls == []
    assert read_lock(paths) is None
    assert all(b"synthetic-credential" not in path.read_bytes() for path in stored_files)


def test_machine_preview_and_offline_status_classify_username_only_ssh_without_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Would fail if a canonical SSH URL were rejected or previewed differently from status."""
    source = "ssh://git@example.test/profile.git"
    service, _ = manager(tmp_path)

    def resolve_without_network(
        repository: Path, received_source: str, requested_ref: str, *, environ=None
    ) -> str:
        del environ
        assert received_source == source
        assert requested_ref == "main"
        (repository / "ai-dlc-profile.toml").write_text(PROFILE)
        return "a" * 40

    monkeypatch.setattr(profile_source, "_resolve_commit", resolve_without_network)

    preview = service.enroll(source, "portable-development", "laptop")
    service.enroll(source, "portable-development", "laptop", apply=True)
    status = service.status()

    assert preview["profile"]["portable"] is True
    assert status["profile"]["portable"] is True


def test_https_source_survives_public_enroll_preview_apply_and_offline_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Would fail if HTTPS metadata were lost outside direct classifier coverage."""
    source = "https://example.test/portable-profile.git"
    service, paths = manager(tmp_path)
    resolution_calls: list[tuple[str, str]] = []

    def resolve_without_network(
        repository: Path, received_source: str, requested_ref: str, *, environ=None
    ) -> str:
        del environ
        resolution_calls.append((received_source, requested_ref))
        (repository / "ai-dlc-profile.toml").write_text(PROFILE)
        return "b" * 40

    monkeypatch.setattr(profile_source, "_resolve_commit", resolve_without_network)

    preview = service.enroll(source, "portable-development", "laptop")
    applied = service.enroll(source, "portable-development", "laptop", apply=True)

    def unexpected_online_resolution(*_arguments: object) -> str:
        raise AssertionError("offline status contacted the HTTPS source")

    monkeypatch.setattr(profile_source, "_resolve_commit", unexpected_online_resolution)
    status = service.status()

    assert resolution_calls == [(source, "main"), (source, "main")]
    assert preview["profile"]["source"] == source
    assert preview["profile"]["portable"] is True
    assert preview["profile"]["resolved_commit"] == "b" * 40
    assert preview["modules"] == ["core", "codex"]
    assert preview["lock"]["source"] == source
    assert applied["lock"]["source"] == source
    assert read_lock(paths).source == source
    assert (paths.profile_root("portable-development", "b" * 40) / "ai-dlc-profile.toml").is_file()
    assert status["cache"] == "healthy"
    assert status["profile"]["source"] == source
    assert status["profile"]["portable"] is True


@pytest.mark.parametrize(
    ("source", "expected_git_source"),
    [
        ("https://example.test/portable-profile.git", None),
        ("ssh://git@example.test/portable-profile.git", None),
        ("git@example.test:portable-profile.git", None),
        ("file:///profiles/portable-profile.git", None),
        ("local-profile", "resolved-local-profile"),
    ],
)
def test_public_enroll_classifies_a_source_before_resolving_only_local_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    expected_git_source: str | None,
):
    """Would fail if a URL-shaped cwd path could replace the external Git source."""
    monkeypatch.chdir(tmp_path)
    source_path = Path(source)
    source_path.mkdir(parents=True)
    service, _ = manager(tmp_path)
    received_sources: list[str] = []

    def resolve_without_network(
        repository: Path, received_source: str, requested_ref: str, *, environ=None
    ) -> str:
        del environ
        received_sources.append(received_source)
        assert requested_ref == "main"
        (repository / "ai-dlc-profile.toml").write_text(PROFILE)
        return "c" * 40

    monkeypatch.setattr(profile_source, "_resolve_commit", resolve_without_network)

    service.enroll(source, "portable-development", "laptop")

    expected = (
        str((tmp_path / "local-profile").resolve())
        if expected_git_source == "resolved-local-profile"
        else source
    )
    assert received_sources == [expected]


@pytest.mark.parametrize(
    "unsafe_source",
    [
        "https:synthetic-credential@example.test/profile.git",
        " https://profile-user:synthetic-credential@example.test/profile.git",
        "https://:443/synthetic-credential.git",
        "credential-helper::synthetic-credential",
        "https%3A//profile-user:synthetic-credential@example.test/profile.git",
    ],
)
def test_status_redacts_an_unsafe_legacy_lock_source(tmp_path: Path, unsafe_source: str):
    """Would fail if status returned a credential from an old unsafe enrollment lock."""
    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    active = read_lock(paths)
    write_lock(
        paths,
        active.model_copy(update={"source": unsafe_source}),
    )

    status = service.status()

    assert "synthetic-credential" not in repr(status)
    assert status["profile"]["source"] == "<redacted profile source>"


def test_enroll_validates_preview_before_replacing_the_active_lock(tmp_path: Path):
    """Would fail if an invalid module structure activated a candidate before result assembly."""
    active_source, _ = disposable_profile(tmp_path / "active")
    invalid_source, _ = disposable_profile(
        tmp_path / "invalid",
        manifest=PROFILE.replace(
            '[modules]\ninclude = ["core", "codex"]\n', 'modules = ["core"]\n'
        ),
    )
    service, paths = manager(tmp_path)
    service.enroll(str(active_source), "portable-development", "laptop", apply=True)
    original_lock = paths.lock_file.read_bytes()

    with pytest.raises((TypeError, ValueError), match="modules"):
        service.enroll(str(invalid_source), "portable-development", "new-laptop", apply=True)

    assert paths.lock_file.read_bytes() == original_lock
    assert not paths.machine_file("new-laptop").exists()


def test_enroll_rejects_invalid_agent_configuration_without_activating_it(tmp_path: Path):
    """Would fail if candidate validation errors were misreported as ownership conflicts."""
    active_source, _ = disposable_profile(tmp_path / "active")
    invalid_source, _ = disposable_profile(
        tmp_path / "invalid",
        manifest=PROFILE.replace('env = ["LINEAR_SANDBOX_TOKEN"]', 'env = ["literal-value"]'),
    )
    service, paths = manager(tmp_path)
    service.enroll(str(active_source), "portable-development", "laptop", apply=True)
    original_lock = paths.lock_file.read_bytes()

    with pytest.raises(ValueError, match="literal values"):
        service.enroll(str(invalid_source), "portable-development", "new-laptop", apply=True)

    assert paths.lock_file.read_bytes() == original_lock
    assert not paths.machine_file("new-laptop").exists()


@pytest.mark.parametrize(
    ("source", "portable"),
    [
        ("local", False),
        ("file", False),
        ("https://example.test/profile.git", True),
        ("ssh://git@example.test/profile.git", True),
        ("git@example.test:profile.git", True),
    ],
)
def test_preview_and_offline_status_use_the_same_source_portability_classification(
    tmp_path: Path,
    source: str,
    portable: bool,
):
    """Would fail if status reclassified a persisted source differently from enrollment."""
    repository, _ = disposable_profile(tmp_path / "source")
    selected_source = {
        "local": str(repository),
        "file": repository.as_uri(),
    }.get(source, source)
    service, paths = manager(tmp_path)
    preview_source = selected_source if source in {"local", "file"} else str(repository)
    preview = service.enroll(preview_source, "portable-development", "laptop")
    lock = preview["lock"].copy()
    lock["source"] = selected_source
    service.enroll(preview_source, "portable-development", "laptop", apply=True)
    write_lock(paths, EnrollmentLock.model_validate(lock))
    repository.rename(tmp_path / "source-offline")

    status = service.status()

    if source in {"local", "file"}:
        assert preview["profile"]["portable"] is portable
    assert status["profile"]["portable"] is portable


def test_enroll_preview_uses_the_provisioning_default_module_when_modules_are_omitted(
    tmp_path: Path,
):
    """Would fail if enrollment preview disagreed with provisioning's default module selection."""
    source, _ = disposable_profile(
        tmp_path,
        manifest=PROFILE.replace('[modules]\ninclude = ["core", "codex"]\n\n', ""),
    )
    service, _ = manager(tmp_path)

    preview = service.enroll(str(source), "portable-development", "laptop")

    assert preview["modules"] == ["core"]


def configure_active_machine(paths: EnrollmentPaths) -> Path:
    active = read_lock(paths)
    machine_file = paths.machine_file(active.machine_id)
    machine_file.write_text(
        'schema = 4\n[credentials.linear-sandbox]\nsource = "environment"\nvariable = "LINEAR_SANDBOX_TOKEN"\n'
    )
    return machine_file


def advance_profile(repository: Path, *, suffix: str = "codex") -> str:
    profile = repository / "ai-dlc-profile.toml"
    profile.write_text(PROFILE.replace('["core", "codex"]', f'["core", "{suffix}"]'))
    git(repository, "add", "--", "ai-dlc-profile.toml")
    git(repository, "commit", "-m", "advance profile")
    return git(repository, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    ("operation", "provision_name"),
    [("plan", "machine_plan"), ("apply", "machine_apply")],
)
def test_explicit_profile_replaces_only_the_personal_scope_for_reconciliation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str, provision_name: str
):
    """Would fail if an explicit profile discarded the active machine binding."""
    from ai_dlc import provision

    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    machine_file = configure_active_machine(paths)
    replacement = tmp_path / "replacement.toml"
    replacement.write_text(PROFILE)
    calls = []

    def boundary(profile: Path, **kwargs) -> dict[str, object]:
        calls.append((profile, kwargs))
        return {"ready": True, "commands": []}

    monkeypatch.setattr(provision, provision_name, boundary)

    result = getattr(service, operation)(profile=replacement)

    assert calls == [
        (
            replacement,
            {
                "headless": False,
                "home": service.home,
                "machine": machine_file,
                "environ": service.environ,
            },
        )
    ]
    assert result["lock"]["machine_id"] == "laptop"


def test_explicit_machine_replaces_only_the_machine_scope_for_doctor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if doctor lost the verified enrolled personal profile for --machine."""
    from ai_dlc import provision

    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path, {"LINEAR_SANDBOX_TOKEN": "present"})
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    configure_active_machine(paths)
    active = read_lock(paths)
    active_profile = (
        paths.profile_root(active.profile_id, active.resolved_commit) / active.profile_file
    )
    replacement = tmp_path / "replacement-machine.toml"
    replacement.write_text('schema = 4\n[paths]\nworkspace = "/replacement"\n')
    calls = []

    def boundary(root: Path, **kwargs) -> dict[str, object]:
        calls.append((root, kwargs))
        return {"ready": True, "credentials": []}

    monkeypatch.setattr(provision, "doctor", boundary)

    result = service.doctor(tmp_path, machine=replacement)

    assert calls == [
        (
            tmp_path,
            {
                "target": "local",
                "personal": active_profile,
                "machine": replacement,
                "home": service.home,
                "environ": service.environ,
            },
        )
    ]
    assert result["ready"] is True


def test_doctor_without_enrollment_forwards_an_explicit_machine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if explicit-machine doctor discarded legacy no-profile compatibility."""
    from ai_dlc import provision

    service, _ = manager(tmp_path)
    machine = tmp_path / "machine.toml"
    machine.write_text("schema = 4\n")
    calls = []

    def boundary(root: Path, **kwargs) -> dict[str, object]:
        calls.append((root, kwargs))
        return {"ready": True, "credentials": []}

    monkeypatch.setattr(provision, "doctor", boundary)

    result = service.doctor(tmp_path, machine=machine)

    assert calls == [
        (
            tmp_path,
            {
                "target": "local",
                "personal": None,
                "machine": machine,
                "home": service.home,
                "environ": service.environ,
            },
        )
    ]
    assert result["ready"] is True
    assert result["machine_status"]["machine"] == {
        "path": str(machine),
        "exists": True,
        "override": True,
    }


def test_explicit_machine_replaces_degraded_enrolled_machine_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if drift on the replaced enrolled machine still blocked doctor readiness."""
    from ai_dlc import provision

    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path, {"LINEAR_SANDBOX_TOKEN": "present"})
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    paths.machine_file("laptop").unlink()
    machine = tmp_path / "replacement-machine.toml"
    machine.write_text("schema = 4\n")
    monkeypatch.setattr(provision, "doctor", lambda *args, **kwargs: {"ready": True})

    result = service.doctor(tmp_path, machine=machine)

    assert result["ready"] is True
    assert result["machine_status"]["ready"] is True
    assert result["machine_status"]["machine"]["path"] == str(machine)
    assert result["machine_checks"] == {"available": True, "unavailable": []}


def test_explicit_machine_does_not_hide_a_corrupt_active_personal_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if machine replacement made a corrupt unreplaced personal cache ready."""
    from ai_dlc import provision

    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    active = read_lock(paths)
    (
        paths.profile_root(active.profile_id, active.resolved_commit) / active.profile_file
    ).write_text("corrupt\n")
    machine = tmp_path / "replacement-machine.toml"
    machine.write_text("schema = 4\n")
    monkeypatch.setattr(provision, "doctor", lambda *args, **kwargs: {"ready": True})

    result = service.doctor(tmp_path, machine=machine)

    assert result["ready"] is False
    assert result["machine_status"]["ready"] is False
    assert result["machine_status"]["machine"] == {
        "path": str(machine),
        "exists": True,
        "override": True,
    }
    assert result["machine_checks"] == {
        "available": False,
        "unavailable": ["verified profile cache", "complete user-agent readiness"],
    }


@pytest.mark.parametrize(
    ("content", "error"),
    [(None, FileNotFoundError), ("schema = [\n", tomllib.TOMLDecodeError)],
)
def test_doctor_rejects_an_invalid_or_missing_explicit_machine_file(
    tmp_path: Path, content: str | None, error: type[Exception]
):
    """Would fail if an explicit bad machine binding were silently ignored."""
    service, _ = manager(tmp_path)
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text("schema = 4\n")
    machine = tmp_path / "machine.toml"
    if content is not None:
        machine.write_text(content)

    with pytest.raises(error):
        service.doctor(root, machine=machine)


def test_plan_uses_only_the_verified_active_profile_and_machine_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if plan fetched, selected another binding, or changed local state."""
    from ai_dlc import provision

    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    machine_file = configure_active_machine(paths)
    active = read_lock(paths)
    active_profile = (
        paths.profile_root(active.profile_id, active.resolved_commit) / active.profile_file
    )
    before = {
        path: path.read_bytes()
        for root in [paths.config_root, paths.cache_root]
        for path in root.rglob("*")
        if path.is_file()
    }
    calls: list[tuple[Path, bool, Path | None, Path | None, object]] = []

    def plan_boundary(
        profile: Path,
        headless: bool = False,
        system: str | None = None,
        architecture: str | None = None,
        home: Path | None = None,
        machine: Path | None = None,
        environ=None,
    ) -> dict[str, object]:
        del system, architecture
        calls.append((profile, headless, home, machine, environ))
        return {"commands": [], "agent_configuration": {"applied": False}}

    monkeypatch.setattr(provision, "machine_plan", plan_boundary)

    result = service.plan(headless=True)

    after = {
        path: path.read_bytes()
        for root in [paths.config_root, paths.cache_root]
        for path in root.rglob("*")
        if path.is_file()
    }
    assert calls == [(active_profile, True, service.home, machine_file, service.environ)]
    assert result["lock"]["resolved_commit"] == active.resolved_commit
    assert result["commands"] == []
    assert after == before


def test_apply_returns_active_lock_identity_with_the_reconciliation_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if apply omitted lock identity or reconciled without the active binding."""
    from ai_dlc import provision

    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    machine_file = configure_active_machine(paths)
    active = read_lock(paths)
    active_profile = (
        paths.profile_root(active.profile_id, active.resolved_commit) / active.profile_file
    )
    calls: list[tuple[Path, bool, Path | None, Path | None, object]] = []

    def apply_boundary(
        profile: Path,
        headless: bool = False,
        home: Path | None = None,
        machine: Path | None = None,
        environ=None,
    ) -> dict[str, object]:
        calls.append((profile, headless, home, machine, environ))
        return {"ready": True, "applied": [["mise", "install"]]}

    monkeypatch.setattr(provision, "machine_apply", apply_boundary)

    result = service.apply(headless=True)

    assert calls == [(active_profile, True, service.home, machine_file, service.environ)]
    assert result["lock"] == active.model_dump(by_alias=True)
    assert result["ready"] is True
    assert result["applied"] == [["mise", "install"]]


def test_sync_preview_fetches_a_moved_ref_and_preserves_lock_and_clients(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if preview activated a candidate or rewrote an agent client."""
    from ai_dlc import provision

    source, old_commit = disposable_profile(tmp_path)
    service, paths = manager(tmp_path, {"LINEAR_SANDBOX_TOKEN": "present"})
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    machine_file = configure_active_machine(paths)
    old_lock = paths.lock_file.read_bytes()
    new_commit = advance_profile(source, suffix="python")
    calls: list[tuple[Path, Path | None, object]] = []

    def plan_boundary(
        profile: Path,
        headless: bool = False,
        system: str | None = None,
        architecture: str | None = None,
        home: Path | None = None,
        machine: Path | None = None,
        environ=None,
    ) -> dict[str, object]:
        del headless, system, architecture, home
        calls.append((profile, machine, environ))
        return {"credentials": [{"id": "linear-sandbox", "present": True}]}

    monkeypatch.setattr(provision, "machine_plan", plan_boundary)

    result = service.sync()

    assert calls == [
        (
            paths.profile_root("portable-development", new_commit) / "ai-dlc-profile.toml",
            machine_file,
            service.environ,
        )
    ]
    assert result["applied"] is False
    assert result["idempotent"] is False
    assert result["changes"]["resolved_commit"] == {"from": old_commit, "to": new_commit}
    assert '-include = ["core", "codex"]' in result["changes"]["configuration"]
    assert '+include = ["core", "python"]' in result["changes"]["configuration"]
    assert result["readiness"]["ready"] is True
    assert paths.lock_file.read_bytes() == old_lock
    assert not (service.home / ".claude.json").exists()
    assert not (service.home / ".codex").exists()


def test_sync_apply_reconciles_candidate_before_activating_its_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if sync activated the new commit before candidate reconciliation."""
    from ai_dlc import provision

    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path, {"LINEAR_SANDBOX_TOKEN": "present"})
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    machine_file = configure_active_machine(paths)
    old_lock = paths.lock_file.read_bytes()
    new_commit = advance_profile(source, suffix="python")
    events: list[str] = []

    def plan_boundary(*args, **kwargs) -> dict[str, object]:
        del args, kwargs
        assert paths.lock_file.read_bytes() == old_lock
        events.append("plan")
        return {"credentials": [{"id": "linear-sandbox", "present": True}]}

    def apply_boundary(
        profile: Path,
        headless: bool = False,
        home: Path | None = None,
        machine: Path | None = None,
        environ=None,
    ) -> dict[str, object]:
        del headless, home
        assert profile == (
            paths.profile_root("portable-development", new_commit) / "ai-dlc-profile.toml"
        )
        assert machine == machine_file
        assert environ is service.environ
        assert paths.lock_file.read_bytes() == old_lock
        events.append("apply")
        return {"ready": True, "applied": [["mise", "install"]]}

    monkeypatch.setattr(provision, "machine_plan", plan_boundary)
    monkeypatch.setattr(provision, "machine_apply", apply_boundary)

    result = service.sync(apply=True)

    assert events == ["plan", "apply"]
    assert read_lock(paths).resolved_commit == new_commit
    assert result["applied"] is True
    assert result["reconciliation"]["ready"] is True


def test_failed_sync_reconciliation_preserves_lock_and_labels_package_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if a partial package operation activated or obscured the candidate."""
    from ai_dlc import provision

    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    configure_active_machine(paths)
    old_lock = paths.lock_file.read_bytes()
    new_commit = advance_profile(source, suffix="python")
    partial = tmp_path / "package-side-effect"
    monkeypatch.setattr(provision, "machine_plan", lambda *args, **kwargs: {"credentials": []})

    def fail_after_package_side_effect(*args, **kwargs):
        del args, kwargs
        partial.write_text("installed before failure")
        raise RuntimeError("package manager failed")

    monkeypatch.setattr(provision, "machine_apply", fail_after_package_side_effect)

    with pytest.raises(RuntimeError, match="reconciliation.*package-side effects.*partial"):
        service.sync(apply=True)

    assert paths.lock_file.read_bytes() == old_lock
    assert partial.is_file()
    assert (
        paths.profile_root("portable-development", new_commit) / "ai-dlc-profile.toml"
    ).is_file()


@pytest.mark.parametrize("failure", ["invalid", "corrupt", "fetch"])
def test_sync_candidate_failures_preserve_the_active_lock(tmp_path: Path, failure: str):
    """Would fail if validation, cache integrity, or fetch failure changed active state."""
    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    configure_active_machine(paths)
    old_lock = paths.lock_file.read_bytes()
    active = read_lock(paths)
    if failure == "invalid":
        profile = source / "ai-dlc-profile.toml"
        profile.write_text(PROFILE + '\napi_key = "synthetic-secret"\n')
        git(source, "add", "--", "ai-dlc-profile.toml")
        git(source, "commit", "-m", "invalid candidate")
    elif failure == "corrupt":
        (
            paths.profile_root(active.profile_id, active.resolved_commit) / active.profile_file
        ).write_text("corrupt\n")
    else:
        source.rename(tmp_path / "source-unavailable")

    with pytest.raises((RuntimeError, ValueError)):
        service.sync()

    assert paths.lock_file.read_bytes() == old_lock


def test_sync_to_the_active_commit_is_idempotent_without_reconciliation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if an unchanged source caused package or client side effects."""
    from ai_dlc import provision

    source, commit = disposable_profile(tmp_path)
    service, paths = manager(tmp_path)
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    configure_active_machine(paths)
    old_lock = paths.lock_file.read_bytes()

    def unexpected(*args, **kwargs):
        del args, kwargs
        raise AssertionError("idempotent sync reconciled an unchanged commit")

    monkeypatch.setattr(provision, "machine_plan", unexpected)
    monkeypatch.setattr(provision, "machine_apply", unexpected)

    result = service.sync(apply=True)

    assert result["idempotent"] is True
    assert result["lock"]["resolved_commit"] == commit
    assert paths.lock_file.read_bytes() == old_lock


def test_machine_doctor_combines_status_and_shared_checks_without_environment_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if doctor skipped active layers or exposed a credential value."""
    from ai_dlc import provision

    marker = "credential-value-that-must-not-escape-doctor"
    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path, {"LINEAR_SANDBOX_TOKEN": marker})
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    machine_file = configure_active_machine(paths)
    active = read_lock(paths)
    active_profile = (
        paths.profile_root(active.profile_id, active.resolved_commit) / active.profile_file
    )
    root = tmp_path / "project"
    root.mkdir()
    calls: list[dict[str, object]] = []

    def doctor_boundary(
        selected_root: Path,
        target: str = "local",
        machine: Path | None = None,
        personal: Path | None = None,
        home: Path | None = None,
        environ=None,
    ) -> dict[str, object]:
        calls.append(
            {
                "root": selected_root,
                "target": target,
                "machine": machine,
                "personal": personal,
                "home": home,
                "environ": environ,
            }
        )
        return {
            "ready": True,
            "runtime_drift": [],
            "user_agents": {"clean": True, "changed": [], "applied": False},
            "signins": [],
            "credentials": [{"id": "linear-sandbox", "present": True}],
            "provider_health": [{"provider": "linear-sandbox", "ready": True}],
        }

    monkeypatch.setattr(provision, "doctor", doctor_boundary)

    result = service.doctor(root, target="container")

    assert calls == [
        {
            "root": root,
            "target": "container",
            "machine": machine_file,
            "personal": active_profile,
            "home": service.home,
            "environ": service.environ,
        }
    ]
    assert result["ready"] is True
    assert result["machine_status"]["cache"] == "healthy"
    assert result["runtime_drift"] == []
    assert result["user_agents"]["clean"] is True
    assert result["credentials"][0]["present"] is True
    assert result["provider_health"][0]["ready"] is True
    assert marker not in repr(result)


@pytest.mark.parametrize("condition", ["unenrolled", "missing-machine", "corrupt-cache"])
def test_machine_doctor_returns_partial_diagnostics_when_enrollment_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, condition: str
):
    """Would fail if a known enrollment problem made doctor raise or fetch."""
    from ai_dlc import provision

    service, paths = manager(tmp_path)
    if condition != "unenrolled":
        source, _ = disposable_profile(tmp_path)
        service.enroll(str(source), "portable-development", "laptop", apply=True)
        if condition == "missing-machine":
            paths.machine_file("laptop").unlink()
        else:
            active = read_lock(paths)
            (
                paths.profile_root(active.profile_id, active.resolved_commit) / active.profile_file
            ).write_text("corrupt\n")
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text("schema = 4\n")
    calls: list[tuple[Path | None, Path | None]] = []

    def doctor_boundary(
        selected_root: Path,
        target: str = "local",
        machine: Path | None = None,
        personal: Path | None = None,
        home: Path | None = None,
        environ=None,
    ) -> dict[str, object]:
        del selected_root, target, home, environ
        calls.append((personal, machine))
        return {"ready": True, "runtime_drift": [], "credentials": []}

    def unexpected_fetch(*args, **kwargs):
        del args, kwargs
        raise AssertionError("doctor contacted the profile source")

    monkeypatch.setattr(provision, "doctor", doctor_boundary)
    monkeypatch.setattr(profile_source, "_resolve_commit", unexpected_fetch)

    result = service.doctor(root)

    assert result["ready"] is False
    assert result["machine_status"]["ready"] is False
    assert result["machine_checks"]["available"] is False
    assert result["machine_checks"]["unavailable"]
    assert len(calls) == 1
    if condition == "unenrolled":
        assert calls == [(None, None)]
    elif condition == "missing-machine":
        assert calls[0][0] is not None
        assert calls[0][1] is None
    else:
        assert calls[0][0] is None


def test_manager_injected_environment_flows_through_status_plan_apply_and_doctor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if any lifecycle method consulted ambient credential state."""
    from ai_dlc import provision
    from ai_dlc.config import resolve_files
    from ai_dlc.credentials import credential_status

    marker = "injected-machine-credential"
    monkeypatch.delenv("LINEAR_SANDBOX_TOKEN", raising=False)
    source, _ = disposable_profile(tmp_path)
    service, paths = manager(tmp_path, {"LINEAR_SANDBOX_TOKEN": marker})
    service.enroll(str(source), "portable-development", "laptop", apply=True)
    configure_active_machine(paths)
    received_environments: list[object] = []

    def readiness(profile: Path, machine: Path | None, environ) -> list[dict[str, object]]:
        received_environments.append(environ)
        return credential_status(
            resolve_files(personal=profile, machine=machine).values,
            environ=environ,
        )

    def plan_boundary(
        profile: Path,
        headless: bool = False,
        system: str | None = None,
        architecture: str | None = None,
        home: Path | None = None,
        machine: Path | None = None,
        environ=None,
    ) -> dict[str, object]:
        del headless, system, architecture, home
        return {"credentials": readiness(profile, machine, environ)}

    def apply_boundary(
        profile: Path,
        headless: bool = False,
        home: Path | None = None,
        machine: Path | None = None,
        environ=None,
    ) -> dict[str, object]:
        del headless, home
        return {"credentials": readiness(profile, machine, environ), "applied": []}

    def doctor_boundary(
        root: Path,
        target: str = "local",
        machine: Path | None = None,
        personal: Path | None = None,
        home: Path | None = None,
        environ=None,
    ) -> dict[str, object]:
        del root, target, home
        return {
            "ready": True,
            "credentials": readiness(personal, machine, environ),
            "provider_health": [{"provider": "linear-sandbox", "ready": True}],
        }

    monkeypatch.setattr(provision, "machine_plan", plan_boundary)
    monkeypatch.setattr(provision, "machine_apply", apply_boundary)
    monkeypatch.setattr(provision, "doctor", doctor_boundary)

    status = service.status()
    plan = service.plan()
    applied = service.apply()
    diagnosed = service.doctor(tmp_path)

    assert status["credentials"][0]["present"] is True
    assert plan["credentials"][0]["present"] is True
    assert applied["credentials"][0]["present"] is True
    assert diagnosed["credentials"][0]["present"] is True
    assert diagnosed["provider_health"][0]["ready"] is True
    assert received_environments == [service.environ, service.environ, service.environ]
    assert marker not in repr((status, plan, applied, diagnosed))


def test_legacy_default_manifest_migration_syncs_unchanged_and_after_ref_movement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if legacy sync guessed identity compatibility from the filename."""
    from ai_dlc import provision

    source, first_commit = disposable_profile(tmp_path, manifest=LEGACY_PROFILE)
    service, paths = manager(tmp_path)
    service.migrate(
        str(source),
        "ai-dlc-profile.toml",
        "portable-development",
        "laptop",
        apply=True,
    )
    unchanged = service.sync()
    profile = source / "ai-dlc-profile.toml"
    profile.write_text(LEGACY_PROFILE.replace('["core", "codex"]', '["core", "python"]'))
    git(source, "add", "--", "ai-dlc-profile.toml")
    git(source, "commit", "-m", "advance legacy profile")
    second_commit = git(source, "rev-parse", "HEAD")
    monkeypatch.setattr(provision, "machine_plan", lambda *args, **kwargs: {"credentials": []})
    monkeypatch.setattr(
        provision,
        "machine_apply",
        lambda *args, **kwargs: {"ready": True, "applied": []},
    )

    moved = service.sync(apply=True)

    assert unchanged["idempotent"] is True
    assert unchanged["lock"]["resolved_commit"] == first_commit
    assert unchanged["lock"]["profile_file"] == "ai-dlc-profile.toml"
    assert moved["applied"] is True
    assert moved["lock"]["resolved_commit"] == second_commit
    assert moved["lock"]["profile_file"] == "ai-dlc-profile.toml"
    assert read_lock(paths).resolved_commit == second_commit
