"""Component catalog loading and validation."""

import hashlib
import json
from pathlib import Path

import pytest


def test_loads_the_packaged_component_catalog_and_its_guidance(tmp_path: Path):
    """Would fail if a distributed provider component or its guidance were omitted."""
    from ai_dlc.components import load_component_catalog

    catalog = load_component_catalog(tmp_path, {})

    assert catalog == {
        "schema": 1,
        "components": [
            {
                "id": "github-issues",
                "roles": ["tracker"],
                "modules": ["core"],
                "guidance": ["providers/github-issues.md"],
                "required_config": ["repository"],
            },
            {
                "id": "linear",
                "roles": ["tracker"],
                "modules": ["linear"],
                "guidance": ["providers/linear.md"],
                "required_config": ["team_id", "statuses.in_progress", "statuses.closed"],
            },
            {
                "id": "openspec",
                "roles": ["specs"],
                "modules": ["openspec"],
                "guidance": ["providers/openspec.md"],
                "required_config": [],
            },
        ],
    }
    from ai_dlc.files import assets

    assert all(
        (assets("agents") / path).is_file()
        for component in catalog["components"]
        for path in component["guidance"]
    )


def _write_manifest(root: Path, name: str, component: dict) -> tuple[str, str]:
    (root / "guidance").mkdir(exist_ok=True)
    for guidance in component["guidance"]:
        (root / guidance).write_text("# Provider guidance\n")
    path = root / "components" / name
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"schema": 1, "components": [component]}))
    return path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()


def test_loads_digest_verified_synthetic_component_fixtures(tmp_path: Path):
    """Would fail if verified repository metadata could not extend built-in components."""
    from ai_dlc.components import load_component_catalog

    specs_manifest, specs_digest = _write_manifest(
        tmp_path,
        "synthetic-specs.json",
        {
            "id": "synthetic-specs",
            "roles": ["specs"],
            "modules": ["openspec"],
            "guidance": ["guidance/synthetic-specs.md"],
            "required_config": [],
        },
    )
    tracker_manifest, tracker_digest = _write_manifest(
        tmp_path,
        "synthetic-tracker.json",
        {
            "id": "synthetic-tracker",
            "roles": ["tracker"],
            "modules": ["core"],
            "guidance": ["guidance/synthetic-tracker.md"],
            "required_config": ["repository"],
        },
    )

    catalog = load_component_catalog(
        tmp_path,
        {
            "providers": {
                "synthetic-specs": {
                    "component_manifest": specs_manifest,
                    "component_manifest_sha256": specs_digest,
                },
                "synthetic-tracker": {
                    "component_manifest": tracker_manifest,
                    "component_manifest_sha256": tracker_digest,
                },
            }
        },
    )

    assert [component["id"] for component in catalog["components"]] == [
        "github-issues",
        "linear",
        "openspec",
        "synthetic-specs",
        "synthetic-tracker",
    ]


def test_rejects_a_raw_custom_manifest_without_its_digest(tmp_path: Path):
    """Would fail if the public loader accepted incomplete provider metadata."""
    from ai_dlc.components import load_component_catalog

    manifest, _ = _write_manifest(
        tmp_path,
        "unverified.json",
        {
            "id": "synthetic-specs",
            "roles": ["specs"],
            "modules": ["openspec"],
            "guidance": ["guidance/synthetic-specs.md"],
            "required_config": [],
        },
    )

    with pytest.raises(
        ValueError, match="must set component manifest and component_manifest_sha256 together"
    ):
        load_component_catalog(
            tmp_path,
            {"providers": {"synthetic-specs": {"component_manifest": manifest}}},
        )


def test_rejects_a_manifest_when_its_configured_digest_does_not_match(tmp_path: Path):
    """Would fail if altered metadata were parsed without integrity verification."""
    from ai_dlc.components import load_component_catalog

    manifest, digest = _write_manifest(
        tmp_path,
        "altered.json",
        {
            "id": "synthetic-specs",
            "roles": ["specs"],
            "modules": ["openspec"],
            "guidance": ["guidance/synthetic-specs.md"],
            "required_config": [],
        },
    )
    (tmp_path / manifest).write_text("not JSON")

    with pytest.raises(ValueError, match="digest mismatch"):
        load_component_catalog(
            tmp_path,
            {
                "providers": {
                    "synthetic-specs": {
                        "component_manifest": manifest,
                        "component_manifest_sha256": digest,
                    }
                }
            },
        )


def test_parses_the_verified_manifest_bytes_when_the_file_changes_after_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Would fail if parsing reread a manifest after its digest check."""
    from ai_dlc.components import load_component_catalog

    manifest, digest = _write_manifest(tmp_path, "race.json", _component())
    manifest_path = tmp_path / manifest
    (tmp_path / "guidance" / "synthetic-tracker.md").write_text("# replacement guidance\n")
    replacement = json.dumps(
        {
            "schema": 1,
            "components": [
                _component(
                    id="synthetic-tracker",
                    roles=["tracker"],
                    modules=["core"],
                    guidance=["guidance/synthetic-tracker.md"],
                    required_config=["repository"],
                )
            ],
        }
    )
    read_bytes = Path.read_bytes

    def read_then_replace(path: Path) -> bytes:
        content = read_bytes(path)
        if path == manifest_path:
            path.write_text(replacement)
        return content

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)

    catalog = load_component_catalog(
        tmp_path,
        {
            "providers": {
                "synthetic-specs": {
                    "component_manifest": manifest,
                    "component_manifest_sha256": digest,
                }
            }
        },
    )

    assert [component["id"] for component in catalog["components"]] == [
        "github-issues",
        "linear",
        "openspec",
        "synthetic-specs",
    ]


def test_rejects_an_unsafe_component_manifest_path(tmp_path: Path):
    """Would fail if custom metadata could escape the selected repository."""
    from ai_dlc.components import load_component_catalog

    outside = tmp_path.parent / "outside-components.json"
    outside.write_text('{"schema": 1, "components": []}')

    with pytest.raises(ValueError, match="relative normalized path"):
        load_component_catalog(
            tmp_path,
            {
                "providers": {
                    "synthetic-specs": {
                        "component_manifest": "../outside-components.json",
                        "component_manifest_sha256": hashlib.sha256(
                            outside.read_bytes()
                        ).hexdigest(),
                    }
                }
            },
        )


def test_rejects_a_drive_qualified_component_manifest_path(tmp_path: Path):
    """Would fail if a Windows drive path bypassed repository path validation."""
    from ai_dlc.components import load_component_catalog

    with pytest.raises(ValueError, match="relative normalized path"):
        load_component_catalog(
            tmp_path,
            {
                "providers": {
                    "synthetic-specs": {
                        "component_manifest": "C:/components.json",
                        "component_manifest_sha256": "a" * 64,
                    }
                }
            },
        )


def _component(**changes: object) -> dict:
    component = {
        "id": "synthetic-specs",
        "roles": ["specs"],
        "modules": ["openspec"],
        "guidance": ["guidance/synthetic-specs.md"],
        "required_config": [],
    }
    component.update(changes)
    return component


@pytest.mark.parametrize(
    ("components", "match"),
    [
        ([_component(modules=["not-a-recipe"])], "unknown module"),
        ([_component(), _component()], "duplicate component ID"),
        ([_component(guidance=["../escape.md"])], "relative normalized path"),
        ([_component(roles=["not-a-role"])], "incompatible role"),
        ([_component(command="echo unsafe")], "unknown or missing fields"),
        ([_component(guidance=["guidance/not-present.md"])], "existing regular file"),
    ],
)
def test_rejects_component_metadata_outside_the_schema(
    tmp_path: Path, components: list[dict], match: str
):
    """Would fail if manifests could name untrusted metadata or unavailable resources."""
    from ai_dlc.components import load_component_catalog

    (tmp_path / "components").mkdir()
    manifest = tmp_path / "components" / "invalid.json"
    manifest.write_text(json.dumps({"schema": 1, "components": components}))

    with pytest.raises(ValueError, match=match):
        load_component_catalog(
            tmp_path,
            {
                "providers": {
                    "synthetic-specs": {
                        "component_manifest": "components/invalid.json",
                        "component_manifest_sha256": hashlib.sha256(
                            manifest.read_bytes()
                        ).hexdigest(),
                    }
                }
            },
        )


def test_rejects_a_non_normalized_guidance_path(tmp_path: Path):
    """Would fail if equivalent path spellings bypassed repository path validation."""
    from ai_dlc.components import load_component_catalog

    (tmp_path / "guidance").mkdir()
    (tmp_path / "guidance" / "synthetic-specs.md").write_text("# guidance\n")
    (tmp_path / "components").mkdir()
    manifest = tmp_path / "components" / "unnormalized.json"
    manifest.write_text(
        json.dumps(
            {"schema": 1, "components": [_component(guidance=["guidance//synthetic-specs.md"])]}
        )
    )

    with pytest.raises(ValueError, match="relative normalized path"):
        load_component_catalog(
            tmp_path,
            {
                "providers": {
                    "synthetic-specs": {
                        "component_manifest": "components/unnormalized.json",
                        "component_manifest_sha256": hashlib.sha256(
                            manifest.read_bytes()
                        ).hexdigest(),
                    }
                }
            },
        )


def test_resolves_an_explicit_openspec_role_to_its_component_requirements():
    """Would fail if an explicit OpenSpec selection did not require its component."""
    from ai_dlc.components import resolve_components

    result = resolve_components(
        {"roles": {"specs": "openspec"}},
        {
            "schema": 1,
            "components": [
                {
                    "id": "openspec",
                    "roles": ["specs"],
                    "modules": ["openspec"],
                    "guidance": ["providers/openspec.md"],
                    "required_config": [],
                }
            ],
        },
    )

    assert result == {
        "schema": 1,
        "components": [
            {
                "id": "openspec",
                "provider": "openspec",
                "role": "specs",
                "modules": ["openspec"],
                "guidance": ["providers/openspec.md"],
                "required_config": [],
            }
        ],
        "unresolved": [],
    }


def test_resolves_only_personal_or_project_roles_from_a_layered_configuration():
    """Would fail if compatibility-only base roles authorized component installation."""
    from ai_dlc.components import resolve_components
    from ai_dlc.config import resolve_layers

    resolved = resolve_layers(
        [
            ("base", {"schema": 4, "roles": {"knowledge": "obsidian"}}),
            ("personal", {"schema": 4, "roles": {"specs": "openspec"}}),
            ("project", {"schema": 4, "roles": {"tracker": "linear"}}),
        ]
    )

    result = resolve_components(
        resolved,
        {
            "schema": 1,
            "components": [
                {
                    "id": "openspec",
                    "roles": ["specs"],
                    "modules": ["openspec"],
                    "guidance": ["providers/openspec.md"],
                    "required_config": [],
                },
                {
                    "id": "linear",
                    "roles": ["tracker"],
                    "modules": ["linear"],
                    "guidance": ["providers/linear.md"],
                    "required_config": ["team_id"],
                },
            ],
        },
    )

    assert result["components"] == [
        {
            "id": "linear",
            "provider": "linear",
            "role": "tracker",
            "modules": ["linear"],
            "guidance": ["providers/linear.md"],
            "required_config": ["team_id"],
        },
        {
            "id": "openspec",
            "provider": "openspec",
            "role": "specs",
            "modules": ["openspec"],
            "guidance": ["providers/openspec.md"],
            "required_config": [],
        },
    ]
    assert result["unresolved"] == []


def test_resolves_a_provider_alias_through_its_declared_kind():
    """Would fail if a provider alias could not use its registered component kind."""
    from ai_dlc.components import resolve_components

    result = resolve_components(
        {
            "roles": {"tracker": "project-issues"},
            "providers": {"project-issues": {"kind": "github-issues"}},
        },
        {
            "schema": 1,
            "components": [
                {
                    "id": "github-issues",
                    "roles": ["tracker"],
                    "modules": ["core"],
                    "guidance": ["providers/github-issues.md"],
                    "required_config": ["repository"],
                }
            ],
        },
    )

    assert result == {
        "schema": 1,
        "components": [
            {
                "id": "github-issues",
                "provider": "project-issues",
                "role": "tracker",
                "modules": ["core"],
                "guidance": ["providers/github-issues.md"],
                "required_config": ["repository"],
            }
        ],
        "unresolved": [],
    }


def test_resolves_a_provider_component_override_before_its_kind():
    """Would fail if an explicit component override were ignored for a provider."""
    from ai_dlc.components import resolve_components

    result = resolve_components(
        {
            "roles": {"tracker": "project-issues"},
            "providers": {
                "project-issues": {"kind": "github-issues", "component": "project-tracker"}
            },
        },
        {
            "schema": 1,
            "components": [
                {
                    "id": "github-issues",
                    "roles": ["tracker"],
                    "modules": ["core"],
                    "guidance": ["providers/github-issues.md"],
                    "required_config": ["repository"],
                },
                {
                    "id": "project-tracker",
                    "roles": ["tracker"],
                    "modules": ["linear"],
                    "guidance": ["guidance/project-tracker.md"],
                    "required_config": ["team_id"],
                },
            ],
        },
    )

    assert result == {
        "schema": 1,
        "components": [
            {
                "id": "project-tracker",
                "provider": "project-issues",
                "role": "tracker",
                "modules": ["linear"],
                "guidance": ["guidance/project-tracker.md"],
                "required_config": ["team_id"],
            }
        ],
        "unresolved": [],
    }


def test_reports_an_unknown_component_override_without_using_the_provider_kind():
    """Would fail if an unknown override silently fell back to the provider kind."""
    from ai_dlc.components import resolve_components

    result = resolve_components(
        {
            "roles": {"tracker": "project-issues"},
            "providers": {
                "project-issues": {"kind": "github-issues", "component": "not-installed"}
            },
        },
        {
            "schema": 1,
            "components": [
                {
                    "id": "github-issues",
                    "roles": ["tracker"],
                    "modules": ["core"],
                    "guidance": ["providers/github-issues.md"],
                    "required_config": ["repository"],
                }
            ],
        },
    )

    assert result == {
        "schema": 1,
        "components": [],
        "unresolved": [
            {
                "provider": "project-issues",
                "role": "tracker",
                "reason": "no component for provider: project-issues",
            }
        ],
    }


def test_reports_an_unknown_selected_provider_without_a_fallback():
    """Would fail if an unknown provider selection were silently ignored or substituted."""
    from ai_dlc.components import resolve_components

    result = resolve_components(
        {"roles": {"tracker": "unlisted-tracker"}},
        {
            "schema": 1,
            "components": [
                {
                    "id": "github-issues",
                    "roles": ["tracker"],
                    "modules": ["core"],
                    "guidance": ["providers/github-issues.md"],
                    "required_config": ["repository"],
                }
            ],
        },
    )

    assert result == {
        "schema": 1,
        "components": [],
        "unresolved": [
            {
                "provider": "unlisted-tracker",
                "role": "tracker",
                "reason": "no component for provider: unlisted-tracker",
            }
        ],
    }


def test_reports_a_component_that_is_incompatible_with_the_selected_role():
    """Would fail if an incompatible component were treated as a valid role selection."""
    from ai_dlc.components import resolve_components

    result = resolve_components(
        {"roles": {"specs": "linear"}},
        {
            "schema": 1,
            "components": [
                {
                    "id": "linear",
                    "roles": ["tracker"],
                    "modules": ["linear"],
                    "guidance": ["providers/linear.md"],
                    "required_config": ["team_id"],
                }
            ],
        },
    )

    assert result == {
        "schema": 1,
        "components": [],
        "unresolved": [
            {
                "provider": "linear",
                "role": "specs",
                "reason": "component linear is incompatible with role: specs",
            }
        ],
    }


def test_sorts_resolved_components_and_their_requirement_lists():
    """Would fail if catalog declaration order changed the capability result."""
    from ai_dlc.components import resolve_components

    result = resolve_components(
        {"roles": {"specs": "openspec", "tracker": "linear"}},
        {
            "schema": 1,
            "components": [
                {
                    "id": "openspec",
                    "roles": ["specs"],
                    "modules": ["python", "openspec"],
                    "guidance": ["providers/openspec.md", "providers/linear.md"],
                    "required_config": ["zeta", "alpha"],
                },
                {
                    "id": "linear",
                    "roles": ["tracker"],
                    "modules": ["python", "linear", "core"],
                    "guidance": ["providers/linear.md", "providers/openspec.md"],
                    "required_config": ["team_id", "statuses.closed"],
                },
            ],
        },
    )

    assert result == {
        "schema": 1,
        "components": [
            {
                "id": "linear",
                "provider": "linear",
                "role": "tracker",
                "modules": ["core", "linear", "python"],
                "guidance": ["providers/linear.md", "providers/openspec.md"],
                "required_config": ["statuses.closed", "team_id"],
            },
            {
                "id": "openspec",
                "provider": "openspec",
                "role": "specs",
                "modules": ["openspec", "python"],
                "guidance": ["providers/linear.md", "providers/openspec.md"],
                "required_config": ["alpha", "zeta"],
            },
        ],
        "unresolved": [],
    }


def test_deduplicates_module_requirements_for_a_resolved_component():
    """Would fail if a component could emit the same installation module twice."""
    from ai_dlc.components import resolve_components

    result = resolve_components(
        {"roles": {"tracker": "linear"}},
        {
            "schema": 1,
            "components": [
                {
                    "id": "linear",
                    "roles": ["tracker"],
                    "modules": ["python", "linear", "python"],
                    "guidance": ["providers/linear.md"],
                    "required_config": ["team_id"],
                }
            ],
        },
    )

    assert result["components"][0]["modules"] == ["linear", "python"]


def test_sorts_unresolved_selections_by_provider_and_role():
    """Would fail if caller input order changed the unresolved diagnostics."""
    from ai_dlc.components import resolve_components

    result = resolve_components(
        {"roles": {"tracker": "zeta", "specs": "alpha"}},
        {"schema": 1, "components": []},
    )

    assert result == {
        "schema": 1,
        "components": [],
        "unresolved": [
            {
                "provider": "alpha",
                "role": "specs",
                "reason": "no component for provider: alpha",
            },
            {
                "provider": "zeta",
                "role": "tracker",
                "reason": "no component for provider: zeta",
            },
        ],
    }
