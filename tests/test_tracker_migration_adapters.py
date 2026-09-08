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


def test_actual_plane_create_reconciliation_preserves_adapter_ledger(adapter_move):
    from ai_dlc.tracker_targets import plan_tracker_targets, reconcile_tracker_targets

    root, env, registry, remote, _, kind = adapter_move
    if kind != "plane":
        pytest.skip("Plane creation contract only")
    api = remote["api"]
    api.items.clear()
    planned = plan_tracker_targets(
        root,
        "next",
        work_ids=["one"],
        create_work_ids=["one"],
        source="local-records",
        environ=env,
        registry=registry,
    )
    before = (root / ".ai-dlc/work/one.toml").read_bytes()
    api.hide_items = True
    api.lose = "create"
    assert (
        reconcile_tracker_targets(root, planned, environ=env, registry=registry)["status"]
        == "unresolved"
    )
    assert (
        reconcile_tracker_targets(root, planned, environ=env, registry=registry)["status"]
        == "unresolved"
    )
    assert len(api.writes) == 1
    api.hide_items = False
    result = reconcile_tracker_targets(root, planned, environ=env, registry=registry)
    assert result["status"] == "resolved"
    assert len(api.writes) == 1
    assert (root / ".ai-dlc/work/one.toml").read_bytes() == before
    assert (
        apply_tracker_migration(root, result["migration_plan"], environ=env, registry=registry)[
            "status"
        ]
        == "applied"
    )


def test_actual_github_create_reconciliation_keeps_one_issue(adapter_move, monkeypatch):
    from ai_dlc.tracker_targets import plan_tracker_targets, reconcile_tracker_targets

    root, env, registry, _, _, kind = adapter_move
    if kind != "github-issues":
        pytest.skip("GitHub creation contract only")
    remote = {"item": None, "creates": 0, "hidden": True}

    def run(args, **kwargs):
        if args[1:3] == ["api", "graphql"]:
            body = {"data": {"viewer": {"id": "expected"}}}
        elif args[1:3] == ["issue", "list"]:
            body = [] if remote["hidden"] or remote["item"] is None else [remote["item"]]
        elif args[1:3] == ["issue", "create"]:
            remote["creates"] += 1
            remote["item"] = {
                "id": "node42",
                "number": 42,
                "url": "https://github.com/target/repo/issues/42",
                "state": "OPEN",
                "stateReason": None,
                "body": args[args.index("--body") + 1],
            }
            # Fixture accepted the issue before the caller lost its response.
            return SimpleNamespace(returncode=1, stdout="", stderr="response lost")
        else:
            assert args[1:4] == ["issue", "view", "42"]
            body = remote["item"]
        return SimpleNamespace(returncode=0, stdout=json.dumps(body), stderr="")

    monkeypatch.setattr("ai_dlc.providers.github_issues.subprocess.run", run)
    planned = plan_tracker_targets(
        root,
        "next",
        work_ids=["one"],
        create_work_ids=["one"],
        source="local-records",
        environ=env,
        registry=registry,
    )
    for _ in range(2):
        assert (
            reconcile_tracker_targets(root, planned, environ=env, registry=registry)["status"]
            == "unresolved"
        )
    remote["hidden"] = False
    result = reconcile_tracker_targets(root, planned, environ=env, registry=registry)
    assert result["status"] == "resolved" and remote["creates"] == 1
    assert (
        apply_tracker_migration(root, result["migration_plan"], environ=env, registry=registry)[
            "status"
        ]
        == "applied"
    )


def test_actual_adapter_local_write_interruption_preserves_remote_target(adapter_move, monkeypatch):
    import ai_dlc.tracker_migration as migration

    root, env, registry, remote, _, kind = adapter_move
    planned = preview(adapter_move)
    before = (root / ".ai-dlc/work/one.toml").read_bytes()
    original = migration._write_bytes
    failed = False

    def write(descriptor, data):
        nonlocal failed
        if b'tracker = "next"' in data and not failed:
            failed = True
            raise OSError("Fixture local write interruption")
        original(descriptor, data)

    monkeypatch.setattr(migration, "_write_bytes", write)
    result = apply_tracker_migration(root, planned, environ=env, registry=registry)
    assert result["status"] == "rolled-back"
    assert (root / ".ai-dlc/work/one.toml").read_bytes() == before
    assert (
        migration.inspect_tracker_migration(root, planned["operation_id"])["status"]
        == "rolled-back"
    )
    if kind == "plane":
        assert len(remote["api"].items) == 1 and remote["api"].writes == []


def test_real_github_adapter_correlation_cannot_replace_known_target(adapter_move, monkeypatch):
    from ai_dlc.tracker_targets import plan_tracker_targets, reconcile_tracker_targets

    root, env, registry, _, _, kind = adapter_move
    if kind != "github-issues":
        pytest.skip("GitHub-specific independent reproduction")
    remote = {"item": None, "creates": 0}

    def run(args, **kwargs):
        if args[1:3] == ["api", "graphql"]:
            body = {"data": {"viewer": {"id": "expected"}}}
        elif args[1:3] == ["issue", "list"]:
            body = [] if remote["item"] is None else [remote["item"]]
        elif args[1:3] == ["issue", "create"]:
            remote["creates"] += 1
            remote["item"] = {
                "id": "node42",
                "number": 42,
                "url": "https://github.com/target/repo/issues/42",
                "state": "OPEN",
                "stateReason": None,
                "body": args[args.index("--body") + 1],
            }
            return SimpleNamespace(returncode=0, stdout=remote["item"]["url"], stderr="")
        else:
            assert args[1:3] == ["issue", "view"]
            body = remote["item"]
        return SimpleNamespace(returncode=0, stdout=json.dumps(body), stderr="")

    monkeypatch.setattr("ai_dlc.providers.github_issues.subprocess.run", run)
    plan = plan_tracker_targets(
        root,
        "next",
        work_ids=["one"],
        create_work_ids=["one"],
        source="local-records",
        environ=env,
        registry=registry,
    )
    first = reconcile_tracker_targets(root, plan, environ=env, registry=registry)
    assert first["status"] == "resolved"
    remote["item"].update(id="node43", number=43, url="https://github.com/target/repo/issues/43")
    second = reconcile_tracker_targets(root, plan, environ=env, registry=registry)
    assert remote["creates"] == 1
    assert second["status"] == "unresolved", second
    assert second["retained_targets"] == first["retained_targets"]
