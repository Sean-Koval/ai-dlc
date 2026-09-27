"""Read-only local integration for bounded native harness verification."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ai_dlc.environment import report as report_service
from ai_dlc.environment import report_schema
from ai_dlc.environment.report_io import read_report, read_report_bytes
from ai_dlc.harness.native_adapters import adapter_contract
from ai_dlc.harness.native_evidence import (
    adjudicate_evidence,
    evidence_exit_code,
    parse_evidence,
    procedure_contract,
)

SAFE_ERROR = "Native verification input could not be read safely."
REQUIRED_CONFIRMATIONS = (
    "client.edition",
    "client.version",
    "platform.os",
    "platform.architecture",
    "observed_at",
    "observer",
    "steps.instruction.artifact_id",
    "steps.instruction.observed_marker",
    "steps.instruction.result",
    "steps.instruction.reason_code",
    "steps.skill.artifact_id",
    "steps.skill.observed_marker",
    "steps.skill.result",
    "steps.skill.reason_code",
    "steps.mcp.artifact_id",
    "steps.mcp.tool_id",
    "steps.mcp.observed_marker",
    "steps.mcp.result",
    "steps.mcp.reason_code",
    "auth.state",
    "auth.observed_at",
    "auth.scope_checked",
    "auth.reason_code",
    "cost_authorization",
    "limitations",
)
_ENGINE_FIELDS = (
    "package_version",
    "installation_kind",
    "source_revision",
    "source_dirty",
    "artifact_sha256",
)


def _selection(evidence: dict | None) -> dict[str, str | None]:
    selected: dict[str, str | None] = {
        "instruction_id": None,
        "skill_id": None,
        "server_id": None,
        "tool_id": None,
    }
    if evidence is None:
        return selected
    for step in evidence["steps"]:
        if step["id"] == "instruction":
            selected["instruction_id"] = step["artifact_id"]
        elif step["id"] == "skill":
            selected["skill_id"] = step["artifact_id"]
        else:
            selected["server_id"] = step["artifact_id"]
            selected["tool_id"] = step["tool_id"]
    return selected


def _evidence_template(report: dict, procedure: dict) -> dict:
    client = next(item for item in report["clients"] if item["id"] == procedure["client_id"])
    contract = procedure["contract"]
    limitations = list(procedure["limitations"])
    configuration_complete, observation_complete = report_schema.completeness(report)
    if not configuration_complete or not observation_complete:
        limitations.append("environment-incomplete")
    return {
        "schema_version": 1,
        "configuration_identity": report["configuration_identity"],
        "observation_identity": report["observation_identity"],
        "engine": {key: report["engine"][key] for key in _ENGINE_FIELDS},
        "client": {
            "id": procedure["client_id"],
            "edition": client["edition"],
            "version": client["version"]["observed"],
        },
        "platform": {
            "os": report["platform"]["os"],
            "architecture": report["platform"]["architecture"],
        },
        "observed_at": None,
        "observer": None,
        "fixture_id": contract["fixture_id"],
        "fixture_sha256": contract["fixture_sha256"],
        "adapter_contract_id": contract["adapter_contract_id"],
        "adapter_contract_sha256": contract["adapter_contract_sha256"],
        "steps": [dict(step) for step in procedure["steps"]],
        "auth": {
            "state": "not-assessed",
            "observed_at": None,
            "scope_checked": False,
            "reason_code": "not-assessed",
        },
        "cost_authorization": "pending",
        "limitations": sorted(set(limitations)),
    }


def _known(value: object) -> bool:
    return value is not None and value != "unknown"


def _local_guidance_scope(client_id: str, evidence: dict | None) -> dict[str, str]:
    scope: dict[str, str] = {}
    if evidence is not None:
        for step in evidence["steps"]:
            if step["artifact_id"] is not None:
                scope[step["id"]] = step["artifact_id"]
    if "instruction" not in scope:
        scope["instruction"] = "claude" if client_id == "claude-code" else "agents"
    return scope


def _reconcile_local(
    imported: dict,
    current: dict,
    client_id: str,
    evidence: dict | None,
    result: dict,
) -> dict:
    current_client = next((item for item in current["clients"] if item["id"] == client_id), None)
    current_configuration_complete, current_observation_complete = report_schema.completeness(
        current
    )
    result["current_local"] = {
        "configuration_identity": current["configuration_identity"],
        "observation_identity": current["observation_identity"],
        "configuration_complete": current_configuration_complete,
        "observation_complete": current_observation_complete,
        "configured": current_client["configured"] if current_client else "no",
        "rendered": current_client["rendered"] if current_client else "no",
        "recognized": "not-assessed",
        "authenticated": "not-assessed",
        "client_edition": current_client["edition"] if current_client else None,
        "client_version": current_client["version"]["observed"] if current_client else None,
    }
    stale_fields = set(result["stale_fields"])
    limitations = set(result["limitations"])
    if current["configuration_identity"] != imported["configuration_identity"]:
        stale_fields.add("local.configuration_identity")
    for key in _ENGINE_FIELDS:
        local_value = current["engine"][key]
        imported_value = imported["engine"][key]
        if _known(local_value) and _known(imported_value) and local_value != imported_value:
            stale_fields.add(f"local.engine.{key}")
    for key in ("os", "architecture"):
        local_value = current["platform"][key]
        imported_value = imported["platform"][key]
        if _known(local_value) and _known(imported_value) and local_value != imported_value:
            stale_fields.add(f"local.platform.{key}")

    imported_guidance = {item["id"]: item for item in imported["project"]["guidance"]}
    current_guidance = {item["id"]: item for item in current["project"]["guidance"]}
    for step, identifier in _local_guidance_scope(client_id, evidence).items():
        local = current_guidance.get(identifier)
        local_state = "missing" if local is None else local["state"]
        previous = imported_guidance.get(identifier)
        previous_state = "missing" if previous is None else previous["state"]
        if local_state in ("missing", "mismatch"):
            limitations.add("render-missing" if local_state == "missing" else "render-stale")
            if local_state != previous_state:
                stale_fields.add(f"local.guidance.{step}")

    if stale_fields:
        result["state"] = "stale"
        result["recognized"] = "stale"
        limitations.add("evidence-stale")
    result["stale_fields"] = sorted(stale_fields)
    result["limitations"] = sorted(limitations)
    return result


def verify_native(
    root: Path,
    client_id: str,
    environment_path: Path,
    evidence_path: Path | None = None,
    *,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict:
    """Generate a manual procedure and compare bounded evidence with safe local facts."""
    try:
        adapter_contract(client_id)
        imported = read_report(environment_path)
        evidence = (
            parse_evidence(read_report_bytes(evidence_path)) if evidence_path is not None else None
        )
        procedure = procedure_contract(imported, client_id, **_selection(evidence))
        current = report_service.collect_report(
            Path(root), home=home, environ=environ, probe_versions=False
        )
        current = report_schema.parse_report(report_schema.report_bytes(current))
        result = adjudicate_evidence(imported, client_id, evidence)
        result = _reconcile_local(imported, current, client_id, evidence, result)
        return {
            "procedure": procedure,
            "evidence_template": _evidence_template(imported, procedure),
            "required_confirmations": list(REQUIRED_CONFIRMATIONS),
            "result": result,
            "exit_code": evidence_exit_code(result),
        }
    except (OSError, RuntimeError, TypeError, ValueError):
        raise ValueError(SAFE_ERROR) from None
