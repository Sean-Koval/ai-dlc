"""Portable reviewed guidance and its offline supporting pages."""

import hashlib
import json
import os
from pathlib import Path

import pytest
from test_workflow_bundles import _bundle_repository, _git

from ai_dlc.agents import inspect_bundle_guidance, render_agents
from ai_dlc.config import resolve_layers
from ai_dlc.workflow_bundles import import_bundle, resolve_bundle, validate_bundle


def company(root: Path):
    root.mkdir(exist_ok=True)
    payload = {
        "skills/sdk/SKILL.md": "---\nname: company-sdk\ndescription: SDK procedure\n---\nRead [rules](references/rules.md).\n",
        "skills/sdk/references/rules.md": "# Reviewed rules\nUse company procedure.\n",
    }
    manifest = {
        "schema": 2,
        "id": "company",
        "skills": {"company-sdk": "skills/sdk/SKILL.md"},
        "templates": {},
        "references": {"company-sdk": ["skills/sdk/references/rules.md"]},
        "guidance": {
            "company-sdk": {
                "owner": "SDK team",
                "status": "approved",
                "sources": ["https://company.example/sdk"],
                "sdk": {"name": "sdk", "versions": ["1.2"]},
            }
        },
        "files": {p: hashlib.sha256(c.encode()).hexdigest() for p, c in payload.items()},
    }
    for p, c in payload.items():
        target = root / p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(c)
    (root / "bundle.json").write_text(json.dumps(manifest))
    return manifest


def test_schema_two_supports_integrity_checked_references(tmp_path):
    manifest = company(tmp_path)
    assert validate_bundle(tmp_path, manifest)["references"] == manifest["references"]
    (tmp_path / "skills/sdk/references/rules.md").write_text("tampered")
    with pytest.raises(ValueError, match="digest mismatch"):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize(
    "path", ["../rules.md", "skills/other/rules.md", "skills/sdk/run.py", "skills/sdk/SKILL.md"]
)
def test_reference_cannot_escape_or_alias_skill(tmp_path, path):
    manifest = company(tmp_path)
    manifest["references"]["company-sdk"] = [path]
    with pytest.raises(ValueError):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize("layer", ["base", "machine", "personal"])
def test_sdk_versions_are_project_only(layer):
    with pytest.raises(ValueError, match="cannot set agents"):
        resolve_layers([(layer, {"schema": 4, "agents": {"sdk_versions": {"sdk": "1.2"}}})])


@pytest.mark.parametrize("versions", [{"sdk": ""}, {"Bad SDK": "1"}, {"sdk": ["1"]}])
def test_sdk_versions_validate_exact_string_selection(versions):
    with pytest.raises(ValueError, match="sdk_versions"):
        resolve_layers([("project", {"schema": 4, "agents": {"sdk_versions": versions}})])


def enroll(tmp_path, status="approved"):
    repository, source, env = _bundle_repository(tmp_path)
    _git(repository, "rm", "-r", ".")
    manifest = company(repository)
    manifest["guidance"]["company-sdk"]["status"] = status
    (repository / "bundle.json").write_text(json.dumps(manifest))
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "company guidance")
    project = tmp_path / "project"
    project.mkdir()
    (project / "ai-dlc.toml").write_text(
        'schema = 4\n[agents]\nbundles = ["company"]\n[agents.sdk_versions]\nsdk = "1.2"\n'
    )
    with resolve_bundle(source, "main", "company", environ=env) as candidate:
        result = import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )
        assert result["applied"]
        assert result["guidance"] == manifest["guidance"]
        assert result["references"] == manifest["references"]
    return project


def test_import_render_references_and_preserve_authored_edits(tmp_path):
    project = enroll(tmp_path)
    render_agents(project, apply=True)
    for native in [".agents", ".claude"]:
        target = project / native / "skills/company-sdk/references/rules.md"
        assert "Reviewed rules" in target.read_text()
    target.write_text("Authored local rule")
    with pytest.raises(ValueError, match="conflict"):
        render_agents(project, apply=True)
    assert target.read_text() == "Authored local rule"


@pytest.mark.parametrize(
    "status,version,reason",
    [
        ("draft", "1.2", "draft"),
        ("superseded", "1.2", "superseded"),
        ("approved", "2", "version"),
        ("approved", None, "applicability"),
    ],
)
def test_inapplicable_guidance_can_import_but_cannot_activate(tmp_path, status, version, reason):
    project = enroll(tmp_path, status)
    config = {
        "agents": {
            "bundles": ["company"],
            "sdk_versions": {} if version is None else {"sdk": version},
        }
    }
    text = 'schema = 4\n[agents]\nbundles = ["company"]\n'
    if version is not None:
        text += f'[agents.sdk_versions]\nsdk = "{version}"\n'
    (project / "ai-dlc.toml").write_text(text)
    results = inspect_bundle_guidance(project, config, ["codex"])
    assert results[0]["status"] == "blocked"
    assert reason in results[0]["reason"]
    with pytest.raises(ValueError, match=reason):
        render_agents(project, apply=True)
    assert not (project / ".agents/skills/company-sdk/SKILL.md").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("owner", ""),
        ("status", "pending"),
        ("sources", []),
        ("sources", ["http://company.example/sdk"]),
        ("sources", ["https://"]),
        ("sdk", {"name": "sdk", "versions": []}),
        ("sdk", {"name": "Bad", "versions": ["1"]}),
    ],
)
def test_invalid_review_metadata_is_rejected(tmp_path, field, value):
    manifest = company(tmp_path)
    manifest["guidance"]["company-sdk"][field] = value
    with pytest.raises(ValueError):
        validate_bundle(tmp_path, manifest)


@pytest.mark.parametrize("mutation", ["missing", "undeclared", "symlink", "unaccounted"])
def test_reference_tree_remains_closed(tmp_path, mutation):
    manifest = company(tmp_path)
    path = tmp_path / "skills/sdk/references/rules.md"
    if mutation == "missing":
        path.unlink()
    elif mutation == "undeclared":
        (path.parent / "extra.md").write_text("extra")
    elif mutation == "symlink":
        path.unlink()
        path.symlink_to(tmp_path / "skills/sdk/SKILL.md")
    else:
        manifest["references"] = {}
    with pytest.raises(ValueError):
        validate_bundle(tmp_path, manifest)


def test_conflicting_selections_report_compatibility_without_prose_inference(tmp_path):
    from ai_dlc.agents import _guidance_selection_details

    manifest = company(tmp_path)
    second = json.loads(json.dumps(manifest))
    second["guidance"]["company-sdk"]["sdk"]["versions"] = ["2"]
    bundles = {"one": {"manifest": manifest}, "two": {"manifest": second}}
    config = {"agents": {"sdk_versions": {"sdk": "1.2"}}}
    details = _guidance_selection_details(bundles, config)
    assert all(any("conflicting" in d for d in errors) for errors in details.values())
    second["guidance"]["company-sdk"]["sdk"]["versions"] = ["1.2", "2"]
    assert _guidance_selection_details(bundles, config) == {"one": [], "two": []}


def test_reference_update_preserves_vendored_local_edits(tmp_path):
    from ai_dlc.workflow_bundles import load_vendored_bundle

    project = enroll(tmp_path)
    vendored = project / ".ai-dlc/bundles/company/skills/sdk/references/rules.md"
    vendored.write_text("authored change")
    with pytest.raises(ValueError, match="digest mismatch"):
        load_vendored_bundle(project, "company")
    repository = tmp_path / "bundle-source"
    source = "https://example.test/workflow.git"
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_ALLOW_PROTOCOL": "file:https:ssh",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"url.{repository.as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_0": source,
        }
    )
    with resolve_bundle(source, "main", "company", environ=environment) as candidate:
        result = import_bundle(
            project, candidate, apply=True, expected_commit=candidate.resolved_commit
        )
    assert not result["applied"]
    assert result["conflicts"]
    assert vendored.read_text() == "authored change"


def test_schema_two_skill_filename_cannot_alias_native_reference_destination(tmp_path):
    manifest = company(tmp_path)
    old = "skills/sdk/SKILL.md"
    new = "skills/sdk/OTHER-SKILL.md"
    (tmp_path / old).rename(tmp_path / new)
    manifest["skills"]["company-sdk"] = new
    manifest["files"][new] = manifest["files"].pop(old)
    with pytest.raises(ValueError, match="SKILL.md filename"):
        validate_bundle(tmp_path, manifest)
