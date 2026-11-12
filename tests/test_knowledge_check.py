"""``knowledge check``: records, links, supersession, OKF section 11, pin and CI mode."""

import asyncio
import json
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.documentation.knowledge_check import check_records
from ai_dlc.files import assets

ROOT = Path(__file__).resolve().parents[1]
VALID = ROOT / "tests/fixtures/records"
INVALID = ROOT / "tests/fixtures/records_invalid"
PIN = "[format]\nversion = 1\n"
# Fixture directory -> (failing path, pointer, part of the message). One rule each.
EXPECTED = {
    "schema": ("a.md", "/status", "a decision status is one of"),
    "no-frontmatter": ("a.md", "", "no YAML frontmatter"),
    "empty-type": ("a.md", "/type", "a non-empty type is required"),
    "index-frontmatter": ("sub/index.md", "", "an index.md carries no frontmatter"),
    "log-heading": ("log.md", "", "is not YYYY-MM-DD"),
    "dangling-link": ("a.md", "/links/0/target", "CONV-0009 is not the id or alias"),
    "superseded-orphan": ("a.md", "/status", "found 0"),
    "superseded-twice": ("a.md", "/status", "found 2"),
    "superseded-by-proposal": ("a.md", "/status", "which is proposed, not accepted"),
    "supersedes-unmarked": ("b.md", "/links/0/target", "which is still accepted"),
    "supersedes-cycle": ("a.md", "/links", "supersedes cycle: DEC-0001 -> DEC-0002 -> DEC-0001"),
    "derived-without-hash": ("a.md", "/source_hash", "required on a record with a derived_from"),
    "duplicate-source": ("b.md", "/source_hash", "duplicate of a.md"),
    "duplicate-id": ("b.md", "/aliases/0", "LES-0001 is already the id or alias of a.md"),
    "pin-mismatch": ("knowledge.toml", "/format/version", "2 is not supported"),
    "pin-missing": ("knowledge.toml", "/format/version", "no knowledge.toml found"),
}


def record(name="a-slug", kind="decision", status="accepted", links="[]", extra="", body="Body"):
    return (
        f"---\nid: {name}\ntype: {kind}\nscope: team\nstatus: {status}\ndate: 2026-11-10\n"
        f"owner: sean\nsource: SRC-0001\nlinks: {links}\n{extra}---\n{body}\n"
    )


def test_valid_bundle_passes_and_reports_legacy():
    result = check_records(VALID)
    assert result["failures"] == [], result["failures"]
    assert result["records"] == 7
    assert result["legacy"] == [{"path": "legacy/release-runbook.md", "kind": "runbook"}]


def test_every_invalid_fixture_has_a_case():
    assert {path.name for path in INVALID.iterdir()} == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_rule_has_a_failing_fixture(name):
    path, pointer, message = EXPECTED[name]
    result = check_records(INVALID / name)
    assert result["status"] == "invalid"
    assert any(
        item["path"] == path and item["pointer"] == pointer and message in item["message"]
        for item in result["failures"]
    ), result["failures"]


def test_cli_prints_one_line_per_failure_and_exits_non_zero():
    runner = CliRunner()
    good = runner.invoke(app, ["knowledge", "check", str(VALID)])
    assert good.exit_code == 0, good.output
    assert "7 records, 0 failures, 1 legacy" in good.output
    bad = runner.invoke(app, ["knowledge", "check", str(INVALID / "superseded-twice")])
    assert bad.exit_code == 1
    assert f"{(INVALID / 'superseded-twice').as_posix()}/a.md: /status: a superseded" in bad.stdout
    report = runner.invoke(app, ["knowledge", "check", str(INVALID / "schema"), "--json"])
    assert report.exit_code == 1
    assert json.loads(report.stdout)["failures"][0]["pointer"] == "/status"
    both = runner.invoke(app, ["knowledge", "check", str(VALID), "--vault", str(VALID)])
    assert both.exit_code == 2
    missing = runner.invoke(app, ["knowledge", "check", str(VALID / "absent")])
    assert missing.exit_code == 2


def test_cli_and_mcp_share_the_service(tmp_path):
    from ai_dlc.mcp_server import make_server

    shutil.copytree(INVALID / "dangling-link", tmp_path / "records")
    server = make_server(tmp_path)
    result = asyncio.run(server.call_tool("knowledge_check", {"records": "records"}))
    assert json.loads(result[0].text) == check_records(tmp_path / "records")  # type: ignore[index]


@pytest.mark.parametrize(
    "kind", ["decision", "convention", "lesson", "action", "question", "source"]
)
def test_templates_pass_once_filled(tmp_path, kind):
    text = (assets("agents") / "templates/knowledge" / f"{kind}.md").read_text()
    filled = text.replace("YYYY-MM-DDTHH:MM:SS", "2026-11-10T09:00:00").replace(
        "YYYY-MM-DD", "2026-11-10"
    )
    (tmp_path / "knowledge.toml").write_text(PIN)
    (tmp_path / f"{kind}.md").write_text(filled)
    assert check_records(tmp_path)["failures"] == []


@pytest.mark.parametrize("kind", ["runbook", "note"])
def test_legacy_kinds_do_not_fail(tmp_path, kind):
    (tmp_path / "knowledge.toml").write_text(PIN)
    (tmp_path / "old.md").write_text(f"---\nid: {kind}/old\nkind: {kind}\n---\nOld\n")
    result = check_records(tmp_path)
    assert result["status"] == "valid"
    assert result["legacy"] == [{"path": "old.md", "kind": kind}]


def test_external_link_targets_and_markdown_links_are_not_resolved(tmp_path):
    links = (
        "\n  - {type: implements, target: KAN-423}"
        "\n  - {type: codified_as, target: docs/runbook.md}"
        "\n  - {type: belongs_to, target: project-alpha}"
        "\n  - {type: derived_from, target: https://example.invalid/x}"
    )
    (tmp_path / "knowledge.toml").write_text(PIN)
    (tmp_path / "a.md").write_text(
        record(links=links, extra="source_hash: sha256:1\n", body="[gone](missing.md)")
    )
    assert check_records(tmp_path)["failures"] == []
    (tmp_path / "b.md").write_text(record("b", links="\n  - {type: belongs_to, target: LES-0009}"))
    assert [item["path"] for item in check_records(tmp_path)["failures"]] == ["b.md"]


def test_config_option_and_root_index(tmp_path):
    (tmp_path / "pin.toml").write_text(PIN)
    (tmp_path / "records").mkdir()
    (tmp_path / "records/index.md").write_text('---\nokf_version: "0.2"\ntitle: x\n---\n')
    result = check_records(tmp_path / "records", config=tmp_path / "pin.toml")
    assert [(item["path"], item["pointer"]) for item in result["failures"]] == [
        ("index.md", "/title")
    ]


# --- CI mode -------------------------------------------------------------------------


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "test")
    records = tmp_path / "records"
    records.mkdir()
    (records / "knowledge.toml").write_text(PIN)
    (records / "keep.md").write_text(record("keep-it", extra="aliases: [old-name]\n"))
    (records / "draft.md").write_text(record("draft", status="proposed"))
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "change")
    return records


def failures(records):
    return [
        (item["path"], item["pointer"]) for item in check_records(records, base="main")["failures"]
    ]


def test_ci_mode_allows_unchanged_and_proposed_edits(repo):
    (repo / "draft.md").write_text(record("draft", status="proposed", body="Rewritten"))
    assert failures(repo) == []


def test_ci_mode_refuses_editing_an_accepted_decision(repo):
    (repo / "keep.md").write_text(record("keep-it", extra="aliases: [old-name]\n", body="New"))
    assert failures(repo) == [("keep.md", "")]
    (repo / "keep.md").write_text(record("keep-it", extra="aliases: [old-name]\nowner2: x\n"))
    assert ("keep.md", "/owner2") in failures(repo)


def test_ci_mode_allows_superseding_and_numbering(repo):
    (repo / "keep.md").write_text(
        record(
            "DEC-0001",
            status="superseded",
            extra="aliases: [old-name, keep-it]\nvalid_to: 2026-11-12\n",
        )
    )
    (repo / "next.md").write_text(
        record("DEC-0002", links="\n  - {type: supersedes, target: DEC-0001}")
    )
    assert failures(repo) == []
    git(repo.parent, "add", ".")
    git(repo.parent, "commit", "-q", "-m", "supersede")
    git(repo.parent, "mv", "records/next.md", "records/renamed.md")
    assert failures(repo) == []


def test_ci_mode_refuses_deleting_and_renamed_edits(repo):
    git(repo.parent, "mv", "records/keep.md", "records/moved.md")
    (repo / "moved.md").write_text(record("keep-it", extra="aliases: [old-name]\n", body="Edited"))
    assert failures(repo) == [("moved.md", "")]
    (repo / "moved.md").unlink()
    assert failures(repo) == [("keep.md", "")]


def test_ci_mode_needs_a_known_base(repo):
    with pytest.raises(ValueError, match="cannot compare with base"):
        check_records(repo, base="no-such-ref")


def test_a_thousand_records_check_in_under_five_seconds(tmp_path):
    (tmp_path / "knowledge.toml").write_text(PIN)
    for number in range(1, 1001):
        links = (
            "[]" if number == 1 else f"\n  - {{type: derived_from, target: LES-{number - 1:04d}}}"
        )
        extra = "" if number == 1 else f"source_hash: sha256:{number}\n"
        (tmp_path / f"LES-{number:04d}.md").write_text(
            record(f"LES-{number:04d}", kind="lesson", status="open", links=links, extra=extra)
        )
    started = time.perf_counter()
    result = check_records(tmp_path)
    assert time.perf_counter() - started < 5
    assert result["records"] == 1000 and result["failures"] == []


def test_pre_commit_hook_and_reusable_workflow_run_the_check():
    import yaml

    (hook,) = yaml.safe_load((ROOT / ".pre-commit-hooks.yaml").read_text())
    assert hook["entry"] == "ai-dlc knowledge check" and hook["pass_filenames"] is False
    workflow = yaml.safe_load((ROOT / ".github/workflows/knowledge-check.yml").read_text())
    assert set(workflow[True]["workflow_call"]["inputs"]) == {"records", "ai-dlc-ref"}
    steps = workflow["jobs"]["check"]["steps"]
    assert steps[0]["with"]["fetch-depth"] == 0
    assert '--base "origin/$BASE_REF"' in steps[-1]["run"]
