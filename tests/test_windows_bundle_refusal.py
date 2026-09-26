"""Unsupported bundle operations stop before filesystem or Git work on Windows."""

import pytest

from ai_dlc.errors import RefusedError
from ai_dlc.harness import workflow_bundles as bundles


@pytest.mark.parametrize(
    "operation",
    ["manifest", "validate", "resolve", "project", "vendored", "preview", "apply"],
)
def test_native_bundle_operation_refuses_before_inspection_or_mutation(
    tmp_path, monkeypatch, operation
):
    # Removing an entry-point guard must fail even for otherwise invalid inputs;
    # platform refusal precedes pathname validation, staging, and source resolution.
    monkeypatch.setattr(bundles, "_is_native_windows", lambda: True, raising=False)

    def unexpected_resolution(*args, **kwargs):
        pytest.fail("unsupported native bundle operation contacted a Git source")

    monkeypatch.setattr(bundles, "resolve_git_source", unexpected_resolution)
    (tmp_path / "authored.txt").write_bytes(b"retain")
    candidate = bundles.BundleCandidate(
        source="https://example.invalid/team.git",
        ref="main",
        bundle_id="team",
        resolved_commit="a" * 40,
        root=tmp_path / "missing-candidate",
        manifest={},
        manifest_sha256="b" * 64,
        file_hashes={},
    )
    with pytest.raises(RefusedError, match="not supported on native Windows"):
        match operation:
            case "manifest":
                bundles.load_bundle_manifest(tmp_path)
            case "validate":
                bundles.validate_bundle(tmp_path, {})
            case "resolve":
                bundles.resolve_bundle(candidate.source, "main", "team", environ={})
            case "project":
                bundles.validate_bundle_project(tmp_path)
            case "vendored":
                bundles.load_vendored_bundle(tmp_path, "team")
            case "preview" | "apply":
                bundles.import_bundle(
                    tmp_path,
                    candidate,
                    apply=operation == "apply",
                    expected_commit=candidate.resolved_commit,
                )
    assert [(path.name, path.read_bytes()) for path in tmp_path.iterdir()] == [
        ("authored.txt", b"retain")
    ]
