"""Impact evidence must follow real Git changes, not self-attested freshness."""

import json
import subprocess

import pytest


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


@pytest.fixture
def project(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/api.py").write_text("VERSION = 1\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/api.md").write_text("# API\n\nVersion one.\n")
    (tmp_path / "docs/catalog.toml").write_text("""schema = 1
[[documents]]
id = "api"
path = "docs/api.md"
kind = "reference"
owner = "maintainers"
status = "active"
code_paths = ["src/*.py"]
requirements = ["openspec/specs/api/spec.md"]
verification_paths = ["tests/test_api.py"]
""")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "baseline")
    return tmp_path


def api():
    from ai_dlc.documentation import document_impact

    return document_impact


def test_public_interface_change_surfaces_guide_and_unmapped(project):
    (project / "src/api.py").write_text("VERSION = 2\n")
    (project / "other.py").write_text("unmapped = True\n")
    result = api().inspect_impact(project, base="HEAD")
    assert result["documents"] == ["docs/api.md"]
    assert result["unmapped"] == ["other.py"]
    assert result["changed"] == ["other.py", "src/api.py"]


def test_source_and_document_changes_invalidate_disposition(project):
    (project / "src/api.py").write_text("VERSION = 2\n")
    service = api()
    decisions = [
        {"target": "docs/api.md", "outcome": "updated", "reason": "Guide covers version two."}
    ]
    receipt = service.prepare_disposition(
        project, base="HEAD", decisions=decisions, reviewer="maintainer"
    )
    assert service.check_disposition(project, base="HEAD", evidence=receipt)["valid"]
    (project / "docs/api.md").write_text("# API\nVersion two.\n")
    assert not service.check_disposition(project, base="HEAD", evidence=receipt)["valid"]
    receipt = service.prepare_disposition(
        project, base="HEAD", decisions=decisions, reviewer="maintainer"
    )
    (project / "src/api.py").write_text("VERSION = 3\n")
    assert not service.check_disposition(project, base="HEAD", evidence=receipt)["valid"]


def test_unmapped_change_requires_justified_disposition(project):
    (project / "unknown.py").write_text("new = True\n")
    with pytest.raises(ValueError, match="disposition"):
        api().prepare_disposition(project, base="HEAD", decisions=[], reviewer="maintainer")
    with pytest.raises(ValueError):
        api().prepare_disposition(
            project,
            base="HEAD",
            decisions=[{"target": "unknown.py", "outcome": "no-impact", "reason": ""}],
            reviewer="maintainer",
        )


def test_unsafe_catalog_mapping_and_symlink_evidence_refused(project, tmp_path):
    catalog = project / "docs/catalog.toml"
    catalog.write_text(catalog.read_text().replace("src/*.py", "../outside/*"))
    with pytest.raises(ValueError):
        api().inspect_impact(project, base="HEAD")


def test_baseline_preserves_old_debt_but_new_link_blocks(project):
    guide = project / "docs/api.md"
    guide.write_text("# API\n[Old](missing-old.md)\n")
    baseline = api().prepare_baseline(
        project, owner="maintainer", reason="Historical broken link under review."
    )
    assert api().check_objective_debt(project, baseline=baseline)["valid"]
    (project / "docs/new.md").write_text("# New\n[Broken](missing-new.md)\n")
    report = api().check_objective_debt(project, baseline=baseline)
    assert not report["valid"]
    assert any(f["path"] == "docs/new.md" for f in report["new_findings"])


def test_forged_or_malformed_dispositions_fail_closed(project):
    (project / "src/api.py").write_text("VERSION = 2\n")
    report = api().check_disposition(project, base="HEAD", evidence={"schema": 1, "decisions": []})
    assert not report["valid"]
    assert not api().check_disposition(project, base="HEAD", evidence=[])["valid"]


def test_deleted_sources_are_changes_and_evidence_storage_is_excluded(project):
    (project / "src/api.py").unlink()
    (project / ".ai-dlc/documentation").mkdir(parents=True)
    (project / ".ai-dlc/documentation/review.json").write_text(json.dumps({"schema": 1}))
    report = api().inspect_impact(project, base="HEAD")
    assert report["changed"] == ["src/api.py"]
    assert report["documents"] == ["docs/api.md"]


def test_cli_and_mcp_expose_same_impact_and_gate(project):
    import asyncio

    from typer.testing import CliRunner

    from ai_dlc.cli import app
    from ai_dlc.mcp_server import make_server

    (project / "src/api.py").write_text("VERSION = 2\n")
    runner = CliRunner()
    result = runner.invoke(
        app, ["project", "docs-impact", "--root", str(project), "--base", "HEAD"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["documents"] == ["docs/api.md"]
    tools = asyncio.run(make_server(project).list_tools())
    assert {"project_docs_impact", "project_docs_disposition", "project_docs_gate"} <= {
        t.name for t in tools
    }
    result = runner.invoke(app, ["project", "docs-gate", "--root", str(project)])
    assert result.exit_code == 2


def test_broad_mapping_never_hashes_its_own_evidence(project):
    catalog = project / "docs/catalog.toml"
    catalog.write_text(catalog.read_text().replace("src/*.py", "**"))
    (project / "src/api.py").write_text("VERSION = 2\n")
    decisions = [
        {"target": "docs/api.md", "outcome": "updated", "reason": "Reviewed all mapped changes."}
    ]
    service = api()
    receipt = service.prepare_disposition(
        project, base="HEAD", decisions=decisions, reviewer="maintainer"
    )
    evidence = project / ".ai-dlc/documentation/current.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps(receipt))
    assert service.check_disposition(project, base="HEAD", evidence=receipt)["valid"]
    catalog.write_text(
        catalog.read_text().replace(
            'code_paths = ["**"]', 'code_paths = [".ai-dlc/documentation/current.json"]'
        )
    )
    with pytest.raises(ValueError, match="evidence"):
        service.inspect_impact(project, base="HEAD")


def test_cli_honors_independently_supplied_ci_base(project, monkeypatch):
    from typer.testing import CliRunner

    from ai_dlc.cli import app

    monkeypatch.delenv("AI_DLC_DOCS_BASE", raising=False)
    service = api()
    evidence_dir = project / ".ai-dlc/documentation"
    evidence_dir.mkdir(parents=True)
    baseline = service.prepare_baseline(project, owner="maintainer", reason="No objective defects.")
    (evidence_dir / "baseline.json").write_text(json.dumps(baseline))
    receipt = service.prepare_disposition(project, base="HEAD", decisions=[], reviewer="maintainer")
    (evidence_dir / "current.json").write_text(json.dumps(receipt))
    runner = CliRunner()
    assert runner.invoke(app, ["project", "docs-gate", "--root", str(project)]).exit_code == 0
    monkeypatch.setenv("AI_DLC_DOCS_BASE", "missing-ci-base")
    assert runner.invoke(app, ["project", "docs-gate", "--root", str(project)]).exit_code == 2
