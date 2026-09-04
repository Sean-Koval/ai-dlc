def test_status_reports_presence_without_returning_environment_value(monkeypatch):
    from ai_dlc.credentials import credential_status

    marker = "fake-value-that-must-not-escape"
    monkeypatch.setenv("LINEAR_SANDBOX_TOKEN", marker)
    config = {
        "credentials": {
            "linear-sandbox": {
                "description": "Linear sandbox access",
                "required_by": ["provider.linear-sandbox"],
                "source": "environment",
                "variable": "LINEAR_SANDBOX_TOKEN",
            }
        }
    }

    result = credential_status(config)

    assert result == [
        {
            "id": "linear-sandbox",
            "description": "Linear sandbox access",
            "required_by": ["provider.linear-sandbox"],
            "source": "environment",
            "variable": "LINEAR_SANDBOX_TOKEN",
            "configured": True,
            "present": True,
        }
    ]
    assert marker not in repr(result)


def test_status_marks_unbound_requirement_as_not_configured_or_present():
    from ai_dlc.credentials import credential_status

    result = credential_status(
        {
            "credentials": {
                "linear-sandbox": {
                    "description": "Linear sandbox access",
                    "required_by": ["provider.linear-sandbox"],
                }
            }
        },
        environ={},
    )

    assert result[0]["configured"] is False
    assert result[0]["present"] is False


def test_status_marks_unset_environment_binding_as_configured_but_not_present():
    from ai_dlc.credentials import credential_status

    result = credential_status(
        {
            "credentials": {
                "linear-sandbox": {
                    "description": "Linear sandbox access",
                    "required_by": ["provider.linear-sandbox"],
                    "source": "environment",
                    "variable": "LINEAR_SANDBOX_TOKEN",
                }
            }
        },
        environ={},
    )

    assert result[0]["configured"] is True
    assert result[0]["present"] is False


def test_status_normalizes_uncovered_legacy_provider_token_environment():
    from ai_dlc.credentials import credential_status

    result = credential_status(
        {"providers": {"linear": {"token_env": "LINEAR_API_KEY"}}},
        environ={"LINEAR_API_KEY": "present"},
    )

    assert result[0]["id"] == "provider.linear"
    assert result[0]["required_by"] == ["provider.linear"]
    assert result[0]["source"] == "environment"
    assert result[0]["variable"] == "LINEAR_API_KEY"
    assert result[0]["configured"] is True
    assert result[0]["present"] is True


def test_status_normalizes_the_linear_default_token_environment():
    """Would fail if default Linear authentication bypassed shared readiness."""
    from ai_dlc.credentials import credential_status

    absent = credential_status(
        {"providers": {"linear": {"kind": "linear"}}},
        environ={},
    )
    present = credential_status(
        {"providers": {"linear": {"kind": "linear"}}},
        environ={"LINEAR_API_KEY": "present"},
    )

    assert absent == [
        {
            "id": "provider.linear",
            "description": "Credential for provider linear",
            "required_by": ["provider.linear"],
            "source": "environment",
            "variable": "LINEAR_API_KEY",
            "configured": True,
            "present": False,
        }
    ]
    assert present[0]["present"] is True


def test_distinct_provider_token_environment_remains_visible_with_logical_requirement():
    from ai_dlc.credentials import credential_status

    result = credential_status(
        {
            "credentials": {
                "linear-sandbox": {
                    "description": "Linear sandbox access",
                    "required_by": ["provider.linear"],
                    "source": "environment",
                    "variable": "LINEAR_SANDBOX_TOKEN",
                }
            },
            "providers": {"linear": {"token_env": "LINEAR_API_KEY"}},
        },
        environ={"LINEAR_API_KEY": "provider", "LINEAR_SANDBOX_TOKEN": "logical"},
    )

    assert [item["id"] for item in result] == ["linear-sandbox", "provider.linear"]
    assert [item["variable"] for item in result] == [
        "LINEAR_SANDBOX_TOKEN",
        "LINEAR_API_KEY",
    ]


def test_matching_provider_token_environment_is_not_reported_twice():
    """Would fail if one physical credential produced duplicate readiness entries."""
    from ai_dlc.credentials import credential_status

    result = credential_status(
        {
            "credentials": {
                "linear-sandbox": {
                    "description": "Linear sandbox access",
                    "required_by": ["provider.linear"],
                    "source": "environment",
                    "variable": "LINEAR_API_KEY",
                }
            },
            "providers": {"linear": {"kind": "linear"}},
        },
        environ={"LINEAR_API_KEY": "present"},
    )

    assert [item["id"] for item in result] == ["linear-sandbox"]


def test_status_uses_supplied_environment_mapping_without_mutating_process_environment(monkeypatch):
    from ai_dlc.credentials import credential_status

    monkeypatch.delenv("LINEAR_SANDBOX_TOKEN", raising=False)
    config = {
        "credentials": {
            "linear-sandbox": {
                "description": "Linear sandbox access",
                "required_by": ["provider.linear-sandbox"],
                "source": "environment",
                "variable": "LINEAR_SANDBOX_TOKEN",
            }
        }
    }

    result = credential_status(config, environ={"LINEAR_SANDBOX_TOKEN": "supplied"})

    assert result[0]["present"] is True
    assert "LINEAR_SANDBOX_TOKEN" not in __import__("os").environ


def test_status_is_sorted_by_logical_credential_id():
    from ai_dlc.credentials import credential_status

    result = credential_status(
        {
            "credentials": {
                "zebra": {"description": "Zebra access", "required_by": []},
                "alpha": {"description": "Alpha access", "required_by": []},
            },
            "providers": {"linear": {"token_env": "LINEAR_API_KEY"}},
        },
        environ={},
    )

    assert [item["id"] for item in result] == ["alpha", "provider.linear", "zebra"]
