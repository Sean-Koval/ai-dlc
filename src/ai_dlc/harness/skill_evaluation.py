"""Declared control/treatment evaluations; outputs await human review."""

import json
import os
import re
import tomllib
from datetime import UTC, datetime
from pathlib import Path

_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def _read_relative(root, name):
    path = root / name
    if Path(name).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Evaluation input must remain under its declaration directory")
    return path.read_text()


def load_plan(declaration: Path) -> dict:
    config = tomllib.loads(declaration.read_text())
    if config.get("schema") != 1:
        raise ValueError("Unsupported evaluation schema")
    if config.get("require_control") is not True or config.get("require_human_review") is not True:
        raise ValueError("Evaluation requires controls and human review")
    for key in ("repetitions", "max_output_tokens", "max_total_tokens"):
        if type(config.get(key)) is not int or config[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if not _SAFE_NAME.fullmatch(config.get("model", "")):
        raise ValueError("Invalid evaluation model")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", config.get("credential_env", "")):
        raise ValueError("credential_env must name an environment variable")
    if not isinstance(config.get("reasoning_effort"), str) or not config["reasoning_effort"]:
        raise ValueError("reasoning_effort is required")
    scenarios = json.loads(_read_relative(declaration.parent, config["scenarios"]))
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Evaluation requires scenarios")
    requests = []
    for index, scenario in enumerate(scenarios):
        if not _SAFE_NAME.fullmatch(scenario["skill"]):
            raise ValueError("Invalid skill name")
        if any(
            not isinstance(scenario.get(key), str) or not scenario[key]
            for key in ("prompt", "expected")
        ):
            raise ValueError("Scenario prompt and expected text are required")
        skill = _read_relative(declaration.parent, f"skills/{scenario['skill']}/SKILL.md")
        for variant in ("control", "skill"):
            messages = [{"role": "user", "content": scenario["prompt"]}]
            if variant == "skill":
                messages.insert(0, {"role": "system", "content": skill})
            for rep in range(1, config["repetitions"] + 1):
                requests.append(
                    {
                        "skill": scenario["skill"],
                        "scenario_index": index,
                        "variant": variant,
                        "repetition": rep,
                        "expected": scenario["expected"],
                        "path": f"{scenario['skill']}/{index}-{variant}-{rep}.json",
                        "request": {
                            "model": config["model"],
                            "input": messages,
                            "reasoning": {"effort": config["reasoning_effort"]},
                            "max_output_tokens": config["max_output_tokens"],
                            "store": False,
                        },
                    }
                )
    return {**config, "requests": requests}


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _usage(raw):
    response = json.loads(raw)
    usage = response.get("usage", {})
    if not isinstance(usage, dict) or any(
        type(usage.get(k)) is not int or usage[k] < 0
        for k in ("input_tokens", "output_tokens", "total_tokens")
    ):
        raise ValueError("usage-unavailable")
    if usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]:
        raise ValueError("usage-contract-violation")
    return usage


def _review_sheet(summary):
    lines = [
        "# Skill evaluation review",
        "",
        "Human review is pending. Mark each result against its expected behavior.",
        "",
        "| Transcript | Expected behavior | Human result | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for item in summary["transcripts"]:
        expected = item["expected"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| [{item['path']}]({item['path']}) | {expected} | | |")
    return "\n".join(lines) + "\n"


def _evaluate(plan, output, client):
    summary: dict = {
        "model": plan["model"],
        "reasoning_effort": plan["reasoning_effort"],
        "max_output_tokens": plan["max_output_tokens"],
        "max_total_tokens": plan["max_total_tokens"],
        "repetitions": plan["repetitions"],
        "started_at": datetime.now(UTC).isoformat(),
        "review": "pending-human-review",
        "total_tokens": 0,
        "reserved_tokens": 0,
        "scenarios": [
            {
                "skill": item["skill"],
                "scenario_index": item["scenario_index"],
                "expected": item["expected"],
            }
            for item in plan["requests"]
            if item["variant"] == "control" and item["repetition"] == 1
        ],
        "transcripts": [],
        "unsent": [],
        "stop_reason": None,
    }
    for index, item in enumerate(plan["requests"]):
        try:
            inputs = client.count_input_tokens(item["request"])
            if type(inputs) is not int or inputs < 0:
                raise ValueError("Invalid input token count")
        except Exception:  # noqa: BLE001 -- stop without exposing credentials in transport errors
            summary["stop_reason"] = "input-count-unavailable"
            summary["unsent"] = [r["path"] for r in plan["requests"][index:]]
            break
        reservation = inputs + plan["max_output_tokens"]
        if summary["total_tokens"] + reservation > plan["max_total_tokens"]:
            summary["stop_reason"] = "budget-exhausted"
            summary["unsent"] = [r["path"] for r in plan["requests"][index:]]
            break
        started = datetime.now(UTC).isoformat()
        summary["reserved_tokens"] = summary["total_tokens"] + reservation
        try:
            raw = client.complete(item["request"])
        except Exception:  # noqa: BLE001 -- never retry an uncertain charged request
            summary["stop_reason"] = "response-unavailable"
            summary["unsent"] = [r["path"] for r in plan["requests"][index + 1 :]]
            summary["uncertain_request"] = item
            break
        transcript = {
            **item,
            "started_at": started,
            "completed_at": datetime.now(UTC).isoformat(),
            "input_tokens_counted": inputs,
            "response_json": raw,
        }
        try:
            usage = _usage(raw)
            transcript["usage"] = usage
            summary["total_tokens"] += usage["total_tokens"]
            summary["reserved_tokens"] = summary["total_tokens"]
            if (
                usage["total_tokens"] > reservation
                or usage["output_tokens"] > plan["max_output_tokens"]
            ):
                summary["stop_reason"] = "usage-contract-violation"
        except (ValueError, TypeError, AttributeError) as exc:
            summary["stop_reason"] = (
                str(exc) if str(exc) == "usage-contract-violation" else "usage-unavailable"
            )
        _write(output / item["path"], transcript)
        summary["transcripts"].append({"path": item["path"], "expected": item["expected"]})
        if summary["stop_reason"]:
            summary["unsent"] = [r["path"] for r in plan["requests"][index + 1 :]]
            break
    summary["completed_at"] = datetime.now(UTC).isoformat()
    _write(output / "summary.json", summary)
    (output / "review-sheet.md").write_text(_review_sheet(summary))
    return summary


def run(declaration: Path, *, dry_run=False, output: Path | None = None, client_factory=None):
    plan = load_plan(declaration)
    if dry_run:
        return plan
    token = os.environ.get(plan["credential_env"])
    if not token:
        raise ValueError(f"Set {plan['credential_env']} before a live evaluation")
    output = (
        output
        or declaration.parent / "evaluations/runs" / f"{datetime.now(UTC).date()}-{plan['model']}"
    )
    if output.exists():
        raise FileExistsError(f"Evaluation output already exists: {output}")
    if client_factory is None:
        from ai_dlc.providers.evaluation_api import EvaluationClient

        client_factory = EvaluationClient
    client = client_factory(plan["api_url"], token)
    try:
        output.mkdir(parents=True, exist_ok=False)
        return _evaluate(plan, output, client)
    finally:
        close = getattr(client, "close", None)
        if close:
            close()
