import hashlib

import httpx
import pytest


def test_contract_hides_completion():
    from ai_dlc.contracts import manifest

    assert "complete" not in manifest()["operations"]
    assert "create" in manifest()["operations"]


def test_journal_conflicts_and_recovers(tmp_path):
    from ai_dlc.journal import Journal

    j = Journal(tmp_path / "state.db")
    assert j.begin("op", {"x": 1})["status"] == "pending"
    j.uncertain("op")
    assert j.begin("op", {"x": 1})["status"] == "uncertain"
    with pytest.raises(ValueError, match="conflict"):
        j.begin("op", {"x": 2})
    j.succeed("op", {"id": "a"})
    assert j.begin("op", {"x": 1})["result"] == {"id": "a"}


def test_executable_digest_and_protocol(tmp_path):
    from ai_dlc.providers import ExecutableProvider

    script = tmp_path / "provider"
    script.write_text(
        '#!/usr/bin/env python3\nimport json,sys\nr=json.load(sys.stdin)\nprint(json.dumps({"id":"1","url":"https://example/1","state":"open"}))\n'
    )
    script.chmod(0o755)
    with pytest.raises(ValueError, match="digest"):
        ExecutableProvider({"command": str(script), "sha256": "bad"})
    p = ExecutableProvider(
        {"command": str(script), "sha256": hashlib.sha256(script.read_bytes()).hexdigest()}
    )
    assert p.invoke("read", {"reference": "1"})["id"] == "1"
    with pytest.raises(ValueError):
        p.invoke("complete", {"reference": "1"})


def test_linear_transport():
    from ai_dlc.providers.linear import LinearProvider

    def handle(request):
        assert request.headers["Authorization"] == "secret"
        return httpx.Response(
            200,
            json={
                "data": {
                    "issue": {"id": "id", "url": "https://linear.app/i", "state": {"name": "Todo"}}
                }
            },
        )

    p = LinearProvider(
        {"token_env": "TEST_TOKEN"},
        client=httpx.Client(transport=httpx.MockTransport(handle)),
        environ={"TEST_TOKEN": "secret"},
    )
    assert p.invoke("read", {"reference": "id"})["state"] == "open"


def test_linear_completed_native_state_is_normalized_for_reconciliation():
    from ai_dlc.providers.linear import LinearProvider

    p = LinearProvider({}, environ={"LINEAR_API_KEY": "fake"})
    assert (
        p.item(
            {
                "id": "id",
                "url": "https://linear.app/i",
                "state": {"id": "done-id", "name": "Shipped", "type": "completed"},
            }
        )["state"]
        == "closed"
    )


def test_linear_graphql_error():
    from ai_dlc.providers.linear import LinearProvider

    p = LinearProvider(
        {"token_env": "TEST_TOKEN"},
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"errors": [{"message": "denied"}]})
            )
        ),
        environ={"TEST_TOKEN": "secret"},
    )
    with pytest.raises(RuntimeError, match="denied"):
        p.invoke("read", {"reference": "id"})


def test_public_registry_blocks_terminal_transitions():
    from ai_dlc.providers import Registry

    registry = Registry()
    for state in ["closed", "done", "completed", "CLOSED"]:
        with pytest.raises(ValueError, match="finish"):
            registry.invoke(
                "unused", "transition", {"reference": "1", "state": state, "operation_id": "op"}
            )


def test_github_executable_wraps_gh_and_rejects_intermediate_state(tmp_path, monkeypatch):
    import os

    from ai_dlc.providers import Registry

    gh = tmp_path / "gh"
    gh.write_text(
        '#!/usr/bin/env python3\nimport json,sys\nassert "--repo" in sys.argv\nprint(json.dumps({"number":12,"url":"https://github.com/a/b/issues/12","state":"OPEN","body":""}))\n'
    )
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("PYTHONPATH", str(__import__("pathlib").Path("src").resolve()))
    registry = Registry({"providers": {"issues": {"kind": "github-issues", "repository": "a/b"}}})
    provider = registry.get("issues")
    assert provider.invoke("read", {"reference": "12"})["id"] == "12"
    with pytest.raises(RuntimeError, match="intermediate"):
        provider.invoke(
            "transition", {"reference": "12", "state": "in_progress", "operation_id": "op"}
        )


def test_contract_includes_role_capabilities():
    from ai_dlc.contracts import manifest

    assert set(manifest()["roles"]) == {
        "tracker",
        "specs",
        "scm",
        "deploy",
        "knowledge",
    }


def test_python_plugin_requires_dependency_closure_before_loading(tmp_path, monkeypatch):
    import importlib.metadata

    from ai_dlc.providers import Registry

    lock = tmp_path / "uv.lock"
    lock.write_text("version = 1")

    class Distribution:
        files = ()
        requires = ("dependency>=1",)
        entry_points = ()

    monkeypatch.setattr(importlib.metadata, "distribution", lambda name: Distribution())
    registry = Registry(
        {
            "providers": {
                "plugin": {
                    "kind": "python",
                    "distribution": "plugin",
                    "dependency_lock": str(lock),
                    "dependency_lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
                    "distribution_files": {},
                }
            }
        }
    )
    with pytest.raises(ValueError, match="distribution|dependency"):
        registry.get("plugin")


def test_python_plugin_verifies_transitive_distribution_files(tmp_path, monkeypatch):
    import importlib.metadata
    from pathlib import Path

    from ai_dlc.providers import Registry

    lock = tmp_path / "lock"
    lock.write_text("locked")
    plugin = tmp_path / "plugin.py"
    plugin.write_text("safe")
    loaded = []

    class Entry:
        group = "ai_dlc.providers"
        name = "plugin"

        def load(self):
            loaded.append(True)
            return lambda cfg: object()

    class Distribution:
        files = (Path("plugin.py"),)
        requires = ("dependency>=1",)
        entry_points = (Entry(),)

        def locate_file(self, path):
            return tmp_path / path

    monkeypatch.setattr(importlib.metadata, "distribution", lambda name: Distribution())
    cfg = {
        "kind": "python",
        "distribution": "plugin",
        "entry_point": "plugin",
        "dependency_lock": str(lock),
        "dependency_lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
        "distribution_files": {"plugin.py": hashlib.sha256(plugin.read_bytes()).hexdigest()},
    }
    with pytest.raises(ValueError, match="dependency"):
        Registry({"providers": {"plugin": cfg}}).get("plugin")
    assert not loaded


def test_schema_describes_specific_mutation_payload():
    from ai_dlc.contracts import manifest, validate_request

    assert "operation_id" in manifest()["operations"]["create"]["payload"]["required"]
    with pytest.raises(ValueError):
        validate_request(
            "create",
            {"title": "A", "correlation": "marker", "operation_id": "op", "unexpected": True},
        )


def test_registry_discovers_builtin_role_adapters(tmp_path):
    from ai_dlc.providers import Registry

    registry = Registry({"scm": {"repository": "a/b"}}, root=tmp_path)
    assert hasattr(registry.get("openspec"), "current")
    assert hasattr(registry.get("github"), "merged")


def test_executable_specification_contract(tmp_path):
    from ai_dlc.providers import ExecutableProvider

    script = tmp_path / "spec"
    script.write_text(
        '#!/usr/bin/env python3\nimport json,sys\nr=json.load(sys.stdin)\nassert r["operation"]=="current"\nprint(json.dumps({"current":True,"archive":"openspec/changes/archive/2026-01-01-one"}))\n'
    )
    script.chmod(0o755)
    provider = ExecutableProvider(
        {"command": str(script), "sha256": hashlib.sha256(script.read_bytes()).hexdigest()}
    )
    assert provider.current({"id": "one"})["current"] is True


def test_python_provider_deadline_is_bounded():
    import time

    from ai_dlc.providers import PythonProvider

    class Slow:
        def invoke(self, operation, payload):
            time.sleep(0.1)
            return {"id": "1", "url": "https://example/1", "state": "open"}

    provider = PythonProvider(Slow(), timeout=0.01)
    with pytest.raises(TimeoutError, match="uncertain"):
        provider.invoke("read", {"reference": "1"})


def test_public_terminal_guard_uses_canonical_state():
    from ai_dlc.providers import Registry

    registry = Registry()
    for state in [" closed ", "\tdone\n", " COMPLETED "]:
        with pytest.raises(ValueError, match="work.finish"):
            registry.invoke(
                "github-issues",
                "transition",
                {"reference": "1", "state": state, "operation_id": "guard"},
            )


def test_python_integrity_rejects_unchecked_importable_cache(tmp_path):
    import py_compile

    from ai_dlc.providers import reject_unsafe_imports

    source = tmp_path / "plugin.py"
    source.write_text("answer=1\n")
    py_compile.compile(str(source))
    with pytest.raises(ValueError, match="bytecode"):
        reject_unsafe_imports([source])


def test_registry_dispatches_builtin_named_role_method(tmp_path):
    from ai_dlc.providers import Registry

    registry = Registry(root=tmp_path, config={"paths": {"vault": str(tmp_path)}})
    result = registry.invoke(
        "obsidian", "append", {"path": "session.md", "body": "Outcome", "operation_id": "session"}
    )
    assert result["created"] is True
    assert "Outcome" in (tmp_path / "session.md").read_text()


def test_new_contract_is_discoverable_without_implied_workflow(tmp_path):
    import json

    from ai_dlc.providers import Registry

    path = tmp_path / "custom.json"
    path.write_text(
        json.dumps({"schema": 1, "roles": {"design": {"version": 1, "mandatory": ["draw"]}}})
    )
    registry = Registry(
        {
            "contracts": {
                "manifests": [
                    {"path": "custom.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                ]
            }
        },
        root=tmp_path,
    )
    assert registry.discover()["manifest"]["roles"]["design"]["version"] == 1
    with pytest.raises(ValueError, match="Unsupported"):
        registry.invoke("design", "draw", {})


def test_isolated_provider_ignores_shadow_modules_and_poisoned_bytecode(tmp_path, monkeypatch):
    import py_compile

    from ai_dlc.providers import IsolatedPythonProvider

    trusted = tmp_path / "trusted"
    trusted.mkdir()
    dependency = trusted / "dependency.py"
    dependency.write_text('value="evil"\n')
    py_compile.compile(
        str(dependency), invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH
    )
    dependency.write_text('value="safe"\n')
    plugin = trusted / "plugin.py"
    plugin.write_text(
        'import dependency\nclass Provider:\n def __init__(self, config): pass\n def invoke(self, operation, payload): return {"id":dependency.value,"url":"https://example.test/1","state":"open"}\n'
    )
    shadow = tmp_path / "shadow"
    shadow.mkdir()
    (shadow / "dependency.py").write_text('raise RuntimeError("unverified shadow imported")\n')
    monkeypatch.chdir(shadow)
    monkeypatch.setenv("PYTHONPATH", str(shadow))
    modules = {
        p.stem: {
            "path": str(p),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "package": False,
            "native": False,
        }
        for p in [plugin, dependency]
    }
    provider = IsolatedPythonProvider({}, modules, "plugin:Provider")
    assert provider.invoke("read", {"reference": "1"})["id"] == "safe"
    dependency.write_text('value="changed"\n')
    with pytest.raises(RuntimeError, match="digest changed"):
        provider.invoke("read", {"reference": "1"})
