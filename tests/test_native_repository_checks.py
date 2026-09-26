"""The contributor journey must not secretly require a POSIX shell on Windows."""

import tomllib
from pathlib import Path

from ai_dlc.setup.commands import parse_command

ROOT = Path(__file__).resolve().parents[1]


def test_contributor_setup_and_required_checks_have_native_command_records():
    config = tomllib.loads((ROOT / "ai-dlc.toml").read_text())
    commands = [config["checks"]["commands"][name] for name in config["checks"]["required"]]
    for step in config["setup"]["steps"]:
        commands.extend([step["command"], step["verify"]])
    for command in commands:
        assert parse_command(command).shell is None, command


def test_native_bootstrap_assets_are_packaged_byte_for_byte():
    for name in (
        "scripts/bootstrap.ps1",
        "bootstrap/windows.json",
        "bootstrap/windows.ps1",
        "bootstrap/windows-native.cs",
        "bootstrap/windows-select.py",
    ):
        assert (ROOT / name).read_bytes() == (
            ROOT / "project-templates/project" / name
        ).read_bytes()
