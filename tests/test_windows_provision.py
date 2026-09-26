"""Selected native provisioning reports real limitations instead of upgrading tools."""

import os
import subprocess
import sys

import pytest

from ai_dlc.setup import provision


@pytest.fixture
def native(tmp_path, monkeypatch):
    profile = tmp_path / "profile.toml"
    profile.write_text('schema=4\n[modules]\ninclude=["core"]\n')
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(provision.platform, "system", lambda: "Windows")
    monkeypatch.setattr(provision.platform, "machine", lambda: "AMD64")
    return profile, home, {"AI_DLC_BOOTSTRAP_HOME": str(tmp_path / "bootstrap"), "PATH": ""}


def test_missing_core_is_actionable_without_auth_or_installing(native):
    profile, home, env = native
    result = provision.machine_plan(profile, home=home, environ=env)
    assert result["ready"] is False
    assert {tool["id"] for tool in result["tools"]} == {"git", "gh"}
    assert all(tool["status"] == "missing" for tool in result["tools"])
    gh = next(tool for tool in result["tools"] if tool["id"] == "gh")
    assert gh["package"]["id"] == "GitHub.cli" and gh["package"]["scope"] == "user"
    assert gh["package"]["version"] and gh["package"]["source"] == "winget"
    assert "machine" in gh["reason"] and "manual" in gh["next_action"]
    assert result["commands"] == []
    assert not list(home.iterdir())
    assert result["authentication"] == "not-assessed"


def test_native_plan_names_every_selected_and_implied_unsupported_module(native, tmp_path):
    profile, home, env = native
    profile.write_text('schema=4\n[modules]\ninclude=["vscode", "rust"]\n')
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text('schema=4\n[roles]\nspecs="openspec"\n')
    result = provision.machine_plan(profile, root=root, home=home, environ=env)
    assert {item["id"] for item in result["unsupported"]} == {"vscode", "rust", "openspec"}
    implied = next(item for item in result["unsupported"] if item["id"] == "openspec")
    assert implied["required_by"] == [{"provider": "openspec", "role": "specs"}]
    assert not result["ready"] and result["commands"] == []


def test_native_reuses_observed_adequate_tools_without_upgrades(native, monkeypatch):
    profile, home, env = native
    monkeypatch.setattr("ai_dlc.setup.windows.find_executable", lambda name, *_: "/native/" + name)

    def run(argv, **kwargs):
        assert argv[-1] == "--version"
        return subprocess.CompletedProcess(
            argv,
            0,
            "git version 2.53.0.windows.2"
            if "git" in argv[0]
            else "gh version 2.87.3 (2026-02-23)",
            "",
        )

    monkeypatch.setattr(subprocess, "run", run)
    result = provision.machine_apply(profile, home=home, environ=env)
    assert result["ready"] and result["applied"] == []
    assert [tool["observed_version"] for tool in result["tools"]] == ["2.53.0", "2.87.3"]
    assert not list(home.iterdir())


def test_native_preserves_old_or_unverifiable_installations(native, monkeypatch):
    profile, home, env = native
    monkeypatch.setattr("ai_dlc.setup.windows.find_executable", lambda name, *_: "/native/" + name)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda argv, **kw: subprocess.CompletedProcess(
            argv, 0, "git version 1.0.0" if "git" in argv[0] else "unrecognized output", ""
        ),
    )
    result = provision.machine_apply(profile, home=home, environ=env)
    assert not result["ready"] and result["applied"] == []
    assert [tool["status"] for tool in result["tools"]] == ["incompatible", "unverified"]


def test_python_apply_verifies_exact_runtime_after_install(native, monkeypatch):
    profile, home, env = native
    profile.write_text('schema=4\n[modules]\ninclude=["python", "node"]\n')
    monkeypatch.setattr(
        "ai_dlc.setup.windows.find_executable",
        lambda name, *_: "/native/mise.exe" if name == "mise.exe" else None,
    )
    installed = False

    def run(argv, **kwargs):
        nonlocal installed
        assert "auth" not in argv and "upgrade" not in argv
        if "install" in argv:
            installed = True
            return subprocess.CompletedProcess(argv, 0, "", "")
        if not installed:
            return subprocess.CompletedProcess(argv, 1, "", "runtime missing")
        if "which" in argv:
            return subprocess.CompletedProcess(argv, 0, str(home / (argv[2] + ".exe")), "")
        return subprocess.CompletedProcess(
            argv, 0, "Python 3.12.11" if "python.exe" in argv[0] else "uv 0.9.11", ""
        )

    monkeypatch.setattr(subprocess, "run", run)
    result = provision.machine_apply(profile, home=home, environ=env)
    assert result["applied"] and all(item["status"] == "ready" for item in result["tools"])
    assert not result["ready"] and result["unsupported"][0]["id"] == "node"
    assert result["workstation"]["profile_applied"] is False


def test_python_failed_install_stays_incomplete(native, monkeypatch):
    profile, home, env = native
    profile.write_text('schema=4\n[modules]\ninclude=["python"]\n')
    monkeypatch.setattr(
        "ai_dlc.setup.windows.find_executable",
        lambda name, *_: "/native/mise.exe" if name == "mise.exe" else None,
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda argv, **kw: subprocess.CompletedProcess(argv, 1, "", "private diagnostic"),
    )
    result = provision.machine_apply(profile, home=home, environ=env)
    assert not result["ready"] and result["failures"]
    assert "private diagnostic" not in str(result)


def test_python_rerun_reuses_exact_versions_without_reinstall(native, monkeypatch):
    profile, home, env = native
    profile.write_text('schema=4\n[modules]\ninclude=["python"]\n')
    monkeypatch.setattr(
        "ai_dlc.setup.windows.find_executable",
        lambda name, *_: "/native/mise.exe" if name == "mise.exe" else None,
    )

    def run(argv, **kwargs):
        assert "install" not in argv
        assert kwargs["env"]["MISE_AUTO_INSTALL"] in {"0", "false"}
        if "which" in argv:
            return subprocess.CompletedProcess(argv, 0, str(home / (argv[2] + ".exe")), "")
        return subprocess.CompletedProcess(
            argv, 0, "Python 3.12.11" if "python.exe" in argv[0] else "uv 0.9.11", ""
        )

    monkeypatch.setattr(subprocess, "run", run)
    result = provision.machine_apply(profile, home=home, environ=env)
    assert result["ready"] and result["applied"] == []
    assert result["guidance"] == []


def test_invalid_native_module_is_rejected_before_running_tools(native, monkeypatch):
    profile, home, env = native
    profile.write_text('schema=4\n[modules]\ninclude=["not-a-module"]\n')
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: pytest.fail("invalid selection ran a tool")
    )
    with pytest.raises(ValueError, match="unknown module"):
        provision.machine_apply(profile, home=home, environ=env)


def test_native_project_mcp_does_not_become_personal_provisioning(native, tmp_path):
    profile, home, env = native
    profile.write_text("schema=4\n[modules]\ninclude=[]\n")
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[[agents.servers]]\nid="project-only"\ncommand="project-server"\n'
    )
    result = provision.machine_plan(profile, root=root, home=home, environ=env)
    assert result["ready"] and result["unsupported"] == []
    assert not result["agent_configuration"]["applied"]
    assert not list(home.iterdir())


def test_runtime_plan_does_not_activate_mise_environment_hooks(native, monkeypatch):
    profile, home, env = native
    profile.write_text('schema=4\n[modules]\ninclude=["python"]\n')
    monkeypatch.setattr(
        "ai_dlc.setup.windows.find_executable",
        lambda name, *_: "/native/mise.exe" if name == "mise.exe" else None,
    )

    def run(argv, **kwargs):
        assert "exec" not in argv, "planning must not activate user environment hooks"
        if "which" in argv:
            assert "--tool" in argv and "@" in argv[-1]
            return subprocess.CompletedProcess(argv, 0, str(home / (argv[2] + ".exe")), "")
        return subprocess.CompletedProcess(
            argv, 0, "Python 3.12.11" if "python.exe" in argv[0] else "uv 0.9.11", ""
        )

    monkeypatch.setattr(subprocess, "run", run)
    result = provision.machine_plan(profile, home=home, environ=env)
    assert result["ready"] and not result["commands"]


@pytest.mark.parametrize("malformed", [False, True])
def test_mise_path_protocol_decodes_real_bytes_independently_of_locale(
    tmp_path, monkeypatch, malformed
):
    from ai_dlc.setup.windows import _runtime_observation

    executable = str(tmp_path / "runtime é Ω" / "python.exe")
    payload = (executable + "\r\n").encode("utf-8")
    if malformed:
        payload = payload.replace(b"python.exe", b"\xffpython.exe")
    real_run = subprocess.run
    probes = []
    # Match Windows Python's legacy pipe decoding even on UTF-8 developer hosts.
    monkeypatch.setattr(subprocess, "_text_encoding", lambda: "cp1252")

    def run(argv, **kwargs):
        if argv[1] == "which":
            script = f"import sys; sys.stdout.buffer.write(bytes.fromhex('{payload.hex()}'))"
        else:
            probes.append(argv)
            assert not malformed, "Malformed path reached an executable probe"
            assert argv == [executable, "--version"]
            script = "import sys; sys.stdout.buffer.write(b'Python 3.12.11\\r\\n')"
        # Exercise actual pipe bytes and subprocess decoding, not mocked text output.
        return real_run([sys.executable, "-c", script], **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    observed = _runtime_observation("mise.exe", "python", "3.12.11", dict(os.environ), tmp_path)
    assert observed == ((None, []) if malformed else ("3.12.11", [executable, "--version"]))
    assert len(probes) == (0 if malformed else 1)
