"""The bootstrap bin resolver and the owned shell activation section are shared and safe."""

import json
import os
import shlex
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.environment.bootstrap import (
    activation_line,
    bootstrap_bin,
    configured_bin,
    plan_shell_activation,
)
from ai_dlc.errors import RefusedError
from ai_dlc.harness.agents import managed_section, read_managed_section

AUTHORED = "export SECRET_TOKEN=do-not-return\nalias ll='ls -l'\n"


@pytest.fixture
def machine(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = home / ".local/share/ai-dlc/bootstrap/bin"
    bin_dir.mkdir(parents=True)
    environ = {"HOME": str(home), "SHELL": "/bin/zsh", "PATH": "/usr/bin:/bin"}
    return home, bin_dir, environ


def test_bootstrap_bin_honours_the_same_overrides_as_diagnostics(tmp_path):
    home = tmp_path / "home"
    assert bootstrap_bin({}, home) == home / ".local/share/ai-dlc/bootstrap/bin"
    data = {"XDG_DATA_HOME": str(tmp_path / "data")}
    assert bootstrap_bin(data, home) == tmp_path / "data/ai-dlc/bootstrap/bin"
    override = {**data, "AI_DLC_BOOTSTRAP_HOME": str(tmp_path / "boot")}
    assert bootstrap_bin(override, home) == tmp_path / "boot/bin"


@pytest.mark.parametrize(
    ("shell", "expected"),
    [
        ("zsh", 'export PATH="$HOME/.local/share/ai-dlc/bootstrap/bin:$PATH"'),
        ("bash", 'export PATH="$HOME/.local/share/ai-dlc/bootstrap/bin:$PATH"'),
        ("fish", 'set -gx PATH "$HOME/.local/share/ai-dlc/bootstrap/bin" $PATH'),
    ],
)
def test_activation_line_is_exact_and_portable_for_each_shell(machine, shell, expected):
    home, bin_dir, _ = machine
    line = activation_line(shell, bin_dir, home)
    assert line == expected
    assert configured_bin(line, home) == str(bin_dir)
    outside = Path("/opt/ai dlc/bin")
    absolute = activation_line(shell, outside, home)
    assert "$HOME" not in absolute and shlex.quote(str(outside)) in absolute
    assert configured_bin(absolute, home) == str(outside)


def test_configured_bin_reads_only_the_owned_path_line(machine):
    home, bin_dir, _ = machine
    assert configured_bin(f'export PATH={shlex.quote(str(bin_dir))}:"$PATH"', home) == str(bin_dir)
    assert configured_bin("export EDITOR=vim\n", home) is None
    assert configured_bin('export PATH="$PATH:/x"', home) is None
    assert configured_bin("export PATH='unterminated", home) is None
    assert configured_bin("set -gx PATH /x /y $PATH", home) is None


def test_preview_reports_the_section_and_writes_nothing(machine):
    home, bin_dir, environ = machine
    rc = home / ".zshrc"
    rc.write_text(AUTHORED)
    result = plan_shell_activation(environ=environ, home=home)
    assert result["applied"] is False and result["action"] == "create"
    assert result["shell"] == "zsh" and result["rc_file"] == str(rc)
    assert result["line"] == activation_line("zsh", bin_dir, home)
    assert "do-not-return" not in json.dumps(result)
    assert rc.read_text() == AUTHORED


def test_apply_appends_only_the_owned_section_and_is_idempotent(machine):
    home, bin_dir, environ = machine
    rc = home / ".zshrc"
    rc.write_text(AUTHORED)
    os.chmod(rc, 0o600)
    result = plan_shell_activation(environ=environ, home=home, apply=True)
    assert result["applied"] is True and result["action"] == "create"
    written = rc.read_text()
    assert written.startswith(AUTHORED)
    section = read_managed_section(written, toml=True)
    assert section["state"] == "present"
    assert configured_bin(section["body"], home) == str(bin_dir)
    assert os.stat(rc).st_mode & 0o777 == 0o600
    again = plan_shell_activation(environ=environ, home=home, apply=True)
    assert again["action"] == "unchanged" and again["applied"] is False
    assert rc.read_text() == written


def test_apply_creates_a_missing_rc_file(machine):
    home, bin_dir, environ = machine
    result = plan_shell_activation(environ=environ | {"SHELL": "/bin/bash"}, home=home, apply=True)
    rc = home / ".bashrc"
    assert result["rc_file"] == str(rc) and result["action"] == "create"
    assert configured_bin(read_managed_section(rc.read_text(), toml=True)["body"], home) == str(
        bin_dir
    )


def test_fish_uses_its_config_file_and_syntax(machine):
    home, bin_dir, environ = machine
    result = plan_shell_activation(
        environ=environ | {"SHELL": "/usr/bin/fish"}, home=home, apply=True
    )
    rc = home / ".config/fish/config.fish"
    assert result["rc_file"] == str(rc)
    body = read_managed_section(rc.read_text(), toml=True)["body"]
    assert body.startswith("set -gx PATH ")
    assert configured_bin(body, home) == str(bin_dir)


def test_update_replaces_only_the_path_line_of_a_setup_apply_section(machine):
    home, bin_dir, environ = machine
    rc = home / ".zshrc"
    stale = "\n".join(
        [
            f'export PATH={shlex.quote(str(home / "old-bin"))}:"$PATH"',
            'eval "$(/opt/homebrew/bin/brew shellenv)"',
            f'eval "$({shlex.quote(str(home / "old-bin/mise"))} activate zsh)"',
        ]
    )
    rc.write_text(managed_section(AUTHORED, stale + "\n", toml=True))
    preview = plan_shell_activation(environ=environ, home=home)
    assert preview["action"] == "update" and preview["applied"] is False
    result = plan_shell_activation(environ=environ, home=home, apply=True)
    assert result["action"] == "update"
    written = rc.read_text()
    assert written.startswith(AUTHORED)
    body = read_managed_section(written, toml=True)["body"]
    assert configured_bin(body, home) == str(bin_dir)
    assert 'eval "$(/opt/homebrew/bin/brew shellenv)"' in body
    assert "activate zsh" in body
    assert body.count("PATH=") == 1


@pytest.mark.parametrize(
    "case", ["symlink", "directory", "modified", "malformed", "unsupported-shell", "no-bin"]
)
def test_unsafe_states_are_refused_without_writing(machine, case):
    home, bin_dir, environ = machine
    rc = home / ".zshrc"
    if case == "symlink":
        real = home / "dotfiles-zshrc"
        real.write_text(AUTHORED)
        rc.symlink_to(real)
    elif case == "directory":
        rc.mkdir()
    elif case == "modified":
        rc.write_text(
            managed_section(AUTHORED, 'export PATH=/x:"$PATH"\n', toml=True).replace(
                "PATH=/x", "PATH=/y"
            )
        )
    elif case == "malformed":
        rc.write_text(AUTHORED + "# ai-dlc:begin deadbeef\nexport PATH=/x\n")
    elif case == "unsupported-shell":
        rc.write_text(AUTHORED)
        environ = environ | {"SHELL": "/bin/tcsh"}
    elif case == "no-bin":
        rc.write_text(AUTHORED)
        bin_dir.rmdir()
    before = {p: p.read_bytes() for p in home.rglob("*") if p.is_file() and not p.is_symlink()}
    with pytest.raises(RefusedError):
        plan_shell_activation(environ=environ, home=home, apply=True)
    assert {
        p: p.read_bytes() for p in home.rglob("*") if p.is_file() and not p.is_symlink()
    } == before
    if case == "symlink":
        assert rc.is_symlink() and (home / "dotfiles-zshrc").read_text() == AUTHORED


def test_cli_workspace_init_shell_previews_then_applies(machine, monkeypatch, tmp_path):
    home, bin_dir, environ = machine
    for name, value in environ.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("AI_DLC_BOOTSTRAP_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    rc = home / ".zshrc"
    rc.write_text(AUTHORED)
    runner = CliRunner()
    preview = runner.invoke(app, ["project", "workspace-init", "--root", str(tmp_path), "--shell"])
    assert preview.exit_code == 0, preview.output
    report = json.loads(preview.stdout)
    assert report["applied"] is False and report["line"] == activation_line("zsh", bin_dir, home)
    assert rc.read_text() == AUTHORED
    applied = runner.invoke(
        app, ["project", "workspace-init", "--root", str(tmp_path), "--shell", "--apply"]
    )
    assert applied.exit_code == 0, applied.output
    assert json.loads(applied.stdout)["applied"] is True
    assert read_managed_section(rc.read_text(), toml=True)["state"] == "present"
    mixed = runner.invoke(
        app,
        ["project", "workspace-init", "--root", str(tmp_path), "--shell", "--vault", str(tmp_path)],
    )
    assert mixed.exit_code == 2 and "--shell" in mixed.stderr


def test_unreadable_rc_is_refused(machine):
    home, _, environ = machine
    rc = home / ".zshrc"
    rc.write_text(AUTHORED)
    rc.chmod(0o200)
    try:
        with pytest.raises(RefusedError):
            plan_shell_activation(environ=environ, home=home, apply=True)
    finally:
        rc.chmod(0o600)
    assert rc.read_text() == AUTHORED
