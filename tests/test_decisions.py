"""Decision records: template, frontmatter validation and the supersede-not-edit rule."""

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.documentation import knowledge_notes
from ai_dlc.documentation.decisions import EDITED, decision_findings
from ai_dlc.files import assets
from ai_dlc.setup.templates import adopt

ROOT = Path(__file__).resolve().parents[1]

ACCEPTED = """---
id: decision/0007-landing-stays-in-hangar
kind: decision
scope: team
label: internal
status: accepted
sources: [{uri: "https://github.com/o/r/pull/45", hash: "git:abc123"}]
author: human:sean-koval
confidence: high
valid_from: 2026-10-20
valid_to: null
review_by: 2027-04-20
supersedes: []
checks:
  - id: landing-stays-in-hangar
    scope: job
    assert: {never: {event: pr.merge, where: {hangar.pr.merged_by: {not: "hangar-landing[bot]"}}}}
    severity: warn
---
# 0007 Landing stays in hangar

## Decision

Hangar lands every pull request.
"""


def repository(tmp_path, text=ACCEPTED, name="0007-landing-stays-in-hangar.md"):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-b", "main")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Test")
    path = tmp_path / "docs/decisions" / name
    path.parent.mkdir(parents=True)
    path.write_text(text)
    git("add", ".")
    git("commit", "-m", "decision")
    return path


def errors(root):
    return [f for f in decision_findings(root) if f["severity"] == "error"]


def docs_check(root):
    return CliRunner().invoke(app, ["docs", "check", "--root", str(root)])


def test_project_init_ships_the_convention(tmp_path):
    root = tmp_path / "product"
    root.mkdir()
    assert adopt(root, apply=True, initialize=True)["status"] == "applied"
    readme = (root / "docs/decisions/README.md").read_text()
    for phrase in ["NNNN-slug.md", "superseded, not edited", "flightdeck.spec/v1", "CODEOWNERS"]:
        assert phrase in readme
    template = (root / "docs/templates/adr.md").read_bytes()
    assert template == (assets("agents") / "templates/adr.md").read_bytes()
    data, _raw, body = knowledge_notes.split(template.decode())
    assert data is not None
    assert {"id", "kind", "status", "sources", "author", "review_by", "supersedes"} <= set(data)
    assert data["kind"] == "decision" and data["status"] == "proposed"
    for heading in ["Context", "Options considered", "Decision", "Consequences", "Links"]:
        assert f"## {heading}" in body


def test_valid_decision_with_flightdeck_checks_passes(tmp_path):
    repository(tmp_path)
    assert decision_findings(tmp_path) == []


def test_missing_status_is_a_schema_error_and_fails_docs_check(tmp_path):
    repository(tmp_path, ACCEPTED.replace("status: accepted\n", ""))
    assert any("status" in f["message"] for f in errors(tmp_path))
    result = docs_check(tmp_path)
    assert result.exit_code == 2
    assert "decision-schema" in result.output


def test_check_without_assert_is_a_schema_error(tmp_path):
    text = ACCEPTED.replace(
        '    assert: {never: {event: pr.merge, where: {hangar.pr.merged_by: {not: "hangar-landing[bot]"}}}}\n',
        "",
    )
    repository(tmp_path, text)
    assert any(f["message"].startswith("checks.0.assert") for f in errors(tmp_path))


def test_check_shapes_are_validated_not_evaluated(tmp_path):
    text = ACCEPTED.replace("    severity: warn\n", "    severity: page\n").replace(
        "checks:\n",
        "checks:\n  - id: landing-stays-in-hangar\n    assert: {never: {}, eventually: {}}\n",
    )
    repository(tmp_path, text)
    messages = [f["message"] for f in errors(tmp_path)]
    assert any("severity" in m for m in messages)
    assert any("exactly one" in m for m in messages)


def test_check_ids_are_unique_within_a_record(tmp_path):
    text = ACCEPTED.replace(
        "checks:\n",
        "checks:\n  - id: landing-stays-in-hangar\n    assert: {eventually: {event: verify}}\n",
    )
    repository(tmp_path, text)
    assert any("unique" in f["message"] for f in errors(tmp_path))


def test_editing_an_accepted_body_fails_until_superseded(tmp_path):
    path = repository(tmp_path)
    path.write_text(ACCEPTED.replace("Hangar lands", "Anyone lands"))
    assert [f["message"] for f in errors(tmp_path)] == [EDITED]
    result = docs_check(tmp_path)
    assert result.exit_code == 2 and EDITED in result.output

    superseded = ACCEPTED.replace("Hangar lands", "Anyone lands").replace(
        "status: accepted", "status: superseded"
    )
    path.write_text(superseded)
    assert any("valid_to" in f["message"] for f in errors(tmp_path))
    path.write_text(superseded.replace("valid_to: null", "valid_to: 2026-12-01"))
    assert errors(tmp_path) == []


def test_frontmatter_edits_to_an_accepted_record_are_allowed(tmp_path):
    path = repository(tmp_path)
    path.write_text(ACCEPTED.replace("review_by: 2027-04-20", "review_by: 2027-06-01"))
    assert errors(tmp_path) == []


def test_records_without_frontmatter_are_information_only(tmp_path):
    repository(tmp_path, "# Decision\n\nStatus: accepted\n", "0001-old.md")
    (tmp_path / "docs/decisions/README.md").write_text("# Decisions\n")
    findings = decision_findings(tmp_path)
    assert [(f["code"], f["severity"]) for f in findings] == [
        ("decision-frontmatter-missing", "info")
    ]
    assert docs_check(tmp_path).exit_code == 0


def test_this_repositorys_decisions_validate():
    assert errors(ROOT) == []
    data, _raw, _body = knowledge_notes.split(
        (ROOT / "docs/decisions/0001-refocus-ai-dlc.md").read_text()
    )
    assert data is not None
    assert data["id"] == "decision/0001-refocus-ai-dlc" and data["status"] == "accepted"
    assert knowledge_notes.errors(data) == []


def test_schema_accepts_flightdeck_fixture_shape():
    """flightdeck's ADR fixture (frontmatter form) validates once the schema's fields exist."""
    data = knowledge_notes.split(ACCEPTED)[0]
    assert data is not None
    schema = json.loads((ROOT / "contracts/knowledge-note.schema.json").read_text())
    assert "checks" in schema["properties"] and "status" in schema["properties"]
    assert knowledge_notes.errors(data) == []
