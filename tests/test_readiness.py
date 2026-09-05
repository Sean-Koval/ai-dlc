from __future__ import annotations

from pathlib import Path

import pytest


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


def test_reports_missing_guidance_without_declaring_the_component_ready(tmp_path: Path):
    """Would fail if a selected component could pass while its guidance was absent."""
    import hashlib
    import json

    from ai_dlc import readiness
    from ai_dlc.components import load_component_catalog

    manifest = tmp_path / "component.json"
    manifest.write_text(
        json.dumps(
            {
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
            }
        )
    )
    config = {
        "roles": {"specs": "synthetic-specs"},
        "providers": {
            "synthetic-specs": {
                "component_manifest": "component.json",
                "component_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            }
        },
    }
    with pytest.raises(ValueError, match="existing regular file"):
        load_component_catalog(tmp_path, config)

    result = readiness.inspect_readiness(
        tmp_path,
        config,
        environ={},
        probe=lambda argv: {"available": True},
    )

    checks = _checks(result, "synthetic-specs", "guidance")
    assert checks[0]["status"] == "missing"
    assert checks[0]["next_action"]
    assert result["ready"] is False

    (tmp_path / "guidance").mkdir()
    (tmp_path / "guidance/missing.md").write_text("# Restored instructions\n")
    restored = readiness.inspect_readiness(
        tmp_path, config, environ={}, probe=lambda argv: {"available": True}
    )
    assert restored["ready"] is True


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


@pytest.mark.parametrize("client", ["codex", "claude-code"])
def test_selected_harness_requires_delivered_provider_index(tmp_path, client):
    """Source instructions alone must not satisfy selected harness delivery."""
    from ai_dlc.agents import render_agents
    from ai_dlc.config import load_project
    from ai_dlc.readiness import inspect_readiness

    (tmp_path / "ai-dlc.toml").write_text(
        f'schema=4\n[roles]\nspecs="openspec"\nagent-client=["{client}"]\n'
    )
    config = load_project(tmp_path)

    def inspect():
        return inspect_readiness(tmp_path, config, environ={}, probe=lambda _: {"available": True})

    missing = inspect()
    assert missing["ready"] is False
    assert any(c["dimension"] == "guidance" and c["status"] == "missing" for c in missing["checks"])
    render_agents(tmp_path, apply=True)
    assert inspect()["ready"] is True
    if client == "claude-code":
        (tmp_path / "CLAUDE.md").unlink()
    else:
        (tmp_path / ".ai-dlc/providers/openspec.md").unlink()
    assert inspect()["ready"] is False


def test_unknown_harness_is_explicitly_blocked(tmp_path):
    """An unimplemented harness must not inherit supported-client guidance readiness."""
    from ai_dlc.readiness import inspect_readiness

    result = inspect_readiness(
        tmp_path,
        {"roles": {"specs": "openspec", "agent-client": ["unknown"]}},
        environ={},
        probe=lambda _: {"available": True},
    )
    assert not result["ready"]
    assert any(c["dimension"] == "guidance" and c["status"] == "blocked" for c in result["checks"])


def test_duplicate_managed_sections_cannot_claim_guidance_readiness(tmp_path):
    """A conflicting duplicate index must require repair even if one section is intact."""
    from ai_dlc.agents import render_agents
    from ai_dlc.config import load_project
    from ai_dlc.readiness import inspect_readiness

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nspecs="openspec"\nagent-client=["codex"]\n'
    )
    render_agents(tmp_path, apply=True)
    path = tmp_path / "AGENTS.md"
    path.write_text(path.read_text() * 2)
    result = inspect_readiness(
        tmp_path, load_project(tmp_path), environ={}, probe=lambda _: {"available": True}
    )
    assert not result["ready"]


def test_personal_only_provider_has_actionable_delivery_gap_without_changing_project(tmp_path):
    """Missing personal provider delivery must not prescribe a render that cannot fix it."""
    from ai_dlc.agents import render_agents
    from ai_dlc.readiness import inspect_readiness

    project = tmp_path / "ai-dlc.toml"
    project.write_text('schema=4\n[roles]\nagent-client=["codex"]\n')
    render_agents(tmp_path, apply=True)
    before = project.read_bytes()
    result = inspect_readiness(
        tmp_path,
        {"roles": {"specs": "openspec", "agent-client": ["codex"]}},
        environ={},
        probe=lambda _: {"available": True},
    )
    gap = _checks(result, "codex", "guidance")[0]
    assert gap["status"] == "missing"
    assert "ai-dlc.toml" in gap["next_action"]
    assert project.read_bytes() == before
