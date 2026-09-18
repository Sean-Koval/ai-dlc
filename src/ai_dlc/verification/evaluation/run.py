"""Run a planned suite: verify inputs, run every attempt, grade it, retain what reruns need."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import threading
import tomllib
from pathlib import Path

from ai_dlc.verification.evaluation import attempt as lifecycle
from ai_dlc.verification.evaluation.evaluate import evaluate
from ai_dlc.verification.evaluation.planning import plan

WRITER = "import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(sys.argv[2])"


def read_declaration(path: Path) -> dict:
    raw = path.read_text()
    return tomllib.loads(raw) if path.suffix == ".toml" else json.loads(raw)


def tree_digest(root: Path) -> str:
    """Content identity of a directory: relative paths and file bytes, never timestamps."""
    total = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        total.update(path.relative_to(root).as_posix().encode() + b"\0")
        total.update(hashlib.sha256(path.read_bytes()).digest())
    return total.hexdigest()


def derived_from(treatment: list[str], baseline: list[str]) -> bool:
    """The candidate image must be the baseline image plus layers, and nothing else."""
    return len(treatment) > len(baseline) and treatment[: len(baseline)] == baseline


def _layers(image: str) -> list[str]:
    done = lifecycle._docker(
        ["image", "inspect", "--format", "{{json .RootFS.Layers}}", image], timeout=30
    )
    if done.returncode:
        raise ValueError(f"Evaluation image is not present locally and is never pulled: {image}")
    return json.loads(done.stdout)


def _steps(declared: list, base: Path) -> list[list[str]]:
    """A step is an argv list, or {"write": path, "from": file} to place controller-held text."""
    steps = []
    for step in declared:
        if isinstance(step, dict):
            steps.append(["python", "-c", WRITER, step["write"], (base / step["from"]).read_text()])
        else:
            steps.append([str(part) for part in step])
    return steps


def _grader(image: str, hidden: Path):
    def grade(run_dir: Path) -> dict:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            tar.add(run_dir / "tree/project", arcname="project")
            for test in sorted(hidden.glob("test_*.py")):
                tar.add(test, arcname=f"hidden/{test.name}")
        command = (
            "cd project && PYTHONPATH=. python -m unittest discover -s ../hidden -p 'test_*.py'"
        )
        return lifecycle.run_isolated(image, buffer.getvalue(), command, timeout=300)

    return grade


def run_suite(
    suite_path: Path, profile_path: Path, out: Path, cancel: threading.Event | None = None
) -> dict:
    suite, profile = read_declaration(suite_path), read_declaration(profile_path)
    planned = plan(suite, profile)
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"Evaluation output directory is not empty: {out}")
    script_path = (profile_path.parent / profile["driver"]["script"]).resolve()
    script = json.loads(script_path.read_text())
    scenarios = {s["id"]: s for s in suite["scenarios"]}
    for scenario in scenarios.values():
        fixture = (suite_path.parent / scenario["fixture"]["path"]).resolve()
        if tree_digest(fixture) != scenario["fixture"]["digest"]:
            raise ValueError(f"Fixture content does not match its digest: {scenario['id']}")
    if not derived_from(_layers(profile["engine"]["image"]), _layers(profile["image"])):
        raise ValueError(
            "The treatment image must be derived from the baseline image by added layers only"
        )
    (out / "inputs").mkdir(parents=True)
    (out / "plan.json").write_text(json.dumps(planned, indent=2, sort_keys=True) + "\n")
    for name, value in [("suite", suite), ("profile", profile), ("script", script)]:
        (out / f"inputs/{name}.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    arms = []
    for item in planned["attempts"]:
        scenario = scenarios[item["scenario"]]
        run_dir = out / item["scenario"] / item["arm"] / str(item["attempt"])
        result = lifecycle.run_attempt(
            item,
            run_dir=run_dir,
            fixture=(suite_path.parent / scenario["fixture"]["path"]).resolve(),
            install=_steps(script.get("install", []), script_path.parent),
            steps=_steps(script.get(item["arm"], []), script_path.parent),
            cancel=cancel,
        )
        hidden = scenario["fixture"].get("hidden")
        grade = (
            _grader(profile["image"], (suite_path.parent / hidden).resolve()) if hidden else None
        )
        report = evaluate(
            result,
            assertions=scenario["assertions"],
            planned=item["assertions"],
            run_dir=run_dir,
            grade=grade or _no_grader,
        )
        (run_dir / "arm-report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
        arms.append(report)
    summary = {
        "schema": 1,
        "suite": planned["suite"],
        "profile": planned["profile"],
        # Deterministic scripts and fixture providers never qualify live behavior.
        "evidence_kind": "fixture",
        "arms": arms,
        "comparison": planned["comparison"],
    }
    (out / "report.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def _no_grader(run_dir: Path) -> dict:
    raise RuntimeError("scenario declares no hidden tests")
