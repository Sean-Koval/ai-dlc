"""Reports rebuild from retained evidence alone, and tampering or gaps can never pass."""

import io
import json
import socket
import subprocess
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = "python@sha256:" + "a" * 64
CANDIDATE = "sha256:" + "d" * 64
SECRET = "s3cr3t-value-that-must-never-be-retained"


def archive(files):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeDocker:
    """Replaces only the docker process boundary for a whole suite run."""

    def __init__(self):
        self.leak = None
        self.fail_cleanup = False
        self.current = None

    def __call__(self, args, *, timeout, input=None, cancel=None):
        del timeout, input, cancel

        def ok(out=b"", code=0, err=b""):
            return SimpleNamespace(returncode=code, stdout=out, stderr=err)

        if args[:2] == ["image", "inspect"]:
            layers = ["l1", "l2"] + (["l3"] if args[-1] == CANDIDATE else [])
            return ok(json.dumps(layers).encode())
        if args[0] == "create":
            self.current = "treatment" if CANDIDATE in args else "baseline"
        if args[0] == "run" and "tar" in args and "-c" in args:
            files = {"project/csvcheck/validate.py": self.current.encode()}
            if self.current == "treatment":
                files["project/.ai-dlc/work/item.toml"] = b"id = 'item'\n"
            if self.leak:
                files["project/notes.txt"] = f"token={self.leak}\n".encode()
            return ok(archive(files))
        if args[0] == "run" and any("unittest" in part for part in args):
            passed = self.current == "treatment"
            return ok(
                code=0 if passed else 1,
                err=b"Ran 10 tests\n\nOK\n" if passed else b"FAILED (failures=6)\n",
            )
        if args[0] == "rm" and self.fail_cleanup:
            return ok(code=1, err=b"device busy")
        if args[0] == "exec":
            return ok(b"ALL TESTS PASS\n")
        return ok()


@pytest.fixture
def docker(monkeypatch):
    from ai_dlc.verification.evaluation import attempt

    fake = FakeDocker()
    monkeypatch.setattr(attempt, "_docker", fake)
    monkeypatch.setattr(attempt.shutil, "which", lambda name: "/usr/bin/" + name)
    return fake


@pytest.fixture
def profile_path(tmp_path):
    profile = json.loads((ROOT / "evaluations/profiles/local-deterministic.json").read_text())
    profile["image"] = BASE
    profile["engine"]["image"] = CANDIDATE
    profile["credentials"] = ["EVAL_TOKEN"]
    profile["driver"]["script"] = str(ROOT / "evaluations/profiles/local-deterministic.script.json")
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile))
    return path


def run(tmp_path, profile_path):
    from ai_dlc.verification.evaluation.run import run_suite

    return run_suite(ROOT / "evaluations/suites/smoke.json", profile_path, tmp_path / "out")


def rebuild(tmp_path):
    from ai_dlc.verification.evaluation.report import build_report

    return build_report(tmp_path / "out")


def arm(report, name):
    return next(a for a in report["arms"] if a["arm"] == name)


def results(report, name):
    return {a["id"]: a["result"] for a in arm(report, name)["assertions"]}


def test_report_rebuilds_the_same_results_offline(tmp_path, profile_path, docker, monkeypatch):
    original = run(tmp_path, profile_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("report must not start anything")

    from ai_dlc.verification.evaluation import attempt

    monkeypatch.setattr(attempt, "_docker", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    rebuilt = rebuild(tmp_path)
    assert rebuilt == original
    assert arm(rebuilt, "treatment")["outcome"] == "completed"
    assert arm(rebuilt, "baseline")["outcome"] == "product"
    from ai_dlc.verification.evaluation.contracts import Report

    Report.model_validate(rebuilt)


def test_comparison_states_differences_with_attempt_counts_and_no_claim(
    tmp_path, profile_path, docker
):
    comparison = run(tmp_path, profile_path)["comparison"]
    assert comparison["attempts_per_arm"] == 1
    assert comparison["claim"].startswith("none")
    scenario = comparison["scenarios"]["csv-duplicate-rows"]
    assert scenario["correctness_passed"] == {"treatment": 1, "baseline": 0, "difference": 1}
    assert scenario["turns"]["treatment"] == 2 and scenario["turns"]["baseline"] == 1
    assert scenario["usage"] == {"treatment": None, "baseline": None, "difference": None}
    assert set(scenario["wall_seconds"]) == {"treatment", "baseline", "difference"}


def test_changed_artifacts_make_affected_results_unavailable_and_are_named(
    tmp_path, profile_path, docker
):
    run(tmp_path, profile_path)
    grading = tmp_path / "out/csv-duplicate-rows/baseline/1/grading/hidden-tests.json"
    forged = json.loads(grading.read_text())
    forged["exit_code"] = 0
    grading.write_text(json.dumps(forged))
    report = rebuild(tmp_path)
    baseline = arm(report, "baseline")
    assert results(report, "baseline")["hidden-tests"] == "unavailable"
    assert baseline["outcome"] == "incomplete"
    assert "grading/hidden-tests.json" in baseline["detail"]
    assert arm(report, "treatment")["outcome"] == "completed"  # untouched attempts are unaffected


@pytest.mark.parametrize(
    "damage",
    [
        lambda events: events.write_text(events.read_text() + "{not json\n"),
        lambda events: events.write_text("\n".join(events.read_text().splitlines()[:-1]) + "\n"),
        lambda events: events.unlink(),
    ],
)
def test_malformed_truncated_or_missing_traces_are_incomplete(
    tmp_path, profile_path, docker, damage
):
    run(tmp_path, profile_path)
    damage(tmp_path / "out/csv-duplicate-rows/treatment/1/events.jsonl")
    treatment = arm(rebuild(tmp_path), "treatment")
    assert treatment["outcome"] == "incomplete"
    assert "pass" not in {a["result"] for a in treatment["assertions"]}


def test_a_missing_attempt_directory_is_reported_not_skipped(tmp_path, profile_path, docker):
    import shutil

    run(tmp_path, profile_path)
    shutil.rmtree(tmp_path / "out/csv-duplicate-rows/baseline")
    report = rebuild(tmp_path)
    assert len(report["arms"]) == 2
    assert arm(report, "baseline")["outcome"] == "incomplete"


def test_secret_values_are_redacted_from_evidence_and_fail_the_attempt(
    tmp_path, profile_path, docker, monkeypatch
):
    monkeypatch.setenv("EVAL_TOKEN", SECRET)
    docker.leak = SECRET
    report = run(tmp_path, profile_path)
    for item in report["arms"]:
        assert item["outcome"] == "incomplete"
        assert "EVAL_TOKEN" in item["detail"] and "notes.txt" in item["detail"]
    for path in (tmp_path / "out").rglob("*"):
        if path.is_file():
            assert SECRET not in path.read_text(errors="replace"), path
    assert (
        "[REDACTED:EVAL_TOKEN]"
        in (tmp_path / "out/csv-duplicate-rows/baseline/1/tree/project/notes.txt").read_text()
    )
    assert rebuild(tmp_path) == report


def test_cleanup_failure_is_visible_in_the_report(tmp_path, profile_path, docker):
    docker.fail_cleanup = True
    report = run(tmp_path, profile_path)
    assert [a["cleanup_clean"] for a in report["arms"]] == [False, False]
    assert arm(report, "treatment")["outcome"] == "completed"  # a result, but never a clean one


def test_junit_and_timeline_are_written_and_name_the_failed_stage(tmp_path, profile_path, docker):
    from ai_dlc.verification.evaluation.report import write_report

    run(tmp_path, profile_path)
    write_report(tmp_path / "out")
    suites = ET.parse(tmp_path / "out/report.junit.xml").getroot()
    cases = {
        (suite.get("name"), case.get("name")): case
        for suite in suites.iter("testsuite")
        for case in suite.iter("testcase")
    }
    failed = cases[("csv-duplicate-rows.baseline.1", "hidden-tests")]
    assert failed.find("failure") is not None
    assert "FAILED (failures=6)" in failed.find("failure").get("message")
    assert cases[("csv-duplicate-rows.treatment.1", "handoff-rubric")].find("skipped") is not None
    timeline = (tmp_path / "out/report.timeline.md").read_text()
    assert "csv-duplicate-rows / baseline / attempt 1 — product" in timeline
    assert "grading/hidden-tests.json" in timeline
    assert "ALL TESTS PASS" not in timeline


def test_cli_report_rebuilds_without_docker(tmp_path, profile_path, docker):
    from typer.testing import CliRunner

    from ai_dlc.cli import app

    run(tmp_path, profile_path)
    done = CliRunner().invoke(app, ["eval", "report", str(tmp_path / "out")])
    assert done.exit_code == 0, done.output
    assert json.loads(done.stdout)["suite"] == "smoke"
    assert (tmp_path / "out/report.junit.xml").is_file()
