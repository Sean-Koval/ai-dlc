"""Focused tests for the pure phase helpers behind ``inspect_readiness``."""

from __future__ import annotations

from ai_dlc.setup.readiness import (
    _agent_clients,
    _credential_checks,
    _guidance_checks,
    _provider_config_checks,
    _provider_health_checks,
    _summarize_ready,
    _unresolved_checks,
)


def _component(**overrides) -> dict:
    component = {
        "id": "linear",
        "provider": "linear",
        "role": "tracker",
        "modules": [],
        "required_config": ["team_id", "statuses.closed"],
        "guidance": [],
    }
    component.update(overrides)
    return component


def test_unresolved_checks_block_each_unresolved_provider():
    resolved = {
        "unresolved": [
            {"provider": "custom", "reason": "no component"},
            {"provider": "other", "reason": "role mismatch"},
        ]
    }
    checks = _unresolved_checks(resolved)
    assert [c["component"] for c in checks] == ["custom", "other"]
    assert {c["status"] for c in checks} == {"blocked"}
    assert checks[0] == {
        "component": "custom",
        "dimension": "configuration",
        "status": "blocked",
        "reason": "no component",
        "next_action": "Select a compatible configured provider component.",
    }
    assert _unresolved_checks({"unresolved": []}) == []


def test_agent_clients_normalizes_scalar_and_list_forms():
    assert _agent_clients({}) == []
    assert _agent_clients({"roles": {"agent-client": "codex"}}) == ["codex"]
    assert _agent_clients({"roles": {"agent-client": ["codex", "claude-code"]}}) == [
        "codex",
        "claude-code",
    ]


def test_provider_config_checks_report_each_required_path():
    config = {"providers": {"linear": {"team_id": "team", "statuses": {"closed": " "}}}}
    checks = _provider_config_checks(_component(), config)
    assert [(c["status"], c["reason"]) for c in checks] == [
        ("ready", "provider configuration team_id is set"),
        ("missing", "provider configuration statuses.closed is required"),
    ]
    assert checks[1]["next_action"] == "Configure providers.linear.statuses.closed."
    assert all(c["dimension"] == "configuration" for c in checks)


def test_credential_checks_only_consider_credentials_required_by_the_provider():
    credentials = [
        {"id": "present", "required_by": ["provider.linear"], "configured": True, "present": True},
        {
            "id": "unset",
            "required_by": ["provider.linear"],
            "configured": True,
            "present": False,
            "variable": "LINEAR_TOKEN",
        },
        {
            "id": "unbound",
            "required_by": ["provider.linear"],
            "configured": False,
            "present": False,
        },
        {"id": "other", "required_by": ["provider.github"], "configured": True, "present": True},
        {"id": "malformed", "required_by": "provider.linear", "configured": True, "present": True},
    ]
    checks = _credential_checks(_component(), credentials)
    assert [(c["status"], c["next_action"]) for c in checks] == [
        ("ready", "No action required."),
        ("missing", "Set LINEAR_TOKEN using your credential store."),
        ("blocked", "Bind credential unbound in machine configuration."),
    ]
    assert {c["dimension"] for c in checks} == {"credential"}
    assert {c["component"] for c in checks} == {"linear"}


def test_credential_checks_fall_back_when_no_variable_is_named():
    credentials = [
        {"id": "unset", "required_by": ["provider.linear"], "configured": True, "present": False}
    ]
    [check] = _credential_checks(_component(), credentials)
    assert check["reason"] == "credential unset is not present"
    assert check["next_action"] == "Bind credential unset in machine configuration."


def test_guidance_checks_distinguish_available_from_missing(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "present.md").write_text("# guidance\n")
    component = _component(guidance=["docs/present.md", "docs/absent.md", "docs/flagged.md"])
    (tmp_path / "docs" / "flagged.md").write_text("# exists but reported missing\n")
    checks = _guidance_checks(tmp_path, component, {("linear", "docs/flagged.md")})
    assert [(c["status"], c["reason"]) for c in checks] == [
        ("ready", "guidance docs/present.md is available"),
        ("missing", "guidance docs/absent.md is unavailable"),
        ("missing", "guidance docs/flagged.md is unavailable"),
    ]
    assert checks[1]["next_action"] == "Restore the configured guidance file docs/absent.md."


def test_provider_health_checks_skip_explicitly_inactive_capabilities():
    active = _provider_health_checks(_component(), {})
    assert [(c["dimension"], c["status"]) for c in active] == [("provider-health", "unverified")]
    inactive = _component(id="none", provider="none", role="deploy")
    assert _provider_health_checks(inactive, {}) == []
    incompatible = _provider_health_checks(_component(id="none", provider="none"), {})
    assert [c["dimension"] for c in incompatible] == ["provider-health"]


def test_summarize_ready_ignores_non_blocking_dimensions():
    ready = {"dimension": "tool", "status": "ready"}
    assert _summarize_ready([]) is True
    assert _summarize_ready([ready, {"dimension": "provider-health", "status": "unverified"}])
    assert _summarize_ready([ready, {"dimension": "optional-viewer", "status": "unavailable"}])
    assert not _summarize_ready([ready, {"dimension": "credential", "status": "missing"}])
    assert not _summarize_ready([{"dimension": "lifecycle-adapter", "status": "blocked"}])
