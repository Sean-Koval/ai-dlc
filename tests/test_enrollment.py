import hashlib
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError


def valid_lock(**overrides):
    values = {
        "profile_id": "personal-profile",
        "source": "https://example.test/profiles.git",
        "requested_ref": "main",
        "resolved_commit": "a" * 40,
        "content_sha256": "b" * 64,
        "machine_id": "workstation-01",
        "subdirectory": "profiles/default",
        "profile_file": "ai-dlc-profile.toml",
    }
    values.update(overrides)
    return values


def test_enrollment_paths_use_explicit_xdg_roots(tmp_path):
    from ai_dlc.enrollment import EnrollmentPaths

    paths = EnrollmentPaths.from_environment(
        environ={
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "XDG_STATE_HOME": str(tmp_path / "state"),
        }
    )

    assert paths.lock_file == tmp_path / "config/ai-dlc/enrollment.toml"
    assert (
        paths.machine_file("workstation-01")
        == tmp_path / "config/ai-dlc/machines/workstation-01.toml"
    )
    assert paths.profile_root("personal-profile", "a" * 40) == (
        tmp_path / "cache/ai-dlc/profiles/personal-profile" / ("a" * 40)
    )
    assert paths.state_root == tmp_path / "state/ai-dlc"


def test_enrollment_paths_fall_back_to_xdg_locations_under_supplied_home(tmp_path):
    from ai_dlc.enrollment import EnrollmentPaths

    paths = EnrollmentPaths.from_environment(home=tmp_path, environ={})

    assert paths.config_root == tmp_path / ".config/ai-dlc"
    assert paths.cache_root == tmp_path / ".cache/ai-dlc"
    assert paths.state_root == tmp_path / ".local/state/ai-dlc"


def test_enrollment_lock_accepts_the_supported_pinned_profile_shape():
    from ai_dlc.enrollment import EnrollmentLock

    lock = EnrollmentLock(**valid_lock(schema=1))

    assert lock.schema == 1
    assert lock.schema_version == 1
    assert lock.profile_id == "personal-profile"
    assert lock.machine_id == "workstation-01"
    assert lock.subdirectory == "profiles/default"
    assert lock.profile_file == "ai-dlc-profile.toml"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", 2),
        ("profile_id", ""),
        ("profile_id", "Personal-profile"),
        ("machine_id", ""),
        ("machine_id", "Workstation-01"),
        ("resolved_commit", "A" * 40),
        ("resolved_commit", "a" * 39),
        ("content_sha256", "B" * 64),
        ("content_sha256", "b" * 63),
        ("subdirectory", "/profiles"),
        ("subdirectory", "../profiles"),
        ("subdirectory", "."),
        ("subdirectory", "profiles//default"),
        ("profile_file", "/ai-dlc-profile.toml"),
        ("profile_file", "../ai-dlc-profile.toml"),
        ("profile_file", "."),
        ("profile_file", ""),
        ("profile_file", "profiles//ai-dlc-profile.toml"),
    ],
)
def test_invalid_enrollment_lock_values_fail_before_write(tmp_path, field, value):
    from ai_dlc.enrollment import EnrollmentLock, EnrollmentPaths

    paths = EnrollmentPaths.from_environment(home=tmp_path, environ={})
    with pytest.raises(ValidationError):
        EnrollmentLock(**valid_lock(**{field: value}))

    assert not paths.lock_file.exists()


def test_unknown_enrollment_lock_fields_fail_before_write(tmp_path):
    from ai_dlc.enrollment import EnrollmentLock, EnrollmentPaths

    paths = EnrollmentPaths.from_environment(home=tmp_path, environ={})
    with pytest.raises(ValidationError):
        EnrollmentLock(**valid_lock(unexpected="value"))

    assert not paths.lock_file.exists()


def test_internal_schema_alias_is_rejected_as_an_unknown_lock_field(tmp_path):
    from ai_dlc.enrollment import EnrollmentLock, EnrollmentPaths

    paths = EnrollmentPaths.from_environment(home=tmp_path, environ={})
    with pytest.raises(ValidationError):
        EnrollmentLock(**valid_lock(schema_version=1))

    assert not paths.lock_file.exists()


def test_write_lock_is_parseable_private_and_leaves_no_temporary_final_file(tmp_path):
    from ai_dlc.enrollment import EnrollmentLock, EnrollmentPaths, read_lock, write_lock

    paths = EnrollmentPaths.from_environment(home=tmp_path, environ={})
    path = write_lock(paths, EnrollmentLock(**valid_lock()))

    assert path == paths.lock_file
    document = tomllib.loads(path.read_text())
    assert document["schema"] == 1
    assert "schema_version" not in document
    assert document["resolved_commit"] == "a" * 40
    assert path.stat().st_mode & 0o777 == 0o600
    assert not list(path.parent.glob(".ai-dlc-*"))
    assert read_lock(paths) == EnrollmentLock(**valid_lock())


def test_enrollment_module_imports_without_warnings_when_warnings_are_errors():
    result = subprocess.run(
        [sys.executable, "-W", "error::UserWarning", "-c", "import ai_dlc.enrollment"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_machine_file_is_private_schema_four_and_is_not_replaced(tmp_path):
    from ai_dlc.enrollment import EnrollmentPaths, ensure_machine_file

    paths = EnrollmentPaths.from_environment(home=tmp_path, environ={})
    path = ensure_machine_file(paths, "workstation-01")

    assert tomllib.loads(path.read_text()) == {"schema": 4}
    assert path.stat().st_mode & 0o777 == 0o600
    original = b"operator-owned = true\n"
    path.write_bytes(original)
    assert ensure_machine_file(paths, "workstation-01") == path
    assert path.read_bytes() == original


def test_machine_file_publish_failure_leaves_no_partial_final_file(tmp_path, monkeypatch):
    import ai_dlc.files
    from ai_dlc.enrollment import EnrollmentPaths, ensure_machine_file

    paths = EnrollmentPaths.from_environment(home=tmp_path, environ={})
    path = paths.machine_file("workstation-01")

    def fail_publish(staged, final):
        assert Path(staged).read_text() == "schema = 4\n"
        assert Path(staged).stat().st_mode & 0o777 == 0o600
        assert not final.exists()
        raise OSError("injected publish failure")

    monkeypatch.setattr(ai_dlc.files.os, "link", fail_publish)
    with pytest.raises(OSError, match="injected publish failure"):
        ensure_machine_file(paths, "workstation-01")

    assert not path.exists()
    assert not list(path.parent.glob(".ai-dlc-*"))


def test_failed_lock_replacement_preserves_prior_bytes_and_cleans_staging_file(
    tmp_path, monkeypatch
):
    import ai_dlc.files
    from ai_dlc.enrollment import EnrollmentLock, EnrollmentPaths, write_lock

    paths = EnrollmentPaths.from_environment(home=tmp_path, environ={})
    write_lock(paths, EnrollmentLock(**valid_lock(requested_ref="old")))
    before = paths.lock_file.read_bytes()

    def fail_replace(staged, final):
        assert Path(staged).read_text()
        assert final == paths.lock_file
        raise OSError("injected replacement failure")

    monkeypatch.setattr(ai_dlc.files.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replacement failure"):
        write_lock(paths, EnrollmentLock(**valid_lock(requested_ref="new")))

    assert paths.lock_file.read_bytes() == before
    assert not list(paths.lock_file.parent.glob(".ai-dlc-*"))


def test_active_profile_file_combines_only_validated_relative_components(tmp_path):
    from ai_dlc.enrollment import EnrollmentLock, EnrollmentPaths, active_profile_file

    paths = EnrollmentPaths.from_environment(home=tmp_path, environ={})
    lock = EnrollmentLock(**valid_lock(subdirectory="", profile_file="profiles/current.toml"))

    assert active_profile_file(paths, lock) == (
        tmp_path / ".cache/ai-dlc/profiles/personal-profile" / ("a" * 40) / "profiles/current.toml"
    )


def test_runtime_resolution_does_not_cross_home_or_xdg_enrollment_roots(tmp_path):
    from ai_dlc.config import resolve_runtime
    from ai_dlc.enrollment import EnrollmentLock, EnrollmentPaths, write_lock

    def enroll(paths: EnrollmentPaths, profile_id: str, workspace: str) -> None:
        content = f'schema = 4\nprofile_id = "{profile_id}"\n'.encode()
        digest = hashlib.sha256(
            b"ai-dlc-profile.toml\0" + str(len(content)).encode("ascii") + b"\0" + content
        ).hexdigest()
        cached_profile = paths.profile_root(profile_id, "a" * 40) / "ai-dlc-profile.toml"
        cached_profile.parent.mkdir(parents=True)
        cached_profile.write_bytes(content)
        machine_file = paths.machine_file("workstation-01")
        machine_file.parent.mkdir(parents=True)
        machine_file.write_text(f'schema = 4\n[paths]\nworkspace = "{workspace}"\n')
        write_lock(
            paths,
            EnrollmentLock(
                profile_id=profile_id,
                source="https://example.test/profiles.git",
                requested_ref="main",
                resolved_commit="a" * 40,
                content_sha256=digest,
                machine_id="workstation-01",
            ),
        )

    first_environment = {
        "XDG_CONFIG_HOME": str(tmp_path / "first-config"),
        "XDG_CACHE_HOME": str(tmp_path / "first-cache"),
    }
    second_environment = {
        "XDG_CONFIG_HOME": str(tmp_path / "second-config"),
        "XDG_CACHE_HOME": str(tmp_path / "second-cache"),
    }
    first = EnrollmentPaths.from_environment(
        home=tmp_path / "first-home", environ=first_environment
    )
    second = EnrollmentPaths.from_environment(
        home=tmp_path / "second-home", environ=second_environment
    )
    enroll(first, "first-profile", "/first")
    enroll(second, "second-profile", "/second")

    first_runtime = resolve_runtime(home=tmp_path / "first-home", environ=first_environment)
    second_runtime = resolve_runtime(home=tmp_path / "second-home", environ=second_environment)

    assert first_runtime.values["profile_id"] == "first-profile"
    assert first_runtime.values["paths"]["workspace"] == "/first"
    assert second_runtime.values["profile_id"] == "second-profile"
    assert second_runtime.values["paths"]["workspace"] == "/second"
