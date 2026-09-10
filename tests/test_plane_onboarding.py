import json
import tomllib

import httpx
import pytest
import tomli_w
from test_plane_provider import CFG, PlaneHTTP, U
from typer.testing import CliRunner

from ai_dlc.cli import app


@pytest.fixture
def onboarding(tmp_path, monkeypatch):
    from ai_dlc.providers.plane import PlaneProvider
    from ai_dlc.setup import plane_onboarding

    api = PlaneHTTP()
    settings = {
        key: value
        for key, value in CFG.items()
        if key not in {"account_id", "workspace_id", "project_id", "project_key", "statuses"}
    }
    path = tmp_path / "ai-dlc.toml"
    path.write_text(
        "# Authored configuration\n"
        + tomli_w.dumps(
            {"schema": 4, "roles": {"tracker": "local"}, "providers": {"local": settings}}
        )
    )
    monkeypatch.setattr(
        plane_onboarding,
        "make_provider",
        lambda settings, environ: PlaneProvider(
            settings,
            selected=False,
            environ={"PLANE_TEST_TOKEN": "secret-sentinel"},
            transport=httpx.MockTransport(api),
        ),
    )
    return tmp_path, path, api


def invoke(root, *args):
    return CliRunner().invoke(app, ["provider", "connect", "local", "--root", str(root), *args])


def selectors():
    return [
        value
        for key, name in {
            "project": "Fixture",
            "open": "Todo",
            "in_progress": "Doing",
            "closed": "Done",
            "cancelled": "Cancelled",
        }.items()
        for value in ("--select", key + "=" + name)
    ]


def test_common_plane_plan_save_apply_preserves_authored_local_config(onboarding):
    root, path, api = onboarding
    before = path.read_bytes()
    found = invoke(root)
    assert found.exit_code == 0, found.output
    assert json.loads(found.output)["discovery"]["account"]["id"] == U[0]
    planned = invoke(root, *selectors(), "--plan-file", ".ai-dlc/local/plane.json")
    assert planned.exit_code == 0, planned.output
    assert path.read_bytes() == before
    applied = invoke(root, "--plan-file", ".ai-dlc/local/plane.json", "--apply")
    assert applied.exit_code == 0, applied.output
    saved = tomllib.loads(path.read_text())["providers"]["local"]
    assert saved["account_id"] == U[0] and saved["project_id"] == U[2]
    assert saved["statuses"]["cancelled"] == U[6]
    assert path.read_text().startswith("# Authored configuration\n")
    assert (
        not api.writes and "secret-sentinel" not in planned.output + found.output + applied.output
    )


@pytest.mark.parametrize("damage", ["account", "state", "project", "authored"])
def test_common_plane_stale_plan_refuses_without_overwriting(onboarding, damage):
    root, path, api = onboarding
    assert invoke(root, *selectors(), "--plan-file", ".ai-dlc/local/plane.json").exit_code == 0
    if damage == "account":
        api.user = U[9]
    if damage == "state":
        api.states[2]["group"] = "cancelled"
    if damage == "project":
        api.project["workspace"] = U[9]
    if damage == "authored":
        path.write_text(path.read_text() + "\n# Later authored comment\n")
    before = path.read_bytes()
    result = invoke(root, "--plan-file", ".ai-dlc/local/plane.json", "--apply")
    assert result.exit_code != 0
    assert path.read_bytes() == before and not api.writes


def test_plane_is_optional_when_other_trackers_are_selected(tmp_path):
    from ai_dlc.providers import Registry

    config = {
        "providers": {
            "plane": {"kind": "plane"},
            "personal": {"kind": "github-issues", "repository": "fixture/repo"},
            "work": {"kind": "jira-cloud"},
        }
    }
    registry = Registry(config, root=tmp_path, environ={})
    assert registry.get("personal") is not None
    assert registry.get("work") is not None
    assert "plane" not in registry.cache


def test_selected_plane_renders_packaged_guide(tmp_path):
    from ai_dlc.harness.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text(
        tomli_w.dumps(
            {
                "schema": 4,
                "roles": {"tracker": "local", "agent-client": ["codex"]},
                "providers": {"local": CFG},
                "agents": {"servers": []},
            }
        )
    )
    render_agents(tmp_path, apply=True)
    assert (tmp_path / ".ai-dlc/providers/plane.md").is_file()
    assert "providers/plane.md" in (tmp_path / "AGENTS.md").read_text()
