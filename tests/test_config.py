import hashlib
import tomllib
from pathlib import Path

import pytest


def _write_enrollment(
    paths, *, content: bytes, machine_id: str = "workstation-01", machine: str = "schema = 4\n"
) -> None:
    """Create a real, digest-verified cache and its active enrollment lock."""
    from ai_dlc.enrollment import EnrollmentLock, write_lock

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


def test_runtime_resolution_uses_enrolled_files_and_fixed_precedence(tmp_path: Path):
    from ai_dlc.config import resolve_runtime
    from ai_dlc.enrollment import EnrollmentPaths

    paths = EnrollmentPaths.from_environment(home=tmp_path / "home", environ={})
    _write_enrollment(
        paths,
        content=(
            b'schema = 4\nprofile_id = "personal-profile"\n[roles]\ntracker = "personal"\n'
            b'[preferences]\neditor = "personal"\n'
        ),
        machine=('schema = 4\n[preferences]\neditor = "machine"\n[paths]\nworkspace = "/work"\n'),
    )
    paths.machine_file("another-machine").parent.mkdir(parents=True, exist_ok=True)
    paths.machine_file("another-machine").write_text(
        'schema = 4\n[paths]\nworkspace = "/wrong-machine"\n'
    )
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(
        'schema = 4\n[roles]\ntracker = "project"\n[checks]\nrequired = ["test"]\n'
    )

    result = resolve_runtime(root, enrollment_paths=paths)

    assert result.values["roles"]["specs"] == "openspec"
    assert result.values["roles"]["tracker"] == "project"
    assert result.values["profile_id"] == "personal-profile"
    assert result.values["preferences"]["editor"] == "machine"
    assert result.values["paths"]["workspace"] == "/work"
    assert result.sources["roles.specs"] == "base"
    assert result.sources["roles.tracker"] == "project"
    assert result.sources["profile_id"] == "personal"
    assert result.sources["preferences.editor"] == "machine"
    assert result.sources["paths.workspace"] == "machine"


def test_runtime_explicit_personal_replaces_enrollment_without_reordering_project(tmp_path: Path):
    from ai_dlc.config import resolve_runtime
    from ai_dlc.enrollment import EnrollmentPaths

    paths = EnrollmentPaths.from_environment(home=tmp_path / "home", environ={})
    _write_enrollment(
        paths,
        content=(b'schema = 4\nprofile_id = "personal-profile"\n[roles]\ntracker = "cached"\n'),
    )
    explicit_personal = tmp_path / "explicit-personal.toml"
    explicit_personal.write_text('schema = 4\n[roles]\nknowledge = "explicit"\n')
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text('schema = 4\n[roles]\ntracker = "project"\n')

    result = resolve_runtime(root, personal=explicit_personal, enrollment_paths=paths)

    assert result.values["roles"]["knowledge"] == "explicit"
    assert result.values["roles"]["tracker"] == "project"
    assert "profile_id" not in result.values
    assert result.sources["roles.knowledge"] == "personal"
    assert result.sources["roles.tracker"] == "project"


@pytest.mark.parametrize("cache_state", ["missing", "corrupt"])
def test_runtime_explicit_personal_does_not_verify_the_replaced_enrolled_cache(
    tmp_path: Path, cache_state: str
):
    from ai_dlc.config import resolve_runtime
    from ai_dlc.enrollment import EnrollmentPaths

    paths = EnrollmentPaths.from_environment(home=tmp_path / "home", environ={})
    _write_enrollment(
        paths,
        content=b'schema = 4\nprofile_id = "personal-profile"\n',
        machine='schema = 4\n[paths]\nworkspace = "/enrolled"\n',
    )
    cached_profile = paths.profile_root("personal-profile", "a" * 40) / "ai-dlc-profile.toml"
    if cache_state == "missing":
        cached_profile.unlink()
    else:
        cached_profile.write_bytes(b"corrupt")
    explicit_personal = tmp_path / "explicit-personal.toml"
    explicit_personal.write_text('schema = 4\n[roles]\nknowledge = "explicit"\n')

    result = resolve_runtime(personal=explicit_personal, enrollment_paths=paths)

    assert result.values["roles"]["knowledge"] == "explicit"
    assert result.values["paths"]["workspace"] == "/enrolled"
    assert result.sources["roles.knowledge"] == "personal"
    assert result.sources["paths.workspace"] == "machine"


def test_runtime_explicit_machine_replaces_enrollment_and_cannot_weaken_project_checks(
    tmp_path: Path,
):
    from ai_dlc.config import resolve_runtime
    from ai_dlc.enrollment import EnrollmentPaths

    paths = EnrollmentPaths.from_environment(home=tmp_path / "home", environ={})
    _write_enrollment(
        paths,
        content=b'schema = 4\nprofile_id = "personal-profile"\n',
        machine='schema = 4\n[paths]\nworkspace = "/enrolled"\n',
    )
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text('schema = 4\n[checks]\nrequired = ["test"]\n')
    explicit_machine = tmp_path / "explicit-machine.toml"
    explicit_machine.write_text('schema = 4\n[paths]\nworkspace = "/explicit"\n')

    result = resolve_runtime(root, machine=explicit_machine, enrollment_paths=paths)

    assert result.values["paths"]["workspace"] == "/explicit"
    assert result.sources["paths.workspace"] == "machine"

    explicit_machine.write_text("schema = 4\n[checks]\nrequired = []\n")
    with pytest.raises(ValueError, match="machine.*checks"):
        resolve_runtime(root, machine=explicit_machine, enrollment_paths=paths)


def test_runtime_without_enrollment_uses_base_and_an_existing_project_only(tmp_path: Path):
    from ai_dlc.config import resolve_runtime

    root = tmp_path / "project"
    root.mkdir()

    without_project = resolve_runtime(root, home=tmp_path / "home", environ={})
    assert without_project.values["roles"]["specs"] == "openspec"
    assert set(without_project.sources.values()) == {"base"}

    (root / "ai-dlc.toml").write_text('schema = 4\n[roles]\ntracker = "project"\n')
    with_project = resolve_runtime(root, home=tmp_path / "home", environ={})
    assert with_project.values["roles"]["tracker"] == "project"
    assert with_project.sources["roles.tracker"] == "project"


@pytest.mark.parametrize("failure", ["missing", "changed", "malformed"])
def test_runtime_rejects_an_invalid_active_cache(tmp_path: Path, failure: str):
    from ai_dlc.config import resolve_runtime
    from ai_dlc.enrollment import EnrollmentPaths

    paths = EnrollmentPaths.from_environment(home=tmp_path / "home", environ={})
    content = b'schema = 4\nprofile_id = "personal-profile"\n'
    _write_enrollment(paths, content=content)
    cached_profile = paths.profile_root("personal-profile", "a" * 40) / "ai-dlc-profile.toml"
    if failure == "missing":
        cached_profile.unlink()
        expected = RuntimeError
    elif failure == "changed":
        cached_profile.write_bytes(content + b'\n[roles]\ntracker = "changed"\n')
        expected = RuntimeError
    else:
        malformed = b"schema = 4\nprofile_id = [\n"
        cached_profile.write_bytes(malformed)
        lock = paths.lock_file.read_text().replace(
            hashlib.sha256(
                b"ai-dlc-profile.toml\0" + str(len(content)).encode("ascii") + b"\0" + content
            ).hexdigest(),
            hashlib.sha256(
                b"ai-dlc-profile.toml\0" + str(len(malformed)).encode("ascii") + b"\0" + malformed
            ).hexdigest(),
        )
        paths.lock_file.write_text(lock)
        expected = tomllib.TOMLDecodeError

    with pytest.raises(expected):
        resolve_runtime(enrollment_paths=paths)


def test_retained_named_entry_keeps_original_provenance():
    from ai_dlc.config import resolve_layers

    result = resolve_layers(
        [
            (
                "base",
                {
                    "schema": 4,
                    "agents": {"servers": [{"id": "a"}, {"id": "b", "command": "original"}]},
                },
            ),
            (
                "project",
                {"schema": 4, "agents": {"servers": {"remove": ["a"], "add": [{"id": "c"}]}}},
            ),
        ]
    )
    assert result.sources["agents.servers.0.command"] == "base"


def test_machine_cannot_weaken_project_checks():
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match="machine.*checks"):
        resolve_layers(
            [
                ("project", {"schema": 4, "checks": {"required": ["test"]}}),
                ("machine", {"schema": 4, "checks": {"required": []}}),
            ]
        )


def test_named_collections_and_provenance():
    from ai_dlc.config import resolve_layers

    result = resolve_layers(
        [
            ("base", {"schema": 4, "agents": {"servers": [{"id": "context", "args": ["a", "b"]}]}}),
            (
                "project",
                {
                    "schema": 4,
                    "agents": {
                        "servers": {
                            "add": [{"id": "work", "args": ["serve"]}],
                            "remove": ["context"],
                        }
                    },
                },
            ),
        ]
    )
    assert result.values["agents"]["servers"] == [{"id": "work", "args": ["serve"]}]
    assert result.sources["agents.servers.0.args.0"] == "project"


def test_conflicting_collection_edit_and_unknown_version_rejected():
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match="same ID"):
        resolve_layers(
            [
                (
                    "project",
                    {"schema": 4, "agents": {"servers": {"add": [{"id": "a"}], "remove": ["a"]}}},
                )
            ]
        )
    with pytest.raises(ValueError, match="schema"):
        resolve_layers([("project", {"schema": 99})])


def test_project_output_excludes_personal_settings(tmp_path: Path):
    from ai_dlc.config import load_project

    (tmp_path / "ai-dlc.toml").write_text('schema = 4\n[roles]\ntracker = "linear"\n')
    assert load_project(tmp_path)["roles"]["tracker"] == "linear"


def test_misplaced_secret_or_unknown_field_rejected():
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match="unknown"):
        resolve_layers([("project", {"schema": 4, "typo": True})])
    with pytest.raises(ValueError, match="credential"):
        resolve_layers([("project", {"schema": 4, "providers": {"linear": {"token": "secret"}}})])


def test_component_provider_metadata_is_additive_and_keeps_layer_provenance():
    """Would fail if component selections displaced existing schema-4 provider settings."""
    from ai_dlc.config import resolve_layers

    result = resolve_layers(
        [
            (
                "personal",
                {
                    "schema": 4,
                    "providers": {
                        "third-party-tracker": {
                            "kind": "github-issues",
                            "component": "third-party-tracker",
                        }
                    },
                },
            ),
            (
                "project",
                {
                    "schema": 4,
                    "providers": {
                        "third-party-tracker": {
                            "component_manifest": "components/third-party-tracker.json",
                            "component_manifest_sha256": "a" * 64,
                        }
                    },
                },
            ),
        ]
    )

    assert result.values["providers"]["third-party-tracker"] == {
        "kind": "github-issues",
        "component": "third-party-tracker",
        "component_manifest": "components/third-party-tracker.json",
        "component_manifest_sha256": "a" * 64,
    }
    assert result.sources["providers.third-party-tracker.component"] == "personal"
    assert result.sources["providers.third-party-tracker.component_manifest"] == "project"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("component", ["third-party-tracker"]),
        ("component_manifest", ["components/third-party-tracker.json"]),
        ("component_manifest_sha256", ["a" * 64]),
    ],
)
def test_component_provider_metadata_requires_string_fields(field: str, value: object):
    """Would fail if component metadata reached its loader with a non-string field."""
    from ai_dlc.config import resolve_layers

    with pytest.raises(TypeError, match=rf"providers.third-party-tracker.{field} must be a string"):
        resolve_layers(
            [
                (
                    "project",
                    {"schema": 4, "providers": {"third-party-tracker": {field: value}}},
                )
            ]
        )


@pytest.mark.parametrize("layer", ["base", "personal", "project", "machine"])
def test_provider_component_configuration_requires_provider_tables(layer: str):
    """Would fail if a non-table provider shape bypassed component metadata validation."""
    from ai_dlc.config import resolve_layers

    with pytest.raises(TypeError, match=rf"{layer}: providers must be a table"):
        resolve_layers([(layer, {"schema": 4, "providers": ["third-party-tracker"]})])


@pytest.mark.parametrize("field", ["component_manifest", "component_manifest_sha256"])
def test_component_manifest_and_digest_must_be_declared_together(field: str):
    """Would fail if unpaired manifest integrity metadata reached component loading."""
    from ai_dlc.config import resolve_layers

    value = "components/third-party-tracker.json" if field == "component_manifest" else "a" * 64
    with pytest.raises(
        ValueError, match="component manifest and component_manifest_sha256 together"
    ):
        resolve_layers(
            [
                (
                    "project",
                    {"schema": 4, "providers": {"third-party-tracker": {field: value}}},
                )
            ]
        )


@pytest.mark.parametrize(
    "field",
    ["component", "component_manifest", "component_manifest_sha256"],
)
def test_machine_layer_cannot_own_component_provider_metadata(field: str):
    """Would fail if a machine binding could choose a project component or manifest."""
    from ai_dlc.config import resolve_layers

    with pytest.raises(
        ValueError, match=rf"machine: cannot set providers.third-party-tracker.{field}"
    ):
        resolve_layers(
            [
                (
                    "machine",
                    {"schema": 4, "providers": {"third-party-tracker": {field: "value"}}},
                )
            ]
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_tokens", 1024),
        ("token_count", 10),
    ],
)
def test_benign_numeric_token_settings_remain_schema_4_compatible(field: str, value: int):
    """Would fail if credential-field detection ignored key structure and value type."""
    from ai_dlc.config import resolve_layers

    result = resolve_layers(
        [
            (
                "personal",
                {
                    "schema": 4,
                    "providers": {
                        "language-model": {
                            field: value,
                        }
                    },
                },
            )
        ]
    )

    assert result.values["providers"]["language-model"] == {
        field: value,
    }


def test_personal_credential_requirement_and_machine_binding_merge():
    from ai_dlc.config import resolve_layers

    result = resolve_layers(
        [
            (
                "personal",
                {
                    "schema": 4,
                    "profile_id": "sean-development",
                    "credentials": {
                        "linear-sandbox": {
                            "description": "Linear sandbox access",
                            "required_by": ["provider.linear-sandbox"],
                        }
                    },
                },
            ),
            (
                "machine",
                {
                    "schema": 4,
                    "credentials": {
                        "linear-sandbox": {
                            "source": "environment",
                            "variable": "LINEAR_SANDBOX_TOKEN",
                        }
                    },
                },
            ),
        ]
    )

    assert result.values["credentials"]["linear-sandbox"] == {
        "description": "Linear sandbox access",
        "required_by": ["provider.linear-sandbox"],
        "source": "environment",
        "variable": "LINEAR_SANDBOX_TOKEN",
    }
    assert result.sources["credentials.linear-sandbox.description"] == "personal"
    assert result.sources["credentials.linear-sandbox.variable"] == "machine"


@pytest.mark.parametrize("layer", ["base", "project", "machine"])
def test_profile_id_is_limited_to_personal_scope(layer: str):
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match="cannot set profile_id"):
        resolve_layers([(layer, {"schema": 4, "profile_id": "sean-development"})])


@pytest.mark.parametrize(
    ("layer", "entry", "message"),
    [
        (
            "personal",
            {"description": "Linear access", "required_by": [], "source": "environment"},
            "personal.*source",
        ),
        (
            "personal",
            {"description": "Linear access", "required_by": [], "variable": "LINEAR_API_KEY"},
            "personal.*variable",
        ),
        (
            "machine",
            {"source": "environment", "variable": "LINEAR_API_KEY", "description": "Linear access"},
            "machine.*description",
        ),
        (
            "machine",
            {"source": "environment", "variable": "LINEAR_API_KEY", "required_by": []},
            "machine.*required_by",
        ),
        (
            "machine",
            {"source": "file", "variable": "LINEAR_API_KEY"},
            "machine.*source",
        ),
    ],
)
def test_credential_entries_reject_invalid_scope_fields(
    layer: str, entry: dict[str, object], message: str
):
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match=message):
        resolve_layers([(layer, {"schema": 4, "credentials": {"linear-sandbox": entry}})])


@pytest.mark.parametrize(
    ("layer", "credential_id", "entry", "message"),
    [
        (
            "personal",
            "Linear-sandbox",
            {"description": "Linear access", "required_by": []},
            "credential ID",
        ),
        (
            "machine",
            "linear_sandbox",
            {"source": "environment", "variable": "LINEAR_API_KEY"},
            "credential ID",
        ),
        (
            "machine",
            "linear-sandbox",
            {"source": "environment", "variable": "linear-api-key"},
            "environment variable",
        ),
    ],
)
def test_credential_identifiers_are_validated(
    layer: str, credential_id: str, entry: dict[str, object], message: str
):
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match=message):
        resolve_layers([(layer, {"schema": 4, "credentials": {credential_id: entry}})])


def test_credential_values_are_rejected_recursively():
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match="credential value"):
        resolve_layers(
            [
                (
                    "personal",
                    {
                        "schema": 4,
                        "credentials": {
                            "linear-sandbox": {
                                "description": "Linear access",
                                "required_by": [],
                                "metadata": {"secret": "not-allowed"},
                            }
                        },
                    },
                )
            ]
        )


@pytest.mark.parametrize(
    "entry",
    [
        {"required_by": []},
        {"description": "Linear access"},
        {"description": 1, "required_by": []},
        {"description": "Linear access", "required_by": ["provider.linear", 1]},
    ],
)
def test_personal_credential_requirements_must_be_complete(entry: dict[str, object]):
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match="personal"):
        resolve_layers([("personal", {"schema": 4, "credentials": {"linear-sandbox": entry}})])


@pytest.mark.parametrize(
    "entry",
    [
        {"source": "environment"},
        {"variable": "LINEAR_API_KEY"},
        {"source": "environment", "variable": "LINEAR_API_KEY", "unexpected": True},
    ],
)
def test_machine_credential_bindings_must_be_complete_and_exact(entry: dict[str, object]):
    from ai_dlc.config import resolve_layers

    with pytest.raises(ValueError, match="machine"):
        resolve_layers([("machine", {"schema": 4, "credentials": {"linear-sandbox": entry}})])


@pytest.mark.parametrize("credentials", [[], {"linear-sandbox": "not-a-table"}])
def test_credential_tables_must_be_mappings(credentials: object):
    from ai_dlc.config import resolve_layers

    with pytest.raises(TypeError, match="credentials"):
        resolve_layers([("personal", {"schema": 4, "credentials": credentials})])
