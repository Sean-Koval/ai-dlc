"""Real prerequisite distinctions for the standard scaffold roles."""

import pytest

from ai_dlc.readiness import inspect_readiness


def inspect(tmp_path, config, *, gh=True):
    return inspect_readiness(
        tmp_path,
        config,
        environ={},
        probe=lambda commands: {"available": gh or "gh" not in commands},
    )


@pytest.mark.parametrize(
    "repository", [None, "", " ", "owner", "owner/repo/extra", "https://github.com/owner/repo"]
)
def test_missing_or_malformed_root_scm_identity_has_actionable_refusal(tmp_path, repository):
    config = {
        "roles": {"scm": "github"},
        "providers": {"github": {"repository": "ignored/substitute"}},
    }
    if repository is not None:
        config["scm"] = {"repository": repository}
    result = inspect(tmp_path, config)
    assert result["ready"] is False
    assert any(
        c["dimension"] == "configuration"
        and c["status"] == "missing"
        and "scm.repository" in c["next_action"]
        for c in result["checks"]
    )
    assert not any("no component" in c["reason"] for c in result["checks"])


def test_available_scm_prerequisites_never_claim_authenticated_or_live_ci(tmp_path):
    config = {"roles": {"scm": "github"}, "scm": {"repository": "owner/repository"}}
    result = inspect(tmp_path, config)
    assert result["ready"] is True
    assert result["qualification"] == "not-assessed"
    assert any(
        c["dimension"] == "provider-health" and c["status"] == "unverified"
        for c in result["checks"]
    )
    assert any(c["dimension"] == "tool" and c["status"] == "ready" for c in result["checks"])
    assert any(c["dimension"] == "guidance" and c["status"] == "ready" for c in result["checks"])
    # This is the actual runtime configuration contract; construction makes no API call.
    from ai_dlc.providers.scm import GitHubSCM

    assert GitHubSCM(tmp_path, config, environ={}).repo == "owner/repository"


def test_valid_scm_identity_does_not_hide_missing_gh(tmp_path):
    result = inspect(
        tmp_path, {"roles": {"scm": "github"}, "scm": {"repository": "owner/repo"}}, gh=False
    )
    assert result["ready"] is False
    assert any(c["dimension"] == "tool" and c["status"] == "missing" for c in result["checks"])


def test_disabled_deploy_is_explicitly_inactive_without_health_or_tool_requirements(tmp_path):
    result = inspect(tmp_path, {"roles": {"deploy": "none"}}, gh=False)
    assert result["ready"] is True
    assert result["qualification"] == "not-assessed"
    assert any(
        c["dimension"] == "activation" and c["status"] == "inactive" for c in result["checks"]
    )
    assert not any(c["dimension"] in {"tool", "provider-health"} for c in result["checks"])


@pytest.mark.parametrize(
    "role,provider",
    [("scm", "unknown"), ("deploy", "unknown"), ("tracker", "none"), ("tracker", "github")],
)
def test_unknown_and_role_incompatible_selections_stay_blocked(tmp_path, role, provider):
    result = inspect(tmp_path, {"roles": {role: provider}})
    assert result["ready"] is False
    assert any(c["status"] == "blocked" for c in result["checks"])


def test_synthetic_definition_uses_shared_runtime_requirements_and_inactive_metadata(
    tmp_path, monkeypatch
):
    from ai_dlc.provider_definitions import DEFINITIONS, ProviderDefinition, RuntimeRequirement

    monkeypatch.setitem(
        DEFINITIONS,
        "github",
        ProviderDefinition(
            "github",
            ("scm",),
            runtime_requirements=(
                RuntimeRequirement("scm.fixture", r"chosen", "chosen fixture value"),
            ),
            inactive=True,
        ),
    )
    result = inspect(tmp_path, {"roles": {"scm": "github"}, "scm": {"fixture": "wrong"}})
    assert result["ready"] is False
    assert any("scm.fixture" in c["next_action"] for c in result["checks"])
    assert any(c["status"] == "inactive" for c in result["checks"])
    assert not any(c["dimension"] == "provider-health" for c in result["checks"])
