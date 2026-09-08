import json
import tomllib

import pytest
import tomli_w
from test_jira_provider import Jira
from typer.testing import CliRunner

from ai_dlc.cli import app


@pytest.fixture
def onboarding(tmp_path, monkeypatch):
    from ai_dlc import jira_onboarding
    from ai_dlc.providers.jira_cloud import JiraCloudProvider

    jira = Jira()
    settings = {
        key: value
        for key, value in jira.config.items()
        if key
        not in {
            "account_id",
            "project_id",
            "project_key",
            "issue_type_id",
            "statuses",
            "resolutions",
        }
    }
    path = tmp_path / "ai-dlc.toml"
    path.write_text(
        "# authored\n"
        + tomli_w.dumps(
            {"schema": 4, "roles": {"tracker": "work"}, "providers": {"work": settings}}
        )
    )
    monkeypatch.setattr(
        jira_onboarding,
        "make_provider",
        lambda settings, environ: JiraCloudProvider(
            settings,
            client=jira.client,
            environ={"JIRA_TOKEN": "credential-sentinel"},
            selected=False,
        ),
    )
    return tmp_path, path, jira


def invoke(root, *args):
    return CliRunner().invoke(app, ["provider", "connect", "work", "--root", str(root), *args])


def selectors():
    values = {
        "project": "Work",
        "issue_type": "100:10",
        "open": "Open",
        "in_progress": "In Progress",
        "closed": "Done",
        "cancelled": "Cancelled",
        "closed_resolution": "Done",
        "cancelled_resolution": "Won't do",
    }
    return [value for key, choice in values.items() for value in ("--select", f"{key}={choice}")]


def test_common_jira_onboarding_discovers_and_applies_only_local_reviewed_ids(onboarding):
    root, path, jira = onboarding
    before = path.read_bytes()
    discovered = invoke(root)
    assert discovered.exit_code == 0, discovered.output
    assert json.loads(discovered.output)["discovery"]["account"]["id"] == "account-1"
    planned = invoke(root, *selectors(), "--plan-file", ".ai-dlc/local/jira.json")
    assert planned.exit_code == 0, planned.output
    assert path.read_bytes() == before
    applied = invoke(root, "--plan-file", ".ai-dlc/local/jira.json", "--apply")
    assert applied.exit_code == 0, applied.output
    config = tomllib.loads(path.read_text())["providers"]["work"]
    assert (
        config["account_id"] == "account-1"
        and config["project_id"] == "100"
        and config["issue_type_id"] == "10"
    )
    assert config["statuses"]["closed"] == "3" and config["resolutions"]["cancelled"] == ["2000"]
    assert path.read_text().startswith("# authored\n")
    assert jira.writes() == []
    assert "credential-sentinel" not in discovered.output + planned.output + applied.output


@pytest.mark.parametrize("damage", ["account", "required", "overlap"])
def test_onboarding_refuses_stale_identity_fields_and_overlapping_mappings(onboarding, damage):
    root, path, jira = onboarding
    args = selectors()
    if damage == "overlap":
        args = [
            arg.replace("cancelled_resolution=Won't do", "cancelled_resolution=Done")
            for arg in args
        ]
    planned = invoke(root, *args, "--plan-file", ".ai-dlc/local/jira.json")
    before = path.read_bytes()
    if damage == "overlap":
        assert planned.exit_code != 0
    else:
        assert planned.exit_code == 0, planned.output
        if damage == "account":
            jira.account = "other"
        else:
            from test_jira_provider import field

            jira.fields.append(field("customfield_1", required=True))
        assert invoke(root, "--plan-file", ".ai-dlc/local/jira.json", "--apply").exit_code != 0
    assert path.read_bytes() == before and jira.writes() == []


def test_onboarding_requests_only_projects_where_creation_is_available(onboarding):
    root, _, jira = onboarding
    assert invoke(root).exit_code == 0
    projects = [r for r in jira.requests if r.url.path.endswith("/project/search")]
    assert projects and all(r.url.params.get("action") == "create" for r in projects)


def test_selected_jira_alias_renders_packaged_guidance_without_native_auth(tmp_path):
    from test_jira_provider import SETTINGS

    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text(
        tomli_w.dumps(
            {
                "schema": 4,
                "roles": {"tracker": "work", "agent-client": ["codex"]},
                "providers": {"work": SETTINGS},
                "agents": {"servers": []},
            }
        )
    )
    render_agents(tmp_path, apply=True)
    guide = tmp_path / ".ai-dlc/providers/jira-cloud.md"
    assert guide.is_file()
    assert "personal_scoped_token_basic" in guide.read_text()
    assert "providers/jira-cloud.md" in (tmp_path / "AGENTS.md").read_text()


def test_common_plan_refuses_required_empty_multiselect_before_saving(onboarding):
    from test_jira_provider import field

    root, path, jira = onboarding
    metadata = field("customfield_1", "array", required=True)
    metadata["schema"]["items"] = "option"
    metadata["allowedValues"] = [{"id": "5", "value": "Reviewed"}]
    jira.fields.append(metadata)
    path.write_text(path.read_text() + "\n[providers.work.create_fields]\ncustomfield_1 = []\n")
    before = path.read_bytes()
    result = invoke(root, *selectors(), "--plan-file", ".ai-dlc/local/jira.json")
    assert result.exit_code != 0
    assert path.read_bytes() == before
    assert not (root / ".ai-dlc/local/jira.json").exists()
    assert jira.writes() == []
