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


def test_rejects_a_custom_manifest_without_its_digest(tmp_path: Path):
    """Would fail if unverified component metadata were accepted."""
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

    with pytest.raises(ValueError, match="require a SHA-256 digest"):
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
