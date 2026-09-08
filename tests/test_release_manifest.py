"""Candidate artifacts are data-bound; no publication or real package install."""

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def candidate(tmp_path, version="0.4.0"):
    wheel = tmp_path / f"ai_dlc-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"ai_dlc-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: ai-dlc\nVersion: {version}\n",
        )
    constraints = tmp_path / "requirements.txt"
    constraints.write_text("example==1.0 --hash=sha256:" + "a" * 64 + "\n")
    output = tmp_path / "release.sh"
    command = [
        sys.executable,
        str(ROOT / "scripts/release_manifest.py"),
        "--artifacts",
        str(tmp_path),
        "--base-url",
        "https://example.test/releases/v0.4.0",
        "--version",
        "0.4.0",
        "--output",
        str(output),
    ]
    return command, wheel, constraints, output


def test_candidate_manifest_binds_actual_artifacts_for_shell_consumer(tmp_path):
    command, wheel, constraints, output = candidate(tmp_path)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    consumed = subprocess.run(
        [
            "sh",
            "-c",
            (
                '. "$1"; printf "%s\\n" "$AI_DLC_ENGINE_VERSION" '
                '"$AI_DLC_WHEEL_NAME" "$AI_DLC_WHEEL_URL" "$AI_DLC_WHEEL_SHA256" '
                '"$AI_DLC_CONSTRAINTS_URL" "$AI_DLC_CONSTRAINTS_SHA256"'
            ),
            "sh",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert consumed.stdout.splitlines() == [
        "0.4.0",
        wheel.name,
        "https://example.test/releases/v0.4.0/" + wheel.name,
        hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "https://example.test/releases/v0.4.0/requirements.txt",
        hashlib.sha256(constraints.read_bytes()).hexdigest(),
    ]


@pytest.mark.parametrize(
    "fault",
    [
        "wrong-version",
        "multiple",
        "missing-constraints",
        "existing",
        "http",
        "credentials",
        "shell",
        "wrong-name",
    ],
)
def test_candidate_manifest_refuses_unverified_or_ambiguous_input(tmp_path, fault):
    command, wheel, constraints, output = candidate(
        tmp_path, "0.3.0" if fault == "wrong-version" else "0.4.0"
    )
    if fault == "multiple":
        (tmp_path / "other.whl").write_bytes(wheel.read_bytes())
    elif fault == "missing-constraints":
        constraints.unlink()
    elif fault == "existing":
        output.write_text("authored\n")
    elif fault in {"http", "credentials", "shell"}:
        command[command.index("--base-url") + 1] = {
            "http": "http://example.test/release",
            "credentials": "https://user:secret@example.test/release",
            "shell": "https://example.test/$(touch injected)",
        }[fault]
    elif fault == "wrong-name":
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("ai_dlc-0.4.0.dist-info/METADATA", "Name: unrelated\nVersion: 0.4.0\n")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "Candidate manifest:" in result.stderr
    assert output.read_text() == "authored\n" if fault == "existing" else not output.exists()


def test_candidate_hashes_the_same_wheel_bytes_whose_identity_was_validated(tmp_path, monkeypatch):
    """A replacement after ZIP validation must not authenticate another wheel's bytes."""
    import runpy

    _, wheel, constraints, _ = candidate(tmp_path)
    original_digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    original_exit = zipfile.ZipFile.__exit__

    def replace_after_validation(archive, *args):
        result = original_exit(archive, *args)
        replacement = tmp_path / "replacement"
        replacement.write_bytes(b"different wheel after metadata validation")
        replacement.replace(wheel)
        return result

    monkeypatch.setattr(zipfile.ZipFile, "__exit__", replace_after_validation)
    generate = runpy.run_path(str(ROOT / "scripts/release_manifest.py"))["manifest"]
    content = generate(tmp_path, "https://example.test/release", "0.4.0")
    assert f"AI_DLC_WHEEL_SHA256={original_digest}\n" in content
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() != original_digest
    assert constraints.exists()
