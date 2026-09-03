import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_plan_needs_no_python_or_mise():
    result = subprocess.run(
        ["sh", str(ROOT / "scripts/bootstrap.sh"), "--source", "--plan"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "mode=source" in result.stdout
    assert "github.com/astral-sh/uv/releases/download/0.9.11" in result.stdout


def test_digest_mismatch_never_installs_download(tmp_path):
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    curl = fakebin / "curl"
    curl.write_text(
        '#!/bin/sh\nfor arg do previous=$last; last=$arg; done\nprintf tampered > "$last"\n'
    )
    curl.chmod(0o755)
    destination = tmp_path / "download"
    script = '. "$1"; ai_dlc_download https://example.test/file "$2" "$3"'
    result = subprocess.run(
        [
            "sh",
            "-c",
            script,
            "sh",
            str(ROOT / "bootstrap/download.sh"),
            hashlib.sha256(b"expected").hexdigest(),
            str(destination),
        ],
        env={**os.environ, "PATH": str(fakebin) + ":" + os.environ["PATH"]},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "digest mismatch" in result.stderr
    assert not destination.exists()


def test_devcontainer_keeps_linux_environment_off_the_host_checkout():
    config = json.loads((ROOT / ".devcontainer/devcontainer.json").read_text())

    assert (
        "source=${devcontainerId}-venv,target=${containerWorkspaceFolder}/.venv,type=volume"
        in config["mounts"]
    )
    assert config["postCreateCommand"].startswith("sudo chown -R vscode:vscode .venv && ")
