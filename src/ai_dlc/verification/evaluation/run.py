"""Run a planned suite: verify inputs, run every attempt, grade it, retain what reruns need."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
import threading
import tomllib
from pathlib import Path

from ai_dlc.verification.evaluation import attempt as lifecycle
from ai_dlc.verification.evaluation.drivers import load_driver
from ai_dlc.verification.evaluation.planning import plan
from ai_dlc.verification.evaluation.report import MANIFEST, manifest_of, write_report


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
    driver = load_driver(profile, profile_path)
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
    for name, value in [("suite", suite), ("profile", profile), *driver.retained().items()]:
        (out / f"inputs/{name}.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    for item in planned["attempts"]:
        scenario = scenarios[item["scenario"]]
        run_dir = out / item["scenario"] / item["arm"] / str(item["attempt"])
        result = lifecycle.run_attempt(
            item,
            run_dir=run_dir,
            fixture=(suite_path.parent / scenario["fixture"]["path"]).resolve(),
            install=driver.install(item),
            steps=driver.steps(item),
            egress=planned["egress"],
            cancel=cancel,
        )
        hidden = scenario["fixture"].get("hidden")
        if hidden and (run_dir / "tree/project").is_dir():
            _retain_grading(
                run_dir, _grader(profile["image"], (suite_path.parent / hidden).resolve())
            )
        _redact(run_dir, result, profile["credentials"])
        (run_dir / "attempt.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        _redact(run_dir, {}, profile["credentials"])  # the record just written is evidence too
        (run_dir / MANIFEST).write_text(json.dumps(manifest_of(run_dir), indent=2, sort_keys=True))
    return write_report(out)


def _retain_grading(run_dir: Path, grade) -> None:
    """Grade once, at run time; reports only ever read what is retained here."""
    try:
        graded = grade(run_dir)
    except (lifecycle.Stopped, OSError, ValueError):
        return  # no file: the rebuilt result is unavailable, never a pass
    (run_dir / "grading").mkdir(exist_ok=True)
    (run_dir / "grading/hidden-tests.json").write_text(
        json.dumps(graded, indent=2, sort_keys=True) + "\n"
    )


def _redact(run_dir: Path, result: dict, names: list[str]) -> None:
    """Remove profile-named credential values from retained evidence and fail the attempt.

    Values shorter than eight characters are ignored to avoid shredding ordinary text.
    """
    found = []
    for name in names:
        value = os.environ.get(name, "").encode()
        if len(value) < 8:
            continue
        for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
            data = path.read_bytes()
            if value in data:
                path.write_bytes(data.replace(value, f"[REDACTED:{name}]".encode()))
                found.append(f"{name} in {path.relative_to(run_dir).as_posix()}")
    if found:
        result.update(
            outcome="incomplete",
            stage="redaction",
            detail="credential value found in evidence and redacted: " + ", ".join(found),
        )
