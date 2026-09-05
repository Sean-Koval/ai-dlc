import pytest


def executable(path, body):
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)
    return path


def test_headless_plan_omits_desktop_and_does_not_upgrade(tmp_path):
    from ai_dlc.provision import machine_plan

    profile = tmp_path / "profile.toml"
    profile.write_text('schema=4\n[modules]\ninclude=["core","vscode","obsidian"]\n')
    result = machine_plan(profile, headless=True, system="Darwin", architecture="arm64")
    assert [x["id"] for x in result["omitted"]] == ["vscode", "obsidian"]
    assert not any(x == "upgrade" for step in result["commands"] for x in step["argv"])
    assert "--no-upgrade" in result["commands"][0]["argv"]


def test_root_aware_plan_unions_explicit_component_modules_without_editing_profile(tmp_path):
    """Would fail if a selected project component did not add its declared module to setup."""
    from ai_dlc.provision import machine_plan

    profile = tmp_path / "profile.toml"
    profile.write_text('schema = 4\n[modules]\ninclude = ["core"]\n')
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text('schema = 4\n[roles]\nspecs = "openspec"\n')

    result = machine_plan(profile, root=root, system="Darwin", architecture="arm64")

    assert result["component_modules"] == [
        {
            "id": "openspec",
            "provider": "openspec",
            "role": "specs",
            "reason": "selected provider openspec for role specs",
        }
    ]
    assert result["commands"][1] == {
        "argv": ["mise", "install"],
        "mise": {"npm:@fission-ai/openspec": "1.5.0"},
    }
    assert profile.read_text() == 'schema = 4\n[modules]\ninclude = ["core"]\n'


def test_root_aware_plan_keeps_machine_module_precedence_and_no_root_behavior(tmp_path):
    """Would fail if project setup replaced local modules or changed an omitted-root plan."""
    from ai_dlc.provision import machine_plan

    profile = tmp_path / "profile.toml"
    profile.write_text('schema = 4\n[modules]\ninclude = ["core"]\n')
    machine = tmp_path / "machine.toml"
    machine.write_text('schema = 4\n[modules]\ninclude = ["python"]\n')
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text('schema = 4\n[roles]\nspecs = "openspec"\n')

    root_aware = machine_plan(
        profile, root=root, machine=machine, system="Darwin", architecture="arm64"
    )
    without_root = machine_plan(profile, machine=machine, system="Darwin", architecture="arm64")

    assert root_aware["commands"] == [
        {"argv": ["brew", "bundle", "--no-upgrade", "--file", "{Brewfile}"], "content": ""},
        {
            "argv": ["mise", "install"],
            "mise": {
                "python": "3.12.11",
                "uv": "0.9.11",
                "npm:@fission-ai/openspec": "1.5.0",
            },
        },
    ]
    assert root_aware["component_modules"] == [
        {
            "id": "openspec",
            "provider": "openspec",
            "role": "specs",
            "reason": "selected provider openspec for role specs",
        }
    ]
    assert "component_modules" not in without_root
    assert without_root["commands"] == [
        {"argv": ["brew", "bundle", "--no-upgrade", "--file", "{Brewfile}"], "content": ""},
        {"argv": ["mise", "install"], "mise": {"python": "3.12.11", "uv": "0.9.11"}},
    ]


def test_root_aware_plan_refuses_an_unresolved_explicit_component(tmp_path):
    """Would fail if setup silently substituted an unknown selected provider component."""
    from ai_dlc.provision import machine_plan

    profile = tmp_path / "profile.toml"
    profile.write_text("schema = 4\n")
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text('schema = 4\n[roles]\nspecs = "unavailable-specs"\n')

    with pytest.raises(ValueError, match="no component for provider: unavailable-specs"):
        machine_plan(profile, root=root, system="Darwin", architecture="arm64")


def test_unsupported_os_fails_before_install(tmp_path):
    from ai_dlc.provision import machine_plan

    profile = tmp_path / "p.toml"
    profile.write_text("schema=4\n")
    with pytest.raises(ValueError, match="unsupported"):
        machine_plan(profile, system="Windows", architecture="x86_64")


def test_migration_refuses_unknown_future_version_without_writing(tmp_path):
    from ai_dlc.provision import migrate

    profile = tmp_path / "p.toml"
    profile.write_text("schema=99\n")
    before = profile.read_bytes()
    with pytest.raises(ValueError, match="schema"):
        migrate(profile, apply=True)
    assert profile.read_bytes() == before


def test_doctor_checks_alias_provider_requirements(tmp_path, monkeypatch):
    from ai_dlc import agents, provision

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\ntracker="team-tracker"\n[providers.team-tracker]\nkind="linear"\ntoken_env="AI_DLC_TEST_MISSING_TOKEN"\n'
    )
    monkeypatch.delenv("AI_DLC_TEST_MISSING_TOKEN", raising=False)
    monkeypatch.setattr(provision.shutil, "which", lambda name, path=None: None)
    monkeypatch.setattr(agents, "render_agents", lambda root: {"changed": []})
    result = provision.doctor(tmp_path)
    assert not result["ready"]
    assert any("AI_DLC_TEST_MISSING_TOKEN" in s for s in result["signins"])
    assert any("team_id" in s for s in result["configuration"])
    assert any("closed" in s for s in result["configuration"])


def test_doctor_uses_merged_bindings_and_shared_redacted_credential_readiness(
    tmp_path, monkeypatch
):
    """Would fail if doctor bypassed bindings, changed provider kind, or leaked a value."""
    from ai_dlc import agents, provision
    from ai_dlc.providers import Registry

    marker = "credential-value-that-must-not-escape-doctor"
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text("schema = 4\n")
    home = tmp_path / "home"
    home.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()
    profile = tmp_path / "profile.toml"
    profile.write_text(
        """schema = 4
profile_id = "portable-development"
[roles]
tracker = "linear-sandbox"
[providers.linear-sandbox]
kind = "linear"
token_env = "LINEAR_SANDBOX_TOKEN"
team_id = "portable-team"
health_reference = "portable-health"
[providers.linear-sandbox.statuses]
in_progress = "started"
closed = "completed"
[credentials.linear-sandbox]
description = "Linear sandbox access"
required_by = ["provider.linear-sandbox"]
[[agents.servers]]
id = "notes"
command = "notes-mcp"
env = ["LINEAR_SANDBOX_TOKEN"]
"""
    )
    machine = tmp_path / "machine.toml"
    machine.write_text(
        f"""schema = 4
[paths]
vault = "{vault}"
[accounts]
linear = "sandbox"
[providers.linear-sandbox]
account = "sandbox"
[credentials.linear-sandbox]
source = "environment"
variable = "LINEAR_SANDBOX_TOKEN"
"""
    )
    provider_configs: list[dict] = []

    def fail_health(self, name, operation, payload):
        del name, operation, payload
        provider_configs.append(self.config)
        raise RuntimeError(f"provider rejected {marker}")

    monkeypatch.setattr(provision.shutil, "which", lambda name, path=None: None)
    monkeypatch.setattr(agents, "render_agents", lambda selected_root: {"changed": []})
    monkeypatch.setattr(Registry, "invoke", fail_health)

    result = provision.doctor(
        root,
        personal=profile,
        machine=machine,
        home=home,
        environ={"LINEAR_SANDBOX_TOKEN": marker},
    )

    assert result["credentials"] == [
        {
            "id": "linear-sandbox",
            "description": "Linear sandbox access",
            "required_by": ["provider.linear-sandbox"],
            "source": "environment",
            "variable": "LINEAR_SANDBOX_TOKEN",
            "configured": True,
            "present": True,
        }
    ]
    assert result["knowledge"] == "available"
    assert result["user_agents"]["applied"] is False
    assert result["user_agents"]["changed"]
    assert result["provider_health"] == [
        {"provider": "linear-sandbox", "ready": False, "reason": "provider health check failed"}
    ]
    assert provider_configs[0]["providers"]["linear-sandbox"]["kind"] == "linear"
    assert provider_configs[0]["providers"]["linear-sandbox"]["account"] == "sandbox"
    assert marker not in repr(result)
    assert not list(home.iterdir())


def test_doctor_redacts_logical_and_distinct_provider_compatibility_credentials(
    tmp_path, monkeypatch
):
    """Would fail if any provider credential value survived a health failure."""
    from ai_dlc import agents, provision
    from ai_dlc.providers import Registry

    logical_value = "logical-secret-value"
    compatibility_value = "compatibility-secret-value"
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text("schema = 4\n")
    profile = tmp_path / "profile.toml"
    profile.write_text(
        """schema = 4
profile_id = "portable-development"
[providers.linear-sandbox]
kind = "linear"
token_env = "LINEAR_COMPAT_TOKEN"
health_reference = "portable-health"
[credentials.linear-sandbox]
description = "Linear sandbox access"
required_by = ["provider.linear-sandbox"]
"""
    )
    machine = tmp_path / "machine.toml"
    machine.write_text(
        """schema = 4
[credentials.linear-sandbox]
source = "environment"
variable = "LINEAR_LOGICAL_TOKEN"
"""
    )

    def fail_health(self, name, operation, payload):
        del self, name, operation, payload
        raise RuntimeError(f"failed with {logical_value} and {compatibility_value}")

    monkeypatch.setattr(provision.shutil, "which", lambda name, path=None: None)
    monkeypatch.setattr(agents, "render_agents", lambda selected_root: {"changed": []})
    monkeypatch.setattr(Registry, "invoke", fail_health)

    result = provision.doctor(
        root,
        personal=profile,
        machine=machine,
        home=tmp_path / "home",
        environ={
            "LINEAR_LOGICAL_TOKEN": logical_value,
            "LINEAR_COMPAT_TOKEN": compatibility_value,
        },
    )

    assert logical_value not in repr(result)
    assert compatibility_value not in repr(result)
    assert result["provider_health"] == [
        {"provider": "linear-sandbox", "ready": False, "reason": "provider health check failed"}
    ]


def test_doctor_reports_the_injected_default_linear_credential_as_absent_or_present(
    tmp_path, monkeypatch
):
    """Would fail if the Linear default used ambient state or bypassed readiness."""
    from types import SimpleNamespace

    from ai_dlc import agents, provision

    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(
        """schema = 4
[roles]
tracker = "linear-sandbox"
[providers.linear-sandbox]
kind = "linear"
team_id = "portable-team"
[providers.linear-sandbox.statuses]
in_progress = "started"
closed = "completed"
"""
    )
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    monkeypatch.setattr(provision.shutil, "which", lambda name, path=None: f"/bin/{name}")
    monkeypatch.setattr(
        provision.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="{}"),
    )
    monkeypatch.setattr(agents, "render_agents", lambda selected_root: {"changed": []})

    absent = provision.doctor(root, environ={})
    present = provision.doctor(root, environ={"LINEAR_API_KEY": "injected-only"})

    assert absent["credentials"][0]["variable"] == "LINEAR_API_KEY"
    assert absent["credentials"][0]["present"] is False
    assert absent["signins"] == ["Set LINEAR_API_KEY using your credential store"]
    assert absent["ready"] is False
    assert present["credentials"][0]["present"] is True
    assert present["signins"] == []
    assert present["ready"] is True


def test_doctor_provider_health_uses_the_same_explicit_environment_as_readiness(
    tmp_path, monkeypatch
):
    """Would fail if executable health inherited a token that readiness cannot see."""
    import hashlib

    from ai_dlc import agents, provision

    provider_marker = tmp_path / "provider-marker"
    provider = executable(
        tmp_path / "provider",
        'if [ -n "$PROVIDER_MARKER" ]; then printf %s "$PROVIDER_TOKEN" > "$PROVIDER_MARKER"; fi\n'
        '[ -n "$PROVIDER_TOKEN" ] || exit 42\n'
        'printf \'{"id":"1","url":"https://example.test/1","state":"open"}\\n\'\n',
    )
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(
        f'''schema = 4
[providers.health]
kind = "executable"
command = "{provider}"
sha256 = "{hashlib.sha256(provider.read_bytes()).hexdigest()}"
token_env = "PROVIDER_TOKEN"
health_reference = "1"
'''
    )
    monkeypatch.setenv("PROVIDER_TOKEN", "ambient-token")
    monkeypatch.setenv("PROVIDER_MARKER", str(provider_marker))
    monkeypatch.setattr(provision.shutil, "which", lambda name, path=None: None)
    monkeypatch.setattr(agents, "render_agents", lambda selected_root: {"changed": []})

    isolated = provision.doctor(root, environ={})
    assert isolated["credentials"][0]["present"] is False
    assert isolated["provider_health"][0]["ready"] is False
    assert not provider_marker.exists()

    injected = provision.doctor(
        root,
        environ={
            "PROVIDER_TOKEN": "injected-token",
            "PROVIDER_MARKER": str(provider_marker),
        },
    )
    assert injected["credentials"][0]["present"] is True
    assert injected["provider_health"][0]["ready"] is True
    assert provider_marker.read_text() == "injected-token"

    provider_marker.unlink()
    ambient = provision.doctor(root)
    assert ambient["credentials"][0]["present"] is True
    assert ambient["provider_health"][0]["ready"] is True
    assert provider_marker.read_text() == "ambient-token"


def test_doctor_command_discovery_and_execution_respect_explicit_path(tmp_path, monkeypatch):
    """Would fail if doctor discovered or ran ambient tools for an explicit environment."""
    from ai_dlc import agents, provision

    ambient_bin = tmp_path / "ambient-bin"
    ambient_bin.mkdir()
    injected_bin = tmp_path / "injected-bin"
    injected_bin.mkdir()
    ambient_trace = tmp_path / "ambient-trace"
    injected_trace = tmp_path / "injected-trace"
    for binary_dir in [ambient_bin, injected_bin]:
        executable(binary_dir / "git", "exit 0\n")
        executable(
            binary_dir / "mise",
            'printf %s "$TOOL_ORIGIN" >> "$TRACE_FILE"\n'
            'if [ "$1" = "ls" ]; then printf \'{}\\n\'; fi\n',
        )
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text("schema = 4\n")
    monkeypatch.setenv("PATH", str(ambient_bin))
    monkeypatch.setenv("TOOL_ORIGIN", "ambient")
    monkeypatch.setenv("TRACE_FILE", str(ambient_trace))
    monkeypatch.setattr(agents, "render_agents", lambda selected_root: {"changed": []})

    isolated = provision.doctor(root, environ={})
    assert isolated["missing"] == ["git", "mise"]
    assert not ambient_trace.exists()

    injected = provision.doctor(
        root,
        environ={
            "PATH": str(injected_bin),
            "TOOL_ORIGIN": "injected",
            "TRACE_FILE": str(injected_trace),
        },
    )
    assert injected["missing"] == []
    assert injected_trace.read_text() == "injected"
    assert not ambient_trace.exists()

    ambient = provision.doctor(root)
    assert ambient["missing"] == []
    assert ambient_trace.read_text() == "ambient"


def test_machine_apply_activates_runtimes_and_personal_agents(tmp_path, monkeypatch):
    import json
    import tomllib

    from ai_dlc.provision import machine_apply

    binaries = tmp_path / "bin"
    binaries.mkdir()
    for name in ["brew", "mise"]:
        executable = binaries / name
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    bootstrap = tmp_path / "bootstrap"
    profile = tmp_path / "profile.toml"
    profile.write_text(
        """schema=4
[modules]
include=["core", "python"]
[[agents.servers]]
id="notes"
command="notes-mcp"
env=["NOTES_TOKEN"]
"""
    )
    machine = tmp_path / "machine.toml"
    machine.write_text(
        """schema = 4
[paths]
vault = "/machine/vault"
[accounts]
notes = "personal"
"""
    )
    marker = "credential-value-that-must-not-be-rendered"
    monkeypatch.setenv("NOTES_TOKEN", marker)
    monkeypatch.setenv("PATH", f"{binaries}:/usr/bin:/bin")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("AI_DLC_BOOTSTRAP_HOME", str(bootstrap))
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr("ai_dlc.provision.platform.system", lambda: "Darwin")
    monkeypatch.setattr("ai_dlc.provision.platform.machine", lambda: "arm64")

    result = machine_apply(profile, home=home, machine=machine)

    assert result["ready"] is True
    assert result["workstation"]["ready"] is True
    assert result["agent_configuration"]["applied"] is True
    assert tomllib.loads((home / ".config/mise/config.toml").read_text())["tools"] == {
        "python": "3.12.11",
        "uv": "0.9.11",
    }
    assert str(bootstrap / "bin") in (home / ".zshrc").read_text()
    assert json.loads((home / ".claude.json").read_text())["mcpServers"]["notes"] == {
        "command": "notes-mcp",
        "env": {"NOTES_TOKEN": "${NOTES_TOKEN}"},
    }
    assert marker not in repr(result)
    assert all(marker not in path.read_text() for path in home.rglob("*") if path.is_file())


def test_machine_plan_previews_personal_agents_without_writing(tmp_path):
    from ai_dlc.provision import machine_plan

    profile = tmp_path / "profile.toml"
    profile.write_text('schema=4\n[[agents.servers]]\nid="notes"\ncommand="notes-mcp"\n')
    home = tmp_path / "home"
    home.mkdir()
    result = machine_plan(profile, system="Darwin", architecture="arm64", home=home)
    assert result["agent_configuration"]["clean"] is False
    assert result["agent_configuration"]["applied"] is False
    assert not list(home.iterdir())


def test_machine_plan_merges_machine_readiness_without_exposing_environment_values(
    tmp_path, monkeypatch
):
    """Would fail if machine bindings were ignored or a credential value entered a plan."""
    from ai_dlc.provision import machine_plan

    marker = "credential-value-that-must-not-enter-the-plan"
    profile = tmp_path / "profile.toml"
    profile.write_text(
        """schema = 4
profile_id = "portable-development"
[preferences]
headless = false
[providers.linear-sandbox]
kind = "linear"
token_env = "LINEAR_SANDBOX_TOKEN"
[credentials.linear-sandbox]
description = "Linear sandbox access"
required_by = ["provider.linear-sandbox"]
"""
    )
    machine = tmp_path / "machine.toml"
    machine.write_text(
        """schema = 4
[preferences]
headless = true
[paths]
vault = "/machine/vault"
[accounts]
linear = "sandbox"
[providers.linear-sandbox]
account = "sandbox"
[credentials.linear-sandbox]
source = "environment"
variable = "LINEAR_SANDBOX_TOKEN"
"""
    )
    monkeypatch.delenv("LINEAR_SANDBOX_TOKEN", raising=False)

    result = machine_plan(
        profile,
        machine=machine,
        system="Darwin",
        architecture="arm64",
        home=tmp_path / "home",
        environ={"LINEAR_SANDBOX_TOKEN": marker},
    )

    assert result["headless"] is True
    assert result["credentials"] == [
        {
            "id": "linear-sandbox",
            "description": "Linear sandbox access",
            "required_by": ["provider.linear-sandbox"],
            "source": "environment",
            "variable": "LINEAR_SANDBOX_TOKEN",
            "configured": True,
            "present": True,
        }
    ]
    assert marker not in repr(result)


def test_machine_apply_scopes_default_workstation_state_to_explicit_home(tmp_path, monkeypatch):
    from ai_dlc.provision import machine_apply

    binaries = tmp_path / "bin"
    binaries.mkdir()
    for name in ["brew", "mise"]:
        executable = binaries / name
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
    profile = tmp_path / "profile.toml"
    profile.write_text("schema=4\n[modules]\ninclude=[]\n")
    home = tmp_path / "selected-home"
    home.mkdir()
    monkeypatch.setenv("PATH", f"{binaries}:/usr/bin:/bin")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("AI_DLC_BOOTSTRAP_HOME", raising=False)
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr("ai_dlc.provision.platform.system", lambda: "Darwin")
    monkeypatch.setattr("ai_dlc.provision.platform.machine", lambda: "arm64")

    machine_apply(profile, home=home)

    assert (home / ".local/share/ai-dlc/workstation").is_dir()


def test_machine_apply_command_discovery_and_execution_respect_explicit_path(tmp_path, monkeypatch):
    """Would fail if apply selected or ran ambient mise for an explicit environment."""
    from ai_dlc.provision import machine_apply

    ambient_bin = tmp_path / "ambient-bin"
    ambient_bin.mkdir()
    injected_bin = tmp_path / "injected-bin"
    injected_bin.mkdir()
    ambient_trace = tmp_path / "ambient-trace"
    injected_trace = tmp_path / "injected-trace"
    for binary_dir in [ambient_bin, injected_bin]:
        for name in ["brew", "mise"]:
            executable(
                binary_dir / name,
                'printf "%s:%s\\n" "$TOOL_ORIGIN" "$*" >> "$TRACE_FILE"\n',
            )
    profile = tmp_path / "profile.toml"
    profile.write_text('schema = 4\n[modules]\ninclude = ["python"]\n')
    monkeypatch.setenv("PATH", str(ambient_bin))
    monkeypatch.setenv("TOOL_ORIGIN", "ambient")
    monkeypatch.setenv("TRACE_FILE", str(ambient_trace))
    monkeypatch.setattr("ai_dlc.provision.platform.system", lambda: "Darwin")
    monkeypatch.setattr("ai_dlc.provision.platform.machine", lambda: "arm64")

    with pytest.raises(RuntimeError, match="mise is required"):
        machine_apply(profile, home=tmp_path / "empty-home", environ={})
    assert not ambient_trace.exists()

    injected = machine_apply(
        profile,
        home=tmp_path / "injected-home",
        environ={
            "PATH": str(injected_bin),
            "TOOL_ORIGIN": "injected",
            "TRACE_FILE": str(injected_trace),
        },
    )
    assert injected["ready"] is True
    assert injected_trace.read_text().splitlines() == [
        "injected:bundle --no-upgrade --file "
        + str(tmp_path / "injected-home/.local/share/ai-dlc/workstation/Brewfile"),
        "injected:trust "
        + str(tmp_path / "injected-home/.local/share/ai-dlc/workstation/.mise.toml"),
        "injected:install",
    ]
    assert not ambient_trace.exists()

    ambient = machine_apply(profile, home=tmp_path / "ambient-home")
    assert ambient["ready"] is True
    assert ambient_trace.read_text().splitlines() == [
        "ambient:bundle --no-upgrade --file "
        + str(tmp_path / "ambient-home/.local/share/ai-dlc/workstation/Brewfile"),
        "ambient:trust "
        + str(tmp_path / "ambient-home/.local/share/ai-dlc/workstation/.mise.toml"),
        "ambient:install",
    ]
