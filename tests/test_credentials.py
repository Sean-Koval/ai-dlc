def test_status_reports_presence_without_returning_environment_value(monkeypatch):
    from ai_dlc.environment.credentials import credential_status

    marker = "fake-value-that-must-not-escape"
    monkeypatch.setenv("JIRA_SANDBOX_TOKEN", marker)
    config = {
        "credentials": {
            "jira-sandbox": {
                "description": "Jira sandbox access",
                "required_by": ["provider.jira-sandbox"],
                "source": "environment",
                "variable": "JIRA_SANDBOX_TOKEN",
            }
        }
    }

    result = credential_status(config)

    assert result == [
        {
            "id": "jira-sandbox",
            "description": "Jira sandbox access",
            "required_by": ["provider.jira-sandbox"],
            "source": "environment",
            "variable": "JIRA_SANDBOX_TOKEN",
            "configured": True,
            "present": True,
        }
    ]
    assert marker not in repr(result)


def test_status_marks_unbound_requirement_as_not_configured_or_present():
    from ai_dlc.environment.credentials import credential_status

    result = credential_status(
        {
            "credentials": {
                "jira-sandbox": {
                    "description": "Jira sandbox access",
                    "required_by": ["provider.jira-sandbox"],
                }
            }
        },
        environ={},
    )

    assert result[0]["configured"] is False
    assert result[0]["present"] is False


def test_status_marks_unset_environment_binding_as_configured_but_not_present():
    from ai_dlc.environment.credentials import credential_status

    result = credential_status(
        {
            "credentials": {
                "jira-sandbox": {
                    "description": "Jira sandbox access",
                    "required_by": ["provider.jira-sandbox"],
                    "source": "environment",
                    "variable": "JIRA_SANDBOX_TOKEN",
                }
            }
        },
        environ={},
    )

    assert result[0]["configured"] is True
    assert result[0]["present"] is False


def test_status_normalizes_uncovered_legacy_provider_token_environment():
    from ai_dlc.environment.credentials import credential_status

    result = credential_status(
        {"providers": {"jira": {"token_env": "JIRA_API_TOKEN"}}},
        environ={"JIRA_API_TOKEN": "present"},
    )

    assert result[0]["id"] == "provider.jira"
    assert result[0]["required_by"] == ["provider.jira"]
    assert result[0]["source"] == "environment"
    assert result[0]["variable"] == "JIRA_API_TOKEN"
    assert result[0]["configured"] is True
    assert result[0]["present"] is True


def test_status_normalizes_a_definition_default_token_environment(monkeypatch):
    """Would fail if a definition's default authentication bypassed shared readiness."""
    from ai_dlc import provider_definitions
    from ai_dlc.environment.credentials import credential_status
    from ai_dlc.provider_definitions import EnvironmentRequirement, ProviderDefinition

    monkeypatch.setitem(
        provider_definitions.DEFINITIONS,
        "defaulted",
        ProviderDefinition(
            "defaulted",
            ("tracker",),
            environment_requirements=(
                EnvironmentRequirement("token_env", default="DEFAULTED_TOKEN"),
            ),
        ),
    )
    absent = credential_status({"providers": {"tickets": {"kind": "defaulted"}}}, environ={})
    present = credential_status(
        {"providers": {"tickets": {"kind": "defaulted"}}},
        environ={"DEFAULTED_TOKEN": "present"},
    )

    assert absent == [
        {
            "id": "provider.tickets",
            "description": "Credential for provider tickets",
            "required_by": ["provider.tickets"],
            "source": "environment",
            "variable": "DEFAULTED_TOKEN",
            "configured": True,
            "present": False,
        }
    ]
    assert present[0]["present"] is True


def test_distinct_provider_token_environment_remains_visible_with_logical_requirement():
    from ai_dlc.environment.credentials import credential_status

    result = credential_status(
        {
            "credentials": {
                "jira-sandbox": {
                    "description": "Jira sandbox access",
                    "required_by": ["provider.jira"],
                    "source": "environment",
                    "variable": "JIRA_SANDBOX_TOKEN",
                }
            },
            "providers": {"jira": {"token_env": "JIRA_API_TOKEN"}},
        },
        environ={"JIRA_API_TOKEN": "provider", "JIRA_SANDBOX_TOKEN": "logical"},
    )

    assert [item["id"] for item in result] == ["jira-sandbox", "provider.jira"]
    assert [item["variable"] for item in result] == [
        "JIRA_SANDBOX_TOKEN",
        "JIRA_API_TOKEN",
    ]


def test_matching_provider_token_environment_is_not_reported_twice():
    """Would fail if one physical credential produced duplicate readiness entries."""
    from ai_dlc.environment.credentials import credential_status

    result = credential_status(
        {
            "credentials": {
                "jira-sandbox": {
                    "description": "Jira sandbox access",
                    "required_by": ["provider.jira"],
                    "source": "environment",
                    "variable": "JIRA_API_TOKEN",
                }
            },
            "providers": {"jira": {"kind": "jira-cloud", "token_env": "JIRA_API_TOKEN"}},
        },
        environ={"JIRA_API_TOKEN": "present"},
    )

    assert [item["id"] for item in result] == ["jira-sandbox"]


def test_status_uses_supplied_environment_mapping_without_mutating_process_environment(monkeypatch):
    from ai_dlc.environment.credentials import credential_status

    monkeypatch.delenv("JIRA_SANDBOX_TOKEN", raising=False)
    config = {
        "credentials": {
            "jira-sandbox": {
                "description": "Jira sandbox access",
                "required_by": ["provider.jira-sandbox"],
                "source": "environment",
                "variable": "JIRA_SANDBOX_TOKEN",
            }
        }
    }

    result = credential_status(config, environ={"JIRA_SANDBOX_TOKEN": "supplied"})

    assert result[0]["present"] is True
    assert "JIRA_SANDBOX_TOKEN" not in __import__("os").environ


def test_status_is_sorted_by_logical_credential_id():
    from ai_dlc.environment.credentials import credential_status

    result = credential_status(
        {
            "credentials": {
                "zebra": {"description": "Zebra access", "required_by": []},
                "alpha": {"description": "Alpha access", "required_by": []},
            },
            "providers": {"jira": {"token_env": "JIRA_API_TOKEN"}},
        },
        environ={},
    )

    assert [item["id"] for item in result] == ["alpha", "provider.jira", "zebra"]
