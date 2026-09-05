from __future__ import annotations

from pathlib import Path


def _checks(result: dict, component: str, dimension: str) -> list[dict]:
    return [
        check
        for check in result["checks"]
        if check["component"] == component and check["dimension"] == dimension
    ]


def _linear_config(*, headless: bool = False) -> dict:
    config = {
        "roles": {"tracker": "linear"},
        "providers": {
            "linear": {
                "team_id": "team",
                "token_env": "READINESS_TEST_TOKEN",
                "statuses": {"in_progress": "started", "closed": "completed"},
            }
        },
    }
    if headless:
        config["preferences"] = {"headless": True}
    return config


def test_reports_a_missing_tool_with_an_actionable_next_step(tmp_path: Path):
    """Would fail if an unavailable module executable did not block readiness."""
    from ai_dlc.readiness import inspect_readiness

    result = inspect_readiness(
        tmp_path,
        {"roles": {"specs": "openspec"}},
        environ={},
        probe=lambda argv: {"available": False},
    )

    checks = _checks(result, "openspec", "tool")
    assert checks[0]["status"] == "missing"
    assert checks[0]["reason"]
    assert checks[0]["next_action"]
    assert result["ready"] is False
    assert result["qualification"] == "not-assessed"


def test_reports_missing_component_configuration_separately(tmp_path: Path):
    """Would fail if required provider configuration were mistaken for tool readiness."""
    from ai_dlc.readiness import inspect_readiness

    result = inspect_readiness(
        tmp_path,
        {"roles": {"tracker": "linear"}, "providers": {"linear": {}}},
        environ={"READINESS_TEST_TOKEN": "present"},
        probe=lambda argv: {"available": True},
    )

    checks = _checks(result, "linear", "configuration")
    assert [check["status"] for check in checks] == ["missing", "missing", "missing"]
    assert all(check["next_action"] for check in checks)
    assert result["ready"] is False


def test_reports_an_absent_environment_credential_without_its_value(tmp_path: Path):
    """Would fail if readiness treated an unset credential binding as ready or exposed it."""
    from ai_dlc.readiness import inspect_readiness

    result = inspect_readiness(
        tmp_path,
        _linear_config(),
        environ={},
        probe=lambda argv: {"available": True},
    )

    checks = _checks(result, "linear", "credential")
    assert checks[0]["status"] == "missing"
    assert checks[0]["next_action"]
    assert result["ready"] is False


def test_reports_missing_guidance_without_declaring_the_component_ready(
    tmp_path: Path, monkeypatch
):
    """Would fail if a selected component could pass while its guidance was absent."""
    from ai_dlc import readiness

    monkeypatch.setattr(
        readiness,
        "load_component_catalog",
        lambda root, config: {
            "schema": 1,
            "components": [
                {
                    "id": "synthetic-specs",
                    "roles": ["specs"],
                    "modules": [],
                    "guidance": ["guidance/missing.md"],
                    "required_config": [],
                }
            ],
        },
    )

    result = readiness.inspect_readiness(
        tmp_path,
        {"roles": {"specs": "synthetic-specs"}},
        environ={},
        probe=lambda argv: {"available": True},
    )

    checks = _checks(result, "synthetic-specs", "guidance")
    assert checks[0]["status"] == "missing"
    assert checks[0]["next_action"]
    assert result["ready"] is False


def test_reports_ready_offline_requirements_and_unverified_provider_health(tmp_path: Path):
    """Would fail if offline readiness performed health checks or treated them as blocking."""
    from ai_dlc.readiness import inspect_readiness

    probes: list[list[str]] = []
    result = inspect_readiness(
        tmp_path,
        {"roles": {"specs": "openspec"}},
        environ={},
        probe=lambda argv: probes.append(argv) or {"available": True},
    )

    assert probes == [["openspec"]]
    assert _checks(result, "openspec", "tool")[0]["status"] == "ready"
    assert _checks(result, "openspec", "guidance")[0]["status"] == "ready"
    assert _checks(result, "openspec", "provider-health")[0]["status"] == "unverified"
    assert result["ready"] is True
    assert result["qualification"] == "not-assessed"


def test_reports_headless_desktop_capability_as_blocked(tmp_path: Path):
    """Would fail if headless readiness silently substituted or accepted a desktop module."""
    from ai_dlc.readiness import inspect_readiness

    result = inspect_readiness(
        tmp_path,
        _linear_config(headless=True),
        environ={"READINESS_TEST_TOKEN": "present"},
        probe=lambda argv: {"available": True},
    )

    checks = _checks(result, "linear", "tool")
    assert checks[0]["status"] == "blocked"
    assert "headless" in checks[0]["reason"]
    assert result["ready"] is False
    assert result["qualification"] == "not-assessed"


def test_never_returns_credential_values(tmp_path: Path):
    """Would fail if any readiness field copied a supplied credential value."""
    from ai_dlc.readiness import inspect_readiness

    credential_value = "readiness-credential-value-that-must-not-escape"
    result = inspect_readiness(
        tmp_path,
        _linear_config(),
        environ={"READINESS_TEST_TOKEN": credential_value},
        probe=lambda argv: {"available": True},
    )

    assert result["ready"] is True
    assert credential_value not in repr(result)
