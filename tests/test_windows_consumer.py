"""Artifact refusals are portable; consumer qualification requires actual Windows."""

import hashlib
import importlib.util
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def driver():
    spec = importlib.util.spec_from_file_location(
        "windows_consumer", ROOT / "scripts/verify_windows_consumer.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hashes(directory):
    entries = sorted(path for path in directory.iterdir() if path.name != "SHA256SUMS")
    (directory / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in entries
        )
    )


@pytest.fixture
def artifacts(tmp_path):
    directory = tmp_path / "artifacts"
    directory.mkdir()
    values = {
        "ai_dlc-0.4.0-py3-none-any.whl": b"controlled wheel bytes",
        "requirements.txt": b"package==1 --hash=sha256:" + b"a" * 64 + b"\n",
        **{
            name: b"controlled helper bytes"
            for name in (
                "bootstrap.ps1",
                "windows.ps1",
                "windows.json",
                "windows-native.cs",
                "windows-select.py",
            )
        },
    }
    for name, body in values.items():
        (directory / name).write_bytes(body)
    (directory / "release.sh").write_text(
        "AI_DLC_ENGINE_VERSION=0.4.0\nAI_DLC_WHEEL_NAME=ai_dlc-0.4.0-py3-none-any.whl\n"
        "AI_DLC_WHEEL_URL=https://candidate.invalid/ai_dlc-0.4.0-py3-none-any.whl\n"
        f"AI_DLC_WHEEL_SHA256={hashlib.sha256(values['ai_dlc-0.4.0-py3-none-any.whl']).hexdigest()}\n"
        "AI_DLC_CONSTRAINTS_URL=https://candidate.invalid/requirements.txt\n"
        f"AI_DLC_CONSTRAINTS_SHA256={hashlib.sha256(values['requirements.txt']).hexdigest()}\n"
    )
    hashes(directory)
    return directory


def test_consumer_binds_original_manifest_and_all_artifact_digests(artifacts):
    result = driver().validate_artifacts(artifacts)
    assert result["manifest"]["AI_DLC_ENGINE_VERSION"] == "0.4.0"
    assert (
        result["hashes"]["release.sh"]
        == hashlib.sha256((artifacts / "release.sh").read_bytes()).hexdigest()
    )
    assert set(result["hashes"]) >= {"windows-native.cs", "windows-select.py", "requirements.txt"}


@pytest.mark.parametrize(
    "fault", ["tamper", "duplicate", "escape", "missing-helper", "manifest-drift"]
)
def test_consumer_rejects_artifact_drift_before_bootstrap(artifacts, fault):
    if fault == "tamper":
        (artifacts / "requirements.txt").write_bytes(b"different")
    elif fault == "duplicate":
        with (artifacts / "SHA256SUMS").open("a") as output:
            output.write((artifacts / "SHA256SUMS").read_text().splitlines()[0] + "\n")
    elif fault == "escape":
        (artifacts / "SHA256SUMS").write_text("a" * 64 + "  ../outside.whl\n")
    elif fault == "missing-helper":
        (artifacts / "windows-native.cs").unlink()
        hashes(artifacts)
    else:
        manifest = artifacts / "release.sh"
        manifest.write_text(
            manifest.read_text().replace("AI_DLC_WHEEL_SHA256=", "AI_DLC_WHEEL_SHA256=0")
        )
        hashes(artifacts)
    with pytest.raises(ValueError):
        driver().validate_artifacts(artifacts)


@pytest.mark.parametrize("layout", ["mingw64/bin", "bin", "cmd"])
def test_native_git_selects_existing_command_only_directory(tmp_path, layout):
    installation = tmp_path / "Git installation"
    selected = installation / layout / "git.exe"
    selected.parent.mkdir(parents=True)
    selected.write_bytes(b"existing git")
    command = installation / "cmd/git.exe"
    command.parent.mkdir(exist_ok=True)
    command.write_bytes(b"existing command git")
    if layout != "cmd":
        (selected.parent / "sh.exe").write_bytes(b"shell")
    assert driver().native_git(selected) == command
    assert command.read_bytes() == b"existing command git"


@pytest.mark.parametrize(
    "tool", ["SH.EXE", "bash.exe", "python.exe", "node.cmd", "uv.exe", "mise.exe"]
)
def test_native_git_refuses_runtime_or_shell_directory_without_safe_fallback(tmp_path, tool):
    selected = tmp_path / "Git/cmd/git.exe"
    selected.parent.mkdir(parents=True)
    selected.write_bytes(b"git")
    (selected.parent / tool).write_bytes(b"forbidden tool")
    with pytest.raises(ValueError, match="command-only Git"):
        driver().native_git(selected)


def test_consumer_child_environment_excludes_credentials_and_existing_runtimes(
    tmp_path, monkeypatch
):
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "OPENAI_API_KEY", "PYTHONPATH", "PSModulePath"):
        monkeypatch.setenv(name, "must-not-reach-the-consumer")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env = driver().controlled_environment(
        workspace, tmp_path / "gitcmd/git.exe", tmp_path / "windows"
    )
    assert not {
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "OPENAI_API_KEY",
        "PYTHONPATH",
        "PSModulePath",
    }.intersection(env)
    assert str(Path(sys.executable).parent) not in env["PATH"].split(os.pathsep)
    assert not Path(env["AI_DLC_BOOTSTRAP_HOME"]).exists()


def test_consumer_does_not_expose_system32_wsl_launchers(tmp_path):
    system = tmp_path / "windows"
    system32 = system / "System32"
    system32.mkdir(parents=True)
    for name in ("bash", "bash.exe"):
        launcher = system32 / name
        launcher.write_bytes(b"not executed")
        launcher.chmod(0o755)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env = driver().controlled_environment(workspace, tmp_path / "gitcmd/git.exe", system)
    assert str(system32) not in env["PATH"].split(os.pathsep)
    assert env["COMSPEC"] == str(system32 / "cmd.exe")


@pytest.mark.skipif(
    os.name != "nt", reason="requires actual native Windows bootstrap and consumers"
)
def test_native_exact_artifacts_bootstrap_generated_consumers(tmp_path):
    selected = os.environ.get("AI_DLC_WINDOWS_CONSUMER_ARTIFACTS")
    if selected:
        directory = Path(selected)
    else:
        directory = tmp_path / "candidate"
        directory.mkdir()
        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(directory)], cwd=ROOT, check=True
        )
        subprocess.run(
            [
                "uv",
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements-txt",
                "--output-file",
                str(directory / "requirements.txt"),
            ],
            cwd=ROOT,
            check=True,
        )
        version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/prepare_release_assets.py"),
                "--artifacts",
                str(directory),
                "--base-url",
                "https://candidate.invalid/windows",
                "--version",
                version,
            ],
            cwd=ROOT,
            check=True,
        )
    evidence = Path(os.environ.get("AI_DLC_WINDOWS_CONSUMER_EVIDENCE", str(tmp_path / "evidence")))
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/verify_windows_consumer.py"),
            "--artifacts",
            str(directory),
            "--workspace",
            str(tmp_path / "journey space é"),
            "--evidence",
            str(evidence),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=2400,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr + f"\nEvidence: {evidence}"
    import json

    report = json.loads((evidence / "result.json").read_text())
    assert report["status"] == "passed"
    assert set(report["consumers"]) == {"generic", "python"}
    assert report["controller"]["revision"]
    assert (
        report["artifacts"]["hashes"]["release.sh"]
        == hashlib.sha256((directory / "release.sh").read_bytes()).hexdigest()
    )
