"""Evaluation planning validates the whole matrix offline and never reads a secret."""

import copy
import json
import socket
import subprocess

import pytest

IMAGE = "ghcr.io/example/eval@sha256:" + "a" * 64

SCENARIO = {
    "id": "csv-feature",
    "goal": "Add duplicate-row detection to the CSV validator.",
    "fixture": {"path": "fixtures/csv-validator", "digest": "b" * 64},
    "answers": [{"match": "which column", "reply": "Use every column."}],
    "checkpoints": ["reviewed-work", "pull-request"],
    "assertions": [
        {"id": "hidden-tests", "dimension": "correctness", "kind": "hidden-tests"},
        {"id": "work-before-code", "dimension": "workflow", "kind": "ordering"},
        {"id": "handoff-rubric", "dimension": "quality", "kind": "human-review"},
    ],
    "arms": ["treatment", "baseline"],
}
SUITE = {"schema": 1, "id": "smoke", "scenarios": [SCENARIO]}
PROFILE = {
    "schema": 1,
    "id": "local-deterministic",
    "mode": "candidate",
    "image": IMAGE,
    "engine": {
        "artifact": "dist/ai_dlc-0.4.0-py3-none-any.whl",
        "sha256": "c" * 64,
        "image": "sha256:" + "d" * 64,
    },
    "driver": {"kind": "deterministic", "version": "1", "script": "script.json"},
    "model": "none",
    "budgets": {"max_tokens": 0, "max_spend_usd": 0},
    "credentials": ["EVAL_GITHUB_TOKEN"],
    "resources": ["docker"],
    "attempts": 1,
}


def planning():
    from ai_dlc.verification.evaluation import planning as module

    return module


def plan(suite=SUITE, profile=PROFILE):
    return planning().plan(copy.deepcopy(suite), copy.deepcopy(profile))


def changed(source, path, value):
    result = copy.deepcopy(source)
    target = result
    for key in path[:-1]:
        target = target[key]
    if value is None:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return result


def test_plan_lists_every_scenario_arm_and_attempt_with_its_pinned_inputs():
    result = plan(profile=changed(PROFILE, ["attempts"], 2))
    assert [(a["scenario"], a["arm"], a["attempt"]) for a in result["attempts"]] == [
        ("csv-feature", "treatment", 1),
        ("csv-feature", "treatment", 2),
        ("csv-feature", "baseline", 1),
        ("csv-feature", "baseline", 2),
    ]
    first = result["attempts"][0]
    assert first["image"] == "sha256:" + "d" * 64  # the prebuilt candidate image
    assert result["attempts"][2]["image"] == IMAGE
    assert first["engine_sha256"] == "c" * 64
    assert first["limits"] == {"timeout_minutes": 30, "max_turns": 20}
    assert result["budgets"] == {"max_tokens": 0, "max_spend_usd": 0}
    assert result["credentials"] == ["EVAL_GITHUB_TOKEN"]


def test_workflow_assertions_apply_only_to_the_treatment_arm():
    by_arm = {a["arm"]: a["assertions"] for a in plan()["attempts"]}
    assert by_arm["treatment"] == ["hidden-tests", "work-before-code", "handoff-rubric"]
    assert by_arm["baseline"] == ["hidden-tests", "handoff-rubric"]
    assert plan()["attempts"][1]["engine_sha256"] is None  # baseline installs no engine


def test_single_attempt_is_labelled_as_no_basis_for_comparison():
    assert plan()["comparison"] == {
        "attempts_per_arm": 1,
        "claim": "none: one attempt per arm shows differences without supporting a conclusion",
    }


@pytest.mark.parametrize(
    ("path", "value", "named"),
    [
        (["model"], None, "model"),
        (["budgets", "max_tokens"], None, "max_tokens"),
        (["budgets", "max_spend_usd"], None, "max_spend_usd"),
        (["image"], "ghcr.io/example/eval:latest", "image"),
        (["engine", "sha256"], "short", "sha256"),
        (["credentials"], ["lowercase_name"], "credentials"),
        (["attempts"], 0, "attempts"),
        (["driver"], {"kind": "telepathy", "version": "1"}, "kind"),
        (["driver", "script"], None, "script"),
        (["engine", "image"], "candidate:latest", "image"),
    ],
)
def test_incomplete_or_unpinned_profiles_are_refused_by_field(path, value, named):
    with pytest.raises(ValueError, match=named):
        plan(profile=changed(PROFILE, path, value))


def test_release_mode_requires_a_published_hash_verified_artifact():
    release = changed(PROFILE, ["mode"], "release")
    with pytest.raises(ValueError, match="published"):
        plan(profile=release)
    url = "https://github.com/Sean-Koval/ai-dlc/releases/download/v0.4.0/ai_dlc-0.4.0.whl"
    assert plan(profile=changed(release, ["engine", "artifact"], url))["mode"] == "release"


@pytest.mark.parametrize(
    ("path", "value", "named"),
    [
        (["scenarios", 0, "api_token"], "anything", "api_token"),
        (["scenarios", 0, "goal"], "Use ghp_" + "A" * 36 + " to push.", "goal"),
        (["scenarios", 0, "answers", 0, "reply"], "-----BEGIN PRIVATE KEY-----", "reply"),
    ],
)
def test_secrets_in_scenarios_are_refused_and_never_echoed(path, value, named):
    with pytest.raises(ValueError, match=named) as raised:
        plan(suite=changed(SUITE, path, value))
    assert str(value) not in str(raised.value)


def test_arms_cannot_differ_in_anything_but_ai_dlc(monkeypatch):
    overridden = changed(
        SUITE, ["scenarios", 0, "arms"], ["treatment", {"name": "baseline", "goal": "Easier."}]
    )
    with pytest.raises(ValueError, match="arms"):
        plan(suite=overridden)
    with pytest.raises(ValueError, match="baseline"):
        plan(suite=changed(SUITE, ["scenarios", 0, "arms"], ["treatment"]))


def test_duplicate_identifiers_and_mandatory_observations_are_checked():
    duplicate = changed(SUITE, ["scenarios"], [SCENARIO, SCENARIO])
    with pytest.raises(ValueError, match="csv-feature"):
        plan(suite=duplicate)
    repeated = changed(SUITE, ["scenarios", 0, "assertions"], [SCENARIO["assertions"][0]] * 2)
    with pytest.raises(ValueError, match="hidden-tests"):
        plan(suite=repeated)


def test_planning_never_starts_a_process_opens_a_socket_or_reads_a_credential(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("planning must stay offline")

    class Environment(dict):
        def __getitem__(self, key):
            forbidden()

        get = __getitem__

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr("os.environ", Environment())
    assert len(plan()["attempts"]) == 2


def test_cli_plans_from_files_and_refuses_with_exit_status(tmp_path):
    from typer.testing import CliRunner

    from ai_dlc.cli import app

    suite, profile = tmp_path / "suite.json", tmp_path / "profile.json"
    suite.write_text(json.dumps(SUITE))
    profile.write_text(json.dumps(PROFILE))
    runner = CliRunner()
    planned = runner.invoke(app, ["eval", "plan", str(suite), "--profile", str(profile)])
    assert planned.exit_code == 0, planned.output
    assert len(json.loads(planned.stdout)["attempts"]) == 2
    profile.write_text(json.dumps(changed(PROFILE, ["model"], None)))
    refused = runner.invoke(app, ["eval", "plan", str(suite), "--profile", str(profile)])
    assert refused.exit_code != 0


def test_published_schemas_match_the_models():
    from pathlib import Path

    from ai_dlc.verification.evaluation import contracts

    published = Path(__file__).resolve().parents[1] / "contracts/evaluation"
    for name, model in contracts.SCHEMAS.items():
        schema = json.loads((published / f"{name}.schema.json").read_text())
        assert schema == model.model_json_schema()
