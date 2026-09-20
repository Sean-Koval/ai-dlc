"""A driver decides what an attempt runs; the runner never special-cases a driver kind."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = "python@sha256:" + "a" * 64
CANDIDATE = "sha256:" + "d" * 64
PROFILE = ROOT / "evaluations/profiles/local-deterministic.json"
ITEM = {"scenario": "csv-duplicate-rows", "arm": "treatment", "attempt": 1}


def drivers():
    from ai_dlc.verification.evaluation import drivers as module

    return module


def profile(tmp_path, **driver):
    data = json.loads(PROFILE.read_text())
    data["image"], data["engine"]["image"] = BASE, CANDIDATE
    data["driver"].update(driver)
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(data))
    return data, path


def test_deterministic_driver_returns_the_scripted_steps_for_each_arm(tmp_path):
    script = str(PROFILE.parent / "local-deterministic.script.json")
    data, path = profile(tmp_path, script=script)
    driver = drivers().load_driver(data, path)
    assert driver.install(ITEM) == []
    treatment = driver.steps(ITEM)
    reference = (ROOT / "evaluations/hidden/csv-validator/reference/validate.py").read_text()
    assert treatment[0][:2] == ["python", "-c"]
    assert treatment[0][-2:] == ["csvcheck/validate.py", reference]
    assert driver.steps(dict(ITEM, arm="baseline")) == [["python", "-c", "print('ALL TESTS PASS')"]]
    assert driver.retained() == {"script": json.loads(Path(script).read_text())}


def test_a_driver_kind_without_an_implementation_is_refused_before_anything_starts(
    tmp_path, monkeypatch
):
    from ai_dlc.verification.evaluation import attempt, run

    def forbidden(*args, **kwargs):
        raise AssertionError("nothing may start")

    monkeypatch.setattr(attempt, "_docker", forbidden)
    _, path = profile(tmp_path, kind="codex", script=None)
    with pytest.raises(ValueError, match=r"driver\.kind.*codex"):
        run.run_suite(ROOT / "evaluations/suites/smoke.json", path, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_the_runner_runs_whatever_the_driver_returns(tmp_path, monkeypatch):
    from ai_dlc.verification.evaluation import run

    class Fake:
        def retained(self):
            return {"goal": {"text": "fix it"}}

        def install(self, item):
            return [["install", item["arm"]]]

        def steps(self, item):
            return [["go", item["arm"]]]

    seen = []

    def run_attempt(item, *, run_dir, install, steps, **_):
        seen.append((item["arm"], install, steps))
        run_dir.mkdir(parents=True)
        return {"scenario": item["scenario"], "arm": item["arm"], "attempt": 1,
                "outcome": "infrastructure", "stage": "provision"}  # fmt: skip

    monkeypatch.setattr(run, "load_driver", lambda profile, path: Fake())
    monkeypatch.setattr(
        run, "_layers", lambda image: ["l1"] + (["l2"] if image == CANDIDATE else [])
    )
    monkeypatch.setattr(run.lifecycle, "run_attempt", run_attempt)
    _, path = profile(tmp_path)
    run.run_suite(ROOT / "evaluations/suites/smoke.json", path, tmp_path / "out")
    assert seen == [
        ("treatment", [["install", "treatment"]], [["go", "treatment"]]),
        ("baseline", [["install", "baseline"]], [["go", "baseline"]]),
    ]
    assert json.loads((tmp_path / "out/inputs/goal.json").read_text()) == {"text": "fix it"}
