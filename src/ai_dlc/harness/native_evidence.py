"""Pure, closed operator evidence parsing and conservative native adjudication.

These unsigned attestations describe historical observations. They never launch
clients, establish current authentication, or repair missing EER provenance.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any, Literal, NoReturn

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_dlc.environment import report_schema
from ai_dlc.environment.report_schema import (
    OS,
    Architecture,
    Digest,
    Identifier,
    Revision,
    Timestamp,
    Version,
)
from ai_dlc.harness.native_adapters import MARKERS, adapter_contract

MAX_BYTES = 1024 * 1024
MAX_DEPTH = 12
SAFE_ERROR = "Invalid native evidence."
Reason = Literal[
    "observed",
    "not-assessed",
    "native-observation-pending",
    "smoke-failed",
    "evidence-stale",
    "client-schema-unverified",
    "environment-incomplete",
    "no-selected-instruction",
    "no-selected-skill",
    "no-selected-mcp",
    "safe-operation-unverified",
    "skill-contract-unverified",
    "enumerated-only",
    "cost-authorization-pending",
    "authentication-failed",
    "authenticated-call",
    "no-auth-required",
    "render-missing",
    "render-stale",
    "context-unknown",
]
Marker = Literal["NHV-INSTRUCTION-1", "NHV-SKILL-1", "NHV-MCP-1"]


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _Engine(_Record):
    package_version: Version | None
    installation_kind: Literal["release", "source", "unknown"]
    source_revision: Revision | None
    source_dirty: bool | None
    artifact_sha256: Digest | None


class _Client(_Record):
    id: Literal["codex", "claude-code", "antigravity"]
    edition: Identifier
    version: Version


class _Platform(_Record):
    os: OS
    architecture: Architecture


class _Step(_Record):
    id: Literal["instruction", "skill", "mcp"]
    artifact_id: Identifier | None
    tool_id: Identifier | None
    expected_marker: Marker
    observed_marker: Marker | None
    result: Literal["passed", "failed", "pending", "not-applicable"]
    reason_code: Reason


class _Auth(_Record):
    state: Literal["verified", "failed", "not-assessed", "not-applicable"]
    observed_at: Timestamp | None
    scope_checked: bool
    reason_code: Literal[
        "authenticated-call", "authentication-failed", "not-assessed", "no-auth-required"
    ]


class _Evidence(_Record):
    schema_version: Literal[1]
    configuration_identity: Digest
    observation_identity: Digest
    engine: _Engine
    client: _Client
    platform: _Platform
    observed_at: Timestamp
    observer: Literal["operator", "maintainer", "reviewer"]
    fixture_id: Identifier
    fixture_sha256: Digest
    adapter_contract_id: Identifier
    adapter_contract_sha256: Digest
    steps: Annotated[list[_Step], Field(min_length=3, max_length=3)]
    auth: _Auth
    cost_authorization: Literal["not-required", "authorized", "pending"] = "pending"
    limitations: Annotated[list[Reason], Field(max_length=32)]


def _fail() -> NoReturn:
    raise ValueError(SAFE_ERROR)


def _bounded(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        _fail()
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                _fail()
            _bounded(child, depth + 1)
    elif type(value) is list:
        for child in value:
            _bounded(child, depth + 1)
    elif value is not None and type(value) not in (str, bool, int):
        _fail()


def _object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def parse_evidence(raw: bytes) -> dict:
    """Parse <=1 MiB UTF-8 JSON; all refusals use a fixed path-free error."""
    try:
        if type(raw) is not bytes or len(raw) > MAX_BYTES:
            _fail()
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_object, parse_constant=lambda _: _fail()
        )
        _bounded(value)
        if type(value) is not dict or type(value.get("schema_version")) is not int:
            _fail()
        result = _Evidence.model_validate(value).model_dump()
        observed_at = datetime.fromisoformat(result["observed_at"])
        if {s["id"] for s in result["steps"]} != set(MARKERS):
            _fail()
        for step in result["steps"]:
            if step["id"] != "mcp" and step["tool_id"] is not None:
                _fail()
        auth = result["auth"]
        if (
            auth["observed_at"] is not None
            and datetime.fromisoformat(auth["observed_at"]) > observed_at
        ):
            _fail()
        if auth["state"] != "not-assessed" and auth["observed_at"] is None:
            _fail()
        if auth["state"] == "verified" and not auth["scope_checked"]:
            _fail()
        if (
            auth["reason_code"]
            != {
                "verified": "authenticated-call",
                "failed": "authentication-failed",
                "not-assessed": "not-assessed",
                "not-applicable": "no-auth-required",
            }[auth["state"]]
        ):
            _fail()
        result["steps"].sort(key=lambda step: tuple(MARKERS).index(step["id"]))
        result["limitations"] = sorted(set(result["limitations"]))
        return result
    except (ValidationError, ValueError, TypeError, RecursionError, OverflowError):
        raise ValueError(SAFE_ERROR) from None


def _context(report: dict, client_id: str) -> tuple[dict, dict, dict]:
    try:
        validated = report_schema.parse_report(report_schema.report_bytes(report))
        contract = adapter_contract(client_id)
        client = next(c for c in validated["clients"] if c["id"] == client_id)
        return validated, client, contract
    except (ValueError, TypeError, StopIteration):
        raise ValueError(SAFE_ERROR) from None


def procedure_contract(
    report: dict,
    client_id: str,
    *,
    instruction_id: str | None = None,
    skill_id: str | None = None,
    server_id: str | None = None,
    tool_id: str | None = None,
) -> dict:
    """Describe candidate scope without selecting artifacts or approving execution."""
    report, client, contract = _context(report, client_id)
    candidates = {
        step: [g["id"] for g in report["project"]["guidance"] if g["kind"] == kind and g["id"]]
        for step, kind in (
            ("instruction", "instruction"),
            ("skill", "skill"),
            ("mcp", "native-server"),
        )
    }
    selected = dict(zip(MARKERS, (instruction_id, skill_id, server_id), strict=True))
    steps = []
    for step, marker in MARKERS.items():
        artifact = selected[step]
        if artifact is not None and artifact not in candidates[step]:
            _fail()
        record = {
            "id": step,
            "artifact_id": artifact,
            "tool_id": tool_id if step == "mcp" else None,
            "expected_marker": marker,
            "observed_marker": None,
            "result": "pending",
            "reason_code": "native-observation-pending",
        }
        try:
            _Step.model_validate(record)
        except ValidationError:
            raise ValueError(SAFE_ERROR) from None
        steps.append(record)
    return {
        "client_id": client_id,
        "client": {
            "id": client_id,
            "edition": client["edition"],
            "version": client["version"]["observed"],
        },
        "configuration_identity": report["configuration_identity"],
        "observation_identity": report["observation_identity"],
        "contract": contract,
        "candidates": candidates,
        "steps": steps,
        "cost_authorization": "pending",
        "authenticated": "not-assessed",
        "limitations": [
            "client-schema-unverified",
            "skill-contract-unverified",
            "safe-operation-unverified",
            "cost-authorization-pending",
            *(f"no-selected-{step}" for step, artifact in selected.items() if artifact is None),
        ],
    }


def adjudicate_evidence(report: dict, client_id: str, evidence: dict | None) -> dict:
    """Retain independent historical outcomes, with EER completeness authoritative.

    The present adapter catalog has no qualified versions or reviewed operations,
    so even all passing observations remain limited. A future positive catalog
    must establish those contracts before enabling exact-context qualification.
    """
    report, client, contract = _context(report, client_id)
    config_complete, observation_complete = report_schema.completeness(report)
    procedure = procedure_contract(report, client_id)
    result = {
        "state": "pending",
        "provenance": "operator-attested" if evidence else "not-observed",
        "configuration_identity": report["configuration_identity"],
        "observation_identity": report["observation_identity"],
        "configuration_complete": config_complete,
        "observation_complete": observation_complete,
        "configured": client["configured"],
        "rendered": client["rendered"],
        "recognized": "pending",
        "authenticated": "not-assessed",
        "historical_auth": None,
        "steps": procedure["steps"],
        "cost_authorization": "pending",
        "limitations": list(procedure["limitations"]),
        "stale_fields": [],
    }
    if not config_complete or not observation_complete:
        result["limitations"].append("environment-incomplete")
    for guidance in report["project"]["guidance"]:
        if guidance["state"] in ("missing", "mismatch"):
            result["limitations"].append(
                "render-missing" if guidance["state"] == "missing" else "render-stale"
            )
    if evidence is None:
        return result
    try:
        evidence = parse_evidence(json.dumps(evidence, ensure_ascii=True).encode())
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise ValueError(SAFE_ERROR) from None
    stale = result["stale_fields"]
    for key in ("configuration_identity", "observation_identity"):
        if evidence[key] != report[key]:
            stale.append(key)
    for key in ("fixture_id", "fixture_sha256", "adapter_contract_id", "adapter_contract_sha256"):
        if evidence[key] != contract[key]:
            stale.append(key)
    for field, observed, expected in (
        ("client.id", evidence["client"]["id"], client_id),
        ("client.edition", evidence["client"]["edition"], client["edition"]),
        ("client.version", evidence["client"]["version"], client["version"]["observed"]),
        *(
            (f"platform.{k}", evidence["platform"][k], report["platform"][k])
            for k in ("os", "architecture")
        ),
        *((f"engine.{k}", v, report["engine"][k]) for k, v in evidence["engine"].items()),
    ):
        if expected is None or expected == "unknown":
            reason = report["engine"]["current_process"]["reasons"].get(
                field.removeprefix("engine.")
            )
            if not (field.startswith("engine.") and reason == "not-applicable"):
                result["limitations"].append("context-unknown")
        elif observed != expected:
            stale.append(field)
    result["evidence_context"] = {
        key: value
        for key, value in evidence.items()
        if key not in ("steps", "auth", "cost_authorization", "limitations")
    }
    result["steps"] = evidence["steps"]
    result["cost_authorization"] = evidence["cost_authorization"]
    result["observed_at"] = evidence["observed_at"]
    result["observer"] = evidence["observer"]
    result["limitations"] = [
        r
        for r in result["limitations"]
        if r != "cost-authorization-pending" and not r.startswith("no-selected-")
    ]
    result["limitations"].extend(evidence["limitations"])
    if evidence["cost_authorization"] == "pending":
        result["limitations"].append("cost-authorization-pending")
    for step in result["steps"]:
        step_id = step["id"]
        if step["artifact_id"] is None or (step_id == "mcp" and step["tool_id"] is None):
            reason = f"no-selected-{step_id}"
            result["limitations"].append(reason)
            if step["result"] == "passed":
                step.update(result="pending", reason_code=reason)
        elif step["artifact_id"] not in procedure["candidates"][step_id]:
            stale.append(f"steps.{step_id}.artifact_id")
        if (
            step["reason_code"] == "enumerated-only"
            or step["result"] == "passed"
            and step["reason_code"] != "observed"
        ):
            step.update(result="pending", observed_marker=None)
        elif step["result"] == "passed" and (
            step["expected_marker"] != MARKERS[step_id]
            or step["observed_marker"] != MARKERS[step_id]
        ):
            step.update(result="failed", reason_code="smoke-failed")
        if step["result"] == "not-applicable":
            result["limitations"].append(step["reason_code"])
    auth = evidence["auth"]
    mcp = next(step for step in result["steps"] if step["id"] == "mcp")
    if auth["state"] == "verified" and mcp["result"] != "passed":
        auth = {**auth, "state": "not-assessed", "reason_code": "not-assessed"}
    result["historical_auth"] = auth
    provider = next(
        (
            g["native_server"]["provider"]
            for g in report["project"]["guidance"]
            if g["id"] == mcp["artifact_id"] and g["native_server"]
        ),
        None,
    )
    later_failures = [
        a["verified_at"]
        for a in report["auth"]
        if a["verification"] == "failed"
        and a["verified_at"] is not None
        and (
            (a["kind"] == "client" and a["id"] == client_id)
            or (a["kind"] == "provider" and provider is not None and a["id"] == provider)
        )
        and datetime.fromisoformat(a["verified_at"])
        > datetime.fromisoformat(auth["observed_at"] or evidence["observed_at"])
    ]
    if later_failures:
        result["later_auth_failure_at"] = max(later_failures, key=datetime.fromisoformat)
        result["limitations"].append("authentication-failed")
    if stale:
        result["state"] = "stale"
        result["limitations"].append("evidence-stale")
    elif (
        any(step["result"] == "failed" for step in result["steps"])
        or auth["state"] == "failed"
        or later_failures
    ):
        result["state"] = "failed"
        if auth["state"] == "failed":
            result["limitations"].append("authentication-failed")
    elif any(step["result"] == "pending" for step in result["steps"]):
        result["state"] = "pending"
    else:
        result["state"] = "limited"
    result["recognized"] = result["state"]
    result["limitations"] = sorted(set(result["limitations"]))
    return result


def evidence_exit_code(result: dict) -> int:
    """Valid observations remain exit 1 until positive compatibility is available."""
    return 1
