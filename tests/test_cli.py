import hashlib
import json
from pathlib import Path

import pytest
from click import unstyle
from typer.testing import CliRunner


@pytest.mark.parametrize("invalid", [None, "digest", "path", "symlink", "schema"])
def test_missing_custom_guidance_retains_attribution_and_independent_checks(
    tmp_path, monkeypatch, invalid
):
    """Only authenticated, otherwise valid metadata may survive a missing guidance target."""
    from ai_dlc.cli import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PATH", "")
    root = tmp_path / "project"
    root.mkdir()
    guidance = root / "guidance.md"
    guidance.write_text("# Custom instructions\n")
    guidance.unlink()
    paths = ["guidance.md"]
    if invalid == "path":
        paths.append("../outside.md")
    if invalid == "symlink":
        (root / "linked.md").symlink_to(root / "absent.md")
        paths.append("linked.md")
    manifest = root / "component.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "components": [
                    {
                        "id": "custom-specs",
                        "roles": ["specs"],
                        "modules": ["core"],
                        "guidance": paths,
                        "required_config": ["repository"] if invalid != "schema" else 5,
                    }
                ],
            }
        )
    )
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest() if invalid != "digest" else "a" * 64
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nspecs="custom-specs"\ntracker="github-issues"\n'
        '[providers.custom-specs]\ncomponent_manifest="component.json"\n'
        f'component_manifest_sha256="{digest}"\n'
    )
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}

    result = CliRunner().invoke(app, ["project", "readiness", "--root", str(root)])

    assert result.exit_code == 1, result.output
    report = json.loads(result.stdout)
    assert report["qualification"] == "not-assessed"
    assert not report["ready"]
    if invalid:
        assert len(report["checks"]) == 1
        assert report["checks"][0]["dimension"] == "configuration"
        assert report["checks"][0]["status"] == "blocked"
    else:
        gaps = [
            c
            for c in report["checks"]
            if c["component"] == "custom-specs" and c["dimension"] == "guidance"
        ]
        assert len(gaps) == 1
        assert gaps[0]["status"] == "missing"
        assert "guidance.md" in gaps[0]["reason"]
        assert "Restore" in gaps[0]["next_action"] and "guidance.md" in gaps[0]["next_action"]
        for component in ["custom-specs", "github-issues"]:
            assert any(
                c["component"] == component
                and c["dimension"] == "tool"
                and c["status"] == "missing"
                for c in report["checks"]
            )
        assert any(
            c["component"] == "custom-specs"
            and c["dimension"] == "configuration"
            and "repository" in c["next_action"]
            for c in report["checks"]
        )
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("command", [["project", "readiness"], ["doctor"], ["machine", "doctor"]])
def test_malformed_component_metadata_returns_blocked_diagnostics(tmp_path, monkeypatch, command):
    """Schema type failures must not abort offline reports or erase enrollment diagnostics."""
    from ai_dlc.cli import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PATH", "")
    root = tmp_path / "project"
    root.mkdir()
    manifest = root / "component.json"
    manifest.write_text('{"schema": 1, "components": {}}')
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nspecs="custom"\n[providers.custom]\n'
        'component_manifest="component.json"\n'
        f'component_manifest_sha256="{digest}"\n'
    )
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    result = CliRunner().invoke(app, [*command, "--root", str(root)])
    assert result.exit_code == 1
    assert result.stdout.strip().startswith("{"), repr(result.exception)
    report = json.loads(result.stdout)
    readiness = report if command == ["project", "readiness"] else report["project_readiness"]
    assert readiness["ready"] is False
    assert readiness["checks"][0]["status"] == "blocked"
    assert readiness["checks"][0]["next_action"]
    if command != ["project", "readiness"]:
        assert report["ready"] is False
        assert report["machine_status"]["enrolled"] is False
        assert report["machine_checks"]["unavailable"]
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_project_readiness_is_offline_read_only_and_exits_for_required_gaps(tmp_path, monkeypatch):
    """Readiness must report gaps, never execute tools or load secret files, and return 0 after rendering."""
    import subprocess

    from ai_dlc.agents import render_agents
    from ai_dlc.cli import app

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nspecs="openspec"\nagent-client=["codex"]\n'
    )
    binary = tmp_path / "bin"
    binary.mkdir()
    for name in ["openspec", "codex"]:
        path = binary / name
        path.write_text("#!/bin/sh\nexit 99\n")
        path.chmod(0o755)
    monkeypatch.setenv("PATH", str(binary))
    (root / ".env").write_text("SENTINEL=must-not-be-read\n")
    read_text = Path.read_text

    def refuse_secret_file(path, *args, **kwargs):
        if path == root / ".env":
            raise AssertionError("plain readiness read a secret file")
        return read_text(path, *args, **kwargs)

    def no_execution(*args, **kwargs):
        raise AssertionError("plain readiness executed a process")

    monkeypatch.setattr(subprocess, "run", no_execution)
    monkeypatch.setattr(Path, "read_text", refuse_secret_file)
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    result = CliRunner().invoke(app, ["project", "readiness", "--root", str(root)])
    assert result.exit_code == 1, result.output
    report = json.loads(result.stdout)
    assert not report["ready"]
    assert report["qualification"] == "not-assessed"
    assert all(
        c["status"] == "unverified" for c in report["checks"] if c["dimension"] == "provider-health"
    )
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    render_agents(root, apply=True)
    result = CliRunner().invoke(app, ["project", "readiness", "--root", str(root)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["ready"]


def _write_cli_enrollment(tmp_path: Path) -> dict[str, str]:
    from ai_dlc.enrollment import EnrollmentLock, EnrollmentPaths, write_lock

    environment = {
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_STATE_HOME": str(tmp_path / "state"),
    }
    paths = EnrollmentPaths.from_environment(home=tmp_path / "unused-home", environ=environment)
    content = (
        b'schema = 4\nprofile_id = "personal-profile"\n[roles]\nknowledge = "enrolled-personal"\n'
    )
    profile_file = "ai-dlc-profile.toml"
    resolved_commit = "a" * 40
    content_sha256 = hashlib.sha256(
        profile_file.encode() + b"\0" + str(len(content)).encode() + b"\0" + content
    ).hexdigest()
    cached_profile = paths.profile_root("personal-profile", resolved_commit) / profile_file
    cached_profile.parent.mkdir(parents=True)
    cached_profile.write_bytes(content)
    machine = paths.machine_file("workstation-01")
    machine.parent.mkdir(parents=True)
    machine.write_text('schema = 4\n[paths]\nworkspace = "/enrolled-machine"\n')
    write_lock(
        paths,
        EnrollmentLock(
            profile_id="personal-profile",
            source="https://example.test/profiles.git",
            requested_ref="main",
            resolved_commit=resolved_commit,
            content_sha256=content_sha256,
            machine_id="workstation-01",
        ),
    )
    return environment


def test_command_help_exposes_public_groups():
    from ai_dlc.cli import app

    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in [
        "project",
        "work",
        "setup",
        "profile",
        "machine",
        "knowledge",
        "mcp",
        "scaffold",
    ]:
        assert name in result.stdout


def test_machine_help_exposes_the_lifecycle_commands():
    """Would fail if an enrolled-machine lifecycle route disappeared from the public CLI."""
    from ai_dlc.cli import app

    result = CliRunner().invoke(app, ["machine", "--help"])

    assert result.exit_code == 0, result.output
    for name in ["enroll", "migrate", "plan", "apply", "sync", "status", "doctor"]:
        assert name in result.stdout


def test_machine_commands_forward_their_documented_defaults(monkeypatch):
    """Would fail if a lifecycle route changed its manager call or preview default."""
    from ai_dlc import cli

    calls = []

    class Manager:
        def enroll(self, source, profile_id, machine_id, **kwargs):
            calls.append(("enroll", source, profile_id, machine_id, kwargs))
            return {"route": "enroll"}

        def migrate(self, source, profile_file, profile_id, machine_id, **kwargs):
            calls.append(("migrate", source, profile_file, profile_id, machine_id, kwargs))
            return {"route": "migrate"}

        def plan(self, **kwargs):
            calls.append(("plan", kwargs))
            return {"route": "plan"}

        def apply(self, **kwargs):
            calls.append(("apply", kwargs))
            return {"route": "apply"}

        def sync(self, **kwargs):
            calls.append(("sync", kwargs))
            return {"route": "sync"}

        def status(self):
            calls.append(("status",))
            return {"route": "status", "ready": True}

        def doctor(self, root, *, target="local"):
            calls.append(("doctor", root, target))
            return {"route": "doctor", "ready": True}

    monkeypatch.setattr(cli, "MachineManager", Manager, raising=False)
    runner = CliRunner()
    invocations = [
        [
            "machine",
            "enroll",
            "/tmp/profile-repo",
            "--profile-id",
            "test-development",
            "--machine-id",
            "test-mac",
        ],
        [
            "machine",
            "enroll",
            "/tmp/profile-repo",
            "--profile-id",
            "test-development",
            "--machine-id",
            "test-mac",
            "--ref",
            "stable",
            "--subdirectory",
            "config",
            "--apply",
        ],
        [
            "machine",
            "migrate",
            "/tmp/profile-repo",
            "--profile-file",
            "profiles/sean.toml",
            "--profile-id",
            "sean-development",
            "--machine-id",
            "personal-macbook",
        ],
        ["machine", "plan"],
        ["machine", "apply"],
        ["machine", "sync"],
        ["machine", "sync", "--apply"],
        ["machine", "status"],
        ["machine", "doctor", "--root", "/tmp/project"],
    ]

    for invocation in invocations:
        result = runner.invoke(cli.app, invocation)
        assert result.exit_code == 0, result.output

    assert calls == [
        (
            "enroll",
            "/tmp/profile-repo",
            "test-development",
            "test-mac",
            {"requested_ref": "main", "subdirectory": "", "apply": False},
        ),
        (
            "enroll",
            "/tmp/profile-repo",
            "test-development",
            "test-mac",
            {"requested_ref": "stable", "subdirectory": "config", "apply": True},
        ),
        (
            "migrate",
            "/tmp/profile-repo",
            "profiles/sean.toml",
            "sean-development",
            "personal-macbook",
            {"requested_ref": "main", "subdirectory": "", "apply": False},
        ),
        ("plan", {"headless": False}),
        ("apply", {"headless": False}),
        ("sync", {"apply": False, "headless": False}),
        ("sync", {"apply": True, "headless": False}),
        ("status",),
        ("doctor", Path("/tmp/project"), "local"),
    ]


def test_scaffold_matches_legacy_assets_and_preserves_conflicts(tmp_path, monkeypatch):
    from ai_dlc.cli import app
    from ai_dlc.files import assets

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["scaffold", "--provider", "gemini"])
    assert result.exit_code == 0, result.output
    source = assets("legacy") / "gemini"
    files = [p for p in source.rglob("*") if p.is_file()]
    assert files
    for file in files:
        assert (tmp_path / ".gemini" / file.relative_to(source)).read_bytes() == file.read_bytes()
    modified = tmp_path / ".gemini" / files[0].relative_to(source)
    modified.write_text("custom")
    result = runner.invoke(app, ["scaffold", "--provider", "gemini"])
    assert result.exit_code != 0
    assert modified.read_text() == "custom"


def test_provider_conformance_failure_is_nonzero(tmp_path, monkeypatch):
    import ai_dlc.sandbox
    from ai_dlc.cli import app

    manifest = tmp_path / "test.toml"
    manifest.write_text("")
    monkeypatch.setattr(ai_dlc.sandbox, "test_provider", lambda *args, **kwargs: {"passed": False})
    result = CliRunner().invoke(app, ["provider", "test", "linear", str(manifest)])
    assert result.exit_code == 1


def test_personal_agent_render_is_explicit_and_project_independent(tmp_path, monkeypatch):
    import json

    from ai_dlc.cli import app

    personal = tmp_path / "personal.toml"
    personal.write_text('schema=4\n[[agents.servers]]\nid="notes"\ncommand="notes-mcp"\n')
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    runner = CliRunner()
    arguments = ["agents", "render", "--personal", str(personal), "--home", str(home)]
    preview = runner.invoke(app, [*arguments, "--check"])
    assert preview.exit_code == 1, preview.output
    assert not list(home.iterdir())
    applied = runner.invoke(app, [*arguments, "--apply"])
    assert applied.exit_code == 0, applied.output
    assert json.loads((home / ".claude.json").read_text())["mcpServers"]["notes"] == {
        "command": "notes-mcp"
    }
    assert runner.invoke(app, [*arguments, "--check"]).exit_code == 0
    assert not list(project.iterdir())


def test_setup_commands_accept_documented_profile_option(tmp_path, monkeypatch):
    import ai_dlc.provision
    from ai_dlc.cli import app

    profile = tmp_path / "profile.toml"
    profile.write_text("schema=4\n")
    monkeypatch.setattr(
        ai_dlc.provision,
        "machine_plan",
        lambda profile, headless=False, home=None, **kwargs: {"profile": str(profile)},
    )
    monkeypatch.setattr(
        ai_dlc.provision,
        "machine_apply",
        lambda profile, headless=False, home=None, **kwargs: {"profile": str(profile)},
    )
    runner = CliRunner()
    for action in ["plan", "apply"]:
        result = runner.invoke(app, ["setup", action, "--profile", str(profile)])
        assert result.exit_code == 0, result.output


def test_setup_commands_without_a_profile_use_the_enrolled_manager(monkeypatch):
    """Would fail if no-profile setup bypassed the active enrolled profile."""
    from ai_dlc import cli

    calls = []

    class Manager:
        def __init__(self, *, home=None):
            self.home = home

        def plan(self, *, headless=False, profile=None):
            calls.append(("plan", self.home, headless, profile))
            return {"route": "enrolled-plan", "home": str(self.home)}

        def apply(self, *, headless=False, profile=None):
            calls.append(("apply", self.home, headless, profile))
            return {"route": "enrolled-apply", "home": str(self.home)}

    monkeypatch.setattr(cli, "MachineManager", Manager)
    runner = CliRunner()

    home = Path("/tmp/sandbox-home")
    for action in ["plan", "apply"]:
        result = runner.invoke(cli.app, ["setup", action, "--home", str(home)])
        assert result.exit_code == 0, result.output
        assert str(home) in result.stdout

    assert calls == [("plan", home, False, None), ("apply", home, False, None)]


def test_setup_profile_replacement_and_home_delegate_to_the_manager(monkeypatch, tmp_path):
    """Would fail if setup bypassed the manager and lost the opposite enrolled scope."""
    from ai_dlc import cli

    profile = tmp_path / "replacement.toml"
    home = tmp_path / "sandbox-home"
    calls = []

    class Manager:
        def __init__(self, *, home=None):
            self.home = home

        def plan(self, *, headless=False, profile=None):
            calls.append(("plan", self.home, headless, profile))
            return {"home": str(self.home), "profile": str(profile)}

        def apply(self, *, headless=False, profile=None):
            calls.append(("apply", self.home, headless, profile))
            return {"home": str(self.home), "profile": str(profile)}

    monkeypatch.setattr(cli, "MachineManager", Manager)
    runner = CliRunner()

    for action in ["plan", "apply"]:
        result = runner.invoke(
            cli.app, ["setup", action, "--profile", str(profile), "--home", str(home)]
        )
        assert result.exit_code == 0, result.output
        assert str(home) in result.stdout
        assert str(profile) in result.stdout

    assert calls == [("plan", home, False, profile), ("apply", home, False, profile)]


def test_setup_and_machine_commands_forward_an_explicit_root(monkeypatch, tmp_path):
    """Would fail if a public setup route accepted --root but dropped the project selection."""
    from ai_dlc import cli

    root = tmp_path / "project"
    calls = []

    class Manager:
        def __init__(self, *, home=None):
            self.home = home

        def plan(self, *, headless=False, profile=None, root=None):
            calls.append(("plan", headless, profile, root))
            return {"route": "plan"}

        def apply(self, *, headless=False, profile=None, root=None):
            calls.append(("apply", headless, profile, root))
            return {"route": "apply"}

    monkeypatch.setattr(cli, "MachineManager", Manager)
    runner = CliRunner()

    for command in [
        ["setup", "plan"],
        ["setup", "apply"],
        ["machine", "plan"],
        ["machine", "apply"],
    ]:
        result = runner.invoke(cli.app, [*command, "--root", str(root)])
        assert result.exit_code == 0, result.output

    assert calls == [
        ("plan", False, None, root),
        ("apply", False, None, root),
        ("plan", False, None, root),
        ("apply", False, None, root),
    ]


def test_profile_show_without_paths_uses_enrolled_runtime_resolution(monkeypatch):
    """Would fail if profile show skipped verified enrollment layers by default."""
    from ai_dlc import cli

    calls = []

    class Resolved:
        def __init__(self):
            self.values = {"profile_id": "enrolled"}
            self.sources = {"profile_id": "personal"}

    def runtime(root=None, *, base=None, personal=None, project=None, machine=None):
        calls.append((root, base, personal, project, machine))
        return Resolved()

    monkeypatch.setattr(cli, "resolve_runtime", runtime, raising=False)

    result = CliRunner().invoke(cli.app, ["profile", "show"])

    assert result.exit_code == 0, result.output
    assert '"profile_id": "enrolled"' in result.stdout
    assert calls == [(None, None, None, None, None)]


def test_profile_show_explicit_personal_keeps_enrolled_machine_and_composes_project(tmp_path):
    from ai_dlc.cli import app

    environment = _write_cli_enrollment(tmp_path)
    personal = tmp_path / "personal.toml"
    personal.write_text('schema = 4\n[roles]\nknowledge = "explicit-personal"\n')
    project = tmp_path / "project.toml"
    project.write_text('schema = 4\n[roles]\ntracker = "explicit-project"\n')

    result = CliRunner().invoke(
        app,
        [
            "profile",
            "show",
            "--personal",
            str(personal),
            "--project",
            str(project),
        ],
        env=environment,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["values"]["roles"]["knowledge"] == "explicit-personal"
    assert payload["values"]["roles"]["tracker"] == "explicit-project"
    assert payload["values"]["paths"]["workspace"] == "/enrolled-machine"
    assert payload["sources"]["roles.knowledge"] == "personal"
    assert payload["sources"]["roles.tracker"] == "project"
    assert payload["sources"]["paths.workspace"] == "machine"


def test_profile_show_explicit_machine_keeps_enrolled_personal_and_composes_project(tmp_path):
    from ai_dlc.cli import app

    environment = _write_cli_enrollment(tmp_path)
    machine = tmp_path / "machine.toml"
    machine.write_text('schema = 4\n[paths]\nworkspace = "/explicit-machine"\n')
    project = tmp_path / "project.toml"
    project.write_text('schema = 4\n[roles]\ntracker = "explicit-project"\n')

    result = CliRunner().invoke(
        app,
        ["profile", "show", "--project", str(project), "--machine", str(machine)],
        env=environment,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["values"]["profile_id"] == "personal-profile"
    assert payload["values"]["roles"]["knowledge"] == "enrolled-personal"
    assert payload["values"]["roles"]["tracker"] == "explicit-project"
    assert payload["values"]["paths"]["workspace"] == "/explicit-machine"
    assert payload["sources"]["profile_id"] == "personal"
    assert payload["sources"]["roles.knowledge"] == "personal"
    assert payload["sources"]["roles.tracker"] == "project"
    assert payload["sources"]["paths.workspace"] == "machine"


def test_explicit_machine_is_forwarded_to_runtime_resolution(monkeypatch, tmp_path):
    """Would fail if workflow configuration ignored a caller's machine override."""
    from ai_dlc import cli

    root = tmp_path / "project"
    machine = tmp_path / "machine.toml"
    calls = []

    class Resolved:
        def __init__(self):
            self.values = {"paths": {"workspace": "/explicit"}}

    def runtime(selected_root, *, machine=None):
        calls.append((selected_root, machine))
        return Resolved()

    monkeypatch.setattr(cli, "resolve_runtime", runtime, raising=False)

    assert cli.config_for(root, machine) == {"paths": {"workspace": "/explicit"}}
    assert calls == [(root, machine)]


def test_root_and_machine_doctor_share_enrolled_readiness(monkeypatch, tmp_path):
    """Would fail if the root doctor used a readiness path different from machine doctor."""
    from ai_dlc import cli

    calls = []

    class Manager:
        def doctor(self, root, *, target="local", machine=None):
            calls.append((root, target, machine))
            return {"ready": False, "machine_checks": {"available": False}}

    monkeypatch.setattr(cli, "MachineManager", Manager)
    runner = CliRunner()

    root_result = runner.invoke(cli.app, ["doctor", "--root", str(tmp_path)])
    machine_result = runner.invoke(cli.app, ["machine", "doctor", "--root", str(tmp_path)])

    assert root_result.exit_code == machine_result.exit_code == 1
    assert root_result.stdout == machine_result.stdout
    assert calls == [(tmp_path, "local", None), (tmp_path, "local", None)]


def test_root_doctor_help_exposes_root_once():
    """Would fail if root doctor registered duplicate --root options."""
    from ai_dlc.cli import app

    result = CliRunner().invoke(app, ["doctor", "--help"])

    assert result.exit_code == 0, result.output
    assert unstyle(result.stdout).count("--root") == 1


def test_explicit_machine_delegates_root_doctor_to_the_manager(monkeypatch, tmp_path):
    """Would fail if root doctor bypassed enrolled personal resolution for --machine."""
    from ai_dlc import cli

    root = tmp_path / "project"
    machine = tmp_path / "machine.toml"
    calls = []

    class Manager:
        def doctor(self, selected_root, *, target="local", machine=None):
            calls.append((selected_root, target, machine))
            return {"ready": True, "personal": "enrolled"}

    monkeypatch.setattr(cli, "MachineManager", Manager)

    result = CliRunner().invoke(cli.app, ["doctor", "--root", str(root), "--machine", str(machine)])

    assert result.exit_code == 0, result.output
    assert calls == [(root, "local", machine)]


def test_explicit_machine_doctor_keeps_the_nonzero_readiness_contract(monkeypatch, tmp_path):
    """Would fail if an unready effective machine override exited successfully."""
    from ai_dlc import cli

    class Manager:
        def doctor(self, root, *, target="local", machine=None):
            return {"ready": False, "machine": str(machine)}

    monkeypatch.setattr(cli, "MachineManager", Manager)

    result = CliRunner().invoke(
        cli.app,
        ["doctor", "--root", str(tmp_path), "--machine", str(tmp_path / "machine.toml")],
    )

    assert result.exit_code == 1
    assert '"ready": false' in result.stdout
