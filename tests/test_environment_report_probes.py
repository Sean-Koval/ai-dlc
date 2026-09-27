"""Explicit built-in probes, including real bounded subprocess behavior."""

import os
import subprocess
import sys
import time

import pytest

from ai_dlc.environment import version_probes


def test_missing_and_unsupported_tools_never_start_a_process(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("unexpected process")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert version_probes.probe_version("python", environ={"PATH": ""})["state"] == "missing"
    assert (
        version_probes.probe_version("SECRET-command", environ={"PATH": ""})["state"]
        == "unsupported"
    )


@pytest.mark.parametrize(
    "output,observed",
    [
        (b"Python 3.12.11\n", "3.12.11"),
        (b"Python 3.12.11 SECRET\n", None),
        (b"SECRET 3.12.11\n", None),
        (b"Python 3.12.11\nSECRET\n", None),
    ],
)
def test_strict_parser_discards_unrecognized_output(output, observed):
    assert version_probes.parse_version("python", output) == observed


def test_real_probe_uses_fixed_argv_and_minimal_environment(monkeypatch):
    actual = subprocess.Popen
    calls = []

    def start(argv, **kwargs):
        calls.append((argv, kwargs))
        return actual([sys.executable, "-c", "print('Python 3.12.11')"], **kwargs)

    monkeypatch.setattr(subprocess, "Popen", start)
    monkeypatch.setattr(version_probes, "find_executable", lambda *_: sys.executable)
    result = version_probes.probe_version(
        "python", environ={**os.environ, "SECRET_TOKEN": "secret"}
    )
    assert result == {"observed": "3.12.11", "state": "observed", "reason": None}
    assert calls[0][0] == [sys.executable, "--version"]
    assert "SECRET_TOKEN" not in calls[0][1]["env"]
    assert calls[0][1]["stdin"] == subprocess.DEVNULL
    assert calls[0][1].get("shell", False) is False


@pytest.mark.parametrize(
    "script,reason",
    [
        ("import os; os.write(1, b'x'*12000); os.write(2, b'y'*12000)", "output-limit"),
        ("import sys; print('SECRET'); sys.exit(1)", "probe-failed"),
        ("import os; os.write(1, b'\\xff\\xfeSECRET')", "unsupported-version"),
    ],
)
def test_real_output_cap_and_discarded_errors_survive_delayed_startup(monkeypatch, script, reason):
    actual = subprocess.Popen

    def start(argv, **kwargs):
        time.sleep(0.3)
        return actual([sys.executable, "-c", script], **kwargs)

    monkeypatch.setattr(subprocess, "Popen", start)
    monkeypatch.setattr(version_probes, "find_executable", lambda *_: sys.executable)
    start = time.monotonic()
    result = version_probes.probe_version("python", environ=os.environ)
    assert time.monotonic() - start < version_probes.TIMEOUT_SECONDS + 1
    assert result == {"observed": None, "state": "unknown", "reason": reason}


def test_real_timeout_is_bounded(monkeypatch):
    actual = subprocess.Popen
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda argv, **kwargs: actual(
            [sys.executable, "-c", "import time; time.sleep(30)"], **kwargs
        ),
    )
    monkeypatch.setattr(version_probes, "find_executable", lambda *_: sys.executable)
    monkeypatch.setattr(version_probes, "TIMEOUT_SECONDS", 0.2)
    start = time.monotonic()
    result = version_probes.probe_version("python", environ=os.environ)
    assert time.monotonic() - start < 2
    assert result == {"observed": None, "state": "unknown", "reason": "probe-timeout"}


def test_inherited_output_pipe_cannot_extend_deadline(monkeypatch):
    actual = subprocess.Popen
    script = "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(1)']); print('Python 3.12.11')"
    monkeypatch.setattr(
        subprocess, "Popen", lambda argv, **kwargs: actual([sys.executable, "-c", script], **kwargs)
    )
    monkeypatch.setattr(version_probes, "find_executable", lambda *_: sys.executable)
    monkeypatch.setattr(version_probes, "TIMEOUT_SECONDS", 0.2)
    start = time.monotonic()
    result = version_probes.probe_version("python", environ=os.environ)
    assert time.monotonic() - start < 0.9
    assert result["reason"] == "probe-timeout"


def test_windows_batch_wrappers_are_not_executed(monkeypatch):
    monkeypatch.setattr(version_probes, "find_executable", lambda *_: "C:\\private\\npm.cmd")

    def forbidden(*args, **kwargs):
        pytest.fail("batch wrappers require a shell")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert (
        version_probes.probe_version("npm", environ={"PATH": "private"})["state"] == "unsupported"
    )


def test_capture_never_reads_more_than_combined_limit(monkeypatch):
    actual, original_read = subprocess.Popen, os.read
    sizes = []
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda argv, **kwargs: actual(
            [sys.executable, "-c", "import os; os.write(1,b'x'*1000000)"], **kwargs
        ),
    )
    monkeypatch.setattr(version_probes, "find_executable", lambda *_: sys.executable)

    def read(descriptor, count):
        result = original_read(descriptor, count)
        if count <= 4096:  # Popen's independent startup error pipe uses a larger read.
            sizes.append(len(result))
        return result

    monkeypatch.setattr(os, "read", read)
    assert version_probes.probe_version("python", environ=os.environ)["reason"] == "output-limit"
    assert sum(sizes) <= 16384


def test_default_deadline_really_returns_after_five_seconds(monkeypatch):
    actual = subprocess.Popen
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda argv, **kwargs: actual(
            [sys.executable, "-c", "import time; time.sleep(30)"], **kwargs
        ),
    )
    monkeypatch.setattr(version_probes, "find_executable", lambda *_: sys.executable)
    start = time.monotonic()
    result = version_probes.probe_version("python", environ=os.environ)
    elapsed = time.monotonic() - start
    assert result["reason"] == "probe-timeout"
    assert 4.5 <= elapsed < 6.5


def test_windows_lookup_uses_supplied_extensions_without_ambient_fallback(tmp_path, monkeypatch):
    executable = tmp_path / "python.EXE"
    executable.write_bytes(b"fixture")
    executable.chmod(0o700)
    monkeypatch.setattr(version_probes, "_WINDOWS", True, raising=False)
    monkeypatch.setenv("PATHEXT", ".SECRET")
    assert version_probes.find_executable(
        "python", {"PATH": str(tmp_path), "PATHEXT": ".EXE"}
    ) == str(executable)
