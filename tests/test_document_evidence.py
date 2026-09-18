"""Per-work evidence binds reviewed content, so disjoint branches never invalidate each other."""

import json
import subprocess

import pytest


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def api():
    from ai_dlc.documentation import document_impact

    return document_impact


API_DECISION = {"target": "docs/api.md", "outcome": "updated", "reason": "Guide covers the change."}


def no_impact(target):
    return {"target": target, "outcome": "no-impact", "reason": "Not user-facing."}


def commit(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)


def record(root, evidence_id, decisions, base="main"):
    return api().record_disposition(
        root, base=base, decisions=decisions, reviewer="maintainer", evidence_id=evidence_id
    )


def gate(root, base="main"):
    return api().check_evidence(root, base=base)


@pytest.fixture
def main(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
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
""")
    commit(tmp_path, "baseline")
    return tmp_path


def branch_with_guide_change(root):
    git(root, "switch", "-qc", "guide", "main")
    (root / "src/api.py").write_text("VERSION = 2\n")
    (root / "docs/api.md").write_text("# API\n\nVersion two.\n")
    record(root, "guide", [API_DECISION])
    commit(root, "guide")


def branch_with_unmapped_change(root):
    git(root, "switch", "-qc", "tool", "main")
    (root / "tool.sh").write_text("echo tool\n")
    record(root, "tool", [no_impact("tool.sh")])
    commit(root, "tool")


@pytest.mark.parametrize("order", [("guide", "tool"), ("tool", "guide")])
def test_disjoint_branches_merge_in_either_order_without_recording_again(main, order):
    branch_with_guide_change(main)
    branch_with_unmapped_change(main)
    first, second = order
    git(main, "switch", "-q", "main")
    git(main, "merge", "-q", "--no-ff", "--no-edit", first)
    git(main, "switch", "-q", second)
    git(main, "merge", "-q", "--no-edit", "main")  # raises on a Git conflict
    assert gate(main) == {"valid": True, "missing": [], "stale": [], "errors": []}
    before = git(main, "rev-parse", "main")
    git(main, "switch", "-q", "main")
    git(main, "merge", "-q", "--no-ff", "--no-edit", second)
    assert gate(main, base=before)["valid"]


def test_target_branch_changing_bound_content_is_stale_and_named(main):
    git(main, "switch", "-qc", "extra", "main")
    (main / "src/extra.py").write_text("EXTRA = True\n")
    (main / "note.txt").write_text("note\n")
    record(main, "extra", [API_DECISION, no_impact("note.txt")])
    commit(main, "extra")
    git(main, "switch", "-q", "main")
    (main / "src/api.py").write_text("VERSION = 2\n")
    commit(main, "target changes a bound source")
    git(main, "switch", "-q", "extra")
    git(main, "merge", "-q", "--no-edit", "main")
    report = gate(main)
    assert not report["valid"]
    assert report["missing"] == []
    assert report["stale"] == [{"target": "docs/api.md", "paths": ["src/api.py"]}]


def test_changed_catalog_entry_stales_only_its_document(main):
    catalog = main / "docs/catalog.toml"
    catalog.write_text(
        catalog.read_text()
        + '\n[[documents]]\nid = "ops"\npath = "docs/ops.md"\nkind = "runbook"\n'
        'owner = "maintainers"\nstatus = "active"\n'
    )
    (main / "docs/ops.md").write_text("# Ops\n")
    commit(main, "ops")
    git(main, "switch", "-qc", "both", "main")
    (main / "src/api.py").write_text("VERSION = 2\n")
    (main / "docs/ops.md").write_text("# Ops\n\nRestart it.\n")
    ops = {"target": "docs/ops.md", "outcome": "updated", "reason": "Adds restart."}
    record(main, "both", [API_DECISION, ops])
    assert gate(main)["valid"]
    catalog.write_text(catalog.read_text().replace('owner = "maintainers"', 'owner = "api"', 1))
    report = gate(main)
    assert [item["target"] for item in report["stale"]] == ["docs/api.md"]
    assert report["stale"][0]["paths"] == ["catalog:docs/api.md"]
    assert report["missing"] == ["docs/catalog.toml"]


def test_branch_behind_its_target_is_judged_on_its_own_changes(main):
    branch_with_unmapped_change(main)
    git(main, "switch", "-q", "main")
    (main / "unrelated.txt").write_text("target moved\n")
    commit(main, "target moves")
    git(main, "switch", "-q", "tool")
    assert gate(main)["valid"]


def test_push_run_fails_when_conflict_resolution_alters_bound_content(main):
    branch_with_guide_change(main)
    git(main, "switch", "-q", "main")
    before = git(main, "rev-parse", "HEAD")
    git(main, "merge", "-q", "--no-ff", "--no-commit", "guide")
    (main / "docs/api.md").write_text("# API\n\nResolved differently.\n")
    commit(main, "merge guide")
    report = gate(main, base=before)
    assert [item["target"] for item in report["stale"]] == ["docs/api.md"]
    assert report["stale"][0]["paths"] == ["docs/api.md"]


def test_recording_keeps_valid_decisions_and_reports_each_group(main):
    git(main, "switch", "-qc", "work", "main")
    (main / "src/api.py").write_text("VERSION = 2\n")
    first = record(main, "work", [API_DECISION])
    assert first["added"] == ["docs/api.md"]
    (main / "tool.sh").write_text("echo tool\n")
    second = record(main, "work", [no_impact("tool.sh")])
    assert (second["kept"], second["added"]) == (["docs/api.md"], ["tool.sh"])
    assert gate(main)["valid"]
    (main / "tool.sh").unlink()
    third = record(main, "work", [])
    assert (third["kept"], third["dropped"]) == (["docs/api.md"], ["tool.sh"])
    (main / "src/api.py").write_text("VERSION = 3\n")
    with pytest.raises(ValueError, match=r"Missing documentation disposition: docs/api\.md"):
        record(main, "work", [])
    assert record(main, "work", [API_DECISION])["replaced"] == ["docs/api.md"]
    stored = json.loads((main / ".ai-dlc/documentation/evidence/work.json").read_text())
    assert stored["schema"] == 2
    assert {d["reviewer"] for d in stored["decisions"]} == {"maintainer"}


def test_missing_and_unrequired_decisions(main):
    git(main, "switch", "-qc", "work", "main")
    (main / "tool.sh").write_text("echo tool\n")
    assert gate(main)["missing"] == ["tool.sh"]
    with pytest.raises(ValueError, match="Unknown or duplicate"):
        record(main, "work", [no_impact("tool.sh"), no_impact("absent.sh")])


@pytest.mark.parametrize("evidence_id", ["../escape", "a/b", "", ".hidden"])
def test_unsafe_evidence_identifiers_are_refused(main, evidence_id):
    with pytest.raises(ValueError, match="evidence identifier"):
        record(main, evidence_id, [])


@pytest.mark.parametrize(
    "forged",
    [
        [],
        {"schema": 2, "decisions": [{"target": "tool.sh"}]},
        {"schema": 2, "decisions": [dict(no_impact("tool.sh"), reviewer="x", bound="all")]},
        {"schema": 2, "decisions": [dict(no_impact("tool.sh"), reviewer="", bound={})]},
    ],
)
def test_forged_evidence_never_satisfies_a_target(main, forged):
    git(main, "switch", "-qc", "work", "main")
    (main / "tool.sh").write_text("echo tool\n")
    folder = main / ".ai-dlc/documentation/evidence"
    folder.mkdir(parents=True)
    (folder / "forged.json").write_text(json.dumps(forged))
    report = gate(main)
    assert not report["valid"]
    assert report["missing"] == ["tool.sh"] or report["errors"]


def legacy_gate_files(root):
    folder = root / ".ai-dlc/documentation"
    folder.mkdir(parents=True, exist_ok=True)
    baseline = api().prepare_baseline(root, owner="maintainer", reason="None.")
    (folder / "baseline.json").write_text(json.dumps(baseline))
    return folder


def test_gate_uses_legacy_evidence_until_per_work_evidence_exists(main):
    git(main, "switch", "-qc", "work", "main")
    (main / "src/api.py").write_text("VERSION = 2\n")
    folder = legacy_gate_files(main)
    base = git(main, "rev-parse", "main")
    legacy = api().prepare_disposition(
        main, base=base, decisions=[API_DECISION], reviewer="maintainer"
    )
    (folder / "current.json").write_text(json.dumps(legacy))
    assert api().check_gate(main)["valid"]
    report = record(main, "work", [API_DECISION])
    assert report["legacy"] == ".ai-dlc/documentation/current.json"
    (folder / "current.json").unlink()
    result = api().check_gate(main)
    assert result["valid"]
    assert result["disposition"]["stale"] == []
    (main / "src/api.py").write_text("VERSION = 3\n")
    assert not api().check_gate(main)["valid"]


def test_gate_without_a_comparison_uses_the_configured_target_branch(main):
    (main / "ai-dlc.toml").write_text('[scm]\ntarget_branch = "trunk"\n')
    commit(main, "configure")
    git(main, "branch", "-m", "main", "trunk")
    git(main, "switch", "-qc", "work", "trunk")
    (main / "tool.sh").write_text("echo tool\n")
    legacy_gate_files(main)
    record(main, "work", [no_impact("tool.sh")], base="trunk")
    assert api().check_gate(main)["valid"]
    git(main, "branch", "-m", "trunk", "elsewhere")
    result = api().check_gate(main)
    assert not result["valid"]
    assert "trunk" in result["errors"][0]


def test_prune_lists_then_removes_only_inert_evidence(main):
    branch_with_unmapped_change(main)
    git(main, "switch", "-q", "main")
    git(main, "merge", "-q", "--no-ff", "--no-edit", "tool")
    git(main, "switch", "-qc", "next", "main")
    (main / "tool.sh").write_text("echo changed\n")
    record(main, "next", [no_impact("tool.sh")])
    listed = api().prune_evidence(main, base="main")
    assert listed == {"inert": [".ai-dlc/documentation/evidence/tool.json"], "removed": []}
    assert (main / listed["inert"][0]).exists()
    removed = api().prune_evidence(main, base="main", apply=True)
    assert removed["removed"] == listed["inert"]
    assert not (main / listed["inert"][0]).exists()
    assert gate(main)["valid"]


def test_cli_records_to_the_evidence_file_and_gates(main, monkeypatch):
    from typer.testing import CliRunner

    from ai_dlc.cli import app

    monkeypatch.delenv("AI_DLC_DOCS_BASE", raising=False)
    git(main, "switch", "-qc", "work", "main")
    (main / "tool.sh").write_text("echo tool\n")
    legacy_gate_files(main)
    decisions = main / ".ai-dlc/documentation/decisions.json"
    decisions.write_text(json.dumps([no_impact("tool.sh")]))
    runner = CliRunner()
    recorded = runner.invoke(
        app,
        ["docs", "review", "--root", str(main), "--base", "main", "--reviewer", "maintainer"]
        + ["--disposition", str(decisions), "--evidence-id", "work"],
    )
    assert recorded.exit_code == 0, recorded.output
    report = json.loads(recorded.stdout)
    assert report["path"] == ".ai-dlc/documentation/evidence/work.json"
    assert report["added"] == ["tool.sh"]
    assert runner.invoke(app, ["docs", "gate", "--root", str(main)]).exit_code == 0
    (main / "tool.sh").write_text("echo changed\n")
    assert runner.invoke(app, ["docs", "gate", "--root", str(main)]).exit_code == 2


def test_generated_project_ci_supplies_an_independent_comparison_with_history():
    from ai_dlc.files import assets

    workflow = (assets("project-templates") / "project/.github/workflows/verify.yml").read_text()
    assert "fetch-depth: 0" in workflow
    assert "AI_DLC_DOCS_BASE: ${{ github.event.pull_request.base.sha || github.event.before }}" in (
        workflow
    )


def test_recording_counts_targets_another_work_item_already_decided(main):
    branch_with_guide_change(main)
    git(main, "switch", "-qc", "stacked", "guide")
    (main / "tool.sh").write_text("echo tool\n")
    report = record(main, "stacked", [no_impact("tool.sh")])
    assert report["added"] == ["tool.sh"]
    assert report["elsewhere"] == ["docs/api.md"]
    assert gate(main)["valid"]
    (main / "src/api.py").write_text("VERSION = 3\n")
    with pytest.raises(ValueError, match=r"Missing documentation disposition: docs/api\.md"):
        record(main, "stacked", [])
