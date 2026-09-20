"""One isolated evaluation attempt: provision, install, drive, collect, then clean up.

The controller stays on the host. The attempt's project lives in a per-attempt volume
so a separate collector can read it after the agent's container is stopped, and nothing
from the host is mounted into the attempt. There is no host fallback.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import tarfile
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

PINNED = re.compile(r"([^\s@]+@)?sha256:[0-9a-f]{64}")
AGENT = "1000:1000"
HOST = re.compile(r"[a-z0-9]([a-z0-9.-]*[a-z0-9])?")
PROXY_SOURCE = Path(__file__).parents[1] / "test_proxy.py"
ISOLATION = [
    "--read-only",
    "--cap-drop=ALL",
    "--security-opt=no-new-privileges",
]


class Stopped(Exception):
    """A limit or cancellation ended the attempt; `limit` names which."""

    def __init__(self, limit: str):
        super().__init__(limit)
        self.limit = limit


class StageFailed(Exception):
    def __init__(self, stage: str, outcome: str, detail: str):
        super().__init__(detail)
        self.stage, self.outcome, self.detail = stage, outcome, detail


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _docker(args, *, timeout: float, input: bytes | None = None, cancel=None):
    """Run the docker CLI, polling so a deadline or cancellation interrupts a long exec."""
    process = subprocess.Popen(
        ["docker", *args],
        stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    result: dict = {}

    def communicate():
        result["out"], result["err"] = process.communicate(input)

    reader = threading.Thread(target=communicate, daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout
    while reader.is_alive():
        reader.join(0.2)
        limit = (
            "cancelled"
            if cancel is not None and cancel.is_set()
            else "timeout_minutes"
            if time.monotonic() > deadline
            else None
        )
        if limit and reader.is_alive():
            process.kill()
            reader.join(5)
            raise Stopped(limit)
    return subprocess.CompletedProcess(
        args, process.returncode, result.get("out", b""), result.get("err", b"")
    )


def _fixture_archive(fixture: Path) -> bytes:
    fixture = fixture.resolve()
    if not fixture.is_dir():
        raise ValueError(f"Evaluation fixture is not a directory: {fixture}")
    if any(p.is_symlink() for p in fixture.rglob("*")):
        raise ValueError("Evaluation fixtures cannot include a symlink")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        tar.add(fixture, arcname=".", recursive=True)
    return buffer.getvalue()


def _extract(data: bytes, destination: Path) -> dict[str, str]:
    """Unpack collected evidence with the data filter, which refuses traversal and links."""
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(destination, filter="data")
    return {
        p.relative_to(destination).as_posix(): sha256(p.read_bytes())
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }


class _Attempt:
    def __init__(
        self, planned, run_dir, fixture, install, steps, timeout, cancel, memory, pids, egress
    ):
        self.planned, self.run_dir, self.egress = planned, run_dir, egress
        self.fixture, self.install, self.steps = fixture, install, steps
        self.cancel, self.memory, self.pids = cancel, memory, pids
        self.deadline = time.monotonic() + timeout
        uid = "ai-dlc-eval-" + uuid.uuid4().hex[:12]
        self.container, self.volume = uid, uid + "-work"
        self.proxy, self.internal, self.external = uid + "-proxy", uid + "-int", uid + "-ext"
        self.created: list[tuple[str, str]] = []

    def event(self, kind: str, **fields) -> None:
        record = {
            "schema": 1,
            "source": "controller",
            "at": datetime.now(UTC).isoformat(),
            "kind": kind,
            **fields,
        }
        with (self.run_dir / "events.jsonl").open("a") as log:
            log.write(json.dumps(record, sort_keys=True) + "\n")

    def docker(self, *args, input=None, bounded=True, floor=30.0):
        remaining = self.deadline - time.monotonic()
        if bounded and remaining <= 0:
            raise Stopped("timeout_minutes")
        # Controller-owned collection and cleanup keep a floor so a spent deadline
        # cannot discard evidence.
        timeout = remaining if bounded else max(remaining, floor)
        return _docker(
            list(args), timeout=timeout, input=input, cancel=self.cancel if bounded else None
        )

    def must(self, stage: str, outcome: str, *args, input=None):
        done = self.docker(*args, input=input)
        if done.returncode:
            raise StageFailed(stage, outcome, done.stderr.decode(errors="replace").strip())
        return done

    def provision(self) -> None:
        if not shutil.which("docker"):
            raise StageFailed("provision", "infrastructure", "Docker is required; no host fallback")
        self.must("provision", "infrastructure", "volume", "create", self.volume)
        self.created.append(("volume", self.volume))
        self.must(
            "provision",
            "infrastructure",
            "create",
            "--name",
            self.container,
            *(self.start_proxy() if self.egress else ["--network=none"]),
            *ISOLATION,
            f"--user={AGENT}",
            f"--memory={self.memory}",
            f"--pids-limit={self.pids}",
            "--tmpfs=/tmp:rw,nosuid,size=256m",
            "--tmpfs=/home/agent:rw,nosuid,exec,uid=1000,gid=1000,size=512m",
            "--env=HOME=/home/agent",
            "--workdir=/work/project",
            "--mount",
            f"type=volume,src={self.volume},dst=/work",
            self.planned["image"],
            "sleep",
            "infinity",
        )
        self.created.append(("container", self.container))
        self.event("provision", container=self.container, volume=self.volume)

    def start_proxy(self) -> list[str]:
        """The agent's only route out: an internal network whose one other member is the proxy."""
        self.must("provision", "infrastructure", "network", "create", "--internal", self.internal)
        self.created.append(("network", self.internal))
        self.must("provision", "infrastructure", "network", "create", self.external)
        self.created.append(("network", self.external))
        self.must(
            "provision",
            "infrastructure",
            "run",
            "-d",
            "--name",
            self.proxy,
            f"--network={self.external}",
            *ISOLATION,
            "--user=65534:65534",
            "--memory=128m",
            "--pids-limit=128",
            "--env=ALLOW_HOSTS=" + ",".join(self.egress["hosts"]),
            self.egress["proxy_image"],
            "python",
            "-u",
            "-c",
            # Passed as text so that no host path is mounted anywhere.
            PROXY_SOURCE.read_text(),
        )
        self.created.append(("container", self.proxy))
        self.must("provision", "infrastructure", "network", "connect", self.internal, self.proxy)
        address = f"http://{self.proxy}:8080"
        return [
            f"--network={self.internal}",
            f"--env=HTTPS_PROXY={address}",
            f"--env=https_proxy={address}",
        ]

    def collect_egress(self) -> dict:
        """Retain the proxy's decision log verbatim; an unreadable log is not a clean result."""
        done = self.docker("logs", self.proxy, bounded=False)
        if done.returncode:
            raise StageFailed("collect", "incomplete", "egress log unavailable")
        (self.run_dir / "egress.jsonl").write_bytes(done.stdout)
        seen: dict[bool, set[str]] = {True: set(), False: set()}
        for line in done.stdout.decode(errors="replace").splitlines():
            try:
                record = json.loads(line)
                seen[bool(record["allowed"])].add(str(record["host"]))
            except (ValueError, KeyError, TypeError) as exc:
                raise StageFailed("collect", "incomplete", "egress log malformed") from exc
        summary = {"allowed": sorted(seen[True]), "refused": sorted(seen[False])}
        self.event("egress", **summary)
        return summary

    def stage_fixture(self) -> None:
        # Controller-owned stager: the only root process, gone before the agent starts.
        self.must(
            "stage-fixture",
            "infrastructure",
            "run",
            "--rm",
            "-i",
            "--network=none",
            "--cap-drop=ALL",
            "--cap-add=CHOWN",
            "--cap-add=DAC_OVERRIDE",
            "--cap-add=FOWNER",
            "--security-opt=no-new-privileges",
            "--mount",
            f"type=volume,src={self.volume},dst=/w",
            self.planned["image"],
            "sh",
            "-c",
            f"mkdir -p /w/project && tar -x -C /w/project && chown -R {AGENT} /w",
            input=_fixture_archive(self.fixture),
        )
        self.must("stage-fixture", "infrastructure", "start", self.container)
        self.event("stage-fixture", sha256=sha256(_fixture_archive(self.fixture)))

    def run_install(self) -> None:
        # The baseline arm differs in exactly this: nothing is installed.
        commands = self.install if self.planned["arm"] == "treatment" else []
        for command in commands:
            self.must("install", "infrastructure", "exec", self.container, *command)
        self.event("install", commands=len(commands), engine_sha256=self.planned["engine_sha256"])

    def drive(self) -> None:
        (self.run_dir / "steps").mkdir(exist_ok=True)
        for index, command in enumerate(self.steps, start=1):
            done = self.docker("exec", self.container, *command)
            record = {
                "command": command,
                "exit_code": done.returncode,
                "stdout": done.stdout.decode(errors="replace"),
                "stderr": done.stderr.decode(errors="replace"),
            }
            (self.run_dir / "steps" / f"{index:02d}.json").write_text(
                json.dumps(record, indent=2, sort_keys=True) + "\n"
            )
            self.event("step", index=index, exit_code=done.returncode)
            if done.returncode:
                killed = self.docker(
                    "inspect", "--format", "{{.State.OOMKilled}}", self.container, bounded=False
                )
                if killed.stdout.decode().strip() == "true" or done.returncode == 137:
                    raise StageFailed("step", "infrastructure", "memory limit reached")
                raise StageFailed("step", "incomplete", f"step {index} exited {done.returncode}")

    def collect(self) -> dict:
        """Stop the agent, then read its project through a separate read-only collector."""
        self.docker("kill", self.container, bounded=False)
        done = self.docker(
            "run",
            "--rm",
            "--network=none",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--mount",
            f"type=volume,src={self.volume},dst=/w,readonly",
            self.planned["image"],
            "tar",
            "-c",
            "-C",
            "/w",
            "project",
            bounded=False,
            floor=120.0,
        )
        if done.returncode:
            raise StageFailed("collect", "incomplete", done.stderr.decode(errors="replace").strip())
        try:
            tree = _extract(done.stdout, self.run_dir / "tree")
        except (tarfile.TarError, OSError) as exc:
            shutil.rmtree(self.run_dir / "tree", ignore_errors=True)
            raise StageFailed(
                "collect", "incomplete", f"unsafe or unreadable evidence: {exc}"
            ) from exc
        self.event("collect", files=len(tree))
        return {"tree": tree}

    def cleanup(self) -> dict:
        failed = []
        for kind, name in reversed(self.created):
            args = {
                "container": ("rm", "-f", name),
                "volume": ("volume", "rm", "-f", name),
                "network": ("network", "rm", name),
            }[kind]
            try:
                done = self.docker(*args, bounded=False)
                error = done.stderr.decode(errors="replace").strip() if done.returncode else None
            except (Stopped, OSError) as exc:
                error = str(exc)
            if error:
                failed.append({"kind": kind, "id": name, "error": error})
        if failed:
            with (self.run_dir / "cleanup-ledger.jsonl").open("a") as ledger:
                for item in failed:
                    ledger.write(json.dumps(item, sort_keys=True) + "\n")
        self.event("cleanup", clean=not failed)
        return {"clean": not failed, "failed": failed}


def run_attempt(
    planned: dict,
    *,
    run_dir: Path,
    fixture: Path,
    steps: list[list[str]],
    install: list[list[str]] | None = None,
    timeout_seconds: float | None = None,
    cancel: threading.Event | None = None,
    memory: str = "1g",
    pids: int = 256,
    egress: dict | None = None,
) -> dict:
    """Run one planned attempt and return its driver-level outcome with evidence references."""
    if not PINNED.fullmatch(planned.get("image", "")):
        raise ValueError("Evaluation image must be pinned by digest")
    if egress is not None and (
        not PINNED.fullmatch(egress.get("proxy_image", ""))
        or not egress.get("hosts")
        or not all(HOST.fullmatch(host) for host in egress["hosts"])
    ):
        raise ValueError("Evaluation egress needs host names and a proxy image pinned by digest")
    _fixture_archive(fixture)  # refuse an unsafe fixture before anything is created
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "inputs.json").write_text(
        json.dumps({"planned": planned, "steps": steps, "install": install or []}, indent=2)
    )
    timeout = timeout_seconds or planned["limits"]["timeout_minutes"] * 60
    state = _Attempt(
        planned, run_dir, fixture, install or [], steps, timeout, cancel, memory, pids, egress
    )
    result: dict = {
        "scenario": planned["scenario"],
        "arm": planned["arm"],
        "attempt": planned["attempt"],
        "outcome": "completed",
        "stage": None,
        "limit": None,
        "detail": None,
        "resources": {"container": state.container, "volume": state.volume},
        # Disk is metered by collection size only; the local volume driver enforces no quota.
        "enforced": ["timeout_minutes", "memory", "pids", "network"],
    }
    try:
        state.provision()
        state.stage_fixture()
        state.run_install()
        state.drive()
    except Stopped as stop:
        result.update(outcome="incomplete", stage="step", limit=stop.limit)
    except StageFailed as failure:
        result.update(outcome=failure.outcome, stage=failure.stage, detail=failure.detail)
        if failure.detail == "memory limit reached":
            result["limit"] = "memory"
    try:
        result["evidence"] = state.collect() if state.created else {"tree": {}}
        if egress and ("container", state.proxy) in state.created:
            result["egress"] = state.collect_egress()
            result["evidence"]["egress.jsonl"] = sha256((run_dir / "egress.jsonl").read_bytes())
    except (Stopped, StageFailed) as failure:
        result.setdefault("evidence", {"tree": {}})  # a collected tree survives a lost log
        if result["outcome"] == "completed":
            result.update(outcome="incomplete", stage="collect", detail=str(failure))
    result["cleanup"] = state.cleanup() if state.created else {"clean": True, "failed": []}
    (run_dir / "attempt.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def run_isolated(image: str, archive: bytes, command: str, *, timeout: float) -> dict:
    """Run a controller-owned command over an unpacked archive; no network, nothing mounted."""
    if not PINNED.fullmatch(image):
        raise ValueError("Evaluation image must be pinned by digest")
    done = _docker(
        [
            "run",
            "--rm",
            "-i",
            "--network=none",
            *ISOLATION,
            f"--user={AGENT}",
            "--memory=512m",
            "--pids-limit=128",
            "--tmpfs=/tmp:rw,nosuid,size=64m",
            "--tmpfs=/g:rw,nosuid,exec,uid=1000,gid=1000,size=256m",
            "--env=HOME=/tmp",
            "--env=PYTHONDONTWRITEBYTECODE=1",
            image,
            "sh",
            "-c",
            f"tar -x -C /g && cd /g && {command}",
        ],
        timeout=timeout,
        input=archive,
    )
    return {
        "exit_code": done.returncode,
        "stdout": done.stdout.decode(errors="replace"),
        "stderr": done.stderr.decode(errors="replace"),
    }
