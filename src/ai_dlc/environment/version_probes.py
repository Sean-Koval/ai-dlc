"""Fixed, opt-in executable version observations; raw child output never escapes.

A PATH executable is trusted to implement its version flag. This is not a sandbox.
The single binary reader owns its pipe, so an inherited pipe cannot delay the
caller's deadline through a blocking stream close or unbounded communicate().
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import threading
import time
from collections.abc import Mapping

_WINDOWS = os.name == "nt"
TIMEOUT_SECONDS = 5.0
MAX_OUTPUT_BYTES = 16 * 1024
_NUMBER = r"([0-9]+(?:\.[0-9]+)*)"
# Full-output matches only; suffixes are fixed adapter grammar, never exported.
_PATTERNS = {
    "ai-dlc": rf"(?:ai-dlc(?:, version)? )?{_NUMBER}",
    "python": rf"Python {_NUMBER}",
    "uv": rf"uv {_NUMBER}(?: \([0-9a-f]+ [0-9-]+\))?",
    "node": rf"v{_NUMBER}",
    "npm": _NUMBER,
    "npx": _NUMBER,
    "git": rf"git version {_NUMBER}(?:\.windows\.[0-9]+| \(Apple Git-[0-9]+\))?",
    "gh": rf"gh version {_NUMBER}(?: \([0-9-]+\))?(?:\nhttps://github.com/cli/cli/releases/tag/v[0-9.]+)?",
    "cargo": rf"cargo {_NUMBER}(?: \([0-9a-f]+ [0-9-]+\))?",
    "rustc": rf"rustc {_NUMBER}(?: \([0-9a-f]+ [0-9-]+\))?",
    "docker": rf"Docker version {_NUMBER}, build [0-9a-f]+",
    "code": rf"{_NUMBER}\n[0-9a-f]+\n(?:x64|arm64|ia32)",
    "codex": rf"codex-cli {_NUMBER}",
    "claude": rf"{_NUMBER} \(Claude Code\)",
    "openspec": _NUMBER,
    "wrangler": _NUMBER,
}


def supports_probe(name: str) -> bool:
    """Whether a fixed built-in executable observation exists."""
    return name in _PATTERNS


def find_executable(name: str, environ: Mapping[str, str]) -> str | None:
    """Only fixed adapter names are looked up; an empty PATH means no lookup."""
    if name not in _PATTERNS or not environ.get("PATH"):
        return None
    if not _WINDOWS:
        return shutil.which(name, path=environ["PATH"])
    # shutil.which consults ambient PATHEXT on Windows even with explicit PATH.
    # Use only the caller's lookup environment and never add the current directory.
    extensions = environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
    for directory in environ["PATH"].split(";"):
        for extension in extensions:
            if extension.lower() not in {".com", ".exe", ".bat", ".cmd"}:
                continue
            candidate = os.path.join(directory.strip('"'), name + extension)
            if os.path.isfile(candidate) and os.access(candidate, os.F_OK | os.X_OK):
                return candidate
    return None


def parse_version(name: str, output: bytes) -> str | None:
    """Accept one bounded, complete known version response, without free text."""
    pattern = _PATTERNS.get(name)
    if pattern is None or len(output) >= MAX_OUTPUT_BYTES:
        return None
    try:
        text = output.decode("utf-8").strip("\r\n").replace("\r\n", "\n")
    except UnicodeDecodeError:
        return None
    match = re.fullmatch(pattern, text)
    return match.group(1) if match and len(match.group(1)) <= 64 else None


def _unknown(reason: str, state: str = "unknown") -> dict:
    return {"observed": None, "state": state, "reason": reason}


def _stop(process: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except OSError:
        pass
    # poll is nonblocking. The reader eventually reaps if descendants hold its pipe.
    process.poll()


def probe_version(name: str, *, environ: Mapping[str, str]) -> dict:
    """Run a fixed --version probe with a five-second/16 KiB combined bound."""
    if name not in _PATTERNS:
        return _unknown("not-assessed", "unsupported")
    executable = find_executable(name, environ)
    if executable is None:
        return _unknown("not-found", "missing")
    if executable.lower().endswith((".cmd", ".bat")):
        return _unknown("not-assessed", "unsupported")
    environment = {
        key: value
        for key, value in environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "PATHEXT"}
    }
    environment.update({"LC_ALL": "C", "LANG": "C", "NO_COLOR": "1"})
    deadline = time.monotonic() + TIMEOUT_SECONDS
    try:
        process = subprocess.Popen(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=environment,
            shell=False,
            bufsize=0,
            start_new_session=os.name == "posix",
        )
    except OSError:
        return _unknown("probe-failed")
    output = bytearray()
    done = threading.Event()
    failed = threading.Event()
    overflow = threading.Event()
    pipe = process.stdout
    assert pipe is not None

    def read() -> None:
        try:
            with pipe:
                while len(output) < MAX_OUTPUT_BYTES:
                    chunk = os.read(pipe.fileno(), min(4096, MAX_OUTPUT_BYTES - len(output)))
                    if not chunk:
                        break
                    output.extend(chunk)
                if len(output) == MAX_OUTPUT_BYTES:
                    overflow.set()
        except OSError:
            failed.set()
        finally:
            done.set()
            process.poll()

    threading.Thread(target=read, daemon=True, name="ai-dlc-version-probe").start()
    if not done.wait(max(0.0, deadline - time.monotonic())):
        _stop(process)
        return _unknown("probe-timeout")
    if overflow.is_set():
        _stop(process)
        return _unknown("output-limit")
    if failed.is_set():
        _stop(process)
        return _unknown("probe-failed")
    try:
        code = process.wait(timeout=max(0.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        _stop(process)
        return _unknown("probe-timeout")
    if code != 0:
        return _unknown("probe-failed")
    version = parse_version(name, bytes(output))
    if version is None:
        return _unknown("unsupported-version")
    return {"observed": version, "state": "observed", "reason": None}
