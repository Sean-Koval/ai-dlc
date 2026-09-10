"""Real shared lifecycle and registration; only HTTP and SCM evidence are fixtures."""

import json
import os
import subprocess
import sys

import httpx
import pytest
import tomli_w
from test_plane_provider import CFG, PlaneHTTP, U


@pytest.fixture
def lifecycle(tmp_path):
    from ai_dlc.providers import Registry
    from ai_dlc.providers.plane import PlaneProvider
    from ai_dlc.work.workflow import WorkService

    api = PlaneHTTP()
    config = {
        "schema": 4,
        "roles": {"tracker": "local", "scm": "fixture"},
        "providers": {"local": CFG},
        "scm": {"repository": "fixture/repo"},
    }
    (tmp_path / "ai-dlc.toml").write_text(tomli_w.dumps(config))
    work = tmp_path / ".ai-dlc/work"
    work.mkdir(parents=True)
    (work / "one.toml").write_text(
        tomli_w.dumps(
            {
                "schema": 1,
                "id": "one",
                "title": "New work",
                "scope": "Plane fixture",
                "requires_spec": False,
                "spec_reason": "Fixture",
                "acceptance": ["Authored acceptance"],
                "reviewed": True,
                "providers": {"tracker": "local", "scm": "fixture"},
            }
        )
    )
    subprocess.run(
        ["git", "init", "-b", "work/one", str(tmp_path)], check=True, capture_output=True
    )

    class SCM:
        allowed = False

        def merged(self, reference):
            if not self.allowed:
                raise ValueError("Fixture PR unmerged")
            return {"sha": "fixture-merge", "pr": {"merged": True}}

        def ci(self, sha):
            return {"sha": sha, "run_id": 1, "receipt": {"fixture_only": True}}

    scm = SCM()
    registry = Registry(config, root=tmp_path)
    registry.register(
        "local",
        PlaneProvider(
            CFG,
            root=tmp_path,
            state_home=tmp_path / "state",
            environ={"PLANE_TEST_TOKEN": "fixture"},
            transport=httpx.MockTransport(api),
        ),
        operations=["capabilities"],
    )
    registry.register("fixture", scm)
    return (
        WorkService(tmp_path, config, state_path=tmp_path / "outer-state", registry=registry),
        api,
        scm,
    )


def test_shared_plane_lifecycle_keeps_finish_gates(lifecycle):
    service, api, scm = lifecycle
    assert service.publish("one")["tracker"]["state"] == "open"
    assert service.start("one")["tracker"]["state"] == "in_progress"
    service.link("one", "pr", "https://github.com/fixture/repo/pull/1")
    before = len(api.writes)
    assert service.finish("one")["status"] == "blocked"
    assert len(api.writes) == before
    scm.allowed = True
    assert service.finish("one")["tracker"]["state"] == "closed"
    assert service.finish("one")["status"] == "completed"


def test_shared_uncertain_link_reinvocation_never_writes_twice(lifecycle):
    service, api, _ = lifecycle
    service.publish("one")
    api.lose = "link"
    api.hide_links = True
    for _ in range(2):
        with pytest.raises(RuntimeError):
            service.link("one", "pr", "https://github.com/fixture/repo/pull/1")
    assert len(api.writes) == 2
    api.hide_links = False
    service.link("one", "pr", "https://github.com/fixture/repo/pull/1")
    assert len(api.writes) == 2


def test_shared_uncertain_create_does_not_retry(lifecycle):
    service, api, _ = lifecycle
    api.lose = "create"
    api.hide_items = True
    with pytest.raises(RuntimeError):
        service.publish("one")
    with pytest.raises(RuntimeError, match="refusing duplicate retry"):
        service.publish("one")
    assert len(api.writes) == 1
    api.hide_items = False
    service.publish("one")
    assert len(api.writes) == 1


def test_registry_supplies_root_and_state_only_as_trusted_invocation_context(tmp_path):
    from ai_dlc.providers import Registry

    registry = Registry(
        {"providers": {"local": CFG}},
        root=tmp_path,
        environ={
            **os.environ,
            "PLANE_TEST_TOKEN": "fixture",
            "XDG_STATE_HOME": str(tmp_path / "state"),
        },
    )
    provider = registry.get("local")
    result = provider.invoke("capabilities", {})
    assert result["optional_operations"] == ["link"]
    config, context = map(json.loads, provider.command[-2:])
    assert config == CFG
    assert context == {"root": str(tmp_path.resolve()), "state_home": str(tmp_path / "state")}
    for state in ("closed", "cancelled", U[5], U[6]):
        with pytest.raises(ValueError, match="finish"):
            registry.invoke(
                "local", "transition", {"reference": U[7], "state": state, "operation_id": "bypass"}
            )


def test_direct_executable_without_trusted_context_refuses_mutation():
    from test_plane_provider import CREATE

    result = subprocess.run(
        [sys.executable, "-m", "ai_dlc.providers.plane", json.dumps(CFG)],
        input=json.dumps({"operation": "create", "payload": CREATE}),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PLANE_TEST_TOKEN": "fixture"},
    )
    assert result.returncode == 1 and "root" in result.stderr


def test_registry_discovery_exposes_available_plane_without_contact(tmp_path):
    from ai_dlc.providers import Registry

    assert "plane" in Registry({}, root=tmp_path, environ={}).discover()["builtins"]
