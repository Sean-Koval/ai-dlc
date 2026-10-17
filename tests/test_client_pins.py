import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_client_pins.py"


def run(lock: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--hangar-lock", str(lock)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_matching_lock_passes(tmp_path):
    lock = tmp_path / "harnesses.lock.yaml"
    lock.write_text("claude-code:\n  version: 2.1.296\ncodex:\n  version: 0.162.1\n")
    result = run(lock)
    assert result.returncode == 0, result.stderr
    assert "match" in result.stdout


def test_drifted_lock_names_each_client(tmp_path):
    lock = tmp_path / "harnesses.lock.yaml"
    lock.write_text("claude-code:\n  version: 2.1.300\ncodex:\n  version: 0.170.0\n")
    result = run(lock)
    assert result.returncode == 1
    assert "claude-code: catalog 2.1.296 != hangar 2.1.300" in result.stderr
    assert "codex: catalog 0.162.1 != hangar 0.170.0" in result.stderr
