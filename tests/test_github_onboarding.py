import copy
import json
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.providers.github_issues import GitHubIssuesProvider


@pytest.fixture
def checkout(tmp_path):
    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n# authored\n[roles]\ntracker="linear"\n[providers.linear]\ntoken_env="KEY"\n'
    )
    return tmp_path


@pytest.fixture
def remote(monkeypatch):
    data = {
        "viewer": {"id": "U1", "login": "alice"},
        "repository": {
            "id": "R1",
            "nameWithOwner": "acme/app",
            "hasIssuesEnabled": True,
            "viewerPermission": "WRITE",
        },
        "projects": [
            {
                "id": "P1",
                "title": "Delivery",
                "number": 2,
                "url": "https://github.com/orgs/acme/projects/2",
            }
        ],
        "fields": [
            {
                "id": "F1",
                "name": "Status",
                "__typename": "ProjectV2SingleSelectField",
                "options": [
                    {"id": str(i), "name": n} for i, n in enumerate(["Todo", "Doing", "Done"])
                ],
            }
        ],
    }

    def query(self, query, variables):
        if "DiscoveryViewer" in query:
            return {"viewer": copy.deepcopy(data["viewer"])}
        if "DiscoveryRepository" in query:
            return {"repository": copy.deepcopy(data["repository"])}
        if "DiscoveryProjects" in query:
            if data.get("denied"):
                raise RuntimeError("missing required scopes [read:project] secret-token")
            return {
                "repositoryOwner": {
                    "login": variables["owner"],
                    "projectsV2": {
                        "nodes": copy.deepcopy(data["projects"]),
                        "pageInfo": {"hasNextPage": False},
                    },
                }
            }
        if "ProjectFields" in query:
            return {
                "node": {
                    "id": "P1",
                    "__typename": "ProjectV2",
                    "fields": {
                        "nodes": copy.deepcopy(data["fields"]),
                        "pageInfo": {"hasNextPage": False},
                    },
                }
            }
        raise AssertionError(query)

    monkeypatch.setattr(GitHubIssuesProvider, "graphql", query)
    return data


def connect(root, **kwargs):
    from ai_dlc.github_onboarding import connect_github_provider

    return connect_github_provider(root, alias="tickets", environ={}, **kwargs)


def selections():
    return {
        "repository": "acme/app",
        "project": "Delivery",
        "status_field": "Status",
        "open": "Todo",
        "in_progress": "Doing",
        "closed": "Done",
    }


def test_named_project_plan_and_apply_preserve_authored_config(checkout, remote):
    before = (checkout / "ai-dlc.toml").read_text()
    result = connect(checkout, **selections(), plan_file=Path(".ai-dlc/local/github.json"))
    assert (checkout / "ai-dlc.toml").read_text() == before
    assert result["plan"]["patch"]["project"] == {
        "id": "P1",
        "status_field_id": "F1",
        "statuses": {"open": "0", "in_progress": "1", "closed": "2"},
    }
    assert result["plan"]["patch"]["viewer_id"] == "U1"
    assert (
        connect(checkout, apply=True, plan_file=Path(".ai-dlc/local/github.json"))["status"]
        == "applied"
    )
    text = (checkout / "ai-dlc.toml").read_text()
    assert text.startswith(before)
    config = tomllib.loads(text)
    assert config["roles"]["tracker"] == "linear"
    assert config["providers"]["linear"] == {"token_env": "KEY"}
    assert config["providers"]["tickets"]["repository"] == "acme/app"


@pytest.mark.parametrize("changed", ["viewer", "repository", "project", "field", "config", "work"])
def test_saved_plan_refuses_drift(checkout, remote, changed):
    path = Path(".ai-dlc/local/github.json")
    connect(checkout, **selections(), plan_file=path)
    if changed in {"viewer", "repository"}:
        remote[changed]["id"] = "OTHER"
    elif changed == "project":
        remote["projects"][0]["title"] = "Renamed"
    elif changed == "field":
        remote["fields"][0]["options"][0]["name"] = "Renamed"
    elif changed == "config":
        with (checkout / "ai-dlc.toml").open("a") as stream:
            stream.write("# new author edit\n")
    else:
        work = checkout / ".ai-dlc/work"
        work.mkdir()
        (work / "new.toml").write_text('id="new"\n')
    before = (checkout / "ai-dlc.toml").read_bytes()
    with pytest.raises((ValueError, RuntimeError), match="changed|drift|match|available|selection"):
        connect(checkout, apply=True, plan_file=path)
    assert (checkout / "ai-dlc.toml").read_bytes() == before


def test_issues_only_does_not_require_projects_permission(checkout, remote):
    remote["denied"] = True
    result = connect(checkout, repository="acme/app")
    assert "project" not in result["plan"]["patch"]
    with pytest.raises(RuntimeError, match="read:project") as error:
        connect(checkout, **selections())
    assert "secret-token" not in str(error.value)


def test_discovery_offers_named_fields_and_options(checkout, remote):
    result = connect(checkout, repository="acme/app", project="2")
    assert result["discovery"]["project"]["fields"][0]["name"] == "Status"
    assert result["discovery"]["project"]["fields"][0]["options"][1]["name"] == "Doing"


@pytest.mark.parametrize("part", ["projects", "fields"])
def test_ambiguous_names_refused(checkout, remote, part):
    remote[part].append(copy.deepcopy(remote[part][0]))
    with pytest.raises(ValueError, match="ambiguous"):
        connect(checkout, **selections())


def test_inline_table_and_bound_mapping_are_not_overwritten(checkout, remote):
    path = checkout / "ai-dlc.toml"
    path.write_text(
        'schema=4\n[providers]\ntickets={kind="github-issues", repository="old/repo"}\n'
    )
    with pytest.raises(ValueError, match="representation|safely"):
        connect(checkout, repository="acme/app")
    path.write_text(
        'schema=4\n[roles]\ntracker="tickets"\n[providers.tickets]\nkind="github-issues"\nrepository="old/repo"\n'
    )
    work = checkout / ".ai-dlc/work"
    work.mkdir(parents=True)
    (work / "w.toml").write_text('schema=1\nid="w"\ntitle="W"\n[bindings]\ntracker="1"\n')
    with pytest.raises(ValueError, match="migration|bound"):
        connect(checkout, repository="acme/app")


def test_plan_path_symlink_refused(checkout, remote, tmp_path):
    local = checkout / ".ai-dlc/local"
    local.mkdir(parents=True)
    (local / "link").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        connect(checkout, repository="acme/app", plan_file=Path(".ai-dlc/local/link/plan.json"))


def test_cli_alias_and_linear_alias_guard(checkout, remote):
    with (checkout / "ai-dlc.toml").open("a") as stream:
        stream.write(
            '\n[providers.tickets]\nkind="github-issues"\n[providers.other]\nkind="linear"\n'
        )
    result = CliRunner().invoke(
        app, ["provider", "connect", "tickets", "--root", str(checkout), "--repository", "acme/app"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["provider"] == "tickets"
    before = (checkout / "ai-dlc.toml").read_bytes()
    result = CliRunner().invoke(app, ["provider", "connect", "other", "--root", str(checkout)])
    assert result.exit_code == 2
    assert "alias" in result.output
    assert (checkout / "ai-dlc.toml").read_bytes() == before


def test_github_transport_uses_explicit_environment(monkeypatch):
    import subprocess

    monkeypatch.setenv("GH_TOKEN", "ambient")

    def run(args, **kwargs):
        assert kwargs["env"] == {"PATH": "/test", "GH_HOST": "github.com"}
        return subprocess.CompletedProcess(args, 0, stdout="{}")

    monkeypatch.setattr(subprocess, "run", run)
    GitHubIssuesProvider({"repository": "acme/app"}, environ={"PATH": "/test"}).run(["api", "user"])


def test_repository_discovery_paginates_and_rejects_incomplete_results(
    checkout, remote, monkeypatch
):
    original = GitHubIssuesProvider.graphql

    def query(self, query, variables):
        if "DiscoveryRepositories" not in query:
            return original(self, query, variables)
        after = variables["after"]
        return {
            "viewer": {
                "repositories": {
                    "nodes": [
                        {
                            **remote["repository"],
                            "id": "R1" if after is None else "R2",
                            "nameWithOwner": "acme/" + ("first" if after is None else "second"),
                        }
                    ],
                    "pageInfo": {"hasNextPage": after is None, "endCursor": "cursor"},
                }
            }
        }

    monkeypatch.setattr(GitHubIssuesProvider, "graphql", query)
    result = connect(checkout)
    assert [r["nameWithOwner"] for r in result["discovery"]["repositories"]] == [
        "acme/first",
        "acme/second",
    ]


@pytest.mark.parametrize("project", ["https://github.com/orgs/acme/projects/2", "2"])
def test_project_url_and_number_resolve_names(checkout, remote, project):
    assert (
        connect(checkout, **{**selections(), "project": project})["plan"]["patch"]["project"]["id"]
        == "P1"
    )


def test_existing_plan_is_never_overwritten(checkout, remote):
    plan = Path(".ai-dlc/local/github.json")
    connect(checkout, repository="acme/app", plan_file=plan)
    before = (checkout / plan).read_bytes()
    with pytest.raises(FileExistsError):
        connect(checkout, repository="acme/app", plan_file=plan)
    assert (checkout / plan).read_bytes() == before


def test_stage_replacement_is_retained_without_deleting_authored_file(
    checkout, remote, monkeypatch
):
    import os

    path = Path(".ai-dlc/local/github.json")
    connect(checkout, repository="acme/app", plan_file=path)
    original_fsync = os.fsync

    def fsync(fd):
        original_fsync(fd)
        for stage in checkout.glob(".ai-dlc-github-*/config.toml"):
            stage.rename(stage.with_name("owned-original.toml"))
            stage.write_text("authored replacement")

    monkeypatch.setattr(os, "fsync", fsync)
    before = (checkout / "ai-dlc.toml").read_bytes()
    with pytest.raises(ValueError, match="stage changed"):
        connect(checkout, apply=True, plan_file=path)
    assert (checkout / "ai-dlc.toml").read_bytes() == before
    assert next(checkout.glob(".ai-dlc-github-*/config.toml")).read_text() == "authored replacement"


def test_saved_plan_rejects_additional_execution_options(checkout, remote):
    path = Path(".ai-dlc/local/github.json")
    connect(checkout, repository="acme/app", plan_file=path)
    saved = json.loads((checkout / path).read_text())
    saved["selected"]["apply"] = True
    (checkout / path).write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="Invalid GitHub connection plan"):
        connect(checkout, apply=True, plan_file=path)


def test_unselected_duplicate_option_identity_is_incomplete(checkout, remote):
    remote["fields"][0]["options"].extend(
        [{"id": "EXTRA", "name": "Blocked"}, {"id": "EXTRA", "name": "Paused"}]
    )
    with pytest.raises(ValueError, match="ambiguous|duplicate"):
        connect(checkout, **selections())


@pytest.mark.parametrize("command", ["init", "adopt"])
def test_cli_explicit_tracker_scaffold(tmp_path, command):
    root = tmp_path / "new"
    args = ["project", command]
    args += [str(root)] if command == "init" else ["--root", str(root), "--apply"]
    result = CliRunner().invoke(app, [*args, "--tracker", "github-issues"])
    assert result.exit_code == 0, result.output
    assert tomllib.loads((root / "ai-dlc.toml").read_text())["roles"]["tracker"] == "github-issues"
