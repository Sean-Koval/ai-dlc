"""Default onboarding catches missing association, duplicate creation and silent opt-outs."""

import copy
import json
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.github_onboarding import connect_github_provider
from ai_dlc.providers.github_issues import GitHubIssuesProvider


@pytest.fixture
def setup(tmp_path, monkeypatch):
    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[project]\nname="App"\n[scm]\nrepository="acme/app"\n[roles]\ntracker="linear"\n'
    )
    env = {f"XDG_{name}_HOME": str(tmp_path / name) for name in ("CONFIG", "STATE", "CACHE")}
    data = {
        "projects": [],
        "creates": 0,
        "links": set(),
        "viewer": "U1",
        "denied": False,
        "lost": False,
    }
    repo = {
        "id": "R1",
        "nameWithOwner": "acme/app",
        "hasIssuesEnabled": True,
        "viewerPermission": "ADMIN",
    }
    fields = [
        {
            "id": "F1",
            "name": "Status",
            "__typename": "ProjectV2SingleSelectField",
            "options": [
                {"id": "todo", "name": "Todo"},
                {"id": "doing", "name": "In Progress"},
                {"id": "done", "name": "Done"},
            ],
        }
    ]
    data["fields"] = fields

    def query(self, query, variables):
        if "DiscoveryViewer" in query:
            return {"viewer": {"id": data["viewer"], "login": "alice"}}
        if "DiscoveryRepositories" in query:
            return {
                "viewer": {
                    "repositories": {
                        "nodes": [copy.deepcopy(repo)],
                        "pageInfo": {"hasNextPage": False},
                    }
                }
            }
        if "DiscoveryRepository" in query:
            return {"repository": copy.deepcopy(repo)}
        if "DiscoveryProjects" in query:
            if data["denied"]:
                raise RuntimeError("secret denied")
            return {
                "repositoryOwner": {
                    "id": "O1",
                    "login": "acme",
                    "projectsV2": {
                        "nodes": copy.deepcopy(data["projects"]),
                        "pageInfo": {"hasNextPage": False},
                    },
                }
            }
        if "ProjectSetupOwner" in query:
            return {"repositoryOwner": {"id": "O1", "login": "acme"}}
        if "CreateDefaultProject" in query:
            assert variables == {"owner": "O1", "repository": "R1", "title": "App"}
            data["creates"] += 1
            project = {
                "id": "P1",
                "title": "App",
                "number": 1,
                "url": "https://github.com/orgs/acme/projects/1",
            }
            data["projects"].append(project)
            data["links"].add("P1")
            if data["lost"]:
                raise TimeoutError("lost response")
            return {"createProjectV2": {"projectV2": copy.deepcopy(project)}}
        if "LinkDefaultProject" in query:
            assert variables["repository"] == "R1"
            data["links"].add(variables["project"])
            return {"linkProjectV2ToRepository": {"repository": {"id": "R1"}}}
        if "ProjectFields" in query:
            return {
                "node": {
                    "id": variables["project"],
                    "__typename": "ProjectV2",
                    "fields": {"nodes": copy.deepcopy(fields), "pageInfo": {"hasNextPage": False}},
                }
            }
        raise AssertionError(query)

    monkeypatch.setattr(GitHubIssuesProvider, "graphql", query)

    def connect(**kwargs):
        return connect_github_provider(tmp_path, alias="github-issues", environ=env, **kwargs)

    return tmp_path, data, connect


def test_default_preview_infers_repository_and_proposes_creation_without_mutation(setup):
    root, remote, connect = setup
    before = (root / "ai-dlc.toml").read_bytes()
    result = connect(plan_file=Path(".ai-dlc/local/project.json"))
    assert result["plan"]["kind"] == "github-project-setup"
    assert result["plan"]["repository"] == "acme/app"
    assert result["plan"]["title"] == "App"
    assert result["plan"]["project"] is None
    assert remote["creates"] == 0
    assert (root / "ai-dlc.toml").read_bytes() == before


def test_default_apply_creates_links_and_configures_project(setup):
    root, remote, connect = setup
    plan = Path(".ai-dlc/local/project.json")
    connect(plan_file=plan)
    result = connect(apply=True, plan_file=plan)
    settings = tomllib.loads((root / "ai-dlc.toml").read_text())
    assert result["status"] == "applied"
    assert settings["providers"]["github-issues"]["project"] == {
        "id": "P1",
        "status_field_id": "F1",
        "statuses": {"open": "todo", "in_progress": "doing", "closed": "done"},
    }
    assert settings["roles"]["tracker"] == "linear"
    assert remote["creates"] == 1 and remote["links"] == {"P1"}
    connect(plan_file=Path(".ai-dlc/local/repeat.json"))
    connect(apply=True, plan_file=Path(".ai-dlc/local/repeat.json"))
    assert remote["creates"] == 1


def test_existing_matching_project_is_reused_and_linked(setup):
    root, remote, connect = setup
    remote["projects"] = [
        {"id": "P2", "title": "App", "number": 2, "url": "https://github.com/orgs/acme/projects/2"}
    ]
    plan = Path(".ai-dlc/local/project.json")
    connect(plan_file=plan)
    connect(apply=True, plan_file=plan)
    assert remote["creates"] == 0 and remote["links"] == {"P2"}
    assert (
        tomllib.loads((root / "ai-dlc.toml").read_text())["providers"]["github-issues"]["project"][
            "id"
        ]
        == "P2"
    )


def test_default_never_silently_downgrades_when_projects_denied(setup):
    _, remote, connect = setup
    remote["denied"] = True
    with pytest.raises(RuntimeError, match="Project"):
        connect()
    result = connect(issues_only=True)
    assert "project" not in result["plan"]["patch"]


def test_uncertain_creation_cannot_be_blindly_retried(setup):
    root, remote, connect = setup
    plan = Path(".ai-dlc/local/project.json")
    connect(plan_file=plan)
    remote["lost"] = True
    with pytest.raises(RuntimeError, match="uncertain"):
        connect(apply=True, plan_file=plan)
    remote["projects"].clear()  # Remote list may lag a successful create.
    with pytest.raises(RuntimeError, match="uncertain"):
        connect(apply=True, plan_file=plan)
    assert remote["creates"] == 1
    assert "providers" not in tomllib.loads((root / "ai-dlc.toml").read_text())


def test_retry_after_status_discovery_failure_reuses_created_project(setup):
    _root, remote, connect = setup
    plan = Path(".ai-dlc/local/project.json")
    connect(plan_file=plan)
    remote["fields"][0]["options"][1]["name"] = "Custom doing"
    with pytest.raises(ValueError, match="selection|mapping"):
        connect(apply=True, plan_file=plan)
    remote["fields"][0]["options"][1]["name"] = "In Progress"
    connect(apply=True, plan_file=plan)
    assert remote["creates"] == 1


@pytest.mark.parametrize("change", ["config", "viewer", "duplicate"])
def test_creation_plan_drift_refused_before_create(setup, change):
    root, remote, connect = setup
    plan = Path(".ai-dlc/local/project.json")
    connect(plan_file=plan)
    if change == "config":
        with (root / "ai-dlc.toml").open("a") as f:
            f.write("# edit\n")
    elif change == "viewer":
        remote["viewer"] = "U2"
    else:
        remote["projects"] = [
            {
                "id": f"P{i}",
                "title": "App",
                "number": i,
                "url": f"https://github.com/orgs/acme/projects/{i}",
            }
            for i in (1, 2)
        ]
    with pytest.raises(ValueError, match="changed|drift|ambiguous"):
        connect(apply=True, plan_file=plan)
    assert remote["creates"] == 0


def test_cli_explicit_issues_only_works_without_project_permission(setup, monkeypatch):
    root, remote, _ = setup
    remote["denied"] = True
    for name in ("CONFIG", "STATE", "CACHE"):
        monkeypatch.setenv(f"XDG_{name}_HOME", str(root / name))
    result = CliRunner().invoke(
        app, ["provider", "connect", "github-issues", "--root", str(root), "--issues-only"]
    )
    assert result.exit_code == 0, result.output
    assert "project" not in json.loads(result.output)["plan"]["patch"]


@pytest.mark.parametrize("lost", [True, False])
def test_reauthentication_cannot_duplicate_retained_create(setup, lost):
    _, remote, connect = setup
    first = Path(".ai-dlc/local/first.json")
    connect(plan_file=first)
    remote["lost"] = lost
    if not lost:
        remote["fields"][0]["options"][1]["name"] = "Custom doing"
    with pytest.raises((RuntimeError, ValueError)):
        connect(apply=True, plan_file=first)
    created = copy.deepcopy(remote["projects"])
    remote["projects"].clear()
    remote["viewer"] = "U2"
    remote["fields"][0]["options"][1]["name"] = "In Progress"
    remote["lost"] = False
    second = Path(".ai-dlc/local/second.json")
    connect(plan_file=second)
    if lost:
        with pytest.raises(RuntimeError, match="uncertain"):
            connect(apply=True, plan_file=second)
    else:
        remote["projects"] = created
        connect(apply=True, plan_file=second)
    assert remote["creates"] == 1


def test_final_repository_identity_drift_refuses_link_and_config(setup, monkeypatch):
    root, remote, connect = setup
    plan = Path(".ai-dlc/local/project.json")
    connect(plan_file=plan)
    original = GitHubIssuesProvider.graphql

    def query(self, query, variables):
        result = original(self, query, variables)
        if "DiscoveryRepository" in query and remote["creates"]:
            result["repository"]["id"] = "R2"
        return result

    monkeypatch.setattr(GitHubIssuesProvider, "graphql", query)
    with pytest.raises(ValueError, match="identity changed"):
        connect(apply=True, plan_file=plan)
    assert "providers" not in tomllib.loads((root / "ai-dlc.toml").read_text())


def test_host_capitalization_cannot_bypass_uncertain_creation(setup):
    _, remote, connect = setup
    first = Path(".ai-dlc/local/first.json")
    connect(plan_file=first)
    remote["lost"] = True
    with pytest.raises(RuntimeError, match="uncertain"):
        connect(apply=True, plan_file=first)
    remote["projects"].clear()
    remote["lost"] = False
    second = Path(".ai-dlc/local/second.json")
    connect(host="GitHub.com", plan_file=second)
    with pytest.raises(RuntimeError, match="uncertain"):
        connect(apply=True, plan_file=second)
    assert remote["creates"] == 1
