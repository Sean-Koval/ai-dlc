"""Native activation preserves authored profiles and does not inherit Unix defaults."""

import os

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.environment import bootstrap
from ai_dlc.errors import RefusedError
from ai_dlc.harness.agents import read_managed_section


def test_native_location_uses_known_folder_and_explicit_override(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap.platform, "system", lambda: "Windows")
    monkeypatch.setattr(bootstrap, "_native_local_app_data", lambda: tmp_path / "local")
    environment = {"XDG_DATA_HOME": str(tmp_path / "unix"), "LOCALAPPDATA": str(tmp_path / "fake")}
    assert bootstrap.bootstrap_bin(environment, tmp_path) == tmp_path / "local/ai-dlc/bootstrap/bin"
    environment["AI_DLC_BOOTSTRAP_HOME"] = str(tmp_path / "custom")
    assert bootstrap.bootstrap_bin(environment, tmp_path) == tmp_path / "custom/bin"


def test_powershell_requires_explicit_profile_even_with_unix_shell(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap.platform, "system", lambda: "Windows")
    with pytest.raises(RefusedError, match="profile"):
        bootstrap.plan_shell_activation(environ={"SHELL": "/bin/bash"}, home=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_profile_preview_apply_and_repeat_preserve_authored_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap, "_powershell_policy", lambda _: "RemoteSigned")
    install = tmp_path / "a space Ω 'quoted'"
    (install / "bin").mkdir(parents=True)
    profile = tmp_path / "selected-profile.ps1"
    authored = b"# authored secret not in report\r\n$custom = 'retained'  \r\n"
    profile.write_bytes(authored)
    environment = {"AI_DLC_BOOTSTRAP_HOME": str(install)}
    preview = bootstrap.plan_shell_activation(
        environ=environment, home=tmp_path, powershell_profile=profile
    )
    assert preview["shell"] == "powershell" and not preview["applied"]
    assert "secret" not in str(preview)
    assert profile.read_bytes() == authored
    bootstrap.plan_shell_activation(
        environ=environment, home=tmp_path, powershell_profile=profile, apply=True
    )
    written = profile.read_bytes()
    assert written.startswith(authored)
    section = read_managed_section(written.decode("utf-8"), toml=True)
    assert bootstrap.configured_bin(section["body"], tmp_path) == str(install / "bin")
    repeated = bootstrap.plan_shell_activation(
        environ=environment, home=tmp_path, powershell_profile=profile, apply=True
    )
    assert repeated["action"] == "unchanged" and profile.read_bytes() == written
    profile.write_bytes(written.replace(b"-split", b"-csplit"))
    with pytest.raises(RefusedError, match="modified"):
        bootstrap.plan_shell_activation(
            environ=environment, home=tmp_path, powershell_profile=profile, apply=True
        )


def test_cli_explicit_powershell_profile_previews_without_applying(tmp_path, monkeypatch):
    install = tmp_path / "bootstrap"
    (install / "bin").mkdir(parents=True)
    monkeypatch.setenv("AI_DLC_BOOTSTRAP_HOME", str(install))
    selected = tmp_path / "profile.ps1"
    result = CliRunner().invoke(
        app, ["project", "workspace-init", "--shell", "--powershell-profile", str(selected)]
    )
    assert result.exit_code == 0, result.output
    assert not selected.exists()


@pytest.mark.skipif(os.name != "nt", reason="actual Windows PowerShell and native profile guard")
def test_native_profile_runs_twice_without_duplicate_path(tmp_path):
    import subprocess

    install = tmp_path / "space Ω"
    (install / "bin").mkdir(parents=True)
    profile = tmp_path / "profile.ps1"
    bootstrap.plan_shell_activation(
        environ={**os.environ, "AI_DLC_BOOTSTRAP_HOME": str(install)},
        powershell_profile=profile,
        apply=True,
    )
    script = (
        ". '"
        + str(profile).replace("'", "''")
        + "'; . '"
        + str(profile).replace("'", "''")
        + "'; [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($env:PATH))"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        check=True,
    )
    import base64

    observed = base64.b64decode(result.stdout.strip()).decode("utf-8")
    assert observed.split(";").count(str(install / "bin")) == 1


def test_policy_block_refuses_profile_mutation_with_direct_route(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap.platform, "system", lambda: "Windows")
    install = tmp_path / "bootstrap"
    (install / "bin").mkdir(parents=True)
    profile = tmp_path / "profile.ps1"
    original = b"# unchanged\r\n"
    profile.write_bytes(original)
    monkeypatch.setattr(bootstrap, "_powershell_policy", lambda _: "AllSigned")
    with pytest.raises(RefusedError, match="AllSigned"):
        bootstrap.plan_shell_activation(
            environ={"AI_DLC_BOOTSTRAP_HOME": str(install)},
            powershell_profile=profile,
            apply=True,
        )
    assert profile.read_bytes() == original


def test_utf16_profile_preserves_authored_encoding(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap, "_powershell_policy", lambda _: "RemoteSigned")
    install = tmp_path / "bootstrap"
    (install / "bin").mkdir(parents=True)
    profile = tmp_path / "profile.ps1"
    original = "# authored Ω\r\n".encode("utf-16")
    profile.write_bytes(original)
    bootstrap.plan_shell_activation(
        environ={"AI_DLC_BOOTSTRAP_HOME": str(install)},
        powershell_profile=profile,
        apply=True,
    )
    written = profile.read_bytes()
    assert written.startswith(original)
    assert read_managed_section(written.decode("utf-16"), toml=True)["state"] == "present"


def test_copied_native_launcher_attribution_requires_matching_bytes(tmp_path, monkeypatch):
    import hashlib
    import json

    from ai_dlc.documentation import workspace_diagnostics as diagnostics

    monkeypatch.setattr(diagnostics.platform, "system", lambda: "Windows")
    env = tmp_path / "source-environment"
    (env / "Scripts").mkdir(parents=True)
    cli = env / "Scripts/ai-dlc.exe"
    cli.write_bytes(b"launcher fixture")
    root = tmp_path / "checkout"
    root.mkdir()
    (env / "ai-dlc-source-root").write_text(str(root), encoding="utf-8")
    selected = tmp_path / "bin"
    selected.mkdir()
    alias = selected / "ai-dlc.exe"
    alias.write_bytes(cli.read_bytes())
    (selected / "ai-dlc-selection.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "environment": str(env),
                "cli": str(cli),
                "mode": "source",
                "source_root": str(root),
                "source_revision": "a" * 40,
                "launcher_sha256": hashlib.sha256(cli.read_bytes()).hexdigest(),
            }
        )
    )
    result = diagnostics._alias_checkout(alias, root)
    assert result["alias_is_this_checkout"] is True
    alias.write_bytes(b"replaced launcher")
    assert diagnostics._alias_checkout(alias, root)["alias_is_this_checkout"] is None


@pytest.mark.skipif(os.name != "nt", reason="actual native NTFS junction refusal")
def test_native_profile_refuses_junction_parent_without_changing_target(tmp_path, monkeypatch):
    import subprocess

    target = tmp_path / "authored"
    target.mkdir()
    profile = target / "profile.ps1"
    profile.write_bytes(b"# must remain unchanged\r\n")
    alias = tmp_path / "redirected"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(alias), str(target)], check=True, capture_output=True
    )
    install = tmp_path / "bootstrap"
    (install / "bin").mkdir(parents=True)
    monkeypatch.setattr(bootstrap, "_powershell_policy", lambda _: "RemoteSigned")
    with pytest.raises((RefusedError, ValueError, OSError)):
        bootstrap.plan_shell_activation(
            environ={"AI_DLC_BOOTSTRAP_HOME": str(install)},
            powershell_profile=alias / "profile.ps1",
            apply=True,
        )
    assert profile.read_bytes() == b"# must remain unchanged\r\n"
    assert list(target.iterdir()) == [profile]


@pytest.mark.skipif(os.name != "nt", reason="actual NTFS alternate-stream preservation")
@pytest.mark.parametrize("apply", [False, True])
def test_marked_profile_refuses_preview_and_apply_without_removing_zone(
    tmp_path, monkeypatch, apply
):
    from pathlib import Path

    install = tmp_path / "bootstrap"
    (install / "bin").mkdir(parents=True)
    profile = tmp_path / "marked-profile.ps1"
    original = b"# authored downloaded profile\r\n$authored = 'preserved'\r\n"
    zone = b"[ZoneTransfer]\r\nZoneId=3\r\nHostUrl=https://example.invalid/profile.ps1\r\n"
    profile.write_bytes(original)
    marker = Path(str(profile) + ":Zone.Identifier")
    marker.write_bytes(zone)
    monkeypatch.setattr(bootstrap, "_powershell_policy", lambda _: "RemoteSigned")
    with pytest.raises(RefusedError, match="Zone.Identifier"):
        bootstrap.plan_shell_activation(
            environ={"AI_DLC_BOOTSTRAP_HOME": str(install)},
            powershell_profile=profile,
            apply=apply,
        )
    assert profile.read_bytes() == original
    assert marker.read_bytes() == zone
    assert not list(tmp_path.glob(".ai-dlc-profile-*"))
