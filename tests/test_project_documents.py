import json
from datetime import date

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.moc import scaffold_5_pillar_docs
from ai_dlc.templates import adopt


def test_scaffold_rejects_symlink_before_any_writes(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (docs / "architecture").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        scaffold_5_pillar_docs(docs, "demo")
    assert list(outside.iterdir()) == []
    assert not (docs / "index.md").exists()


def test_existing_layout_is_canonical_and_specs_are_not_duplicated(tmp_path):
    docs = tmp_path / "docs"
    (docs / "decisions").mkdir(parents=True)
    (tmp_path / "openspec" / "specs").mkdir(parents=True)
    (docs / "architecture.md").write_text("Real architecture")
    (docs / "decisions" / "chosen.md").write_text("A real decision")
    scaffold_5_pillar_docs(docs, "demo")
    assert not (docs / "architecture").exists()
    assert not (docs / "adr").exists()
    assert not (docs / "specs").exists()
    assert (docs / "architecture.md").read_text() == "Real architecture"
    text = (docs / "index.md").read_text()
    assert "(architecture.md)" in text
    assert "(../openspec/)" in text
    assert (docs / "catalog.toml").is_file()
    assert scaffold_5_pillar_docs(docs, "demo") == []


def _template(tmp_path):
    template = tmp_path / "template"
    template.mkdir()
    (template / "copier.yml").write_text("{}\n")
    (template / "owned.md").write_text("generated")
    return template


def test_adoption_conflict_does_not_scaffold(tmp_path):
    template = _template(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    (project / "owned.md").write_text("authored")
    result = CliRunner().invoke(
        app,
        [
            "project",
            "adopt",
            "--root",
            str(project),
            "--template-source",
            str(template),
            "--apply",
            "--docs-preset",
            "5-pillar",
        ],
    )
    assert json.loads(result.stdout)["status"] == "conflict"
    assert not (project / "docs").exists()
    assert (project / "owned.md").read_text() == "authored"


def test_shared_adoption_preview_includes_docs_and_apply_matches(tmp_path):
    template = _template(tmp_path)
    project = tmp_path / "project"
    preview = adopt(project, template_source=str(template), docs_preset="organized")
    assert "docs/index.md" in preview["files"]
    assert not project.exists()
    result = adopt(project, template_source=str(template), docs_preset="organized", apply=True)
    assert result["files"] == preview["files"]
    assert not (project / "docs" / "specs").exists()


def test_unknown_docs_preset_refused_before_adoption(tmp_path):
    template = _template(tmp_path)
    with pytest.raises(ValueError, match="preset"):
        adopt(tmp_path / "project", template_source=str(template), docs_preset="typo", apply=True)
    assert not (tmp_path / "project").exists()


def test_document_inspection_reports_real_gaps_without_mutating(tmp_path):
    from ai_dlc.documents import check_documents

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Shared guide\n")
    (docs / "copy.md").write_text("# Shared guide\n")
    (docs / "catalog.toml").write_text("""schema = 1
[[documents]]
id = "guide"
path = "docs/guide.md"
kind = "runbook"
owner = "maintainers"
status = "active"
reviewed_on = "2026-01-01"
review_after_days = 90
[[documents]]
id = "missing"
path = "docs/missing.md"
kind = "reference"
owner = "unassigned"
status = "draft"
""")
    before = {p.name: p.read_bytes() for p in docs.iterdir()}
    result = check_documents(tmp_path, today=date(2026, 9, 8))
    codes = {item["code"] for item in result["findings"]}
    assert {
        "missing-document",
        "review-overdue",
        "owner-missing",
        "review-unknown",
        "uncatalogued",
        "duplicate-content",
    } <= codes
    assert {p.name: p.read_bytes() for p in docs.iterdir()} == before


@pytest.mark.parametrize("body", ["broken = [", "schema = 2", 'schema = 1\ndocuments = "bad"'])
def test_invalid_catalog_reports_findings(tmp_path, body):
    from ai_dlc.documents import check_documents

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "catalog.toml").write_text(body)
    assert "invalid-catalog" in {i["code"] for i in check_documents(tmp_path)["findings"]}


def test_catalog_paths_and_sources_do_not_authorize_outside_reads(tmp_path):
    from ai_dlc.documents import check_documents

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "catalog.toml").write_text("""schema = 1
[[documents]]
id = "outside"
path = "../private.md"
kind = "reference"
owner = "maintainer"
status = "active"
""")
    assert "invalid-path" in {i["code"] for i in check_documents(tmp_path)["findings"]}


def test_docs_check_cli_and_mcp_share_read_only_result(tmp_path):
    import asyncio

    from ai_dlc.mcp_server import make_server

    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    cli = CliRunner().invoke(app, ["project", "docs-check", "--root", str(tmp_path)])
    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["findings"][0]["code"] == "catalog-missing"
    strict = CliRunner().invoke(app, ["project", "docs-check", "--root", str(tmp_path), "--strict"])
    assert strict.exit_code == 2
    server = make_server(tmp_path)
    result = asyncio.run(server.call_tool("project_docs_check", {}))
    assert "catalog-missing" in str(result)
    assert not (tmp_path / "docs").exists()


def test_catalog_identifies_duplicates_supersession_and_provenance(tmp_path):
    import tomli_w

    from ai_dlc.documents import check_documents

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/a.md").write_text("A")
    entries = [
        {"id": "one", "path": "docs/a.md", "kind": "summary", "owner": "team", "status": "active"},
        {
            "id": "one",
            "path": "docs/a.md",
            "kind": "reference",
            "owner": "team",
            "status": "superseded",
        },
    ]
    (tmp_path / "docs/catalog.toml").write_text(tomli_w.dumps({"schema": 1, "documents": entries}))
    codes = {i["code"] for i in check_documents(tmp_path)["findings"]}
    assert {"duplicate-id", "duplicate-path", "replacement-missing", "source-missing"} <= codes


def test_adoption_preflights_vault_and_preview_includes_portal(tmp_path):
    template = _template(tmp_path)
    project = tmp_path / "project"
    with pytest.raises(ValueError, match="vault"):
        adopt(
            project,
            template_source=str(template),
            docs_preset="organized",
            link_vault=True,
            vault=tmp_path / "missing",
            apply=True,
        )
    assert not project.exists()
    vault = tmp_path / "vault"
    vault.mkdir()
    preview = adopt(
        project,
        template_source=str(template),
        docs_preset="organized",
        link_vault=True,
        vault=vault,
    )
    assert preview["vault_link"]["action"] == "create"
    assert not project.exists()
    assert list(vault.iterdir()) == []
    result = adopt(
        project,
        template_source=str(template),
        docs_preset="organized",
        link_vault=True,
        vault=vault,
        apply=True,
    )
    assert result["vault_link"]["created"]
    assert (vault / "Projects/project.md").is_file()


def test_adoption_preserves_file_inserted_after_planning(tmp_path, monkeypatch):
    from ai_dlc import document_files

    template = _template(tmp_path)
    project = tmp_path / "project"
    original = document_files.create_document

    def insert(path, body):
        if path.name == "index.md":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Authored concurrent map")
        return original(path, body)

    monkeypatch.setattr(document_files, "create_document", insert)
    with pytest.raises(ValueError, match="retained|appeared"):
        adopt(project, template_source=str(template), docs_preset="organized", apply=True)
    assert (project / "docs/index.md").read_text() == "Authored concurrent map"


def test_docs_init_is_preview_first_and_preserves_existing_index(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("Existing index")
    preview = CliRunner().invoke(app, ["project", "docs-init", "--root", str(tmp_path)])
    assert preview.exit_code == 0
    assert not (docs / "catalog.toml").exists()
    result = CliRunner().invoke(app, ["project", "docs-init", "--root", str(tmp_path), "--apply"])
    assert result.exit_code == 0
    assert (docs / "index.md").read_text() == "Existing index"
    assert (docs / "catalog.toml").exists()


def test_docs_check_detects_broken_local_navigation_without_fetching_urls(tmp_path):
    from ai_dlc.documents import check_documents

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "catalog.toml").write_text("schema=1\n")
    (docs / "index.md").write_text(
        "[missing](missing.md)\n[remote](https://example.invalid/page)\n"
        "[specs](../openspec/)\n```md\n[example](not-a-real-link.md)\n```\n"
    )
    findings = check_documents(tmp_path)["findings"]
    broken = [i for i in findings if i["code"] == "broken-link"]
    assert len(broken) == 2
    assert not any("example.invalid" in str(i) for i in findings)


@pytest.mark.parametrize("field,value", [("kind", []), ("status", {}), ("superseded_by", [])])
def test_malformed_entry_fields_never_crash_inspection(tmp_path, field, value):
    import tomli_w

    from ai_dlc.documents import check_documents

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("A")
    entry = {
        "id": "a",
        "path": "docs/a.md",
        "kind": "reference",
        "status": "superseded",
        "owner": "team",
    }
    entry[field] = value
    (docs / "catalog.toml").write_text(tomli_w.dumps({"schema": 1, "documents": [entry]}))
    assert check_documents(tmp_path)["findings"]


@pytest.mark.parametrize("relative", [".", "./"])
def test_empty_normalized_catalog_path_is_reported(tmp_path, relative):
    import tomli_w

    from ai_dlc.documents import check_documents

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/catalog.toml").write_text(
        tomli_w.dumps({"schema": 1, "documents": [{"id": "bad", "path": relative}]})
    )
    assert "invalid-path" in {i["code"] for i in check_documents(tmp_path)["findings"]}


def test_malformed_url_does_not_abort_document_scan(tmp_path):
    from ai_dlc.documents import check_documents

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "catalog.toml").write_text("schema=1\n")
    (docs / "a.md").write_text("[bad](https://[oops)")
    (docs / "z.md").write_text("[missing](absent.md)")
    findings = check_documents(tmp_path)["findings"]
    assert any(i["code"] == "broken-link" and i["path"] == "docs/a.md" for i in findings)
    assert any(i["code"] == "broken-link" and i["path"] == "docs/z.md" for i in findings)


def test_architecture_directory_remains_canonical(tmp_path):
    docs = tmp_path / "docs"
    (docs / "architecture").mkdir(parents=True)
    (docs / "architecture/system.md").write_text("Authored system description")
    scaffold_5_pillar_docs(docs, "demo")
    assert not (docs / "architecture.md").exists()
    assert "(architecture/README.md)" in (docs / "index.md").read_text()
    assert "(system.md)" in (docs / "architecture/README.md").read_text()


def test_non_directory_document_parent_refused_before_any_scaffolding(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "reference").write_text("Authored file")
    with pytest.raises(ValueError):
        scaffold_5_pillar_docs(docs, "demo")
    assert sorted(p.name for p in docs.iterdir()) == ["reference"]
