import os
import subprocess
from pathlib import Path

import pytest

from ai_dlc import profile_source
from ai_dlc.enrollment import EnrollmentLock, EnrollmentPaths
from ai_dlc.profile_source import (
    ProfileCandidate,
    redact_source,
    resolve_profile_source,
    source_portability,
    verify_cached_profile,
)

NORMAL_MANIFEST = """\
schema = 4
profile_id = "test-development"

[modules]
include = ["core"]

[credentials.linear-sandbox]
description = "Linear sandbox access"
required_by = ["provider.linear-sandbox"]
"""


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        check=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def disposable_git_repository(
    tmp_path: Path,
    *,
    manifest: str = NORMAL_MANIFEST,
    profile_path: str = "ai-dlc-profile.toml",
) -> tuple[Path, str]:
    repository = tmp_path / "source"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    git(repository, "config", "user.name", "AI-DLC Test")
    git(repository, "config", "user.email", "ai-dlc@example.test")
    path = repository / profile_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest)
    git(repository, "add", "--", profile_path)
    git(repository, "commit", "-m", "add profile")
    return repository, git(repository, "rev-parse", "HEAD")


def enrollment_paths(tmp_path: Path) -> EnrollmentPaths:
    return EnrollmentPaths.from_environment(home=tmp_path / "home", environ={})


def lock_for(candidate: ProfileCandidate) -> EnrollmentLock:
    return EnrollmentLock(
        profile_id=candidate.profile_id,
        source=candidate.source,
        requested_ref=candidate.requested_ref,
        resolved_commit=candidate.resolved_commit,
        content_sha256=candidate.content_sha256,
        machine_id="test-machine",
        subdirectory=candidate.subdirectory,
        profile_file=candidate.profile_file,
    )


def cache_snapshot(paths: EnrollmentPaths) -> dict[str, bytes]:
    if not paths.cache_root.exists():
        return {}
    return {
        path.relative_to(paths.cache_root).as_posix(): path.read_bytes()
        for path in paths.cache_root.rglob("*")
        if path.is_file()
    }


def test_resolution_pins_exact_commit_and_has_deterministic_bundle_digest(tmp_path: Path):
    repository, commit = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)

    candidate = resolve_profile_source(str(repository), "test-development", "main", paths)

    assert candidate.resolved_commit == commit
    assert len(candidate.resolved_commit) == 40
    assert candidate.content_sha256 == (
        "3bc76f2b624ea58774b9980efd8c775f7fe07b597c9e356a766e6b4dbdca5b7c"
    )
    assert len(candidate.content_sha256) == 64
    assert candidate.cache_root == paths.profile_root("test-development", commit)


def test_cache_contains_only_declared_profile_without_git_or_unrelated_files(tmp_path: Path):
    repository, _ = disposable_git_repository(tmp_path)
    (repository / "unrelated.txt").write_text("do not cache\n")
    (repository / "nested").mkdir()
    (repository / "nested/also-unrelated.txt").write_text("do not cache\n")
    git(repository, "add", "--", "unrelated.txt", "nested/also-unrelated.txt")
    git(repository, "commit", "-m", "add unrelated files")
    paths = enrollment_paths(tmp_path)

    candidate = resolve_profile_source(str(repository), "test-development", "main", paths)

    entries = sorted(
        path.relative_to(candidate.cache_root).as_posix()
        for path in candidate.cache_root.rglob("*")
    )
    assert entries == ["ai-dlc-profile.toml"]
    assert not (candidate.cache_root / ".git").exists()
    assert (candidate.cache_root / "ai-dlc-profile.toml").read_text() == NORMAL_MANIFEST


def test_relative_subdirectory_selects_only_its_declared_profile(tmp_path: Path):
    repository, commit = disposable_git_repository(
        tmp_path, profile_path="profiles/development/ai-dlc-profile.toml"
    )
    (repository / "profiles/development/notes.txt").write_text("not part of the profile\n")
    git(repository, "add", "--", "profiles/development/notes.txt")
    git(repository, "commit", "-m", "add nearby unrelated file")
    commit = git(repository, "rev-parse", "HEAD")
    paths = enrollment_paths(tmp_path)

    candidate = resolve_profile_source(
        str(repository),
        "test-development",
        "main",
        paths,
        subdirectory="profiles/development",
    )

    assert candidate.resolved_commit == commit
    assert candidate.subdirectory == "profiles/development"
    assert (candidate.cache_root / "profiles/development/ai-dlc-profile.toml").is_file()
    assert not (candidate.cache_root / "profiles/development/notes.txt").exists()


@pytest.mark.parametrize(
    ("subdirectory", "profile_file"),
    [
        ("../outside", "ai-dlc-profile.toml"),
        ("profiles/./development", "ai-dlc-profile.toml"),
        ("", "../ai-dlc-profile.toml"),
        ("", "/tmp/ai-dlc-profile.toml"),
    ],
)
def test_relative_profile_selection_cannot_escape_or_use_unnormalized_paths(
    tmp_path: Path, subdirectory: str, profile_file: str
):
    repository, _ = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)

    with pytest.raises(ValueError, match="relative|normalized"):
        resolve_profile_source(
            str(repository),
            "test-development",
            "main",
            paths,
            subdirectory=subdirectory,
            profile_file=profile_file,
        )

    assert cache_snapshot(paths) == {}


def test_declared_profile_id_must_match_requested_identity(tmp_path: Path):
    repository, _ = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)

    with pytest.raises(ValueError, match="profile_id"):
        resolve_profile_source(str(repository), "other-development", "main", paths)

    assert cache_snapshot(paths) == {}


def test_normal_resolution_requires_declared_profile_identity(tmp_path: Path):
    repository, _ = disposable_git_repository(
        tmp_path, manifest=NORMAL_MANIFEST.replace('profile_id = "test-development"\n', "")
    )
    paths = enrollment_paths(tmp_path)

    with pytest.raises(ValueError, match="profile_id"):
        resolve_profile_source(str(repository), "test-development", "main", paths)

    assert cache_snapshot(paths) == {}


def test_legacy_resolution_accepts_explicit_profile_file_without_identity(tmp_path: Path):
    legacy = NORMAL_MANIFEST.replace('profile_id = "test-development"\n', "")
    repository, commit = disposable_git_repository(
        tmp_path, manifest=legacy, profile_path="legacy/profile.toml"
    )
    paths = enrollment_paths(tmp_path)

    candidate = resolve_profile_source(
        str(repository),
        "test-development",
        "main",
        paths,
        profile_file="legacy/profile.toml",
        allow_legacy_identity=True,
    )

    assert candidate.profile_id == "test-development"
    assert candidate.resolved_commit == commit
    assert (candidate.cache_root / "legacy/profile.toml").read_text() == legacy


def test_legacy_resolution_still_rejects_a_different_declared_identity(tmp_path: Path):
    repository, _ = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)

    with pytest.raises(ValueError, match="profile_id"):
        resolve_profile_source(
            str(repository),
            "other-development",
            "main",
            paths,
            allow_legacy_identity=True,
        )


def test_secret_shaped_profile_field_is_rejected_before_cache_activation(tmp_path: Path):
    secret_manifest = NORMAL_MANIFEST + '\n[providers.linear]\ntoken = "must-not-persist"\n'
    repository, _ = disposable_git_repository(tmp_path, manifest=secret_manifest)
    paths = enrollment_paths(tmp_path)

    with pytest.raises(ValueError, match="credential value"):
        resolve_profile_source(str(repository), "test-development", "main", paths)

    assert cache_snapshot(paths) == {}


@pytest.mark.parametrize(
    "field",
    [
        "tokens",
        "api_token",
        "api_tokens",
        "api-token",
        "api-tokens",
        "apiToken",
        "apiTokens",
        "APIToken",
        "access_token",
        "access-token",
        "client_secret",
        "client-secret",
        "clientSecret",
        "accessToken",
        "private_key",
    ],
)
def test_common_secret_shaped_fields_are_rejected_before_cache_activation(
    tmp_path: Path, field: str
):
    manifest = NORMAL_MANIFEST + f'\n[providers.custom]\n"{field}" = "synthetic-value"\n'
    repository, _ = disposable_git_repository(tmp_path, manifest=manifest)
    paths = enrollment_paths(tmp_path)

    with pytest.raises(ValueError, match="credential value"):
        resolve_profile_source(str(repository), "test-development", "main", paths)

    assert cache_snapshot(paths) == {}


@pytest.mark.parametrize("field", ["max_tokens", "token_count"])
def test_token_metric_fields_reject_literal_strings_before_cache_activation(
    tmp_path: Path, field: str
):
    manifest = NORMAL_MANIFEST + f'\n[providers.custom]\n{field} = "synthetic-value"\n'
    repository, _ = disposable_git_repository(tmp_path, manifest=manifest)
    paths = enrollment_paths(tmp_path)

    with pytest.raises(ValueError, match="credential value"):
        resolve_profile_source(str(repository), "test-development", "main", paths)

    assert cache_snapshot(paths) == {}


def test_benign_secret_field_lookalikes_can_be_cached(tmp_path: Path):
    manifest = (
        NORMAL_MANIFEST
        + """
[providers.custom]
tokenizer = "words"
secretary = "person"
monkey = "animal"
keyboard_layout = "dvorak"
api_version = "v1"
max_tokens = 1024
token_count = 10
"""
    )
    repository, _ = disposable_git_repository(tmp_path, manifest=manifest)
    paths = enrollment_paths(tmp_path)

    candidate = resolve_profile_source(str(repository), "test-development", "main", paths)

    assert (candidate.cache_root / candidate.profile_file).read_text() == manifest


def test_explicit_environment_reference_fields_can_be_cached(tmp_path: Path):
    manifest = (
        NORMAL_MANIFEST
        + """
[providers.custom]
token_env = "CUSTOM_TOKEN"
api_token_env = "CUSTOM_API_TOKEN"
client_secret_env = "CUSTOM_CLIENT_SECRET"
bearer_token_env_var = "CUSTOM_BEARER_TOKEN"
"""
    )
    repository, _ = disposable_git_repository(tmp_path, manifest=manifest)
    paths = enrollment_paths(tmp_path)

    candidate = resolve_profile_source(str(repository), "test-development", "main", paths)

    assert (candidate.cache_root / candidate.profile_file).read_text() == manifest


def test_environment_reference_field_rejects_a_literal_value_before_cache_activation(
    tmp_path: Path,
):
    manifest = NORMAL_MANIFEST + (
        '\n[providers.custom]\napi_token_env = "synthetic-value-not-an-env-name"\n'
    )
    repository, _ = disposable_git_repository(tmp_path, manifest=manifest)
    paths = enrollment_paths(tmp_path)

    with pytest.raises(ValueError, match="credential value"):
        resolve_profile_source(str(repository), "test-development", "main", paths)

    assert cache_snapshot(paths) == {}


def test_symlink_profile_path_is_rejected(tmp_path: Path):
    repository, _ = disposable_git_repository(tmp_path, profile_path="actual.toml")
    os.symlink("actual.toml", repository / "ai-dlc-profile.toml")
    git(repository, "add", "--", "ai-dlc-profile.toml")
    git(repository, "commit", "-m", "add profile symlink")
    paths = enrollment_paths(tmp_path)

    with pytest.raises(ValueError, match="symlink"):
        resolve_profile_source(str(repository), "test-development", "main", paths)

    assert cache_snapshot(paths) == {}


def test_non_regular_profile_path_is_rejected(tmp_path: Path):
    repository, _ = disposable_git_repository(tmp_path)
    (repository / "profile-directory").mkdir()
    (repository / "profile-directory/tracked.txt").write_text("tracked so the directory exists\n")
    git(repository, "add", "--", "profile-directory/tracked.txt")
    git(repository, "commit", "-m", "add profile directory")
    paths = enrollment_paths(tmp_path)

    with pytest.raises(ValueError, match="regular file"):
        resolve_profile_source(
            str(repository),
            "test-development",
            "main",
            paths,
            profile_file="profile-directory",
        )

    assert cache_snapshot(paths) == {}


def test_second_resolution_reuses_existing_byte_identical_cache(tmp_path: Path):
    repository, _ = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)
    first = resolve_profile_source(str(repository), "test-development", "main", paths)
    cached_file = first.cache_root / first.profile_file
    original_bytes = cached_file.read_bytes()
    original_inode = cached_file.stat().st_ino

    second = resolve_profile_source(str(repository), "test-development", "main", paths)

    assert second == first
    assert cached_file.read_bytes() == original_bytes
    assert cached_file.stat().st_ino == original_inode


def test_changed_existing_cache_is_reported_as_corrupt_and_not_replaced(tmp_path: Path):
    repository, _ = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)
    candidate = resolve_profile_source(str(repository), "test-development", "main", paths)
    cached_file = candidate.cache_root / candidate.profile_file
    cached_file.write_bytes(b"corrupt cache bytes\n")

    with pytest.raises(RuntimeError, match="corrupt"):
        resolve_profile_source(str(repository), "test-development", "main", paths)

    assert cached_file.read_bytes() == b"corrupt cache bytes\n"


def test_moved_branch_creates_new_cache_and_preserves_old_verified_cache(tmp_path: Path):
    repository, old_commit = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)
    old_candidate = resolve_profile_source(str(repository), "test-development", "main", paths)
    old_file = old_candidate.cache_root / old_candidate.profile_file
    old_bytes = old_file.read_bytes()

    (repository / "ai-dlc-profile.toml").write_text(NORMAL_MANIFEST + "\n# moved branch\n")
    git(repository, "add", "--", "ai-dlc-profile.toml")
    git(repository, "commit", "-m", "move branch")
    new_commit = git(repository, "rev-parse", "HEAD")
    new_candidate = resolve_profile_source(str(repository), "test-development", "main", paths)

    assert old_candidate.resolved_commit == old_commit
    assert new_candidate.resolved_commit == new_commit
    assert new_candidate.resolved_commit != old_candidate.resolved_commit
    assert new_candidate.cache_root != old_candidate.cache_root
    assert old_file.read_bytes() == old_bytes
    assert verify_cached_profile(lock_for(old_candidate), paths) == old_file


@pytest.mark.parametrize("requested_ref", ["missing-ref", "shared"])
def test_invalid_or_ambiguous_ref_does_not_change_existing_cache(
    tmp_path: Path, requested_ref: str
):
    repository, _ = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)
    resolve_profile_source(str(repository), "test-development", "main", paths)
    before = cache_snapshot(paths)
    if requested_ref == "shared":
        git(repository, "branch", "shared")
        git(repository, "tag", "shared")

    with pytest.raises(RuntimeError, match="Git"):
        resolve_profile_source(str(repository), "test-development", requested_ref, paths)

    assert cache_snapshot(paths) == before
    assert not list(paths.cache_root.parent.glob(".ai-dlc-profile-*"))


@pytest.mark.parametrize("requested_ref_kind", ["head", "commit"])
def test_unadvertised_pseudoref_or_commit_is_rejected_without_changing_cache(
    tmp_path: Path, requested_ref_kind: str
):
    repository, commit = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)
    resolve_profile_source(str(repository), "test-development", "main", paths)
    before = cache_snapshot(paths)
    requested_ref = "HEAD" if requested_ref_kind == "head" else commit

    with pytest.raises(RuntimeError, match="Git"):
        resolve_profile_source(str(repository), "test-development", requested_ref, paths)

    assert cache_snapshot(paths) == before
    assert not list(paths.cache_root.parent.glob(".ai-dlc-profile-*"))


@pytest.mark.parametrize("requested_ref", ["refs/heads/*", "main:refs/heads/copied"])
def test_wildcard_or_refspec_requested_ref_is_rejected(tmp_path: Path, requested_ref: str):
    repository, _ = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)

    with pytest.raises(RuntimeError, match="Git"):
        resolve_profile_source(str(repository), "test-development", requested_ref, paths)

    assert cache_snapshot(paths) == {}
    assert not list(paths.cache_root.parent.glob(".ai-dlc-profile-*"))


def test_requested_ref_is_passed_as_data_without_shell_interpolation(tmp_path: Path):
    repository, _ = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)
    sentinel = tmp_path / "interpolated"

    with pytest.raises(RuntimeError, match="Git"):
        resolve_profile_source(
            str(repository),
            "test-development",
            f"main;touch {sentinel}",
            paths,
        )

    assert not sentinel.exists()
    assert cache_snapshot(paths) == {}


def test_cached_profile_verifies_offline_after_source_disappears(tmp_path: Path):
    repository, _ = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)
    candidate = resolve_profile_source(str(repository), "test-development", "main", paths)
    expected = candidate.cache_root / candidate.profile_file
    repository.rename(tmp_path / "source-unavailable")

    assert verify_cached_profile(lock_for(candidate), paths) == expected


@pytest.mark.parametrize("as_file_url", [False, True])
def test_local_repository_sources_are_nonportable(tmp_path: Path, as_file_url: bool):
    repository, _ = disposable_git_repository(tmp_path)
    paths = enrollment_paths(tmp_path)
    source = repository.as_uri() if as_file_url else str(repository)

    candidate = resolve_profile_source(source, "test-development", "main", paths)

    assert candidate.source == source
    assert candidate.portable is False


@pytest.mark.parametrize(
    "name",
    [
        "local?literal",
        "local#literal",
        "local literal",
    ],
)
def test_literal_query_and_fragment_characters_remain_valid_in_local_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
):
    repository, _ = disposable_git_repository(tmp_path)
    named_source = tmp_path / name
    repository.rename(named_source)
    paths = enrollment_paths(tmp_path)
    monkeypatch.chdir(tmp_path)

    candidate = resolve_profile_source(name, "test-development", "main", paths)

    assert candidate.portable is False


@pytest.mark.parametrize(
    ("source", "portable"),
    [
        ("/profiles/local", False),
        ("file:///profiles/local", False),
        ("https://example.test/profile.git", True),
        ("ssh://git@example.test/profile.git", True),
        ("git@example.test:profile.git", True),
        ("C:/profiles/local", False),
    ],
)
def test_source_portability_classifies_supported_source_syntax(source: str, portable: bool):
    assert source_portability(source) is portable


@pytest.mark.parametrize(
    "source",
    [
        "https:profile-user:synthetic-credential@example.test/profile.git",
        "https://example.test%3Fsynthetic-credential/profile.git",
        "https://example.test%EF%BC%8Fsynthetic-credential/profile.git",
    ],
)
def test_malformed_or_encoded_url_syntax_is_nonportable_and_redacted(source: str):
    assert source_portability(source) is False
    assert redact_source(source) == "<redacted profile source>"


def test_cleartext_http_source_fails_closed_before_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    paths = enrollment_paths(tmp_path)
    source = "http://example.test/profile.git"
    git_calls: list[tuple[object, ...]] = []

    def record_git(*arguments: object, **keywords: object) -> str:
        git_calls.append((*arguments, keywords))
        return ""

    monkeypatch.setattr(profile_source, "_run_git", record_git)

    with pytest.raises(ValueError) as raised:
        resolve_profile_source(source, "test-development", "main", paths)

    assert str(raised.value) == "profile source is invalid"
    assert source_portability(source) is False
    assert redact_source(source) == "<redacted profile source>"
    assert git_calls == []
    assert cache_snapshot(paths) == {}


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("credential-helper::synthetic-credential", id="git-transport-helper"),
        pytest.param(
            "https%3A//profile-user:synthetic-credential@example.test/profile.git",
            id="encoded-colon-upper",
        ),
        pytest.param(
            "https%3a//profile-user:synthetic-credential@example.test/profile.git",
            id="encoded-colon-lower",
        ),
        pytest.param(
            "https://example.test/profile%2Fsynthetic-credential.git",
            id="encoded-slash-upper",
        ),
        pytest.param(
            "ssh://git@example.test/profile%2fsynthetic-credential.git",
            id="encoded-slash-lower",
        ),
        pytest.param("example.test:profile%40synthetic-credential.git", id="encoded-at"),
        pytest.param("./profile%3Fsynthetic-credential.git", id="encoded-query"),
        pytest.param("./profile%23synthetic-credential.git", id="encoded-fragment"),
        pytest.param(
            "https://example.test/profile%26synthetic-credential.git",
            id="encoded-sub-delimiter",
        ),
    ],
)
def test_ambiguous_source_syntax_fails_closed_before_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
):
    """Would fail if ambiguous Git/URI syntax bypassed the shared classifier."""
    paths = enrollment_paths(tmp_path)
    git_calls: list[tuple[object, ...]] = []

    def record_git(*arguments: object) -> str:
        git_calls.append(arguments)
        return ""

    monkeypatch.setattr(profile_source, "_run_git", record_git)

    with pytest.raises(ValueError) as raised:
        resolve_profile_source(source, "test-development", "main", paths)

    assert str(raised.value) == "profile source is invalid"
    assert raised.value.__cause__ is None
    assert "synthetic-credential" not in str(raised.value)
    assert source_portability(source) is False
    assert redact_source(source) == "<redacted profile source>"
    assert git_calls == []
    assert cache_snapshot(paths) == {}


@pytest.mark.parametrize(
    "source",
    [
        "",
        " https://profile-user:synthetic-credential@example.test/profile.git",
        "\thttps://profile-user:synthetic-credential@example.test/profile.git",
        "\nhttps://profile-user:synthetic-credential@example.test/profile.git",
        "https://profile-user:synthetic-credential@example.test/profile.git ",
        "https://profile-user:synthetic-credential@example.test/profile.git\n",
        "https：//profile-user:synthetic-credential@example.test/profile.git",
        "https://example.test/profile\u2060synthetic-credential.git",
        "https://example.test/profile\u202esynthetic-credential.git",
        "local\u2028synthetic-credential",
        "local\u1680synthetic-credential",
        "local\ue000synthetic-credential",
        "local\ufdd0synthetic-credential",
    ],
)
def test_source_lexical_safety_is_enforced_before_git_or_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
):
    """Would fail if unsafe source text fell through to a local or SCP Git source."""
    paths = enrollment_paths(tmp_path)
    git_calls: list[tuple[object, ...]] = []

    def record_git(*arguments: object) -> str:
        git_calls.append(arguments)
        return ""

    monkeypatch.setattr(profile_source, "_run_git", record_git)

    with pytest.raises(ValueError) as raised:
        resolve_profile_source(source, "test-development", "main", paths)

    assert str(raised.value) == "profile source is invalid"
    assert raised.value.__cause__ is None
    assert "synthetic-credential" not in str(raised.value)
    assert redact_source(source) == "<redacted profile source>"
    assert git_calls == []
    assert cache_snapshot(paths) == {}


@pytest.mark.parametrize("codepoint", [*range(32), 127])
def test_every_ascii_control_and_del_is_rejected_before_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    codepoint: int,
):
    """Would fail if URL parsing erased or tolerated an ASCII control character."""
    paths = enrollment_paths(tmp_path)
    git_calls: list[tuple[object, ...]] = []
    source = f"https://example.test/profile{chr(codepoint)}synthetic-credential.git"

    def record_git(*arguments: object) -> str:
        git_calls.append(arguments)
        return ""

    monkeypatch.setattr(profile_source, "_run_git", record_git)

    with pytest.raises(ValueError) as raised:
        resolve_profile_source(source, "test-development", "main", paths)

    assert str(raised.value) == "profile source is invalid"
    assert "synthetic-credential" not in str(raised.value)
    assert redact_source(source) == "<redacted profile source>"
    assert git_calls == []
    assert cache_snapshot(paths) == {}


@pytest.mark.parametrize(
    "source",
    [
        "https://:443/synthetic-credential.git",
        "ssh://git@/synthetic-credential.git",
        "http://profile-user@example.test/synthetic-credential.git",
        "https://profile-user@example.test/synthetic-credential.git",
        "file://profile-user@localhost/synthetic-credential.git",
        "https://example_test/synthetic-credential.git",
        "https://-example.test/synthetic-credential.git",
        "https://example..test/synthetic-credential.git",
        "https://exam!ple.test/synthetic-credential.git",
        "https://example.test\\synthetic-credential.git",
        "https://example.test/path\\synthetic-credential.git",
        "https://example.test:/synthetic-credential.git",
        "https://example.test:0/synthetic-credential.git",
        "https://example.test:65536/synthetic-credential.git",
        "git://example.test/synthetic-credential.git",
        "nested/git://example.test/synthetic-credential.git",
    ],
)
def test_malformed_or_unsupported_urls_fail_closed_before_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
):
    """Would fail if noncanonical URL authority or scheme syntax reached Git."""
    paths = enrollment_paths(tmp_path)
    git_calls: list[tuple[object, ...]] = []

    def record_git(*arguments: object) -> str:
        git_calls.append(arguments)
        return ""

    monkeypatch.setattr(profile_source, "_run_git", record_git)

    with pytest.raises(ValueError) as raised:
        resolve_profile_source(source, "test-development", "main", paths)

    assert str(raised.value) == "profile source is invalid"
    assert "synthetic-credential" not in str(raised.value)
    assert source_portability(source) is False
    assert redact_source(source) == "<redacted profile source>"
    assert git_calls == []
    assert cache_snapshot(paths) == {}


@pytest.mark.parametrize(
    "source",
    [
        "@example.test:synthetic-credential.git",
        "git@:synthetic-credential.git",
        "example.test:",
        "git:profile-user:synthetic-credential@example.test/profile.git",
        "profile-user:synthetic-credential@example.test/profile.git",
        "example_test:synthetic-credential.git",
    ],
)
def test_malformed_scp_intent_fails_closed_before_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
):
    """Would fail if malformed SCP syntax were reinterpreted as a local repository."""
    paths = enrollment_paths(tmp_path)
    git_calls: list[tuple[object, ...]] = []

    def record_git(*arguments: object) -> str:
        git_calls.append(arguments)
        return ""

    monkeypatch.setattr(profile_source, "_run_git", record_git)

    with pytest.raises(ValueError) as raised:
        resolve_profile_source(source, "test-development", "main", paths)

    assert str(raised.value) == "profile source is invalid"
    assert "synthetic-credential" not in str(raised.value)
    assert redact_source(source) == "<redacted profile source>"
    assert git_calls == []
    assert cache_snapshot(paths) == {}


def test_redact_source_is_total_for_arbitrary_unsafe_unicode_strings():
    """Would fail if legacy status could raise or return unsafe Unicode source text."""
    unsafe_sources = [
        "\ud800",
        "local\u0085synthetic-credential",
        "local\u200esynthetic-credential",
        "https：//profile-user:synthetic-credential@example.test/profile.git",
        "https://example.test／synthetic-credential@example.test/profile.git",
        "https://example.test:" + ("9" * 5000),
    ]

    assert [redact_source(source) for source in unsafe_sources] == [
        "<redacted profile source>",
        "<redacted profile source>",
        "<redacted profile source>",
        "<redacted profile source>",
        "<redacted profile source>",
        "<redacted profile source>",
    ]


@pytest.mark.parametrize(
    ("source", "portable"),
    [
        ("https://example.test/profile.git", True),
        ("https://[2001:db8::1]/profile.git", True),
        ("ssh://git@example.test:22/profile.git", True),
        ("ssh://example.test/profile.git", True),
        ("ssh://git@[2001:db8::1]:22/profile.git", True),
        ("git@example.test:profile?literal#literal.git", True),
        ("example.test:profile.git", True),
        ("./example.test:profile.git", False),
        ("local?literal#literal", False),
    ],
)
def test_supported_remote_and_local_grammars_remain_distinct(source: str, portable: bool):
    """Would fail if strict rejection removed a supported URL, SCP, or local path."""
    assert source_portability(source) is portable
    assert redact_source(source) == source
