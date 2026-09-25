"""Grading trusts only independent observation; a run is reproducible from what it retains."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = "python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de"
ASSERTIONS = [
    {"id": "hidden-tests", "dimension": "correctness", "kind": "hidden-tests"},
    {
        "id": "work-record",
        "dimension": "workflow",
        "kind": "artifact-present",
        "expect": ".ai-dlc/work/*.toml",
    },
    {"id": "ordering", "dimension": "workflow", "kind": "ordering", "mandatory": False},
    {"id": "handoff", "dimension": "quality", "kind": "human-review"},
]


def evaluate_module():
    from ai_dlc.verification.evaluation import evaluate

    return evaluate


def graded(
    tmp_path, *, exit_code=0, arm="treatment", outcome="completed", record=True, grader=None
):
    tree = tmp_path / "tree/project"
    (tree / ".ai-dlc/work").mkdir(parents=True, exist_ok=True)
    if record:
        (tree / ".ai-dlc/work/item.toml").write_text("id = 'item'\n")
    (tmp_path / "steps").mkdir(exist_ok=True)
    (tmp_path / "steps/01.json").write_text(
        json.dumps({"stdout": "ALL TESTS PASS", "exit_code": 0})
    )
    attempt = {"scenario": "csv", "arm": arm, "attempt": 1, "outcome": outcome, "stage": None}
    planned = [a["id"] for a in ASSERTIONS if arm == "treatment" or a["dimension"] != "workflow"]

    def default(run_dir):
        return {"exit_code": exit_code, "stdout": "", "stderr": "Ran 10 tests\n\nOK\n"}

    return evaluate_module().evaluate(
        attempt, assertions=ASSERTIONS, planned=planned, run_dir=tmp_path, grade=grader or default
    )


def results(report):
    return {a["id"]: a["result"] for a in report["assertions"]}


def test_a_transcript_claiming_success_cannot_override_failing_hidden_tests(tmp_path):
    report = graded(tmp_path, exit_code=1)
    assert results(report)["hidden-tests"] == "fail"
    assert report["outcome"] == "product"
    hidden = next(a for a in report["assertions"] if a["id"] == "hidden-tests")
    assert hidden["evidence"] == ["grading/hidden-tests.json"]
    assert "ALL TESTS PASS" not in json.dumps(hidden)


def test_every_assertion_records_expectation_observation_and_evidence(tmp_path):
    report = graded(tmp_path)
    assert report["outcome"] == "completed"
    for item in report["assertions"]:
        assert item["expected"]
        assert set(item) == {"id", "dimension", "expected", "observed", "evidence", "result"}
    assert results(report) == {
        "hidden-tests": "pass",
        "work-record": "pass",
        "ordering": "unavailable",  # no process observer exists for this driver
        "handoff": "pending",  # only a human records quality
    }
    record = next(a for a in report["assertions"] if a["id"] == "work-record")
    assert record["evidence"] == ["tree/project/.ai-dlc/work/item.toml"]


def test_an_unavailable_grader_is_never_a_pass(tmp_path):
    def broken(run_dir):
        raise RuntimeError("collector image missing")

    report = graded(tmp_path, grader=broken)
    assert results(report)["hidden-tests"] == "unavailable"
    assert report["outcome"] == "unavailable"


def test_a_mandatory_unavailable_observation_blocks_completion(tmp_path):
    mandatory = [dict(a, mandatory=True) if a["id"] == "ordering" else a for a in ASSERTIONS]
    (tmp_path / "tree/project").mkdir(parents=True)
    report = evaluate_module().evaluate(
        {
            "scenario": "csv",
            "arm": "treatment",
            "attempt": 1,
            "outcome": "completed",
            "stage": None,
        },
        assertions=mandatory,
        planned=[a["id"] for a in mandatory],
        run_dir=tmp_path,
        grade=lambda run_dir: {"exit_code": 0, "stdout": "", "stderr": "OK"},
    )
    assert report["outcome"] != "completed"


def test_skipping_the_workflow_is_a_violation_even_when_the_code_is_right(tmp_path):
    report = graded(tmp_path, record=False)
    assert results(report)["hidden-tests"] == "pass"
    assert results(report)["work-record"] == "fail"
    assert report["outcome"] == "workflow-violation"


def test_baseline_is_graded_on_correctness_only(tmp_path):
    report = graded(tmp_path, arm="baseline", record=False)
    assert set(results(report)) == {"hidden-tests", "handoff"}
    assert report["outcome"] == "completed"


def test_an_interrupted_attempt_stays_incomplete_whatever_the_tests_say(tmp_path):
    assert graded(tmp_path, outcome="incomplete")["outcome"] == "incomplete"


def test_fixture_digest_binds_content_not_timestamps(tmp_path):
    from ai_dlc.verification.evaluation.run import tree_digest

    (tmp_path / "a").mkdir()
    (tmp_path / "a/x.py").write_text("one")
    first = tree_digest(tmp_path / "a")
    (tmp_path / "a/x.py").touch()
    assert tree_digest(tmp_path / "a") == first
    (tmp_path / "a/x.py").write_text("two")
    assert tree_digest(tmp_path / "a") != first


def test_treatment_image_must_extend_the_baseline_image_layer_for_layer():
    from ai_dlc.verification.evaluation.run import derived_from

    assert derived_from(["a", "b", "c"], ["a", "b"])
    assert not derived_from(["a", "b"], ["a", "b"])  # identical: nothing was installed
    assert not derived_from(["a", "x", "c"], ["a", "b"])
    assert not derived_from(["a"], ["a", "b"])


def test_evaluation_data_is_never_packaged_where_an_attempt_could_read_it():
    import tomllib

    build = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["hatch"]["build"]
    included = json.dumps(build["targets"]["wheel"])
    assert "evaluations" not in included
    assert not (ROOT / "src/ai_dlc/assets/evaluations").exists()
    assert not list((ROOT / "evaluations/fixtures").rglob("test_acceptance.py"))


def test_shipped_suite_plans_and_its_fixture_digest_is_current():
    from ai_dlc.verification.evaluation.planning import plan
    from ai_dlc.verification.evaluation.run import tree_digest

    suite = json.loads((ROOT / "evaluations/suites/smoke.json").read_text())
    profile = json.loads((ROOT / "evaluations/profiles/local-deterministic.json").read_text())
    assert len(plan(suite, profile)["attempts"]) == 2
    fixture = suite["scenarios"][0]["fixture"]
    assert tree_digest(ROOT / "evaluations/suites" / fixture["path"]) == fixture["digest"]


def test_shipped_scenario_keeps_the_goal_neutral_and_grades_committed_work():
    suite = json.loads((ROOT / "evaluations/suites/real-client.json").read_text())
    scenario = suite["scenarios"][0]
    goal = scenario["goal"].lower()
    assert all(term not in goal for term in ("ai-dlc", "git commit", "python -m", "skill"))
    assert {
        item["id"]: {
            key: value for key, value in item.items() if key in ("kind", "path", "before", "after")
        }
        for item in scenario["assertions"]
        if item["dimension"] == "workflow"
    } == {
        "process-commit": {"kind": "commit-present"},
        "work-record-committed": {
            "kind": "path-committed",
            "path": ".ai-dlc/work/*.toml",
        },
        "implementation-committed": {
            "kind": "path-committed",
            "path": "csvcheck/validate.py",
        },
        "work-before-code": {
            "kind": "ordering",
            "before": ".ai-dlc/work/*.toml",
            "after": "csvcheck/validate.py",
        },
    }


# --- Real Docker. Skipped, never passed, when Docker or the pinned image is absent. ---


def docker_ready():
    if not shutil.which("docker"):
        return False
    done = subprocess.run(
        ["docker", "image", "inspect", BASE], capture_output=True, check=False, timeout=30
    )
    return done.returncode == 0


docker = pytest.mark.skipif(
    not docker_ready(), reason="Docker or the digest-pinned image is unavailable; never pulled"
)


@pytest.fixture
def candidate_image():
    """Stands in for a prebuilt candidate image: the baseline image plus one layer."""
    built = subprocess.run(
        ["docker", "build", "-q", "-"],
        input=f"FROM {BASE}\nRUN touch /candidate-marker\n",
        capture_output=True, text=True, check=True, timeout=300,
    )  # fmt: skip
    image = built.stdout.strip()
    yield image
    subprocess.run(["docker", "rmi", "-f", image], capture_output=True, check=False, timeout=60)


@docker
def test_real_run_grades_both_arms_independently_and_retains_its_inputs(tmp_path, candidate_image):
    from ai_dlc.verification.evaluation.run import run_suite

    profile = json.loads((ROOT / "evaluations/profiles/local-deterministic.json").read_text())
    profile["engine"]["image"] = candidate_image
    profile["driver"]["script"] = str(ROOT / "evaluations/profiles/local-deterministic.script.json")
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile))
    report = run_suite(ROOT / "evaluations/suites/smoke.json", path, tmp_path / "out")
    arms = {a["arm"]: a for a in report["arms"]}
    # The deterministic script writes the reference solution in one arm only. This
    # exercises the runner and the grader; it is not a finding about AI-DLC.
    assert arms["treatment"]["outcome"] == "completed", arms["treatment"]
    assert arms["baseline"]["outcome"] == "product", arms["baseline"]
    assert report["evidence_kind"] == "fixture"
    assert report["comparison"]["claim"].startswith("none")
    out = tmp_path / "out"
    assert json.loads((out / "plan.json").read_text())["attempts"][0]["image"] == candidate_image
    for retained in ["inputs/suite.json", "inputs/profile.json", "inputs/script.json"]:
        assert (out / retained).is_file()
    graded_file = out / "csv-duplicate-rows/baseline/1/grading/hidden-tests.json"
    assert "duplicate" in json.loads(graded_file.read_text())["stderr"]
    assert not list(out.rglob("test_acceptance.py"))  # hidden tests never enter evidence


@docker
def test_real_run_refuses_a_treatment_image_that_is_not_derived_from_the_baseline(tmp_path):
    from ai_dlc.verification.evaluation.run import run_suite

    profile = json.loads((ROOT / "evaluations/profiles/local-deterministic.json").read_text())
    profile["engine"]["image"] = BASE
    profile["driver"]["script"] = str(ROOT / "evaluations/profiles/local-deterministic.script.json")
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile))
    with pytest.raises(ValueError, match="derived"):
        run_suite(ROOT / "evaluations/suites/smoke.json", path, tmp_path / "out")
    assert not (tmp_path / "out/csv-duplicate-rows").exists()
