"""Conditional local requirements, without authenticating any account."""

import pytest

from ai_dlc.environment.credentials import credential_status
from ai_dlc.setup.readiness import inspect_readiness


def jira_config(alias="work", mode="personal_scoped_token_basic"):
    return {
        "roles": {"tracker": alias},
        "providers": {
            alias: {
                "kind": "jira-cloud",
                "site_url": "https://work.atlassian.net",
                "cloud_id": "11111111-2222-3333-4444-555555555555",
                "account_id": "account-1",
                "project_id": "100",
                "project_key": "WORK",
                "issue_type_id": "10",
                "auth_mode": mode,
                "token_env": "JIRA_TOKEN",
                "email_env": "JIRA_EMAIL",
                "statuses": {"open": "1", "in_progress": "2", "closed": "3", "cancelled": "4"},
                "resolutions": {"closed": ["1000"], "cancelled": ["2000"]},
            }
        },
    }


@pytest.mark.parametrize("alias", ["work", "jira-cloud"])
@pytest.mark.parametrize("field", ["token_env", "email_env"])
@pytest.mark.parametrize("reference", [None, "", " ", "INVALID-NAME"])
def test_required_missing_or_invalid_reference_remains_visible(alias, field, reference):
    config = jira_config(alias)
    if reference is None:
        del config["providers"][alias][field]
    else:
        config["providers"][alias][field] = reference
    result = credential_status(config, environ={"JIRA_TOKEN": "token", "JIRA_EMAIL": "email"})
    missing = [row for row in result if not row["configured"]]
    assert len(missing) == 1
    assert missing[0]["required_by"] == [f"provider.{alias}"]
    assert missing[0]["present"] is False


@pytest.mark.parametrize("field", ["JIRA_TOKEN", "JIRA_EMAIL"])
@pytest.mark.parametrize("value", [None, "", " \t\n"])
def test_actual_readiness_blocks_absent_or_blank_required_value(tmp_path, field, value):
    environment = {"JIRA_TOKEN": "token-sentinel", "JIRA_EMAIL": "email-sentinel"}
    if value is None:
        del environment[field]
    else:
        environment[field] = value
    result = inspect_readiness(
        tmp_path, jira_config(), environ=environment, probe=lambda _: {"available": True}
    )
    assert result["ready"] is False
    assert result["qualification"] == "not-assessed"
    missing = [
        c for c in result["checks"] if c["dimension"] == "credential" and c["status"] == "missing"
    ]
    assert len(missing) == 1
    assert field in missing[0]["next_action"]
    assert "token-sentinel" not in repr(result)
    assert "email-sentinel" not in repr(result)


def test_actual_readiness_blocks_absent_basic_email_reference(tmp_path):
    config = jira_config()
    del config["providers"]["work"]["email_env"]
    result = inspect_readiness(
        tmp_path, config, environ={"JIRA_TOKEN": "present"}, probe=lambda _: {"available": True}
    )
    assert result["ready"] is False
    assert any(
        c["dimension"] == "credential" and c["status"] == "blocked" for c in result["checks"]
    )


@pytest.mark.parametrize("mode", ["oauth_bearer", "personal_scoped_token_basic"])
def test_auth_mode_selects_only_its_requirements_without_claiming_authentication(tmp_path, mode):
    config = jira_config(mode=mode)
    environment = {"JIRA_TOKEN": "present"}
    if mode == "personal_scoped_token_basic":
        environment["JIRA_EMAIL"] = "person@example.test"
    result = credential_status(config, environ=environment)
    assert [row["id"] for row in result] == (
        ["provider.work"]
        if mode == "oauth_bearer"
        else ["provider.work", "provider.work.email_env"]
    )
    readiness = inspect_readiness(
        tmp_path, config, environ=environment, probe=lambda _: {"available": True}
    )
    assert readiness["ready"] is True
    assert readiness["qualification"] == "not-assessed"


def test_explicit_requirements_deduplicate_by_alias_and_variable():
    config = jira_config()
    config["credentials"] = {
        "explicit-email": {
            "source": "environment",
            "variable": "JIRA_EMAIL",
            "required_by": ["provider.work"],
        },
        "other-account": {
            "source": "environment",
            "variable": "JIRA_TOKEN",
            "required_by": ["provider.personal"],
        },
    }
    result = credential_status(config, environ={"JIRA_EMAIL": "present", "JIRA_TOKEN": "present"})
    assert [row["id"] for row in result] == ["explicit-email", "other-account", "provider.work"]


@pytest.mark.parametrize("collision", ["provider.work", "provider.work.email_env"])
def test_generated_requirement_never_overwrites_explicit_id(collision):
    config = jira_config()
    config["credentials"] = {
        collision: {
            "description": "Authored requirement",
            "source": "environment",
            "variable": "UNRELATED",
            "required_by": ["provider.other"],
        }
    }
    result = credential_status(config, environ={})
    assert len(result) == 3
    assert (
        next(row for row in result if row["id"] == collision)["description"]
        == "Authored requirement"
    )
    assert {row.get("variable") for row in result} == {"UNRELATED", "JIRA_EMAIL", "JIRA_TOKEN"}
    assert len({row["id"] for row in result}) == 3


def test_third_trusted_definition_declares_conditional_requirement(monkeypatch):
    from ai_dlc.provider_definitions import DEFINITIONS, EnvironmentRequirement, ProviderDefinition

    monkeypatch.setitem(
        DEFINITIONS,
        "third",
        ProviderDefinition(
            "third",
            ("tracker",),
            environment_requirements=(
                EnvironmentRequirement("tenant_env", when=("mode", "tenant")),
            ),
        ),
    )
    config = {"providers": {"alias": {"kind": "third", "mode": "tenant"}}}
    assert credential_status(config, environ={})[0]["configured"] is False
    config["providers"]["alias"]["tenant_env"] = "TENANT_ENV"
    assert credential_status(config, environ={"TENANT_ENV": "present"})[0]["present"] is True
    config["providers"]["alias"]["mode"] = "public"
    assert credential_status(config, environ={}) == []
