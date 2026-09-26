"""Pure operator evidence is bounded and never upgrades unknown report context."""

import copy
import json

import pytest
from test_environment_report import payload

from ai_dlc.environment import report_schema
from ai_dlc.harness import native_adapters, native_evidence


def report():
    value = payload()
    for identifier, kind in (("skill.day-start", "skill"), ("server.local", "native-server")):
        item = copy.deepcopy(value["project"]["guidance"][0])
        item.update(id=identifier, kind=kind)
        if kind == "native-server":
            item["native_server"] = {
                "alias": "local",
                "provider": "local",
                "transport": "stdio",
                "recipe_identity": "c" * 64,
                "reasons": dict.fromkeys(("alias", "provider", "transport", "recipe_identity")),
            }
        value["project"]["guidance"].append(item)
    return report_schema.finalize_report(value)


def evidence(context=None):
    context = context or report()
    contract = native_adapters.adapter_contract("codex")
    return {
        "schema_version": 1,
        "configuration_identity": context["configuration_identity"],
        "observation_identity": context["observation_identity"],
        "engine": {
            k: context["engine"][k]
            for k in (
                "package_version",
                "installation_kind",
                "source_revision",
                "source_dirty",
                "artifact_sha256",
            )
        },
        "client": {"id": "codex", "edition": "cli", "version": "1.0.0"},
        "platform": {"os": "linux", "architecture": "x86_64"},
        "observed_at": "2026-09-26T13:00:00Z",
        "observer": "operator",
        "fixture_id": contract["fixture_id"],
        "fixture_sha256": contract["fixture_sha256"],
        "adapter_contract_id": contract["adapter_contract_id"],
        "adapter_contract_sha256": contract["adapter_contract_sha256"],
        "steps": [
            {
                "id": step,
                "artifact_id": artifact,
                "tool_id": tool,
                "expected_marker": marker,
                "observed_marker": marker,
                "result": "passed",
                "reason_code": "observed",
            }
            for step, artifact, tool, marker in (
                ("instruction", "agents", None, "NHV-INSTRUCTION-1"),
                ("skill", "skill.day-start", None, "NHV-SKILL-1"),
                ("mcp", "server.local", "inspect", "NHV-MCP-1"),
            )
        ],
        "auth": {
            "state": "not-applicable",
            "observed_at": "2026-09-26T13:00:00Z",
            "scope_checked": False,
            "reason_code": "no-auth-required",
        },
        "cost_authorization": "authorized",
        "limitations": [],
    }


def parse(value):
    return native_evidence.parse_evidence(json.dumps(value).encode())


def adjudicate(value, context=None):
    return native_evidence.adjudicate_evidence(context or report(), "codex", parse(value))


def test_operator_passes_remain_independent_limited_observations():
    result = adjudicate(evidence())
    assert result["state"] == "limited"
    assert result["provenance"] == "operator-attested"
    assert [s["result"] for s in result["steps"]] == ["passed"] * 3
    assert result["recognized"] == "limited"
    assert result["authenticated"] == "not-assessed"
    assert result["historical_auth"]["state"] == "not-applicable"
    assert "client-schema-unverified" in result["limitations"]
    assert "safe-operation-unverified" in result["limitations"]
    assert native_evidence.evidence_exit_code(result) == 1


def test_default_procedure_does_not_select_artifacts_or_authorize_cost():
    result = native_evidence.procedure_contract(report(), "codex")
    assert result["cost_authorization"] == "pending"
    assert all(s["artifact_id"] is None for s in result["steps"])
    assert all(s["result"] == "pending" for s in result["steps"])
    assert result["candidates"]["skill"] == ["skill.day-start"]
    assert native_evidence.adjudicate_evidence(report(), "codex", None)["state"] == "pending"


@pytest.mark.parametrize("client", ["codex", "claude-code", "antigravity"])
def test_documented_adapters_never_invent_tested_versions(client):
    contract = native_adapters.adapter_contract(client)
    assert contract["tested_versions"] == []
    assert contract["compatibility"] == "client-schema-unverified"


@pytest.mark.parametrize(
    "case",
    [
        "extra",
        "nested-extra",
        "private-id",
        "private-marker",
        "observer",
        "version",
        "bool-schema",
        "timestamp",
        "steps-missing",
        "steps-duplicate",
        "tool-on-skill",
        "auth-time",
        "auth-scope",
        "reason",
    ],
)
def test_closed_schema_refuses_private_or_inconsistent_payload(case):
    value = evidence()
    if case == "extra":
        value["transcript"] = "/Users/private/secret"
    elif case == "nested-extra":
        value["auth"]["account"] = "private@example.org"
    elif case == "private-id":
        value["steps"][0]["artifact_id"] = "/Users/private/secret"
    elif case == "private-marker":
        value["steps"][0]["observed_marker"] = "secret-token-value"
    elif case == "observer":
        value["observer"] = "private@example.org"
    elif case == "version":
        value["client"]["version"] = "1.0+private"
    elif case == "bool-schema":
        value["schema_version"] = True
    elif case == "timestamp":
        value["observed_at"] = "2026-02-30T13:00:00Z"
    elif case == "steps-missing":
        value["steps"].pop()
    elif case == "steps-duplicate":
        value["steps"][1] = value["steps"][0]
    elif case == "tool-on-skill":
        value["steps"][1]["tool_id"] = "inspect"
    elif case == "auth-time":
        value["auth"]["observed_at"] = "2026-09-27T13:00:00Z"
    elif case == "auth-scope":
        value["auth"].update(
            state="verified", reason_code="authenticated-call", scope_checked=False
        )
    else:
        value["limitations"] = ["private-token"]
    with pytest.raises(ValueError, match=r"^Invalid native evidence\.$"):
        parse(value)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":1,"schema_version":1}',
        b'"\xff"',
        b"NaN",
        b"[" * 20 + b"0" + b"]" * 20,
        b" " * (1024 * 1024 + 1),
    ],
    ids=["duplicate", "utf8", "nan", "depth", "size"],
)
def test_bounded_json_refusal_has_no_payload_echo(raw):
    with pytest.raises(ValueError, match=r"^Invalid native evidence\.$"):
        native_evidence.parse_evidence(raw)


@pytest.mark.parametrize(
    "field",
    ["configuration_identity", "observation_identity", "fixture_sha256", "adapter_contract_sha256"],
)
def test_context_digest_changes_are_stale(field):
    value = evidence()
    value[field] = "d" * 64
    assert adjudicate(value)["state"] == "stale"


@pytest.mark.parametrize(
    "case", ["edition", "version", "os", "architecture", "source", "dirty", "artifact", "selection"]
)
def test_known_context_conflicts_are_stale(case):
    value = evidence()
    if case == "edition":
        value["client"]["edition"] = "desktop"
    elif case == "version":
        value["client"]["version"] = "2.0"
    elif case == "os":
        value["platform"]["os"] = "macos"
    elif case == "architecture":
        value["platform"]["architecture"] = "arm64"
    elif case == "source":
        value["engine"]["source_revision"] = "d" * 40
    elif case == "dirty":
        value["engine"]["source_dirty"] = True
    elif case == "artifact":
        value["steps"][0]["artifact_id"] = "other"
    else:
        value["client"]["id"] = "claude-code"
    assert adjudicate(value)["state"] == "stale"


def test_missing_report_version_cannot_be_repaired_by_operator_assertion():
    context = report()
    context["clients"][0]["version"].update(observed=None, state="unknown", reason="not-assessed")
    context = report_schema.finalize_report(context)
    result = adjudicate(evidence(context), context)
    assert result["state"] == "limited"
    assert not result["observation_complete"]
    assert result["steps"][0]["result"] == "passed"


def test_engine_and_opaque_transport_unknowns_preserve_partial_passes():
    context = report()
    for side in ("current_process", "path_selected"):
        context["engine"][side]["source_revision"] = None
        context["engine"][side]["reasons"]["source_revision"] = "provenance-unavailable"
    context["engine"]["source_revision"] = None
    server = context["project"]["guidance"][1]["native_server"]
    server["recipe_identity"] = None
    server["reasons"]["recipe_identity"] = "safe-digest-unavailable"
    context = report_schema.finalize_report(context)
    value = evidence(context)
    value["engine"]["source_revision"] = "d" * 40
    result = adjudicate(value, context)
    assert result["state"] == "limited"
    assert not result["configuration_complete"]
    assert not result["observation_complete"]
    assert all(s["result"] == "passed" for s in result["steps"])


@pytest.mark.parametrize("field", ["expected_marker", "observed_marker"])
def test_wrong_known_marker_fails_only_affected_step(field):
    value = evidence()
    value["steps"][1][field] = "NHV-INSTRUCTION-1"
    result = adjudicate(value)
    assert result["state"] == "failed"
    assert [s["result"] for s in result["steps"]] == ["passed", "failed", "passed"]
    assert result["steps"][1]["reason_code"] == "smoke-failed"


def test_enumeration_is_neither_invocation_nor_authentication():
    value = evidence()
    value["steps"][2]["reason_code"] = "enumerated-only"
    value["auth"].update(state="verified", scope_checked=True, reason_code="authenticated-call")
    result = adjudicate(value)
    assert result["steps"][2]["result"] == "pending"
    assert result["historical_auth"]["state"] == "not-assessed"
    assert result["authenticated"] == "not-assessed"


def test_historical_auth_never_claims_current_session():
    value = evidence()
    value["auth"].update(state="verified", scope_checked=True, reason_code="authenticated-call")
    result = adjudicate(value)
    assert result["historical_auth"]["state"] == "verified"
    assert result["authenticated"] == "not-assessed"
    value["auth"].update(state="failed", reason_code="authentication-failed")
    assert adjudicate(value)["state"] == "failed"


def test_cost_pending_preserves_observations_but_blocks_qualification():
    value = evidence()
    del value["cost_authorization"]
    result = adjudicate(value)
    assert result["cost_authorization"] == "pending"
    assert "cost-authorization-pending" in result["limitations"]
    assert native_evidence.evidence_exit_code(result) == 1


def test_not_applicable_step_is_explicit_partial_scope():
    value = evidence()
    value["steps"][1].update(
        artifact_id=None,
        result="not-applicable",
        observed_marker=None,
        reason_code="no-selected-skill",
    )
    result = adjudicate(value)
    assert result["state"] == "limited"
    assert "no-selected-skill" in result["limitations"]


def test_tampered_report_is_rejected_before_adjudication():
    context = report()
    context["configuration_identity"] = "0" * 64
    with pytest.raises(ValueError, match=r"^Invalid native evidence\.$"):
        native_evidence.adjudicate_evidence(context, "codex", parse(evidence()))


def test_pending_reason_cannot_attest_successful_invocation():
    value = evidence()
    value["steps"][1]["reason_code"] = "native-observation-pending"
    result = adjudicate(value)
    assert result["steps"][1]["result"] == "pending"
    assert result["state"] == "pending"


def test_newer_report_auth_failure_supersedes_historical_success():
    context = report()
    context["auth"] = [
        {
            "kind": "client",
            "id": "codex",
            "credential_presence": "present",
            "verification": "failed",
            "verified_at": "2026-09-26T14:00:00Z",
            "evidence_identity": {
                k: context[k] for k in ("configuration_identity", "observation_identity")
            },
            "reasons": dict.fromkeys(("id", "verified_at", "evidence_identity")),
        }
    ]
    context = report_schema.finalize_report(context)
    value = evidence(context)
    value["auth"].update(state="verified", scope_checked=True, reason_code="authenticated-call")
    result = adjudicate(value, context)
    assert result["state"] == "failed"
    assert result["historical_auth"]["state"] == "verified"
    assert result["later_auth_failure_at"] == "2026-09-26T14:00:00Z"
    assert result["authenticated"] == "not-assessed"


@pytest.mark.parametrize(
    "state,reason", [("missing", "render-missing"), ("mismatch", "render-stale")]
)
def test_broken_guidance_retains_specific_limitation(state, reason):
    context = report()
    context["project"]["guidance"][0].update(state=state, observed_sha256=None)
    context["project"]["guidance"][0]["reasons"]["observed_sha256"] = "safe-digest-unavailable"
    context = report_schema.finalize_report(context)
    assert reason in adjudicate(evidence(context), context)["limitations"]


def test_explicit_procedure_selection_is_validated_against_report():
    result = native_evidence.procedure_contract(report(), "codex", skill_id="skill.day-start")
    assert result["steps"][1]["artifact_id"] == "skill.day-start"
    with pytest.raises(ValueError, match=r"^Invalid native evidence\.$"):
        native_evidence.procedure_contract(report(), "codex", skill_id="unselected")


def test_stale_output_preserves_original_operator_context():
    value = evidence()
    value["client"]["version"] = "2.0"
    result = adjudicate(value)
    assert result["evidence_context"]["client"]["version"] == "2.0"
    assert result["evidence_context"]["engine"] == value["engine"]
    assert result["evidence_context"]["observation_identity"] == value["observation_identity"]


def test_procedure_names_unselected_scope_without_selecting_candidates():
    result = native_evidence.procedure_contract(report(), "codex")
    assert "no-selected-skill" in result["limitations"]
    assert "no-selected-mcp" in result["limitations"]
    result = adjudicate(evidence())
    assert "no-selected-skill" not in result["limitations"]
    assert "no-selected-mcp" not in result["limitations"]


def test_public_markers_cannot_redefine_fixture_contract():
    before = native_adapters.adapter_contract("codex")
    original = native_adapters.MARKERS["instruction"]
    try:
        with pytest.raises(TypeError):
            native_adapters.MARKERS["instruction"] = "NHV-SKILL-1"
        after = native_adapters.adapter_contract("codex")
        assert after["fixture"]["markers"]["instruction"] == "NHV-INSTRUCTION-1"
        assert after["fixture_sha256"] == before["fixture_sha256"]
        assert after["adapter_contract_sha256"] == before["adapter_contract_sha256"]
    finally:
        # Keep the intentional red run from contaminating other tests.
        if isinstance(native_adapters.MARKERS, dict):
            native_adapters.MARKERS["instruction"] = original


def test_returned_contract_is_json_serializable_and_independently_mutable():
    before = native_adapters.adapter_contract("codex")
    edited = native_adapters.adapter_contract("codex")
    edited["fixture"]["markers"]["instruction"] = "NHV-SKILL-1"
    edited["fixture"]["steps"]["instruction"] = "changed"
    edited["sources"].clear()
    edited["tested_versions"].append("1.0")
    after = json.loads(json.dumps(native_adapters.adapter_contract("codex")))
    assert after["fixture"]["markers"]["instruction"] == "NHV-INSTRUCTION-1"
    assert after["fixture"] == before["fixture"]
    assert after["sources"] == before["sources"]
    assert after["tested_versions"] == []
    assert after["fixture_sha256"] == before["fixture_sha256"]
    assert after["adapter_contract_sha256"] == before["adapter_contract_sha256"]
