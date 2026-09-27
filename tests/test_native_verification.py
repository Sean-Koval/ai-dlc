"""Offline native verification binds operator evidence to fresh safe local state."""

from __future__ import annotations

import copy
import json
import os
import socket
import subprocess
from pathlib import Path

import pytest
from test_native_evidence import report as native_evidence_report

from ai_dlc.environment import report as report_service
from ai_dlc.environment import report_schema
from ai_dlc.environment.report_io import write_report
from ai_dlc.harness.agents import render_agents
from ai_dlc.harness.native_evidence import parse_evidence

CLIENTS = ("codex", "claude-code", "antigravity")


def isolated_environment(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    root = Path(os.path.realpath(tmp_path)) / "project"
    root.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    environment = {
        "PATH": "",
        "HOME": str(home),
        "USERPROFILE": str(home),
        "XDG_CONFIG_HOME": str(tmp_path / "xdg-config"),
        "XDG_CACHE_HOME": str(tmp_path / "xdg-cache"),
        "XDG_STATE_HOME": str(tmp_path / "xdg-state"),
        "APPDATA": str(tmp_path / "appdata"),
        "LOCALAPPDATA": str(tmp_path / "local-appdata"),
    }
    for value in environment.values():
        if value:
            Path(value).mkdir(parents=True, exist_ok=True)
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["codex","claude-code","antigravity"]\n'
        '[agents]\nskills=["day-start"]\n'
        'servers=[{id="local", provider="none", command="native-fixture"}]\n'
    )
    render_agents(root, apply=True)
    return root, home, environment


def imported_report(root: Path, home: Path, environment: dict[str, str]) -> dict:
    value = report_service.collect_report(
        root, home=home, environ=environment, probe_versions=False
    )
    for client in value["clients"]:
        client["edition"] = "cli"
        client["version"].update(observed="1.2.3", state="observed", reason=None)
        client["reasons"]["edition"] = None
    return report_schema.finalize_report(value)


def write_context(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, str], dict]:
    root, home, environment = isolated_environment(tmp_path)
    report = imported_report(root, home, environment)
    path = tmp_path / "environment.json"
    write_report(path, report)
    return root, home, path, environment, report


def completed_evidence(output: dict) -> dict:
    value = copy.deepcopy(output["evidence_template"])
    value.update(observed_at="2026-09-26T16:00:00Z", observer="operator")
    candidates = output["procedure"]["candidates"]
    for step in value["steps"]:
        step.update(
            artifact_id=candidates[step["id"]][0],
            observed_marker=step["expected_marker"],
            result="passed",
            reason_code="observed",
        )
        if step["id"] == "mcp":
            step["tool_id"] = "inspect"
    value["auth"] = {
        "state": "not-applicable",
        "observed_at": value["observed_at"],
        "scope_checked": False,
        "reason_code": "no-auth-required",
    }
    value["cost_authorization"] = "authorized"
    value["limitations"] = []
    return value


def historical_removed_scope(tmp_path: Path) -> tuple[Path, Path, Path, Path, dict[str, str], dict]:
    root, home, report_path, environment, report = write_context(tmp_path)
    from ai_dlc.harness.native_verification import verify_native

    procedure = verify_native(
        root,
        "codex",
        report_path,
        home=home,
        environ=environment,
    )
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(completed_evidence(procedure)))
    changed = copy.deepcopy(report)
    prior_guidance = changed["project"]["guidance"]
    replacements = []
    for old_id, new_id in (
        ("skill.day-start", "skill.replacement"),
        ("native.local", "native.replacement"),
    ):
        replacement = copy.deepcopy(next(item for item in prior_guidance if item["id"] == old_id))
        replacement["id"] = new_id
        replacements.append(replacement)
    changed["project"]["guidance"] = replacements + [
        item for item in prior_guidance if item["id"] not in {"skill.day-start", "native.local"}
    ]
    changed = report_schema.finalize_report(changed)
    changed_path = tmp_path / "changed-environment.json"
    write_report(changed_path, changed)
    return root, home, changed_path, evidence_path, environment, changed


def with_instruction_observation(
    report: dict,
    *,
    state: str,
    observed_sha256: str | None,
) -> dict:
    value = copy.deepcopy(report)
    guidance = next(item for item in value["project"]["guidance"] if item["id"] == "agents")
    guidance.update(
        state=state,
        expected_sha256="a" * 64,
        observed_sha256=observed_sha256,
    )
    guidance["reasons"].update(
        expected_sha256=None,
        observed_sha256=None if observed_sha256 is not None else "safe-digest-unavailable",
    )
    client = next(item for item in value["clients"] if item["id"] == "codex")
    client["rendered"] = "yes" if state == "match" else "no" if state == "mismatch" else "unknown"
    client["reasons"]["rendered"] = None if state != "unknown" else "not-assessed"
    return report_schema.finalize_report(value)


def verify_selected_instruction_transition(
    tmp_path: Path,
    monkeypatch,
    imported: dict,
    current: dict,
) -> dict:
    from ai_dlc.harness.native_verification import verify_native

    root = tmp_path / "project"
    home = tmp_path / "home"
    root.mkdir()
    home.mkdir()
    environment = {
        "PATH": "",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(tmp_path / "xdg-config"),
        "XDG_CACHE_HOME": str(tmp_path / "xdg-cache"),
        "XDG_STATE_HOME": str(tmp_path / "xdg-state"),
    }
    report_path = tmp_path / "environment.json"
    write_report(report_path, imported)
    monkeypatch.setattr(report_service, "collect_report", lambda *args, **kwargs: imported)
    procedure = verify_native(
        root,
        "codex",
        report_path,
        home=home,
        environ=environment,
    )
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(completed_evidence(procedure)))
    monkeypatch.setattr(report_service, "collect_report", lambda *args, **kwargs: current)
    return verify_native(
        root,
        "codex",
        report_path,
        evidence_path,
        home=home,
        environ=environment,
    )


@pytest.mark.parametrize("client", CLIENTS)
def test_default_procedure_never_selects_a_client_artifact_or_operation(tmp_path, client):
    """Would fail if procedure generation auto-selected a skill, server or tool."""
    from ai_dlc.harness.native_verification import verify_native

    root, home, report_path, environment, _ = write_context(tmp_path)

    output = verify_native(
        root,
        client,
        report_path,
        home=home,
        environ=environment,
    )

    assert output["procedure"]["client_id"] == client
    assert all(step["artifact_id"] is None for step in output["procedure"]["steps"])
    assert all(step["tool_id"] is None for step in output["procedure"]["steps"])
    assert output["result"]["state"] == "pending"
    assert output["result"]["authenticated"] == "not-assessed"
    assert output["exit_code"] == 1


def test_template_is_json_native_incomplete_and_completed_copy_roundtrips(tmp_path):
    """Would fail if the helper fabricated a native observation or omitted usable fields."""
    from ai_dlc.harness.native_verification import verify_native

    root, home, report_path, environment, report = write_context(tmp_path)

    output = verify_native(
        root,
        "codex",
        report_path,
        home=home,
        environ=environment,
    )
    template = output["evidence_template"]

    assert template["client"] == {"id": "codex", "edition": "cli", "version": "1.2.3"}
    assert template["platform"]["os"] == report["platform"]["os"]
    assert template["observed_at"] is None
    assert template["observer"] is None
    assert all(step["result"] == "pending" for step in template["steps"])
    assert template["auth"]["state"] == "not-assessed"
    assert template["cost_authorization"] == "pending"
    assert "observed_at" in output["required_confirmations"]
    assert "client.version" in output["required_confirmations"]
    assert "steps.mcp.reason_code" in output["required_confirmations"]
    assert "auth.scope_checked" in output["required_confirmations"]
    with pytest.raises(ValueError, match=r"^Invalid native evidence\.$"):
        parse_evidence(json.dumps(template).encode())
    parsed = parse_evidence(json.dumps(completed_evidence(output)).encode())
    assert parsed["client"]["version"] == "1.2.3"
    assert [step["result"] for step in parsed["steps"]] == ["passed"] * 3


def test_imported_probed_observations_are_not_stale_only_because_local_probe_is_off(tmp_path):
    """Would fail if the service compared whole observation digests across probe modes."""
    from ai_dlc.harness.native_verification import verify_native

    root, home, report_path, environment, imported = write_context(tmp_path)

    output = verify_native(
        root,
        "codex",
        report_path,
        home=home,
        environ=environment,
    )

    assert output["result"]["state"] == "pending"
    assert output["result"]["stale_fields"] == []
    assert output["result"]["configuration_identity"] == imported["configuration_identity"]
    assert output["result"]["observation_identity"] == imported["observation_identity"]
    assert output["result"]["current_local"]["client_version"] is None
    assert (
        output["result"]["current_local"]["observation_identity"]
        != imported["observation_identity"]
    )


def test_completed_operator_results_remain_visible_when_current_guidance_turns_stale(tmp_path):
    """Would fail if local freshness erased independent historical step outcomes."""
    from ai_dlc.harness.native_verification import verify_native

    root, home, report_path, environment, _ = write_context(tmp_path)
    procedure = verify_native(
        root,
        "codex",
        report_path,
        home=home,
        environ=environment,
    )
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(completed_evidence(procedure)))

    observed = verify_native(
        root,
        "codex",
        report_path,
        evidence_path,
        home=home,
        environ=environment,
    )
    assert observed["result"]["state"] == "limited"
    assert [step["result"] for step in observed["result"]["steps"]] == ["passed"] * 3
    assert observed["result"]["historical_auth"]["state"] == "not-applicable"
    assert observed["result"]["authenticated"] == "not-assessed"
    assert observed["exit_code"] == 1

    guidance = root / "AGENTS.md"
    guidance.write_text(guidance.read_text().replace("Shared project guidance", "Edited guidance"))
    stale = verify_native(
        root,
        "codex",
        report_path,
        evidence_path,
        home=home,
        environ=environment,
    )
    assert stale["result"]["state"] == "stale"
    assert [step["result"] for step in stale["result"]["steps"]] == ["passed"] * 3
    assert stale["result"]["historical_auth"]["state"] == "not-applicable"
    assert stale["result"]["authenticated"] == "not-assessed"


def test_invalid_explicit_selection_is_rejected_before_local_collection(tmp_path, monkeypatch):
    """Would fail if invalid evidence selection caused an independent host inspection."""
    from ai_dlc.environment import report as current_report
    from ai_dlc.harness.native_verification import SAFE_ERROR, verify_native

    root, home, report_path, environment, _ = write_context(tmp_path)
    procedure = verify_native(
        root,
        "codex",
        report_path,
        home=home,
        environ=environment,
    )
    evidence = completed_evidence(procedure)
    evidence["steps"][1]["artifact_id"] = "skill.not-selected"
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(evidence))

    def forbidden(*args, **kwargs):
        raise AssertionError("selection validation ran after local collection")

    monkeypatch.setattr(current_report, "collect_report", forbidden)
    with pytest.raises(ValueError, match=rf"^{SAFE_ERROR}$"):
        verify_native(
            root,
            "codex",
            report_path,
            evidence_path,
            home=home,
            environ=environment,
        )


def test_historical_removed_skill_and_server_remain_stale_evidence(tmp_path, monkeypatch):
    """Would fail if removed historical selections were rejected as current input."""
    from ai_dlc.harness.native_verification import verify_native

    root, home, report_path, evidence_path, environment, changed = historical_removed_scope(
        tmp_path
    )
    monkeypatch.setattr(report_service, "collect_report", lambda *args, **kwargs: changed)

    output = verify_native(
        root,
        "codex",
        report_path,
        evidence_path,
        home=home,
        environ=environment,
    )

    assert output["exit_code"] == 1
    assert output["result"]["state"] == "stale"
    assert {
        "configuration_identity",
        "observation_identity",
        "steps.skill.artifact_id",
        "steps.mcp.artifact_id",
    } <= set(output["result"]["stale_fields"])
    assert [step["result"] for step in output["result"]["steps"]] == ["passed"] * 3
    assert [step["observed_marker"] for step in output["result"]["steps"]] == [
        "NHV-INSTRUCTION-1",
        "NHV-SKILL-1",
        "NHV-MCP-1",
    ]
    selected = {step["id"]: step for step in output["procedure"]["steps"]}
    assert selected["instruction"]["artifact_id"] == "agents"
    assert selected["skill"]["artifact_id"] is None
    assert selected["mcp"]["artifact_id"] is None
    assert selected["mcp"]["tool_id"] is None
    assert output["procedure"]["candidates"]["skill"] == ["skill.replacement"]
    assert output["procedure"]["candidates"]["mcp"] == ["native.replacement"]
    assert "no-selected-skill" in output["procedure"]["limitations"]
    assert "no-selected-mcp" in output["procedure"]["limitations"]


@pytest.mark.parametrize(
    "change,stale_field",
    [("engine", "local.engine.package_version"), ("platform", "local.platform.os")],
)
def test_known_local_engine_or_platform_change_is_stale(tmp_path, change, stale_field):
    """Would fail if known current host facts were ignored or treated as fresh."""
    from ai_dlc.harness.native_verification import verify_native

    root, home, _, environment, report = write_context(tmp_path)
    if change == "engine":
        report["engine"]["package_version"] = "99.0.0"
        report["engine"]["current_process"]["package_version"] = "99.0.0"
    else:
        report["platform"]["os"] = {
            "linux": "macos",
            "macos": "windows",
            "windows": "linux",
        }[report["platform"]["os"]]
        report["platform"]["reasons"]["os"] = None
    write_report(tmp_path / "changed.json", report_schema.finalize_report(report))

    output = verify_native(
        root,
        "codex",
        tmp_path / "changed.json",
        home=home,
        environ=environment,
    )

    assert output["result"]["state"] == "stale"
    assert stale_field in output["result"]["stale_fields"]
    assert "evidence-stale" in output["result"]["limitations"]


def test_unknown_imported_platform_is_not_filled_or_made_stale_by_local_collection(tmp_path):
    """Would fail if a known host fact repaired or invalidated unknown report provenance."""
    from ai_dlc.harness.native_verification import verify_native

    root, home, _, environment, report = write_context(tmp_path)
    report["platform"]["os"] = None
    report["platform"]["reasons"]["os"] = "not-assessed"
    unknown_path = tmp_path / "unknown.json"
    write_report(unknown_path, report_schema.finalize_report(report))

    output = verify_native(
        root,
        "codex",
        unknown_path,
        home=home,
        environ=environment,
    )

    assert output["result"]["state"] == "pending"
    assert "local.platform.os" not in output["result"]["stale_fields"]
    assert output["evidence_template"]["platform"]["os"] is None
    assert output["result"]["current_local"]["observation_complete"] is False


def test_changed_safe_configuration_is_stale_and_corruption_stays_bounded(tmp_path):
    """Would fail if config drift stayed pending or parser details escaped."""
    from ai_dlc.harness.native_verification import verify_native

    root, home, report_path, environment, imported = write_context(tmp_path)
    (root / "ai-dlc.toml").write_text("schema=4\n[roles]\nagent-client=[]\n")

    changed = verify_native(
        root,
        "codex",
        report_path,
        home=home,
        environ=environment,
    )
    assert changed["result"]["state"] == "stale"
    assert "local.configuration_identity" in changed["result"]["stale_fields"]
    assert (
        changed["result"]["current_local"]["configuration_identity"]
        != imported["configuration_identity"]
    )
    assert changed["result"]["current_local"]["configured"] == "no"

    (root / "ai-dlc.toml").write_text('schema=4\n[roles\nPRIVATE_SENTINEL="unterminated"\n')
    corrupted = verify_native(
        root,
        "codex",
        report_path,
        home=home,
        environ=environment,
    )
    assert corrupted["result"]["state"] == "stale"
    assert "PRIVATE_SENTINEL" not in json.dumps(corrupted)


@pytest.mark.parametrize(
    "mode,reason", [("missing", "render-missing"), ("modified", "render-stale")]
)
def test_current_instruction_guidance_failure_has_a_specific_reason(tmp_path, mode, reason):
    """Would fail if current selected-client render drift were hidden by imported state."""
    from ai_dlc.harness.native_verification import verify_native

    root, home, report_path, environment, _ = write_context(tmp_path)
    guidance = root / "AGENTS.md"
    if mode == "missing":
        guidance.unlink()
    else:
        guidance.write_text(
            guidance.read_text().replace("Shared project guidance", "Edited guidance")
        )

    output = verify_native(
        root,
        "codex",
        report_path,
        home=home,
        environ=environment,
    )

    assert output["result"]["state"] == "stale"
    assert reason in output["result"]["limitations"]
    assert "local.guidance.instruction" in output["result"]["stale_fields"]
    assert output["result"]["current_local"]["rendered"] == "no"


@pytest.mark.parametrize(
    "current_state,current_digest",
    [("match", "a" * 64), ("mismatch", "c" * 64)],
    ids=("repaired", "changed-mismatch"),
)
def test_selected_guidance_known_state_or_digest_change_is_stale(
    tmp_path, monkeypatch, current_state, current_digest
):
    """Would fail if a repair or a different mismatching file reused prior evidence."""
    baseline = native_evidence_report()
    imported = with_instruction_observation(
        baseline,
        state="mismatch",
        observed_sha256="b" * 64,
    )
    current = with_instruction_observation(
        baseline,
        state=current_state,
        observed_sha256=current_digest,
    )
    assert current["configuration_identity"] == imported["configuration_identity"]

    output = verify_selected_instruction_transition(
        tmp_path,
        monkeypatch,
        imported,
        current,
    )

    assert output["result"]["state"] == "stale"
    assert "local.guidance.instruction" in output["result"]["stale_fields"]
    assert "evidence-stale" in output["result"]["limitations"]
    assert [step["result"] for step in output["result"]["steps"]] == ["passed"] * 3


def test_selected_guidance_unknown_import_does_not_claim_freshness_or_copy_digest(
    tmp_path, monkeypatch
):
    """Would fail if current known bytes repaired an unknown imported observation."""
    baseline = native_evidence_report()
    imported = with_instruction_observation(
        baseline,
        state="unknown",
        observed_sha256=None,
    )
    current = with_instruction_observation(
        baseline,
        state="match",
        observed_sha256="a" * 64,
    )
    assert current["configuration_identity"] == imported["configuration_identity"]

    output = verify_selected_instruction_transition(
        tmp_path,
        monkeypatch,
        imported,
        current,
    )

    assert output["result"]["state"] == "limited"
    assert "local.guidance.instruction" not in output["result"]["stale_fields"]
    assert "context-unknown" in output["result"]["limitations"]
    imported_instruction = next(
        item for item in imported["project"]["guidance"] if item["id"] == "agents"
    )
    assert imported_instruction["observed_sha256"] is None


def test_selected_guidance_known_digest_change_is_stale_despite_unknown_state(
    tmp_path, monkeypatch
):
    """Would fail if state uncertainty hid two represented, different file digests."""
    baseline = native_evidence_report()
    imported = with_instruction_observation(
        baseline,
        state="unknown",
        observed_sha256="b" * 64,
    )
    current = with_instruction_observation(
        baseline,
        state="match",
        observed_sha256="a" * 64,
    )
    assert current["configuration_identity"] == imported["configuration_identity"]

    output = verify_selected_instruction_transition(
        tmp_path,
        monkeypatch,
        imported,
        current,
    )

    assert output["result"]["state"] == "stale"
    assert "local.guidance.instruction" in output["result"]["stale_fields"]
    assert "context-unknown" in output["result"]["limitations"]
    assert "evidence-stale" in output["result"]["limitations"]


def test_crlf_managed_instruction_bytes_do_not_create_false_staleness(tmp_path):
    """Would fail if local freshness treated normalized line endings as edited guidance."""
    from ai_dlc.harness.native_verification import verify_native

    root, home, report_path, environment, _ = write_context(tmp_path)
    guidance = root / "AGENTS.md"
    guidance.write_bytes(guidance.read_bytes().replace(b"\n", b"\r\n"))

    output = verify_native(
        root,
        "codex",
        report_path,
        home=home,
        environ=environment,
    )

    assert output["result"]["state"] == "pending"
    assert "local.guidance.instruction" not in output["result"]["stale_fields"]


def test_verification_performs_no_process_network_or_project_write(tmp_path, monkeypatch):
    """Would fail if the offline service launched a client, opened a socket or wrote output."""
    from ai_dlc.harness.native_verification import verify_native

    root, home, report_path, environment, _ = write_context(tmp_path)
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("offline native verification attempted an effect")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)

    verify_native(root, "codex", report_path, home=home, environ=environment)

    assert before == {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            "symlink",
            marks=pytest.mark.skipif(os.name == "nt", reason="POSIX symlink fixture"),
        ),
        pytest.param("oversize"),
        pytest.param("private-unknown"),
    ],
    ids=("symlink", "oversize", "private-unknown"),
)
def test_evidence_file_refusal_is_bounded_path_free_and_content_free(tmp_path, case):
    """Would fail if an unsafe evidence path or parser detail escaped the boundary."""
    from ai_dlc.harness.native_verification import SAFE_ERROR, verify_native

    root, home, report_path, environment, _ = write_context(tmp_path)
    evidence = tmp_path / "SECRET-evidence.json"
    if case == "symlink":
        target = tmp_path / "outside.json"
        target.write_text("{}")
        evidence.symlink_to(target)
    elif case == "oversize":
        evidence.write_bytes(b"x" * (1024 * 1024 + 1))
    else:
        evidence.write_text('{"PRIVATE_SENTINEL":"secret"}')

    with pytest.raises(ValueError, match=rf"^{SAFE_ERROR}$") as error:
        verify_native(
            root,
            "codex",
            report_path,
            evidence,
            home=home,
            environ=environment,
        )

    assert "SECRET" not in str(error.value)
    assert "PRIVATE" not in str(error.value)


@pytest.mark.skipif(os.name == "nt", reason="POSIX FIFO boundary")
def test_evidence_fifo_is_refused_without_waiting_for_a_writer(tmp_path):
    """Would fail by hanging if selected evidence were read as an ordinary stream."""
    from ai_dlc.harness.native_verification import SAFE_ERROR, verify_native

    root, home, report_path, environment, _ = write_context(tmp_path)
    evidence = tmp_path / "evidence.json"
    os.mkfifo(evidence)

    with pytest.raises(ValueError, match=rf"^{SAFE_ERROR}$"):
        verify_native(
            root,
            "codex",
            report_path,
            evidence,
            home=home,
            environ=environment,
        )
