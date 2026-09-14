"""Pure phase helpers extracted from doctor."""

from ai_dlc.setup.provision import (
    _capability_failure_reason,
    _configuration_gaps,
    _credential_signins,
    _inspect_user_agents,
    _provider_kind,
)


def test_provider_kind_prefers_kind_then_type_then_provider_name():
    roles = {"scm": "hub", "tracker": "issues", "deploy": "none"}
    providers = {"hub": {"kind": "github", "type": "ignored"}, "issues": {"type": "linear"}}
    assert _provider_kind(roles, providers, "scm") == "github"
    assert _provider_kind(roles, providers, "tracker") == "linear"
    assert _provider_kind(roles, providers, "deploy") == "none"
    assert _provider_kind(roles, providers, "knowledge") is None


def test_configuration_gaps_for_github_scm_and_issues():
    config = {
        "roles": {"scm": "github", "tracker": "github-issues"},
        "providers": {"github": {"kind": "github"}, "github-issues": {"kind": "github-issues"}},
        "scm": {"repository": "org/repo"},
    }
    assert _configuration_gaps(config) == [
        "scm.workflow is required",
        "scm.target_branch is required",
        "tracker repository is required",
    ]


def test_configuration_gaps_for_linear_tracker_and_clean_configuration():
    config = {
        "roles": {"tracker": "linear"},
        "providers": {"linear": {"kind": "linear", "statuses": {"closed": "Done"}}},
    }
    assert _configuration_gaps(config) == [
        "tracker team_id is required for creation",
        "tracker statuses.in_progress is required",
    ]
    complete = {
        "roles": {"tracker": "linear"},
        "providers": {
            "linear": {
                "kind": "linear",
                "team_id": "team",
                "statuses": {"in_progress": "Doing", "closed": "Done"},
            }
        },
    }
    assert _configuration_gaps(complete) == []
    assert _configuration_gaps({}) == []


def test_capability_failure_reason_calls_out_project_access():
    generic = _capability_failure_reason(RuntimeError("timeout"))
    assert generic.startswith("Declared provider capability inspection failed")
    scoped = _capability_failure_reason(RuntimeError("missing read:project scope"))
    assert scoped.startswith("Projects capability inspection failed")
    assert _capability_failure_reason(RuntimeError("Project not found")) == scoped


def test_credential_signins_only_for_absent_credentials():
    credentials = [
        {"id": "linear", "present": True, "variable": "LINEAR_API_KEY"},
        {"id": "github", "present": False, "variable": "GH_TOKEN"},
        {"id": "vault", "present": False},
    ]
    assert _credential_signins(credentials) == [
        "Set GH_TOKEN using your credential store",
        "Bind credential vault in machine configuration",
    ]
    assert _credential_signins([]) == []


def test_inspect_user_agents_without_personal_profile_is_clean():
    assert _inspect_user_agents({}, None, None) == {
        "clean": True,
        "changed": [],
        "applied": False,
    }
