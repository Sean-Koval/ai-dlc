"""Actual Registry/adapter/service matrix; all remote transport is synthetic."""

import copy
import json
from types import SimpleNamespace

import httpx
import pytest
import tomli_w
from test_plane_provider import CFG, CREATE, PlaneHTTP, U

from ai_dlc.config import resolve_runtime
from ai_dlc.providers import Registry
from ai_dlc.providers.github_issues import GitHubIssuesProvider
from ai_dlc.providers.plane import PlaneProvider
from ai_dlc.tracker_migration import apply_tracker_migration, plan_tracker_migration
from ai_dlc.workflow import WorkService


@pytest.fixture(
    params=[
        ("linear", "github-issues"),
        ("linear", "plane"),
        ("github-issues", "plane"),
        ("plane", "github-issues"),
    ]
)
def adapter_move(request, tmp_path, monkeypatch):
    source, target = request.param
    config = {
        "schema": 4,
        "roles": {"tracker": "old", "scm": "github"},
        "scm": {"repository": "source/scm"},
        "providers": {
            "old": {"kind": source},
            "next": copy.deepcopy(CFG)
            if target == "plane"
            else {"kind": "github-issues", "repository": "target/repo", "viewer_id": "expected"},
        },
    }
    (tmp_path / "ai-dlc.toml").write_text(tomli_w.dumps(config))
    directory = tmp_path / ".ai-dlc/work"
    directory.mkdir(parents=True)
    for name in ("one", "unselected"):
        (directory / f"{name}.toml").write_text(
            tomli_w.dumps(
                {
                    "schema": 1,
                    "id": name,
                    "title": name,
                    "scope": "fixture",
                    "requires_spec": False,
                    "spec_reason": "fixture",
                    "acceptance": ["authored"],
                    "reviewed": True,
                    "artifacts": {
                        "tracker": "old-reference",
                        "pr": "https://github.com/source/scm/pull/1",
                    },
                }
            )
        )
    env = {
        name: str(tmp_path / name)
        for name in ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME")
    }
    registry = Registry(config, root=tmp_path, environ=env)
    remote = {"state": "open", "identity": "expected", "calls": []}
    if target == "plane":
        api = PlaneHTTP()
        adapter = PlaneProvider(
            CFG,
            root=tmp_path,
            state_home=tmp_path / "state",
            environ={"PLANE_TEST_TOKEN": "fixture"},
            transport=httpx.MockTransport(api),
        )
        reference = adapter.invoke("create", CREATE)["url"]
        api.writes.clear()
        remote["api"] = api
    else:

        def run(args, **kwargs):
            remote["calls"].append(args)
            if args[1:3] == ["api", "graphql"]:
                body = {"data": {"viewer": {"id": remote["identity"]}}}
            else:
                assert args[1:4] == ["issue", "view", "42"]
                state = remote["state"]
                body = {
                    "id": "node42",
                    "number": 42,
                    "url": "https://github.com/target/repo/issues/42",
                    "state": "OPEN" if state == "open" else "CLOSED",
                    "stateReason": {"closed": "COMPLETED", "cancelled": "NOT_PLANNED"}.get(state),
                    "body": "authored",
                }
            return SimpleNamespace(returncode=0, stdout=json.dumps(body), stderr="")

        monkeypatch.setattr("ai_dlc.providers.github_issues.subprocess.run", run)
        adapter = GitHubIssuesProvider(config["providers"]["next"], environ={})
        reference = "42"
    registry.register("next", adapter, operations=["capabilities"])
    return tmp_path, env, registry, remote, reference, target


def preview(move, mode="selected"):
    root, env, registry, _, reference, _ = move
    return plan_tracker_migration(
        root,
        "next",
        mode=mode,
        work_ids=["one"] if mode == "selected" else [],
        mappings={"one": reference} if mode == "selected" else {},
        environ=env,
        registry=registry,
    )


@pytest.mark.parametrize("state", ["open", "closed", "cancelled", "unknown"])
def test_real_adapter_substitution_preserves_state_gates_and_unselected_bytes(adapter_move, state):
    root, env, registry, remote, _, kind = adapter_move
    remote["state"] = state
    if kind == "plane":
        remote["api"].items[0]["state"] = CFG["statuses"].get(state, U[10])
    before = (root / ".ai-dlc/work/unselected.toml").read_bytes()
    planned = preview(adapter_move)
    assert planned["evidence"]["targets"]["one"]["state"] == state
    assert planned["evidence"]["targets"]["one"]["completion_evidence"] is False
    assert (
        apply_tracker_migration(root, planned, environ=env, registry=registry)["status"]
        == "applied"
    )
    service = WorkService(
        root,
        resolve_runtime(root, environ=env).values,
        state_path=root / "work-state",
        registry=registry,
    )
    work = service.load("one")
    assert work["providers"]["tracker"] == "next"
    assert work["providers"]["scm"] == "github"
    assert not work.get("completed", False)
    assert (root / ".ai-dlc/work/unselected.toml").read_bytes() == before
    if kind == "plane":
        assert remote["api"].writes == []


def test_real_adapter_default_switch_needs_no_remote_reads(adapter_move):
    root, env, registry, remote, _, _ = adapter_move
    planned = preview(adapter_move, "default-only")
    assert planned["evidence"]["capabilities"]["status"] == "not-inspected"
    assert (
        apply_tracker_migration(root, planned, environ=env, registry=registry)["status"]
        == "applied"
    )
    assert remote["calls"] == []
    assert (
        WorkService(
            root,
            resolve_runtime(root, environ=env).values,
            state_path=root / "work-state",
            registry=registry,
        ).load("one")["providers"]["tracker"]
        == "old"
    )


def test_real_adapter_identity_drift_refuses_local_apply(adapter_move):
    root, env, registry, remote, _, kind = adapter_move
    planned = preview(adapter_move)
    before = (root / ".ai-dlc/work/one.toml").read_bytes()
    if kind == "plane":
        remote["api"].user = U[10]
    else:
        remote["identity"] = "foreign"
    with pytest.raises(ValueError):
        apply_tracker_migration(root, planned, environ=env, registry=registry)
    assert (root / ".ai-dlc/work/one.toml").read_bytes() == before


def test_unowned_plane_target_is_not_silently_adopted(adapter_move):
    _, _, _, remote, _, kind = adapter_move
    if kind != "plane":
        pytest.skip("Plane ownership boundary only")
    remote["api"].items[0]["external_source"] = "human"
    with pytest.raises(ValueError, match="correlation"):
        preview(adapter_move)
