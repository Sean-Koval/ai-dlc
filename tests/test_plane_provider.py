"""Real provider/transport fixtures, no Plane instance or credentials."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

U = [f"00000000-0000-4000-8000-{i:012d}" for i in range(1, 12)]
CFG = {
    "kind": "plane",
    "deployment": "self_hosted",
    "api_url": "http://localhost:3000",
    "web_url": "http://localhost:3000",
    "auth_mode": "api_key",
    "token_env": "PLANE_TEST_TOKEN",
    "account_id": U[0],
    "workspace_slug": "test-team",
    "workspace_id": U[1],
    "project_id": U[2],
    "project_key": "TEST",
    "statuses": dict(zip(("open", "in_progress", "closed", "cancelled"), U[3:7])),
}
CORRELATION = "<!-- ai-dlc:project=fixture;work=one -->"
CREATE = {
    "title": "Authored <title>",
    "body": "Human <body>",
    "correlation": CORRELATION,
    "operation_id": "fixture-create",
}


def page(rows):
    return {
        "results": rows,
        "count": len(rows),
        "total_results": len(rows),
        "next_page_results": False,
        "next_cursor": "",
    }


class PlaneHTTP:
    def __init__(self):
        self.items, self.links, self.writes = [], [], []
        self.hide_items = self.hide_links = False
        self.lose = None
        self.user = U[0]
        self.states = [
            {"id": i, "name": name, "group": group, "project": U[2], "workspace": U[1]}
            for i, name, group in zip(
                U[3:7],
                ("Todo", "Doing", "Done", "Cancelled"),
                ("unstarted", "started", "completed", "cancelled"),
            )
        ]
        self.project = {
            "id": U[2],
            "identifier": "TEST",
            "name": "Fixture",
            "workspace": U[1],
            "archived_at": None,
        }

    def __call__(self, request):
        p = request.url.path
        if request.method == "GET":
            if p.endswith("/users/me/"):
                return httpx.Response(200, json={"id": self.user})
            if p.endswith("/projects/"):
                return httpx.Response(200, json=page([self.project]))
            if p.endswith("/projects/" + U[2] + "/"):
                return httpx.Response(200, json=self.project)
            if p.endswith("/states/"):
                return httpx.Response(200, json=page(self.states))
            if p.endswith("/work-items/"):
                return httpx.Response(200, json=page([] if self.hide_items else self.items))
            if p.endswith("/links/"):
                return httpx.Response(200, json=page([] if self.hide_links else self.links))
            return httpx.Response(200, json=self.items[0])
        body = json.loads(request.content)
        self.writes.append((request.method, p, body))
        if p.endswith("/links/"):
            self.links.append(
                {
                    "id": U[8],
                    "url": body["url"],
                    "title": body.get("title"),
                    "project": U[2],
                    "workspace": U[1],
                    "issue": U[7],
                }
            )
            result = self.links[-1]
        elif request.method == "POST":
            self.items.append(
                {
                    **body,
                    "id": U[7],
                    "sequence_id": 1,
                    "workspace": U[1],
                    "project": U[2],
                    "archived_at": None,
                }
            )
            result = self.items[-1]
        else:
            self.items[0].update(body)
            result = self.items[0]
        if self.lose == (
            "link"
            if p.endswith("/links/")
            else "create"
            if request.method == "POST"
            else "transition"
        ):
            raise httpx.ReadTimeout("secret response payload")
        return httpx.Response(201 if request.method == "POST" else 200, json=result)


def provider(tmp_path, api, config=None, *, root=True):
    from ai_dlc.providers.plane import PlaneProvider

    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    return PlaneProvider(
        config or CFG,
        root=project if root else None,
        state_home=tmp_path / "state",
        environ={"PLANE_TEST_TOKEN": "never-log-this"},
        transport=httpx.MockTransport(api),
    )


def test_real_lifecycle_preserves_authored_content_and_links(tmp_path):
    api = PlaneHTTP()
    p = provider(tmp_path, api)
    created = p.invoke("create", CREATE)
    assert created["id"].endswith("/" + U[7] + "/")
    assert created["state"] == "open"
    assert "&lt;body&gt;" in api.items[0]["description_html"]
    assert api.items[0]["external_source"] == "ai-dlc"
    assert p.invoke("find", {"correlation": CORRELATION})["items"][0]["id"].endswith(
        "/" + U[7] + "/"
    )
    reference = created["url"]
    before = copy.deepcopy(api.items[0])
    link = {
        "reference": reference,
        "url": "https://github.com/example/repo/pull/1",
        "operation_id": "link-one",
    }
    p.invoke("link", link)
    p.invoke("link", link)
    assert len(api.links) == 1
    assert api.items[0] == before
    p.invoke(
        "transition", {"reference": reference, "state": "in_progress", "operation_id": "start-one"}
    )
    assert api.writes[-1][2] == {"state": U[4]}
    p.invoke(
        "transition", {"reference": reference, "state": "closed", "operation_id": "finish-one"}
    )
    assert p.invoke("read", {"reference": reference})["state"] == "closed"


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost",
        "http://127.0.0.1:8080",
        "http://[::1]:8080",
        "https://plane.example:8443",
    ],
)
def test_explicit_self_hosted_origins_work(tmp_path, origin):
    cfg = {**CFG, "api_url": origin, "web_url": origin}
    assert provider(tmp_path, PlaneHTTP(), cfg).invoke("find", {"correlation": CORRELATION}) == {
        "items": []
    }


@pytest.mark.parametrize(
    "origin",
    [
        "http://example.com",
        "http://127.0.0.1.evil",
        "http://127.1",
        "http://[::ffff:127.0.0.1]",
        "http://localhost:0",
        "http://localhost:65536",
        "http://localhost:",
        "http://user@localhost",
        "http://localhost/path",
        "http://localhost?x",
        "http://localhost#x",
        "http://[::1%25lo0]",
        "http://localhost:abc",
    ],
)
def test_unsafe_origins_refuse(tmp_path, origin):
    with pytest.raises(ValueError):
        provider(tmp_path, PlaneHTTP(), {**CFG, "api_url": origin})


@pytest.mark.parametrize(
    "auth,header", [("api_key", "x-api-key"), ("oauth_bearer", "authorization")]
)
def test_explicit_auth_header(tmp_path, auth, header):
    api = PlaneHTTP()

    def transport(request):
        assert request.headers[header] == (
            "never-log-this" if auth == "api_key" else "Bearer never-log-this"
        )
        assert ("authorization" if auth == "api_key" else "x-api-key") not in request.headers
        return api(request)

    provider(tmp_path, transport, {**CFG, "auth_mode": auth}).invoke(
        "find", {"correlation": CORRELATION}
    )


def test_lost_create_has_no_retry_even_when_invisible(tmp_path):
    api = PlaneHTTP()
    api.lose = "create"
    api.hide_items = True
    p = provider(tmp_path, api)
    with pytest.raises(RuntimeError):
        p.invoke("create", CREATE)
    with pytest.raises(RuntimeError, match="inspect"):
        provider(tmp_path, api).invoke("create", CREATE)
    assert len(api.writes) == 1
    api.hide_items = False
    assert p.invoke("create", CREATE)["id"].endswith("/" + U[7] + "/")
    assert len(api.writes) == 1


def test_lost_link_is_reconciled_read_only(tmp_path):
    api = PlaneHTTP()
    p = provider(tmp_path, api)
    ref = p.invoke("create", CREATE)["url"]
    api.lose = "link"
    api.hide_links = True
    payload = {"reference": ref, "url": "https://example.com/pr/1", "operation_id": "link-one"}
    with pytest.raises(RuntimeError):
        p.invoke("link", payload)
    with pytest.raises(RuntimeError):
        provider(tmp_path, api).invoke("link", payload)
    assert len(api.writes) == 2
    api.hide_links = False
    p.invoke("link", payload)
    assert len(api.writes) == 2


def test_cancelled_state_is_never_success_or_reopened(tmp_path):
    api = PlaneHTTP()
    p = provider(tmp_path, api)
    ref = p.invoke("create", CREATE)["url"]
    api.items[0]["state"] = U[6]
    assert p.invoke("read", {"reference": ref})["state"] == "cancelled"
    with pytest.raises(ValueError):
        p.invoke("transition", {"reference": ref, "state": "closed", "operation_id": "finish"})
    assert len(api.writes) == 1


@pytest.mark.parametrize(
    "new_state,target", [(U[6], "closed"), (U[5], "in_progress"), (U[9], "closed")]
)
def test_newer_reconciliation_state_refuses_terminal_or_unknown_write(tmp_path, new_state, target):
    api = PlaneHTTP()
    p = provider(tmp_path, api)
    reference = p.invoke("create", CREATE)["id"]
    reads = 0

    def transport(request):
        nonlocal reads
        if request.method == "GET" and request.url.path.endswith("/work-items/" + U[7] + "/"):
            reads += 1
            if reads == 2:
                api.items[0]["state"] = new_state
        return api(request)

    payload = {"reference": reference, "state": target, "operation_id": "changed-before-write"}
    with pytest.raises(ValueError, match="terminal state reversal"):
        provider(tmp_path, transport).invoke("transition", payload)
    assert reads == 2
    assert api.items[0]["state"] == new_state
    assert len(api.writes) == 1  # Only the preceding create; no PATCH.
    # A later nonterminal observation cannot authorize a send using that same intent.
    api.items[0]["state"] = U[3]
    with pytest.raises(RuntimeError, match="intent remains unresolved"):
        p.invoke("transition", payload)
    assert len(api.writes) == 1


def test_newer_completed_reconciliation_succeeds_without_patch(tmp_path):
    api = PlaneHTTP()
    p = provider(tmp_path, api)
    reference = p.invoke("create", CREATE)["id"]
    reads = 0

    def transport(request):
        nonlocal reads
        if request.method == "GET" and request.url.path.endswith("/work-items/" + U[7] + "/"):
            reads += 1
            if reads == 2:
                api.items[0]["state"] = U[5]
        return api(request)

    payload = {"reference": reference, "state": "closed", "operation_id": "already-finished"}
    assert provider(tmp_path, transport).invoke("transition", payload)["state"] == "closed"
    assert p.invoke("transition", payload)["state"] == "closed"
    assert len(api.writes) == 1


def test_lost_completion_response_reconciles_without_second_patch(tmp_path):
    api = PlaneHTTP()
    p = provider(tmp_path, api)
    reference = p.invoke("create", CREATE)["id"]
    api.lose = "transition"
    payload = {"reference": reference, "state": "closed", "operation_id": "lost-finish"}
    assert p.invoke("transition", payload)["state"] == "closed"
    assert p.invoke("transition", payload)["state"] == "closed"
    assert [method for method, _, _ in api.writes] == ["POST", "PATCH"]


@pytest.mark.parametrize("action", ["begin", "verify"])
def test_fifo_intent_refuses_promptly_without_a_writer(tmp_path, action):
    import subprocess
    import sys

    code = """
import os
import stat
import sys
from pathlib import Path
from ai_dlc.providers.plane_attempts import PlaneAttemptStore

root = Path(sys.argv[1]) / 'project'
root.mkdir()
store = PlaneAttemptStore(root, Path(sys.argv[1]) / 'state')
store.begin('fifo-operation', {})
intent = next(store.path.glob('*.json'))
intent.unlink()
os.mkfifo(intent, 0o600)
try:
    if sys.argv[2] == 'begin':
        store.begin('fifo-operation', {})
    else:
        store.verify()
except ValueError as exc:
    assert 'unsafe or corrupt' in str(exc)
else:
    raise AssertionError('FIFO intent was accepted')
assert stat.S_ISFIFO(intent.lstat().st_mode)
# Refusal released the directory lock; independent legitimate operations remain usable.
assert PlaneAttemptStore(root, Path(sys.argv[1]) / 'state').begin('another-operation', {})
print('refused unsafe FIFO')
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), action],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "refused unsafe FIFO"


def test_wrong_account_and_foreign_reference_refuse(tmp_path):
    api = PlaneHTTP()
    api.user = U[9]
    with pytest.raises(ValueError):
        provider(tmp_path, api).invoke("create", CREATE)
    assert not api.writes
    with pytest.raises(ValueError):
        provider(tmp_path, PlaneHTTP()).invoke("read", {"reference": "http://evil/projects/item"})


def test_ledger_free_create_refuses_before_write(tmp_path):
    api = PlaneHTTP()
    with pytest.raises(ValueError, match="root"):
        provider(tmp_path, api, root=False).invoke("create", CREATE)
    assert not api.writes


def test_redirect_refuses_without_following_or_secret_diagnostic(tmp_path):
    with pytest.raises(RuntimeError) as error:
        provider(
            tmp_path, lambda r: httpx.Response(302, headers={"Location": "https://evil.example"})
        ).invoke("create", CREATE)
    assert "never-log-this" not in str(error.value)


def test_atomic_ledger_intent_elects_one_sender(tmp_path):
    from ai_dlc.providers.plane_attempts import PlaneAttemptStore

    root = tmp_path / "project"
    root.mkdir()

    def begin(_):
        return PlaneAttemptStore(root, tmp_path / "state").begin("op", {"work": "one"})

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(begin, range(8)))
    assert results.count(True) == 1
    assert results.count(False) == 7
    with pytest.raises(ValueError):
        PlaneAttemptStore(root, tmp_path / "state").begin("op", {"work": "two"})


def test_ledger_rejects_symlink_and_corrupt_intent(tmp_path):
    from ai_dlc.providers.plane_attempts import PlaneAttemptStore

    root = tmp_path / "project"
    root.mkdir()
    state = tmp_path / "state"
    state.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError):
        PlaneAttemptStore(root, state).begin("op", {})
    state.unlink()
    store = PlaneAttemptStore(root, state)
    assert store.begin("op", {})
    files = list(state.rglob("*.json"))
    assert len(files) == 1
    files[0].write_text("broken")
    with pytest.raises(ValueError):
        store.begin("op", {})


def test_wire_results_obey_shared_contract(tmp_path):
    from ai_dlc.contracts import validate_response

    api = PlaneHTTP()
    p = provider(tmp_path, api)
    assert validate_response("find", p.invoke("find", {"correlation": CORRELATION})) == {
        "items": []
    }
    created = p.invoke("create", CREATE)
    assert (
        validate_response("read", p.invoke("read", {"reference": created["id"]}))["state"] == "open"
    )
    assert (
        validate_response(
            "link",
            p.invoke(
                "link",
                {
                    "reference": created["id"],
                    "url": "https://example.com/pr",
                    "operation_id": "link",
                },
            ),
        )["id"]
        == created["id"]
    )


def test_item_and_state_damage_refuses_before_write(tmp_path):
    api = PlaneHTTP()
    p = provider(tmp_path, api)
    ref = p.invoke("create", CREATE)["url"]
    api.items[0]["description_html"] = "<p>Authored replacement</p>"
    with pytest.raises(ValueError):
        p.invoke("find", {"correlation": CORRELATION})
    api.states[2]["group"] = "cancelled"
    with pytest.raises(ValueError):
        p.invoke("transition", {"reference": ref, "state": "closed", "operation_id": "finish"})
    assert len(api.writes) == 1


def test_marker_embedded_in_authored_body_cannot_create_unrecoverable_item(tmp_path):
    api = PlaneHTTP()
    with pytest.raises(ValueError):
        provider(tmp_path, api).invoke("create", {**CREATE, "body": CORRELATION})
    assert not api.writes


def test_prior_intent_fingerprint_is_checked_before_existing_result(tmp_path):
    api = PlaneHTTP()
    p = provider(tmp_path, api)
    p.invoke("create", CREATE)
    with pytest.raises(ValueError):
        p.invoke("create", {**CREATE, "title": "Changed title"})
    assert len(api.writes) == 1


@pytest.mark.parametrize("damage", ["truncated", "duplicate", "cycle", "bool_count"])
def test_incomplete_pagination_never_authorizes_create(tmp_path, damage):
    api = PlaneHTTP()

    def transport(request):
        response = api(request)
        if request.url.path.endswith("/work-items/"):
            data = page([])
            if damage == "truncated":
                data["total_results"] = 1
            if damage == "duplicate":
                data = page([{"id": U[7]}, {"id": U[7]}])
            if damage == "cycle":
                data = {
                    **page([{"id": U[7]}]),
                    "total_results": 100,
                    "next_page_results": True,
                    "next_cursor": "same",
                }
            if damage == "bool_count":
                data["count"] = False
            return httpx.Response(200, json=data)
        return response

    with pytest.raises(ValueError):
        provider(tmp_path, transport).invoke("create", CREATE)
    assert not api.writes


def test_ledger_replaced_directory_and_file_refuse(tmp_path):
    from ai_dlc.providers.plane_attempts import PlaneAttemptStore

    root = tmp_path / "project"
    root.mkdir()
    store = PlaneAttemptStore(root, tmp_path / "state")
    store.begin("op", {})
    file = next(store.path.glob("*.json"))
    content = file.read_bytes()
    file.rename(file.with_suffix(".old"))
    file.write_bytes(content)
    file.chmod(0o600)
    with pytest.raises(ValueError):
        store.verify()
    fresh = PlaneAttemptStore(root, tmp_path / "state")
    fresh.begin("op", {})
    store.path.rename(store.path.with_name("moved"))
    store.path.mkdir(mode=0o700)
    with pytest.raises(ValueError):
        fresh.verify()


def test_ledger_competing_processes_elect_one_sender(tmp_path):
    import os
    import subprocess
    import sys

    root = tmp_path / "project"
    root.mkdir()
    code = "from pathlib import Path; from ai_dlc.providers.plane_attempts import PlaneAttemptStore; import sys; print(PlaneAttemptStore(Path(sys.argv[1]),Path(sys.argv[2])).begin('op', {'work':'one'}))"
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", code, str(root), str(tmp_path / "state")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ,
        )
        for _ in range(6)
    ]
    outputs = [process.communicate(timeout=20) for process in processes]
    assert all(process.returncode == 0 for process in processes), outputs
    assert [out.strip() for out, _ in outputs].count("True") == 1
    assert [out.strip() for out, _ in outputs].count("False") == 5


@pytest.mark.parametrize("damage", ["symlink", "hardlink", "permissions"])
def test_unsafe_existing_intent_refuses_even_if_remote_result_exists(tmp_path, damage):
    import os

    api = PlaneHTTP()
    p = provider(tmp_path, api)
    p.invoke("create", CREATE)
    path = next((tmp_path / "state").rglob("*.json"))
    if damage == "symlink":
        other = path.with_suffix(".original")
        path.rename(other)
        path.symlink_to(other)
    if damage == "hardlink":
        os.link(path, path.with_suffix(".linked"))
    if damage == "permissions":
        path.chmod(0o644)
    with pytest.raises(ValueError):
        p.invoke("create", CREATE)
    assert len(api.writes) == 1


def test_crash_after_intent_sync_before_send_preserves_no_retry(tmp_path, monkeypatch):
    import os
    import stat

    api = PlaneHTTP()
    p = provider(tmp_path, api)
    original = os.fsync

    def crash(fd):
        original(fd)
        if stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("simulated crash after intent sync")

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", crash)
        with pytest.raises(ValueError):
            p.invoke("create", CREATE)
    with pytest.raises(RuntimeError, match="inspect"):
        p.invoke("create", CREATE)
    assert not api.writes


def test_replaced_ledger_directory_before_send_refuses(tmp_path):
    api = PlaneHTTP()
    moved = False

    def transport(request):
        nonlocal moved
        if request.url.path.endswith("/work-items/") and request.method == "GET" and not moved:
            files = list((tmp_path / "state").rglob("*.json"))
            if files:
                parent = files[0].parent
                parent.rename(parent.with_name("displaced"))
                parent.mkdir(mode=0o700)
                moved = True
        return api(request)

    with pytest.raises(ValueError):
        provider(tmp_path, transport).invoke("create", CREATE)
    assert moved and not api.writes


def test_server_rejection_after_intent_never_resubmits(tmp_path):
    api = PlaneHTTP()
    posts = []

    def transport(request):
        if request.method == "POST":
            posts.append(request)
            return httpx.Response(429, json={"error": "credential-sentinel"})
        return api(request)

    p = provider(tmp_path, transport)
    for _ in range(2):
        with pytest.raises(RuntimeError) as error:
            p.invoke("create", CREATE)
        assert "credential-sentinel" not in str(error.value)
    assert len(posts) == 1


def test_complete_multipage_find_and_duplicate_correlation(tmp_path):
    api = PlaneHTTP()
    p = provider(tmp_path, api)
    p.invoke("create", CREATE)

    def transport(request):
        if request.url.path.endswith("/work-items/"):
            if "cursor" not in request.url.params:
                return httpx.Response(
                    200,
                    json={
                        **page([{"id": U[9], "description_html": "<p>Other authored work</p>"}]),
                        "total_results": 2,
                        "next_page_results": True,
                        "next_cursor": "next",
                    },
                )
            assert request.url.params["cursor"] == "next"
            return httpx.Response(200, json={**page(api.items), "total_results": 2})
        return api(request)

    assert (
        len(provider(tmp_path, transport).invoke("find", {"correlation": CORRELATION})["items"])
        == 1
    )
    api.items.append({**api.items[0], "id": U[10]})
    with pytest.raises(ValueError, match="duplicated"):
        p.invoke("find", {"correlation": CORRELATION})


def test_unknown_wire_config_and_empty_json_refuse(tmp_path):
    with pytest.raises(ValueError):
        provider(tmp_path, PlaneHTTP(), {**CFG, "root": str(tmp_path)})
    with pytest.raises((ValueError, RuntimeError)):
        provider(tmp_path, lambda r: httpx.Response(200, json=[])).invoke("create", CREATE)


def test_duplicate_foreign_and_authored_links(tmp_path):
    api = PlaneHTTP()
    p = provider(tmp_path, api)
    ref = p.invoke("create", CREATE)["id"]
    payload = {"reference": ref, "url": "https://example.com/pr", "operation_id": "link"}
    api.links = [
        {
            "id": U[8],
            "url": payload["url"],
            "title": "Authored title",
            "project": U[2],
            "workspace": U[1],
            "issue": U[7],
        }
    ]
    assert p.invoke("link", payload)["id"] == ref
    assert len(api.writes) == 1 and api.links[0]["title"] == "Authored title"
    api.links.append({**api.links[0], "id": U[9]})
    with pytest.raises(ValueError, match="duplicated"):
        p.invoke("link", payload)
    api.links.pop()
    api.links[0]["project"] = U[9]
    with pytest.raises(ValueError, match="foreign"):
        p.invoke("link", payload)
    assert len(api.writes) == 1


def test_intent_schema_tampering_is_not_accepted_by_boolean_equality(tmp_path):
    from ai_dlc.providers.plane_attempts import PlaneAttemptStore

    root = tmp_path / "project"
    root.mkdir()
    store = PlaneAttemptStore(root, tmp_path / "state")
    store.begin("op", {})
    file = next(store.path.glob("*.json"))
    record = json.loads(file.read_text())
    record["schema"] = True
    file.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        store.begin("op", {})
