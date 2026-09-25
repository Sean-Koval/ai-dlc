"""An attempt is isolated, bounded and collected before cleanup; failures are never hidden."""

import io
import json
import shutil
import subprocess
import tarfile
import threading
from types import SimpleNamespace

import pytest

IMAGE = "python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de"
ANCHOR = "1" * 40
PLANNED = {
    "scenario": "csv-feature",
    "arm": "treatment",
    "attempt": 1,
    "image": IMAGE,
    "engine_sha256": "c" * 64,
    "limits": {"timeout_minutes": 30, "max_turns": 20},
    "assertions": ["hidden-tests"],
}
REAL_PLANNED = {
    **PLANNED,
    "client": {
        "kind": "claude-code",
        "version": "2.1.220",
        "model": "claude-sonnet-4-6",
        "goal_sha256": "a" * 64,
    },
}


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
    """Replaces only the docker process boundary; records every invocation in order."""

    def __init__(self, tree=None):
        self.calls = []
        self.fail = {}
        self.tree = archive(tree or {"project/app.py": b"print('v2')\n"})

    def __call__(self, args, *, timeout, input=None, cancel=None):
        del timeout, input, cancel
        self.calls.append(list(args))
        verb = self.verb(args)
        if verb in self.fail:
            return SimpleNamespace(returncode=1, stdout=b"", stderr=self.fail[verb].encode())
        stdout = (
            self.tree
            if verb == "collect"
            else f"{ANCHOR}\n".encode()
            if args[0] == "exec" and "rev-parse" in args
            else b""
        )
        return SimpleNamespace(returncode=0, stdout=stdout, stderr=b"")

    @staticmethod
    def verb(args):
        if args[0] == "run" and "tar" in args and "-c" in args:
            return "collect"
        if args[0] == "run":
            return "stage"
        if args[0] == "exec":
            return "exec:" + args[-1]
        return " ".join(args[:2]) if args[0] == "volume" else args[0]

    def verbs(self):
        return [self.verb(call) for call in self.calls]


@pytest.fixture
def fake(monkeypatch):
    docker = FakeDocker()
    monkeypatch.setattr(attempt(), "_docker", docker)
    monkeypatch.setattr(attempt().shutil, "which", lambda name: "/usr/bin/" + name)
    return docker


def run(tmp_path, fixture_dir, **options):
    planned = options.pop("planned", PLANNED)
    options.setdefault("steps", [["sh", "-c", "step-one"]])
    return attempt().run_attempt(planned, run_dir=tmp_path / "run", fixture=fixture_dir, **options)


def test_evidence_is_collected_before_cleanup_and_hashed(tmp_path, fixture_dir, fake):
    result = run(tmp_path, fixture_dir)
    verbs = fake.verbs()
    assert verbs.index("collect") < verbs.index("rm") < verbs.index("volume rm")
    assert result["outcome"] == "completed"
    collected = tmp_path / "run/tree/project/app.py"
    assert collected.read_text() == "print('v2')\n"
    assert result["evidence"]["tree"]["project/app.py"] == attempt().sha256(collected.read_bytes())
    events = [json.loads(line) for line in (tmp_path / "run/events.jsonl").read_text().splitlines()]
    assert [e["kind"] for e in events] == [
        "provision", "stage-fixture", "install", "step", "collect", "cleanup",
    ]  # fmt: skip
    assert all(e["source"] == "controller" and e["schema"] == 1 for e in events)


def test_the_product_is_never_a_mounted_host_path(tmp_path, fixture_dir, fake):
    run(tmp_path, fixture_dir, install=[["sh", "-c", "install"]])
    flat = [part for call in fake.calls for part in call]
    assert not [p for p in flat if p.startswith(("type=bind", "/home", str(tmp_path)))]
    create = next(call for call in fake.calls if call[0] == "create")
    assert IMAGE in create
    for control in ["--network=none", "--cap-drop=ALL", "--security-opt=no-new-privileges",
                    "--read-only", "--user=1000:1000"]:  # fmt: skip
        assert control in create
    assert any(part.startswith("--memory=") for part in create)
    assert any(part.startswith("--pids-limit=") for part in create)


def test_baseline_arm_skips_installation(tmp_path, fixture_dir, fake):
    baseline = dict(PLANNED, arm="baseline", engine_sha256=None)
    attempt().run_attempt(
        baseline, run_dir=tmp_path / "run", fixture=fixture_dir,
        install=[["sh", "-c", "install"]], steps=[["sh", "-c", "step-one"]],
    )  # fmt: skip
    assert "exec:install" not in fake.verbs()
    assert "exec:step-one" in fake.verbs()


def test_controller_stages_a_neutral_git_anchor_before_treatment_install(
    tmp_path, fixture_dir, fake
):
    result = run(
        tmp_path,
        fixture_dir,
        planned=REAL_PLANNED,
        install=[["sh", "-c", "install"]],
    )

    assert result["git_anchor"] == ANCHOR
    commands = [call for call in fake.calls if call[0] == "exec"]
    init = next(call for call in commands if "init" in call)
    identity = [call for call in commands if "config" in call]
    commit = next(call for call in commands if "commit" in call)
    anchor = next(call for call in commands if "update-ref" in call)
    install = next(call for call in commands if call[-1] == "install")
    assert "--initial-branch=main" in init and "--template=" in init
    assert any(call[-2:] == ["user.name", "AI-DLC Evaluation"] for call in identity)
    assert any(call[-2:] == ["user.email", "evaluation@example.invalid"] for call in identity)
    assert "--env=GIT_AUTHOR_DATE=2000-01-01T00:00:00Z" in commit
    assert "--env=GIT_COMMITTER_DATE=2000-01-01T00:00:00Z" in commit
    assert anchor[-2:] == ["refs/ai-dlc/evaluation-anchor", ANCHOR]
    assert (
        commands.index(init)
        < commands.index(commit)
        < commands.index(anchor)
        < commands.index(install)
    )
    assert all(not any("ANTHROPIC_API_KEY" in part for part in call) for call in commands[:-1])
    events = [json.loads(line) for line in (tmp_path / "run/events.jsonl").read_text().splitlines()]
    assert [event["kind"] for event in events][2] == "git-anchor"


def test_fixture_cannot_supply_git_metadata_for_the_controller_anchor(tmp_path, fixture_dir, fake):
    (fixture_dir / ".git").mkdir()
    (fixture_dir / ".git/config").write_text("[core]\n\thooksPath = /fixture-hook\n")

    with pytest.raises(ValueError, match="Git metadata"):
        run(tmp_path, fixture_dir)

    assert fake.calls == []


def test_cleanup_failure_is_recorded_with_resource_ids_and_keeps_evidence(
    tmp_path, fixture_dir, fake
):
    fake.fail["rm"] = "device busy"
    result = run(tmp_path, fixture_dir)
    assert result["outcome"] == "completed"
    assert result["cleanup"]["clean"] is False
    failed = result["cleanup"]["failed"]
    assert failed[0]["kind"] == "container" and failed[0]["error"] == "device busy"
    assert failed[0]["id"].startswith("ai-dlc-eval-")
    ledger = (tmp_path / "run/cleanup-ledger.jsonl").read_text()
    assert failed[0]["id"] in ledger
    assert (tmp_path / "run/tree/project/app.py").exists()
    assert "volume rm" in fake.verbs()  # one failed removal does not skip the others


def test_failed_installation_is_infrastructure_not_product(tmp_path, fixture_dir, fake):
    fake.fail["exec:install"] = "no route to host"
    result = run(tmp_path, fixture_dir, install=[["sh", "-c", "install"]])
    assert result["outcome"] == "infrastructure"
    assert result["stage"] == "install"
    assert "exec:step-one" not in fake.verbs()
    assert "collect" in fake.verbs() and "rm" in fake.verbs()


def test_missing_docker_is_infrastructure_with_no_host_fallback(tmp_path, fixture_dir, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no host execution")

    monkeypatch.setattr(attempt().shutil, "which", lambda name: None)
    monkeypatch.setattr(attempt(), "_docker", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    result = run(tmp_path, fixture_dir)
    assert (result["outcome"], result["stage"]) == ("infrastructure", "provision")
    assert "Docker" in result["detail"]


def test_unpinned_image_and_symlinked_fixture_are_refused(tmp_path, fixture_dir, fake):
    with pytest.raises(ValueError, match="digest"):
        attempt().run_attempt(
            dict(PLANNED, image="python:3.12-slim"),
            run_dir=tmp_path / "run", fixture=fixture_dir, steps=[],
        )  # fmt: skip
    (fixture_dir / "link").symlink_to("/etc/passwd")
    with pytest.raises(ValueError, match="symlink"):
        run(tmp_path, fixture_dir)
    assert fake.calls == []


def test_collected_archive_cannot_escape_the_run_directory(tmp_path, fixture_dir, fake):
    fake.tree = archive({"../escaped.txt": b"x", "project/ok.txt": b"ok"})
    result = run(tmp_path, fixture_dir)
    assert not (tmp_path / "escaped.txt").exists()
    assert result["outcome"] == "incomplete"
    assert result["stage"] == "collect"


# --- Real Docker. Skipped, never passed, when Docker or the pinned image is absent. ---


def docker_ready():
    if not shutil.which("docker"):
        return False
    inspected = subprocess.run(
        ["docker", "image", "inspect", IMAGE], capture_output=True, check=False, timeout=30
    )
    return inspected.returncode == 0


docker = pytest.mark.skipif(
    not docker_ready(), reason="Docker or the digest-pinned image is unavailable; never pulled"
)
PY = ["python", "-c"]
WRITE = (
    "import pathlib,os;pathlib.Path('/work/project/made.txt').write_text('one');"
    "pathlib.Path(os.path.expanduser('~/home-marker')).write_text('x');print('wrote')"
)
PROBE = (
    "import pathlib,os,sys;"
    "sys.exit(pathlib.Path('/work/project/made.txt').exists()"
    " or pathlib.Path(os.path.expanduser('~/home-marker')).exists())"
)
EGRESS = (
    "import socket,sys;s=socket.socket();s.settimeout(3);"
    "sys.exit(0 if s.connect_ex(('1.1.1.1',443)) else 1)"
)


@docker
def test_real_attempts_start_from_fresh_state_and_return_evidence(tmp_path, fixture_dir):
    write = [*PY, WRITE]
    first = attempt().run_attempt(
        PLANNED, run_dir=tmp_path / "one", fixture=fixture_dir, steps=[write]
    )
    assert first["outcome"] == "completed", first
    assert (tmp_path / "one/tree/project/made.txt").read_text() == "one"
    assert (tmp_path / "one/tree/project/app.py").read_text() == "print('v1')\n"
    assert "wrote" in json.loads((tmp_path / "one/steps/01.json").read_text())["stdout"]
    probe = [*PY, PROBE]
    second = attempt().run_attempt(
        PLANNED, run_dir=tmp_path / "two", fixture=fixture_dir, steps=[probe]
    )
    assert second["outcome"] == "completed", second
    assert first["cleanup"]["clean"] and second["cleanup"]["clean"]
    leftovers = subprocess.check_output(
        ["docker", "ps", "-a", "--filter", "name=ai-dlc-eval-", "--format", "{{.Names}}"], text=True
    )
    assert first["resources"]["container"] not in leftovers


@docker
def test_real_timeout_stops_the_attempt_and_still_collects(tmp_path, fixture_dir):
    steps = [
        PY + ["import pathlib;pathlib.Path('/work/project/before.txt').write_text('kept')"],
        PY + ["import time;time.sleep(120)"],
    ]
    result = attempt().run_attempt(
        PLANNED, run_dir=tmp_path / "run", fixture=fixture_dir, steps=steps, timeout_seconds=4
    )
    assert (result["outcome"], result["limit"]) == ("incomplete", "timeout_minutes")
    assert (tmp_path / "run/tree/project/before.txt").read_text() == "kept"
    assert result["cleanup"]["clean"]


@docker
def test_real_cancellation_stops_the_attempt(tmp_path, fixture_dir):
    cancel = threading.Event()
    threading.Timer(1.5, cancel.set).start()
    result = attempt().run_attempt(
        PLANNED, run_dir=tmp_path / "run", fixture=fixture_dir,
        steps=[PY + ["import time;time.sleep(120)"]], cancel=cancel,
    )  # fmt: skip
    assert (result["outcome"], result["limit"]) == ("incomplete", "cancelled")
    assert result["cleanup"]["clean"]


@docker
def test_real_attempt_has_no_network_and_bounded_memory(tmp_path, fixture_dir):
    steps = [[*PY, EGRESS], [*PY, "x=bytearray(900*1024*1024);print(len(x))"]]
    result = attempt().run_attempt(
        PLANNED, run_dir=tmp_path / "run", fixture=fixture_dir, steps=steps, memory="128m"
    )
    first = json.loads((tmp_path / "run/steps/01.json").read_text())
    second = json.loads((tmp_path / "run/steps/02.json").read_text())
    assert first["exit_code"] == 0, "direct egress was possible"
    assert second["exit_code"] != 0
    assert result["outcome"] != "completed"
