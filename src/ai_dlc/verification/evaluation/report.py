"""Rebuild results from a retained run directory alone: no process, no network, no grader.

The per-attempt manifest detects accidental or partial changes to evidence. It is an
integrity check, not a signature: someone who rewrites the manifest too is not detected.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from ai_dlc.verification.evaluation.evaluate import evaluate

MANIFEST = "manifest.json"


def manifest_of(run_dir: Path) -> dict[str, str]:
    return {
        p.relative_to(run_dir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(run_dir.rglob("*"))
        if p.is_file() and p.name != MANIFEST
    }


def _integrity(run_dir: Path) -> list[str]:
    try:
        recorded = json.loads((run_dir / MANIFEST).read_text())
    except (OSError, ValueError):
        return ["evidence manifest missing or unreadable"]
    current = manifest_of(run_dir)
    changed = sorted(
        path for path in recorded.keys() | current.keys() if recorded.get(path) != current.get(path)
    )
    return ["evidence changed since the run: " + ", ".join(changed)] if changed else []


def _events(run_dir: Path) -> tuple[list[dict], list[str]]:
    try:
        lines = (run_dir / "events.jsonl").read_text().splitlines()
        events = [json.loads(line) for line in lines if line.strip()]
        if not all(isinstance(e, dict) and e.get("schema") == 1 and e.get("kind") for e in events):
            raise ValueError
    except (OSError, ValueError):
        return [], ["event trace missing or malformed"]
    if not events or events[-1]["kind"] != "cleanup":
        return events, ["event trace truncated before cleanup"]
    return events, []


def _retained_grader(run_dir: Path) -> dict:
    return json.loads((run_dir / "grading/hidden-tests.json").read_text())


def _metrics(events: list[dict]) -> dict:
    wall = None
    if len(events) > 1:
        first, last = (datetime.fromisoformat(events[i]["at"]) for i in (0, -1))
        wall = round((last - first).total_seconds(), 3)
    # Usage is reported only when a driver meters it; the deterministic driver does not.
    metrics = {"turns": sum(e["kind"] == "step" for e in events), "wall_seconds": wall}
    refused = [e.get("refused", []) for e in events if e["kind"] == "egress"]
    if refused:  # present only for attempts that had a network at all
        metrics["egress_refused"] = sorted({host for hosts in refused for host in hosts})
    return {**metrics, "usage": None}


def _arm(out: Path, planned: dict, scenario: dict) -> dict:
    run_dir = out / planned["scenario"] / planned["arm"] / str(planned["attempt"])
    try:
        attempt = json.loads((run_dir / "attempt.json").read_text())
    except (OSError, ValueError):
        attempt = {
            "scenario": planned["scenario"],
            "arm": planned["arm"],
            "attempt": planned["attempt"],
            "outcome": "incomplete",
            "stage": "collect",
            "detail": "attempt record missing or unreadable",
        }
        problems = [attempt["detail"]]
        events: list[dict] = []
    else:
        events, problems = _events(run_dir)
        problems = _integrity(run_dir) + problems
    graded = evaluate(
        attempt,
        assertions=scenario["assertions"],
        planned=planned["assertions"],
        run_dir=run_dir,
        grade=_retained_grader,
    )
    if problems:
        # Evidence that cannot be trusted supports no result, in either direction.
        for item in graded["assertions"]:
            if item["result"] != "pending":
                item.update(result="unavailable", observed="evidence not trustworthy", evidence=[])
        graded["outcome"] = "incomplete"
    detail = "; ".join(problems) or attempt.get("detail")
    return {
        **graded,
        "stage": attempt.get("stage"),
        "limit": attempt.get("limit"),
        "detail": detail,
        "cleanup_clean": attempt.get("cleanup", {}).get("clean", False),
        "metrics": _metrics(events),
    }


def _spread(values: dict[str, float | None]) -> dict:
    both = values["treatment"] is not None and values["baseline"] is not None
    difference = round(values["treatment"] - values["baseline"], 3) if both else None  # type: ignore[operator]
    return {**values, "difference": difference}


def _comparison(plan: dict, suite: dict, arms: list[dict]) -> dict:
    scenarios = {}
    for scenario in suite["scenarios"]:
        mandatory = {
            a["id"]
            for a in scenario["assertions"]
            if a["dimension"] == "correctness" and a.get("mandatory", True)
        }
        rows = {
            name: [a for a in arms if a["scenario"] == scenario["id"] and a["arm"] == name]
            for name in ("treatment", "baseline")
        }

        def mean(name: str, key: str) -> float | None:
            values = [a["metrics"][key] for a in rows[name] if a["metrics"][key] is not None]  # noqa: B023
            return round(sum(values) / len(values), 3) if values else None

        def passed(name: str) -> int:
            return sum(
                all(x["result"] == "pass" for x in a["assertions"] if x["id"] in mandatory)  # noqa: B023
                for a in rows[name]  # noqa: B023
            )

        scenarios[scenario["id"]] = {
            "correctness_passed": _spread({n: passed(n) for n in rows}),
            "turns": _spread({n: mean(n, "turns") for n in rows}),
            "wall_seconds": _spread({n: mean(n, "wall_seconds") for n in rows}),
            "usage": _spread({n: mean(n, "usage") for n in rows}),
        }
    return {**plan["comparison"], "scenarios": scenarios}


def build_report(out: Path) -> dict:
    plan = json.loads((out / "plan.json").read_text())
    suite = json.loads((out / "inputs/suite.json").read_text())
    scenarios = {s["id"]: s for s in suite["scenarios"]}
    arms = [_arm(out, planned, scenarios[planned["scenario"]]) for planned in plan["attempts"]]
    return {
        "schema": 1,
        "suite": plan["suite"],
        "profile": plan["profile"],
        # Scripted drivers and fixture providers never qualify live behavior.
        "evidence_kind": "fixture",
        "arms": arms,
        "comparison": _comparison(plan, suite, arms),
    }


def _junit(report: dict) -> ET.Element:
    root = ET.Element("testsuites", name=f"{report['suite']}:{report['profile']}")
    for arm in report["arms"]:
        suite = ET.SubElement(
            root,
            "testsuite",
            name=f"{arm['scenario']}.{arm['arm']}.{arm['attempt']}",
            tests=str(len(arm["assertions"])),
        )
        ET.SubElement(suite, "properties").append(
            ET.Element("property", name="outcome", value=arm["outcome"])
        )
        for item in arm["assertions"]:
            case = ET.SubElement(suite, "testcase", name=item["id"], classname=item["dimension"])
            tag = {"fail": "failure", "unavailable": "error", "pending": "skipped"}.get(
                item["result"]
            )
            if tag:
                ET.SubElement(
                    case, tag, message=item["observed"] or item["result"]
                ).text = f"expected: {item['expected']}\nevidence: {', '.join(item['evidence']) or 'none'}"
    return root


def _timeline(out: Path, report: dict) -> str:
    lines = [
        f"# Evaluation {report['suite']} ({report['profile']}, {report['evidence_kind']} evidence)"
    ]
    lines += ["", f"Comparison claim: {report['comparison']['claim']}"]
    for arm in report["arms"]:
        run_dir = out / arm["scenario"] / arm["arm"] / str(arm["attempt"])
        lines += [
            "",
            f"### {arm['scenario']} / {arm['arm']} / attempt {arm['attempt']} — {arm['outcome']}",
        ]
        for key in ("stage", "limit", "detail"):
            if arm.get(key):
                lines.append(f"- {key}: {arm[key]}")
        if not arm["cleanup_clean"]:
            lines.append("- cleanup: NOT clean; see cleanup-ledger.jsonl")
        if arm["metrics"].get("egress_refused"):
            lines.append("- refused destinations: " + ", ".join(arm["metrics"]["egress_refused"]))
        events, _ = _events(run_dir)
        # Controller events only; step output is never quoted as if it were evidence.
        lines += [f"- {e['at']} {e['kind']}" for e in events]
        for item in arm["assertions"]:
            evidence = ", ".join(item["evidence"]) or "none"
            lines.append(
                f"- [{item['result']}] {item['dimension']}/{item['id']}: "
                f"{item['observed'] or '-'} (evidence: {evidence})"
            )
    return "\n".join(lines) + "\n"


def write_report(out: Path) -> dict:
    report = build_report(out)
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    ET.ElementTree(_junit(report)).write(
        out / "report.junit.xml", encoding="unicode", xml_declaration=True
    )
    (out / "report.timeline.md").write_text(_timeline(out, report))
    return report
