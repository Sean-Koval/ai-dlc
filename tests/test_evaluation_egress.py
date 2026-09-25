"""A real-client attempt reaches only the named destinations; refusals are evidence."""

import io
import json
import shutil
import socket
import subprocess
import tarfile
import threading
from types import SimpleNamespace

import pytest

IMAGE = "python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de"
PLANNED = {
    "scenario": "csv-feature",
    "arm": "baseline",
    "attempt": 1,
    "image": IMAGE,
    "engine_sha256": None,
    "limits": {"timeout_minutes": 30, "max_turns": 20},
    "assertions": ["hidden-tests"],
}
EGRESS = {"hosts": ["api.anthropic.com"], "proxy_image": IMAGE}
LOG = (
    b'{"allowed": true, "host": "api.anthropic.com", "port": 443}\n'
    b'{"allowed": false, "host": "pypi.org", "port": 443}\n'
    b'{"allowed": false, "host": "pypi.org", "port": 443}\n'
)


def attempt():
    from ai_dlc.verification.evaluation import attempt as module

    return module


@pytest.fixture
def fixture_dir(tmp_path):
    root = tmp_path / "fixture"
    root.mkdir()
    (root / "app.py").write_text("print('v1')\n")
    return root


def archive(files):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeDocker:
    def __init__(self):
        self.calls = []

    def __call__(self, args, *, timeout, input=None, cancel=None):
        del timeout, input, cancel
        self.calls.append(list(args))
        out = b""
        if args[0] == "run" and "tar" in args:
            out = archive({"project/app.py": b"x"})
        if args[0] == "logs":
            out = LOG
        return SimpleNamespace(returncode=0, stdout=out, stderr=b"")

    def first(self, *prefix):
        return next(c for c in self.calls if c[: len(prefix)] == list(prefix))


@pytest.fixture
def fake(monkeypatch):
    docker = FakeDocker()
    monkeypatch.setattr(attempt(), "_docker", docker)
    monkeypatch.setattr(attempt().shutil, "which", lambda name: "/usr/bin/" + name)
    return docker


def run(tmp_path, fixture_dir, **options):
    options.setdefault("steps", [["true"]])
    return attempt().run_attempt(PLANNED, run_dir=tmp_path / "run", fixture=fixture_dir, **options)


def test_without_egress_nothing_network_related_is_created(tmp_path, fixture_dir, fake):
    result = run(tmp_path, fixture_dir)
    assert "--network=none" in fake.first("create")
    assert not [c for c in fake.calls if c[0] == "network" or c[0] == "logs"]
    assert "egress" not in result


def test_agent_joins_only_an_internal_network_with_a_hardened_pinned_proxy(
    tmp_path, fixture_dir, fake
):
    run(tmp_path, fixture_dir, egress=EGRESS)
    internal = fake.first("network", "create")
    assert "--internal" in internal
    create = fake.first("create")
    assert "--network=none" not in create and f"--network={internal[-1]}" in create
    proxy = next(c for c in fake.calls if c[0] == "run" and "-d" in c)
    name = proxy[proxy.index("--name") + 1]
    assert f"--env=HTTPS_PROXY=http://{name}:8080" in create
    for control in ["--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
                    "--user=65534:65534", "--env=ALLOW_HOSTS=api.anthropic.com"]:  # fmt: skip
        assert control in proxy
    assert IMAGE in proxy
    assert not [part for part in proxy if part.startswith("type=bind")]
    # The stager and collector never get a network, whatever the agent has.
    for helper in [c for c in fake.calls if c[0] == "run" and "-d" not in c]:
        assert "--network=none" in helper


def test_proxy_log_is_retained_before_cleanup_and_refusals_are_named(tmp_path, fixture_dir, fake):
    result = run(tmp_path, fixture_dir, egress=EGRESS)
    verbs = [c[0] for c in fake.calls]
    assert verbs.index("logs") < verbs.index("rm")
    assert (tmp_path / "run/egress.jsonl").read_bytes() == LOG
    assert result["egress"] == {"allowed": ["api.anthropic.com"], "refused": ["pypi.org"]}
    assert "egress.jsonl" in result["evidence"]
    removed = [c[-1] for c in fake.calls if c[:2] == ["network", "rm"]]
    assert len(removed) == 2 and result["cleanup"]["clean"]
    events = [json.loads(x) for x in (tmp_path / "run/events.jsonl").read_text().splitlines()]
    assert "egress" in [e["kind"] for e in events]


def test_unpinned_proxy_image_and_unsafe_hosts_are_refused(tmp_path, fixture_dir, fake):
    for bad in [
        {"hosts": ["api.anthropic.com"], "proxy_image": "python:3.12"},
        {"hosts": ["api.anthropic.com,evil.example"], "proxy_image": IMAGE},
        {"hosts": [], "proxy_image": IMAGE},
    ]:
        with pytest.raises(ValueError, match="egress"):
            run(tmp_path, fixture_dir, egress=bad)
    assert fake.calls == []


def test_plan_refuses_egress_for_the_deterministic_driver_and_without_a_proxy_image():
    from pathlib import Path

    from ai_dlc.verification.evaluation.planning import plan

    root = Path(__file__).resolve().parents[1]
    suite = json.loads((root / "evaluations/suites/smoke.json").read_text())
    profile = json.loads((root / "evaluations/profiles/local-deterministic.json").read_text())
    with pytest.raises(ValueError, match=r"egress.*deterministic"):
        plan(suite, dict(profile, egress={"hosts": ["api.anthropic.com"], "proxy_image": IMAGE}))
    with pytest.raises(ValueError, match="proxy_image"):
        plan(suite, dict(profile, egress={"hosts": ["api.anthropic.com"]}))
    with pytest.raises(ValueError, match="proxy_image"):
        plan(suite, dict(profile, egress={"hosts": ["a.example"], "proxy_image": "python:3"}))


def test_the_proxy_logs_each_decision_as_one_json_line(monkeypatch, capsys):
    import socketserver

    from ai_dlc.verification import test_proxy as proxy

    monkeypatch.setenv("ALLOW_HOSTS", "api.anthropic.com")
    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), proxy.Handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with socket.create_connection(server.server_address, timeout=5) as client:
            client.sendall(b"CONNECT pypi.org:443 HTTP/1.1\r\n\r\n")
            assert b"403" in client.recv(200)
        server.shutdown()
    lines = [json.loads(x) for x in capsys.readouterr().out.splitlines()]
    assert lines == [{"allowed": False, "host": "pypi.org", "port": 443}]


def test_the_runner_hands_egress_to_every_attempt_and_the_report_names_refusals(
    tmp_path, monkeypatch
):
    from pathlib import Path

    from ai_dlc.verification.evaluation import run

    root = Path(__file__).resolve().parents[1]
    candidate = "sha256:" + "d" * 64
    profile = json.loads((root / "evaluations/profiles/local-deterministic.json").read_text())
    profile["image"], profile["engine"]["image"] = IMAGE, candidate
    profile["driver"] = {"kind": "claude-code", "version": "2.1.220"}
    profile["egress"] = EGRESS
    profile["model"] = "claude-sonnet-4-6"
    profile["credentials"] = ["ANTHROPIC_API_KEY"]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-key-not-real")
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile))

    class Driver:
        retained = staticmethod(dict)
        install = staticmethod(lambda item: [])
        steps = staticmethod(lambda item: [["true"]])

    seen = []

    def run_attempt(item, *, run_dir, egress, **_):
        seen.append(egress)
        run_dir.mkdir(parents=True)
        event = {"schema": 1, "source": "controller", "at": "2026-09-20T00:00:00+00:00",
                 "kind": "egress", "allowed": [], "refused": ["pypi.org"]}  # fmt: skip
        (run_dir / "events.jsonl").write_text(json.dumps(event) + "\n")
        return {"scenario": item["scenario"], "arm": item["arm"], "attempt": 1,
                "outcome": "completed", "stage": None, "cleanup": {"clean": True}}  # fmt: skip

    monkeypatch.setattr(run, "load_driver", lambda profile, path: Driver)
    monkeypatch.setattr(
        run, "_layers", lambda image: ["l1"] + (["l2"] if image == candidate else [])
    )
    monkeypatch.setattr(run.lifecycle, "run_attempt", run_attempt)
    report = run.run_suite(root / "evaluations/suites/smoke.json", path, tmp_path / "out")
    assert seen == [EGRESS, EGRESS]
    for arm in report["arms"]:
        assert arm["metrics"]["egress_refused"] == ["pypi.org"]
    assert "pypi.org" in (tmp_path / "out/report.timeline.md").read_text()


# --- Real Docker and real network. Skipped, never passed, when either is absent. ---


def ready():
    if not shutil.which("docker"):
        return False
    try:
        socket.create_connection(("api.anthropic.com", 443), timeout=5).close()
    except OSError:
        return False
    done = subprocess.run(
        ["docker", "image", "inspect", IMAGE], capture_output=True, check=False, timeout=30
    )
    return done.returncode == 0


real = pytest.mark.skipif(not ready(), reason="Docker, the pinned image or the network is absent")
CONNECT = (
    "import os,socket,sys,urllib.parse;u=urllib.parse.urlparse(os.environ['HTTPS_PROXY']);"
    "s=socket.create_connection((u.hostname,u.port),10);"
    "s.sendall(('CONNECT %s:443 HTTP/1.1\\r\\n\\r\\n'%sys.argv[1]).encode());"
    "print(s.recv(64).split()[1].decode())"
)
DIRECT = (
    "import socket,sys;s=socket.socket();s.settimeout(3);"
    "print('direct', 'blocked' if s.connect_ex(('1.1.1.1',443)) else 'open')"
)


@real
def test_real_agent_reaches_a_listed_host_only_and_leaves_nothing_behind(tmp_path, fixture_dir):
    steps = [
        ["python", "-c", DIRECT],
        ["python", "-c", CONNECT, "api.anthropic.com"],
        ["python", "-c", CONNECT, "pypi.org"],
    ]
    result = run(tmp_path, fixture_dir, steps=steps, egress=EGRESS)
    out = [json.loads((tmp_path / f"run/steps/0{i}.json").read_text())["stdout"] for i in (1, 2, 3)]
    assert out == ["direct blocked\n", "200\n", "403\n"], (out, result)
    assert result["egress"] == {"allowed": ["api.anthropic.com"], "refused": ["pypi.org"]}
    assert result["cleanup"]["clean"]
    for listing in (
        ["ps", "-a", "--format", "{{.Names}}"],
        ["network", "ls", "--format", "{{.Name}}"],
    ):
        listed = subprocess.check_output(["docker", *listing])
        assert result["resources"]["container"].encode() not in listed
