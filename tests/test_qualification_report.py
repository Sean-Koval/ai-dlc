"""Synthetic report tests are fixture evidence, never live qualification."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/qualify_framework.py"


def _cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def _report(tmp_path, *, classification="fixture", result="passed"):
    artifact = tmp_path / "transcript.txt"
    artifact.write_text("synthetic observation\n")
    row = {
        "scenario_id": "Q02-provider-cycle",
        "target_id": "github",
        "commit": "1" * 40,
        "profile_revision": None,
        "bundle_revisions": {},
        "environment": {
            "os": "Darwin",
            "version": "fixture",
            "architecture": "arm64",
            "isolation": "existing-host",
            "image_digest": None,
            "container_id": None,
            "inherited_tools": ["synthetic fixture"],
        },
        "harness_name": None,
        "harness_version": None,
        "provider": {
            "kind": "github-issues",
            "alias": "personal",
            "site": "example.test",
            "project": "fixture",
        },
        "steps": ["Record the synthetic result; do not execute it"],
        "expected": "A new item uses the shared lifecycle",
        "observed": "Synthetic case passed",
        "classification": classification,
        "result": result,
        "evidence": [
            {
                "path": "transcript.txt",
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "kind": classification,
                "producer": "test fixture",
                "method": "synthetic transcript",
            }
        ],
        "limitations": [
            "Synthetic only; no live credentials or service",
            "No profile or bundle selected",
        ],
    }
    return {"schema": 1, "run_id": "fixture-run", "scenarios": [row]}


def _validate(tmp_path, report):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report))
    return _cli("--validate", path)


def test_protocol_is_explicitly_unrun_and_schema_valid(tmp_path):
    result = _cli("--protocol")
    assert result.returncode == 0, result.stderr
    protocol = json.loads(result.stdout)
    assert all(
        row["result"] == "not-run" and row["classification"] is None
        for row in protocol["scenarios"]
    )
    assert all(row["commit"] is None and not row["evidence"] for row in protocol["scenarios"])
    checked = _validate(tmp_path, protocol)
    assert checked.returncode == 0, checked.stderr
    assert json.loads(checked.stdout)["qualification_complete"] is False


def test_fixture_evidence_never_fills_live_adapter_slots(tmp_path):
    report = _report(tmp_path)
    second = copy.deepcopy(report["scenarios"][0])
    second["target_id"] = "jira"
    second["provider"]["kind"] = "jira-cloud"
    report["scenarios"].append(second)
    result = _validate(tmp_path, report)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["structurally_valid"] is True
    assert summary["live_authenticated"] is False
    assert summary["qualification_complete"] is False
    assert summary["requirements"]["Q-02"]["reported_live_adapters"] == []
    assert summary["requirements"]["Q-02"]["status"] == "unmet"
    assert {row["classification"] for row in summary["scenarios"]} == {"fixture"}


@pytest.mark.parametrize("result", ["unavailable", "not-run", "failed"])
def test_incomplete_results_are_valid_and_preserved(tmp_path, result):
    report = _report(tmp_path, result=result)
    if result != "failed":
        report["scenarios"][0].update(commit=None, classification=None, evidence=[], observed="")
    checked = _validate(tmp_path, report)
    assert checked.returncode == 0, checked.stderr
    assert json.loads(checked.stdout)["scenarios"][0]["result"] == result


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown-field",
        "duplicate",
        "unknown-scenario",
        "hash",
        "missing",
        "escape",
        "symlink",
        "missing-observation",
        "missing-evidence",
        "missing-commit",
        "mixed-class",
        "container",
        "hosted",
        "harness",
    ],
)
def test_invalid_or_contradictory_reports_fail(tmp_path, mutation):
    report = _report(tmp_path, classification="live-local")
    row = report["scenarios"][0]
    if mutation == "unknown-field":
        row["authentcated"] = True
    elif mutation == "duplicate":
        report["scenarios"].append(copy.deepcopy(row))
    elif mutation == "unknown-scenario":
        row["scenario_id"] = "invented"
    elif mutation == "hash":
        row["evidence"][0]["sha256"] = "0" * 64
    elif mutation == "missing":
        row["evidence"][0]["path"] = "missing.txt"
    elif mutation == "escape":
        row["evidence"][0]["path"] = "../outside.txt"
    elif mutation == "symlink":
        (tmp_path / "linked.txt").symlink_to(tmp_path.parent / "outside.txt")
        row["evidence"][0]["path"] = "linked.txt"
    elif mutation == "missing-observation":
        row["observed"] = " "
    elif mutation == "missing-evidence":
        row["evidence"] = []
    elif mutation == "missing-commit":
        row["commit"] = None
    elif mutation == "mixed-class":
        row["evidence"][0]["kind"] = "fixture"
    elif mutation == "container":
        row["classification"] = row["evidence"][0]["kind"] = "live-container"
        row["environment"]["isolation"] = "container"
    elif mutation == "hosted":
        row["environment"]["isolation"] = "hosted"
    elif mutation == "harness":
        row["scenario_id"] = "Q03-handoff"
    checked = _validate(tmp_path, report)
    assert checked.returncode != 0
    assert json.loads(checked.stdout)["structurally_valid"] is False


def test_two_github_modes_still_count_as_one_adapter(tmp_path):
    report = _report(tmp_path, classification="live-local")
    second = copy.deepcopy(report["scenarios"][0])
    second["target_id"] = "github-project"
    second["provider"]["alias"] = "board"
    report["scenarios"].append(second)
    checked = _validate(tmp_path, report)
    assert checked.returncode == 0, checked.stderr
    summary = json.loads(checked.stdout)
    assert summary["requirements"]["Q-02"]["reported_live_adapters"] == ["github-issues"]
    assert summary["requirements"]["Q-02"]["status"] == "unmet"


def test_even_two_declared_live_adapters_require_human_review(tmp_path):
    report = _report(tmp_path, classification="live-local")
    second = copy.deepcopy(report["scenarios"][0])
    second["target_id"] = "jira"
    second["provider"]["kind"] = "jira-cloud"
    report["scenarios"].append(second)
    result = _validate(tmp_path, report)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["live_authenticated"] is False
    assert summary["qualification_complete"] is False
    assert summary["requirements"]["Q-02"]["status"] == "pending-review"


def test_steps_are_data_and_unknown_execution_option_is_refused(tmp_path):
    report = _report(tmp_path)
    marker = tmp_path / "must-not-exist"
    report["scenarios"][0]["steps"] = [f"touch {marker}"]
    assert _validate(tmp_path, report).returncode == 0
    assert _cli("--execute", marker).returncode != 0
    assert not marker.exists()


def test_schema_is_strict_and_portable():
    result = _cli("--schema")
    assert result.returncode == 0, result.stderr
    schema = json.loads(result.stdout)
    assert schema["additionalProperties"] is False
    assert str(ROOT) not in result.stdout


def test_duplicate_json_keys_cannot_override_classification(tmp_path):
    report = _report(tmp_path)
    path = tmp_path / "report.json"
    encoded = json.dumps(report).replace(
        '"classification": "fixture"', '"classification": "live-local", "classification": "fixture"'
    )
    path.write_text(encoded)
    result = _cli("--validate", path)
    assert result.returncode != 0
    assert "duplicate" in result.stdout


def test_boolean_schema_version_is_not_integer_schema_one(tmp_path):
    report = _report(tmp_path)
    report["schema"] = True
    assert _validate(tmp_path, report).returncode != 0


def test_native_report_cannot_fill_required_container_slot(tmp_path):
    report = _report(tmp_path, classification="live-local")
    row = report["scenarios"][0]
    row["scenario_id"] = "Q01-setup"
    row["target_id"] = "container-ubuntu2404-arm64"
    assert _validate(tmp_path, report).returncode != 0


def test_incomplete_harness_pair_is_refused(tmp_path):
    report = _report(tmp_path)
    report["scenarios"][0]["harness_version"] = "fixture-version"
    assert _validate(tmp_path, report).returncode != 0


def test_validation_retains_report_identity(tmp_path):
    report = _report(tmp_path)
    result = _validate(tmp_path, report)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["run_id"] == report["run_id"]


def test_documented_synthetic_example_validates_without_live_claim(tmp_path):
    document = (ROOT / "docs/verification/framework-qualification.md").read_text()
    example = json.loads(document.split("```json\n", 1)[1].split("\n```", 1)[0])
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "synthetic.txt").write_text("synthetic observation\n")
    result = _validate(tmp_path, example)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["scenarios"][0]["classification"] == "fixture"
    assert summary["qualification_complete"] is False
    assert all(item["status"] == "unmet" for item in summary["requirements"].values())
