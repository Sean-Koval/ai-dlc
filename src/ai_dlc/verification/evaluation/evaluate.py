"""Grade one attempt from independent observation; transcripts are never evidence."""

from __future__ import annotations

import fnmatch
from collections.abc import Callable
from pathlib import Path


def _hidden_tests(run_dir: Path, grade: Callable[[Path], dict]) -> tuple[str, str | None, list]:
    try:
        graded = grade(run_dir)
    except Exception as exc:  # noqa: BLE001 -- any grader failure is an unavailable observation
        return "unavailable", f"grader did not run: {exc}", []
    summary = (graded["stderr"].strip().splitlines() or ["no output"])[-1]
    result = "pass" if graded["exit_code"] == 0 else "fail"
    return result, f"exit {graded['exit_code']}: {summary}", ["grading/hidden-tests.json"]


def _artifact_present(run_dir: Path, pattern: str | None) -> tuple[str, str | None, list]:
    if not pattern:
        return "unavailable", "assertion declares no expected path", []
    project = run_dir / "tree/project"
    found = sorted(
        p.relative_to(run_dir).as_posix()
        for p in project.rglob("*")
        if p.is_file() and fnmatch.fnmatchcase(p.relative_to(project).as_posix(), pattern)
    )
    return ("pass", f"{len(found)} matching", found) if found else ("fail", "none matching", [])


def evaluate(
    attempt: dict,
    *,
    assertions: list[dict],
    planned: list[str],
    run_dir: Path,
    grade: Callable[[Path], dict],
) -> dict:
    """Return the arm report: separate dimensions, and an outcome that absence cannot improve."""
    graded = []
    for assertion in assertions:
        if assertion["id"] not in planned:
            continue
        kind, expect = assertion["kind"], assertion.get("expect")
        if assertion["dimension"] == "quality":
            outcome = ("pending", None, [])  # only a human records quality
            expected = "human review against the versioned rubric"
        elif kind == "hidden-tests":
            outcome = _hidden_tests(run_dir, grade)
            expected = "controller-side acceptance tests pass on the collected project"
        elif kind == "artifact-present":
            outcome = _artifact_present(run_dir, expect)
            expected = f"collected project contains {expect}"
        else:
            outcome = ("unavailable", f"no observer implements {kind}", [])
            expected = expect or kind
        graded.append(
            {
                "id": assertion["id"],
                "dimension": assertion["dimension"],
                "expected": expected,
                "observed": outcome[1],
                "evidence": outcome[2],
                "result": outcome[0],
            }
        )
    mandatory = {a["id"] for a in assertions if a.get("mandatory", True)}

    def any_of(dimension: str, result: str) -> bool:
        return any(
            g["dimension"] == dimension and g["result"] == result and g["id"] in mandatory
            for g in graded
        )

    outcome = attempt["outcome"]
    if outcome == "completed":
        if any_of("correctness", "fail"):
            outcome = "product"
        elif any_of("workflow", "fail"):
            outcome = "workflow-violation"
        elif any_of("correctness", "unavailable") or any_of("workflow", "unavailable"):
            outcome = "unavailable"
    return {
        "scenario": attempt["scenario"],
        "arm": attempt["arm"],
        "attempt": attempt["attempt"],
        "outcome": outcome,
        "assertions": graded,
    }
