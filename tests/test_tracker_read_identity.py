"""Real adapters and services with offline HTTP/gh transport fixtures only."""

import json
import re
import tomllib
from types import SimpleNamespace

import httpx
import pytest
import tomli_w

from ai_dlc.providers import Registry
from ai_dlc.providers.github_issues import GitHubIssuesProvider
from ai_dlc.providers.linear import LinearProvider
from ai_dlc.work.tracker_migration import apply_tracker_migration, plan_tracker_migration
from ai_dlc.work.workflow import WorkService


@pytest.fixture(params=["github-issues", "linear"])
def destination(request, monkeypatch):
    kind = request.param
    remote = {"identity": "expected", "closed": False, "requests": []}
    if kind == "github-issues":
        config = {"kind": kind, "repository": "org/repo", "viewer_id": "expected"}

        def run(args, **kwargs):
            remote["requests"].append(args)
            if args[1:3] == ["api", "graphql"]:
                query = json.loads(kwargs["input"])["query"]
                assert re.search(r"viewer\s*\{\s*id\s*\}", query)
                body = {"data": {"viewer": {"id": remote["identity"]}}}
            else:
                assert args[1:4] == ["issue", "view", "42"]
                row = {
                    "id": "ISSUE_42",
                    "number": 42,
                    "url": "https://github.com/org/repo/issues/42",
                    "state": "CLOSED" if remote["closed"] else "OPEN",
                    "stateReason": "COMPLETED" if remote["closed"] else None,
                    "body": "fixture",
                }
                body = {key: row[key] for key in args[args.index("--json") + 1].split(",")}
            return SimpleNamespace(returncode=0, stdout=json.dumps(body), stderr="")

        monkeypatch.setattr("ai_dlc.providers.github_issues.subprocess.run", run)
        adapter = GitHubIssuesProvider(config)
    else:
        config = {"kind": kind, "team_id": "expected"}

        def handle(request):
            payload = json.loads(request.content)
            remote["requests"].append(payload)
            assert payload["variables"] == {"id": "42"}
            assert payload["query"].startswith("query")
            issue = {
                "id": "42",
                "url": "https://linear.app/org/issue/TEAM-42",
                "description": "fixture",
                "state": {"id": "todo", "name": "Todo", "type": "unstarted"},
            }
            # GraphQL returns only selected fields: an unrequested team cannot
            # accidentally make this fixture establish the identity guarantee.
            if re.search(r"team\s*\{\s*id\s*\}", payload["query"]):
                issue["team"] = {"id": remote["identity"]}
            return httpx.Response(200, json={"data": {"issue": issue}})

        client = httpx.Client(transport=httpx.MockTransport(handle))
        adapter = LinearProvider(config, client=client, environ={"LINEAR_API_KEY": "fixture"})
    yield config, adapter, remote
    if kind == "linear":
        adapter.client.close()


def test_read_rejects_wrong_configured_identity(destination):
    _, adapter, remote = destination
    remote["identity"] = "foreign"
    with pytest.raises(ValueError, match="identity mismatch"):
        adapter.invoke("read", {"reference": "42"})


@pytest.mark.parametrize("identity", [None, "", 42])
def test_read_refuses_missing_or_invalid_identity_evidence(destination, identity):
    _, adapter, remote = destination
    remote["identity"] = identity
    with pytest.raises(ValueError, match="identity mismatch"):
        adapter.invoke("read", {"reference": "42"})


def test_read_verifies_correct_identity_and_preserves_unconfigured_legacy_read(destination):
    config, adapter, remote = destination
    assert adapter.invoke("read", {"reference": "42"})["id"] == "42"
    config.pop("viewer_id" if config["kind"] == "github-issues" else "team_id")
    remote["identity"] = "foreign"
    remote["requests"].clear()
    assert adapter.invoke("read", {"reference": "42"})["state"] == "open"
    assert len(remote["requests"]) == 1


@pytest.fixture
def project(tmp_path, destination):
    config, adapter, remote = destination
    root = tmp_path / "project"
    directory = root / ".ai-dlc/work"
    directory.mkdir(parents=True)
    (root / "ai-dlc.toml").write_text(
        tomli_w.dumps(
            {
                "schema": 4,
                "roles": {"tracker": "old", "scm": "github"},
                "providers": {
                    "old": {"kind": "linear", "team_id": "source"},
                    "destination": config,
                },
            }
        )
    )
    work = {
        "schema": 1,
        "id": "one",
        "title": "One",
        "scope": "fixture",
        "requires_spec": False,
        "spec_reason": "fixture",
        "acceptance": ["done"],
        "reviewed": True,
        "providers": {"tracker": "old", "scm": "github"},
        "artifacts": {"tracker": "SOURCE-1", "pr": "pull/7"},
    }
    (directory / "one.toml").write_text(tomli_w.dumps(work))
    registry = Registry()
    registry.register("destination", adapter, operations=("capabilities",))
    env = {
        key: str(tmp_path / key) for key in ["XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"]
    }
    return root, {"registry": registry, "environ": env}, remote


def snapshot(root):
    return {
        str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


def preview(root, options):
    return plan_tracker_migration(
        root, "destination", mode="selected", work_ids=["one"], mappings={"one": "42"}, **options
    )


def test_migration_preview_refuses_wrong_adapter_identity_without_local_writes(project):
    root, options, remote = project
    remote["identity"] = "foreign"
    before = snapshot(root)
    with pytest.raises(ValueError, match="identity mismatch"):
        preview(root, options)
    assert snapshot(root) == before


def test_migration_apply_rechecks_adapter_identity_before_local_writes(project):
    root, options, remote = project
    planned = preview(root, options)
    remote["identity"] = "foreign"
    before = snapshot(root)
    with pytest.raises(ValueError, match="identity mismatch"):
        apply_tracker_migration(root, planned, **options)
    assert snapshot(root) == before


def test_migration_with_correct_adapter_identity_records_canonical_target(project):
    root, options, _ = project
    before = snapshot(root)
    planned = preview(root, options)
    assert snapshot(root) == before
    assert planned["mappings"]["one"]["target"]["id"] == "42"
    result = apply_tracker_migration(root, planned, **options)
    assert result["status"] == "applied"
    updated = tomllib.loads((root / ".ai-dlc/work/one.toml").read_text())
    assert updated["providers"] == {"tracker": "destination", "scm": "github"}
    assert updated["artifacts"] == {"tracker": "42", "pr": "pull/7"}
    assert (root / "ai-dlc.toml").read_bytes() == before["ai-dlc.toml"]


@pytest.mark.parametrize("destination", ["github-issues"], indirect=True)
def test_already_closed_issue_only_finish_rechecks_viewer_even_after_success(project, destination):
    _, _, remote = destination
    root, options, _ = project
    apply_tracker_migration(root, preview(root, options), **options)

    class SCM:
        def merged(self, reference):
            return {"sha": "merge", "pr": {}}

        def ci(self, sha):
            return {"sha": sha, "run_id": 1, "receipt": {}}

    options["registry"].register("github", SCM())
    app = WorkService(
        root,
        tomllib.loads((root / "ai-dlc.toml").read_text()),
        state_path=root.parent / "state",
        registry=options["registry"],
    )
    remote["closed"] = True
    remote["identity"] = "foreign"
    before = snapshot(root)
    with pytest.raises(ValueError, match="viewer identity mismatch"):
        app.finish("one")
    assert snapshot(root) == before
    remote["identity"] = "expected"
    assert app.finish("one")["status"] == "completed"
    remote["identity"] = "foreign"
    with pytest.raises(ValueError, match="viewer identity mismatch"):
        app.finish("one")
