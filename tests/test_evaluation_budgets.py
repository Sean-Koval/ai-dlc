"""Run-budget regressions through real planning, lifecycle and offline reports.

Only Docker is faked; no model API or paid call is involved.
"""

import json
from copy import deepcopy
from xml.etree import ElementTree as ET

import pytest
from test_evaluation_claude import ROOT, NativeDocker, declaration, encoded, native


def run_budget(
    tmp_path,
    monkeypatch,
    *,
    tokens=10000,
    spend=10,
    cost=0.1,
    attempts=2,
    scenarios=1,
    stream=None,
    cap=2,
    **docker_options,
):
    from ai_dlc.verification.evaluation import run

    profile, profile_path = declaration(tmp_path)
    profile.update(attempts=attempts, budgets={"max_tokens": tokens, "max_spend_usd": spend})
    profile_path.write_text(json.dumps(profile))
    suite = json.loads((ROOT / "evaluations/suites/smoke.json").read_text())
    scenario = suite["scenarios"][0]
    for field in ("path", "hidden"):
        scenario["fixture"][field] = str(
            (ROOT / "evaluations/suites" / scenario["fixture"][field]).resolve()
        )
    scenario["limits"] = {"max_spend_usd": cap}
    suite["scenarios"] = [dict(deepcopy(scenario), id=f"case-{i}") for i in range(scenarios)]
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(suite))
    events = native()
    events[-1]["total_cost_usd"] = cost
    fake = NativeDocker(stream=encoded(events) if stream is None else stream, **docker_options)
    monkeypatch.setattr(run.lifecycle, "_docker", fake)
    monkeypatch.setattr(run.lifecycle.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setattr(
        run,
        "_layers",
        lambda image: ["base", "candidate"] if image == profile["engine"]["image"] else ["base"],
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "private-evaluation-key")
    out = tmp_path / "out"
    return out, run.run_suite(suite_path, profile_path, out), fake


def sessions(fake):
    return [c for c in fake.calls if c[0] == "exec" and "-p" in c]


@pytest.mark.parametrize("tokens,spend", [(0, 10), (1000, 0)])
def test_zero_run_budget_starts_no_attempt_and_reports_all_refusals(
    tmp_path, monkeypatch, tokens, spend
):
    from ai_dlc.verification.evaluation.contracts import Report
    from ai_dlc.verification.evaluation.report import build_report

    out, report, fake = run_budget(tmp_path, monkeypatch, tokens=tokens, spend=spend)
    assert not sessions(fake)
    assert not any(c[0] in ("create", "network", "volume") for c in fake.calls)
    assert len(report["arms"]) == 4
    assert all(a["outcome"] == "not-started" for a in report["arms"])
    assert all(all(v is None for v in a["metrics"].values()) for a in report["arms"])
    assert not any(x["result"] == "pass" for a in report["arms"] for x in a["assertions"])
    assert build_report(out) == report
    Report.model_validate(report)
    cases = list(ET.parse(out / "report.junit.xml").iter("testcase"))
    assert cases and all(c.find("skipped") is not None for c in cases)
    assert "not-started" in (out / "report.timeline.md").read_text()


@pytest.mark.parametrize(
    "tokens,spend,expected",
    [(130, 10, 2), (129, 10, 1), (10000, 0.2, 2), (10000, 0.199, 1), (10000, 0.3, 3)],
)
def test_worst_observed_usage_and_exact_positive_boundary_control_next_start(
    tmp_path, monkeypatch, tokens, spend, expected
):
    _, report, fake = run_budget(tmp_path, monkeypatch, tokens=tokens, spend=spend)
    assert len(sessions(fake)) == expected
    assert sum(a["outcome"] == "not-started" for a in report["arms"]) == 4 - expected
    comparison = report["comparison"]["scenarios"]["case-0"]
    assert comparison["usage"]["treatment"] == 65  # refused rows never dilute means
    assert comparison["cost_usd"]["treatment"] == 0.1


def test_actual_native_spend_cap_shrinks_without_changing_planned_client_identity(
    tmp_path, monkeypatch
):
    out, _, fake = run_budget(tmp_path, monkeypatch, spend=0.3)
    commands = sessions(fake)
    assert [float(c[c.index("--max-budget-usd") + 1]) for c in commands] == [0.3, 0.2, 0.1]
    planned = json.loads((out / "plan.json").read_text())["attempts"]
    assert all(p["client"] == planned[0]["client"] for p in planned)
    assert all(p["limits"]["max_spend_usd"] == 0.3 for p in planned)


def test_one_ledger_spans_scenarios_and_both_arms(tmp_path, monkeypatch):
    _, report, fake = run_budget(tmp_path, monkeypatch, tokens=325, scenarios=2)
    assert len(sessions(fake)) == 5
    assert [
        (a["scenario"], a["arm"], a["attempt"])
        for a in report["arms"]
        if a["outcome"] == "not-started"
    ] == [("case-1", "treatment", 2), ("case-1", "baseline", 1), ("case-1", "baseline", 2)]


@pytest.mark.parametrize("damage", ["partial", "malformed", "redacted"])
def test_unknown_or_compromised_usage_stops_further_spending(tmp_path, monkeypatch, damage):
    events = native()
    if damage == "partial":
        stream = encoded(events[:-1])
    elif damage == "malformed":
        stream = b"not-json\n"
    else:
        events[-1]["result"] = "private-evaluation-key"
        stream = encoded(events)
    _, report, fake = run_budget(tmp_path, monkeypatch, stream=stream)
    assert len(sessions(fake)) == 1
    assert report["arms"][0]["outcome"] == "incomplete"
    assert all(
        a["outcome"] == "not-started" and a["limit"] == "unknown-usage" for a in report["arms"][1:]
    )
    if damage == "redacted":
        assert report["arms"][0]["stage"] == "redaction"


def test_terminal_error_usage_consumes_the_run_budget(tmp_path, monkeypatch):
    events = native()
    events[-1].update(
        subtype="error_max_turns", is_error=True, errors=["limit reached"], total_cost_usd=0.1
    )
    _, report, fake = run_budget(tmp_path, monkeypatch, tokens=65, stream=encoded(events))
    assert len(sessions(fake)) == 1
    assert report["arms"][0]["metrics"]["usage"] == 65
    assert report["arms"][0]["limit"] == "max_turns"
    assert all(a["outcome"] == "not-started" for a in report["arms"][1:])


@pytest.mark.parametrize("spend", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_run_budget_is_a_validation_error(tmp_path, spend):
    from ai_dlc.verification.evaluation.planning import plan

    profile, _ = declaration(tmp_path)
    profile["budgets"]["max_spend_usd"] = spend
    suite = json.loads((ROOT / "evaluations/suites/smoke.json").read_text())
    with pytest.raises(ValueError, match="budgets.max_spend_usd"):
        plan(suite, profile)


@pytest.mark.parametrize(
    "damage",
    [
        "missing-receipt",
        "broken-receipt",
        "duplicate-key",
        "forged-remaining",
        "wrong-attempt",
        "boolean-attempt",
        "wrong-limit-type",
        "execution-evidence",
        "broken-manifest",
    ],
)
def test_rebuilt_refusals_require_consistent_retained_evidence(tmp_path, monkeypatch, damage):
    from ai_dlc.verification.evaluation.report import build_report, manifest_of

    out, _, _ = run_budget(tmp_path, monkeypatch, tokens=0)
    directory = out / "case-0/treatment/1"
    receipt = directory / "budget.json"
    if damage == "missing-receipt":
        receipt.unlink()
    elif damage == "broken-receipt":
        receipt.write_text("[]")
    elif damage == "duplicate-key":
        receipt.write_text(
            receipt.read_text().replace('"start": false', '"start": true, "start": false')
        )
    elif damage == "forged-remaining":
        value = json.loads(receipt.read_text())
        value["remaining_tokens"] = 900
        receipt.write_text(json.dumps(value))
    elif damage in ("wrong-attempt", "boolean-attempt", "wrong-limit-type"):
        path = directory / "attempt.json"
        value = json.loads(path.read_text())
        if damage == "wrong-limit-type":
            value["limit"] = []
        else:
            value["attempt"] = True if damage == "boolean-attempt" else 9
        path.write_text(json.dumps(value))
    elif damage == "execution-evidence":
        (directory / "client-stream.jsonl").write_text("attempt really ran")
    # Even a refreshed manifest cannot turn semantically invalid refusal evidence into a skip.
    (directory / "manifest.json").write_text(
        json.dumps(manifest_of(directory)) if damage != "broken-manifest" else "[]"
    )
    from ai_dlc.verification.evaluation.contracts import Report

    rebuilt = build_report(out)
    Report.model_validate(rebuilt)
    arm = rebuilt["arms"][0]
    assert arm["outcome"] == "incomplete"
    assert all(x["result"] == "unavailable" for x in arm["assertions"])
    assert all(v is None for v in arm["metrics"].values())


def test_changed_earlier_usage_invalidates_later_budget_refusals(tmp_path, monkeypatch):
    from ai_dlc.verification.evaluation.report import build_report

    out, _, _ = run_budget(tmp_path, monkeypatch, tokens=65)
    stream = out / "case-0/treatment/1/client-stream.jsonl"
    events = native()
    events[-1]["usage"]["input_tokens"] = 11
    stream.write_bytes(encoded(events))
    report = build_report(out)
    assert all(a["outcome"] == "incomplete" for a in report["arms"])
    assert all(a["metrics"]["usage"] is None for a in report["arms"])


def test_client_reported_overshoot_is_retained_and_prevents_another_start(tmp_path, monkeypatch):
    _, report, fake = run_budget(tmp_path, monkeypatch, tokens=1, spend=0.01)
    assert len(sessions(fake)) == 1
    assert report["arms"][0]["metrics"]["cost_usd"] == 0.1
    assert report["arms"][0]["metrics"]["usage"] == 65
    assert all(a["outcome"] == "not-started" for a in report["arms"][1:])


def test_zero_attempt_spend_cap_also_refuses_client_start(tmp_path, monkeypatch):
    _, report, fake = run_budget(tmp_path, monkeypatch, cap=0)
    assert not sessions(fake)
    assert all(a["outcome"] == "not-started" for a in report["arms"])


def test_comparison_exposes_unequal_started_and_refused_coverage(tmp_path, monkeypatch):
    _, report, _ = run_budget(tmp_path, monkeypatch, tokens=195)
    scenario = report["comparison"]["scenarios"]["case-0"]
    assert scenario["attempts_incomplete"] == {"treatment": 0, "baseline": 0, "difference": 0}
    assert scenario["attempts_not_started"] == {"treatment": 0, "baseline": 1, "difference": -1}


def test_refused_workflow_only_rows_cannot_be_vacuous_correctness_success(tmp_path, monkeypatch):
    from ai_dlc.verification.evaluation.report import build_report

    out, _, _ = run_budget(tmp_path, monkeypatch, tokens=0)
    path = out / "inputs/suite.json"
    suite = json.loads(path.read_text())
    suite["scenarios"][0]["assertions"] = [
        a for a in suite["scenarios"][0]["assertions"] if a["dimension"] != "correctness"
    ]
    path.write_text(json.dumps(suite))
    counts = build_report(out)["comparison"]["scenarios"]["case-0"]["correctness_passed"]
    assert counts == {"treatment": 0, "baseline": 0, "difference": 0}


@pytest.mark.parametrize("refresh_manifest", [False, True])
def test_empty_attempt_record_rebuilds_as_incomplete(tmp_path, monkeypatch, refresh_manifest):
    from ai_dlc.verification.evaluation.contracts import Report
    from ai_dlc.verification.evaluation.report import build_report, manifest_of

    out, _, _ = run_budget(tmp_path, monkeypatch, tokens=0, attempts=1)
    directory = out / "case-0/treatment/1"
    (directory / "attempt.json").write_text("{}")
    if refresh_manifest:
        (directory / "manifest.json").write_text(json.dumps(manifest_of(directory)))
    report = build_report(out)
    Report.model_validate(report)
    assert report["arms"][0]["outcome"] == "incomplete"
    assert not any(a["result"] == "pass" for a in report["arms"][0]["assertions"])


@pytest.mark.parametrize("tokens", [0, 65])
@pytest.mark.parametrize(
    "field,value",
    [
        ("outcome", None),
        ("outcome", []),
        ("outcome", "unrecognized"),
        ("scenario", "another-scenario"),
        ("arm", "baseline"),
        ("attempt", True),
        ("stage", []),
        ("limit", {}),
        ("detail", ["untrusted"]),
        ("cleanup", []),
        ("cleanup", {"clean": "yes"}),
    ],
)
def test_malformed_attempt_fields_cannot_break_or_forge_reports(
    tmp_path, monkeypatch, tokens, field, value
):
    from ai_dlc.verification.evaluation.contracts import Report
    from ai_dlc.verification.evaluation.report import build_report, manifest_of

    out, _, _ = run_budget(tmp_path, monkeypatch, tokens=tokens, attempts=1)
    directory = out / "case-0/treatment/1"
    path = directory / "attempt.json"
    record = json.loads(path.read_text())
    if value is None:
        del record[field]
    else:
        record[field] = value
    path.write_text(json.dumps(record))
    (directory / "manifest.json").write_text(json.dumps(manifest_of(directory)))
    report = build_report(out)
    Report.model_validate(report)
    arm = report["arms"][0]
    assert (arm["scenario"], arm["arm"], arm["attempt"]) == ("case-0", "treatment", 1)
    assert arm["outcome"] == "incomplete"
    assert arm["metrics"]["usage"] is None
    assert not any(a["result"] == "pass" for a in arm["assertions"])
