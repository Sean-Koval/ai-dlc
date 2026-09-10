"""Reviewed native composition uses local fixtures, never native authentication claims."""

import json
import tomllib
from pathlib import Path

import pytest
import tomli_w
from typer.testing import CliRunner

from ai_dlc.cli import app


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    config = {
        "schema": 4,
        "roles": {
            "tracker": "work-tracker",
            "knowledge": "private-notes",
            "agent-client": ["claude-code"],
        },
        "providers": {
            "work-tracker": {
                "kind": "github-issues",
                "account": "work",
                "repository": "example/project",
            },
            "private-notes": {"kind": "obsidian", "account": "work"},
        },
        "agents": {"servers": []},
    }
    (root / "ai-dlc.toml").write_text("# Authored policy stays here.\n" + tomli_w.dumps(config))
    environ = {
        "HOME": str(tmp_path / "home"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_STATE_HOME": str(tmp_path / "state"),
    }
    return root, environ


def binding(role="tracker", provider="work-tracker", **changes):
    return {
        "role": role,
        "provider": provider,
        "server": "shared",
        "account": "work",
        "command": "ai-dlc",
        "args": ["mcp", "serve"],
        **changes,
    }


def bindings_file(root, rows):
    path = root / "docs/setup/native-bindings.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps({"schema": 1, "bindings": rows}))
    return path


def test_exact_shared_connection_deduplicates_without_changing_role_guidance(project):
    from ai_dlc.harness.native_composition import plan_native_connections

    root, environ = project
    rows = [binding(), binding("knowledge", "private-notes")]
    source = bindings_file(root, rows)
    before = (root / "ai-dlc.toml").read_bytes()
    result = plan_native_connections(root, source, environ=environ)
    assert result["status"] == "planned"
    assert result["plan"]["patch"]["servers"] == [
        {
            "id": "shared",
            "account": "work",
            "command": "ai-dlc",
            "args": ["mcp", "serve"],
            "env": [],
        }
    ]
    assert result["roles"] == {"knowledge": "private-notes", "tracker": "work-tracker"}
    assert result["authentication"] == "unverified"
    assert "endpoint" in result["account_notice"].lower()
    assert (root / "ai-dlc.toml").read_bytes() == before
    assert not (root / ".mcp.json").exists()


@pytest.mark.parametrize(
    "change",
    [
        {"account": "personal"},
        {"args": ["mcp", "different"]},
        {"command": "other"},
        {"env": ["TOKEN_NAME"]},
        {"url": "https://mcp.example.invalid/service"},
    ],
)
def test_conflicting_shared_alias_refuses_before_writes(project, change):
    from ai_dlc.harness.native_composition import plan_native_connections

    root, environ = project
    second = binding("knowledge", "private-notes", **change)
    if "url" in change:
        second.pop("command")
        second.pop("args")
    source = bindings_file(root, [binding(), second])
    before = (root / "ai-dlc.toml").read_bytes()
    with pytest.raises(ValueError):
        plan_native_connections(root, source, environ=environ)
    assert (root / "ai-dlc.toml").read_bytes() == before


@pytest.mark.parametrize(
    "change",
    [
        {"provider": "wrong-provider"},
        {"role": "deploy"},
        {"account": "personal"},
        {"env": ["TOKEN_NAME=value"]},
        {"headers": {"Authorization": "not-a-supported-format"}},
        {"url": "https://mcp.example.invalid/path"},
        {"command": "/Users/private/bin/tool"},
    ],
)
def test_invalid_binding_refuses_without_rewriting_configuration(project, change):
    from ai_dlc.harness.native_composition import plan_native_connections

    root, environ = project
    source = bindings_file(root, [binding(**change)])
    before = (root / "ai-dlc.toml").read_bytes()
    with pytest.raises(ValueError):
        plan_native_connections(root, source, environ=environ)
    assert (root / "ai-dlc.toml").read_bytes() == before


def test_two_projects_keep_distinct_account_expectations_at_one_endpoint(tmp_path):
    from ai_dlc.harness.native_composition import plan_native_connections

    plans = []
    for account in ["personal", "work"]:
        root = tmp_path / account
        root.mkdir()
        (root / "ai-dlc.toml").write_text(
            tomli_w.dumps(
                {
                    "schema": 4,
                    "roles": {"tracker": "selected"},
                    "providers": {"selected": {"kind": "github-issues", "account": account}},
                }
            )
        )
        source = bindings_file(
            root,
            [
                {
                    "role": "tracker",
                    "provider": "selected",
                    "server": "same-alias",
                    "account": account,
                    "url": "https://mcp.example.invalid/service",
                }
            ],
        )
        result = plan_native_connections(root, source, environ={"HOME": str(tmp_path / "home")})
        plans.append(result["plan"]["patch"]["servers"][0])
        assert result["authentication"] == "unverified"
        assert "does not" in result["account_notice"].lower()
    assert plans[0]["url"] == plans[1]["url"]
    assert [row["account"] for row in plans] == ["personal", "work"]


@pytest.mark.parametrize(
    "representation", ["empty-inline", "nonempty-inline", "multiline-inline", "array-tables"]
)
def test_saved_cli_apply_preserves_manual_source_and_defers_render(project, representation):
    from ai_dlc.harness.agents import render_agents

    root, environ = project
    manual = {"id": "authored", "command": "authored-command", "args": []}
    if representation != "empty-inline":
        path = root / "ai-dlc.toml"
        config = tomllib.loads(path.read_text())
        del config["agents"]
        representations = {
            "nonempty-inline": '[agents]\nservers = [{id="authored", command="authored-command", args=[]}] # kept\n',
            "multiline-inline": '[agents]\nservers = [ # kept\n  {id="authored", command="authored-command", args=[]}, # entry stays\n]\n',
            "array-tables": '[[agents.servers]]\nid="authored" # kept\ncommand="authored-command"\nargs=[]\n',
        }
        path.write_text(
            "# Authored policy stays here.\n"
            + tomli_w.dumps(config)
            + "\n"
            + representations[representation]
        )
    source = bindings_file(root, [binding(), binding("knowledge", "private-notes")])
    plan_path = ".ai-dlc/local/native-plan.json"
    result = CliRunner().invoke(
        app,
        [
            "agents",
            "connect",
            "--root",
            str(root),
            "--bindings",
            str(source),
            "--save-plan",
            plan_path,
        ],
        env=environ,
    )
    assert result.exit_code == 0, result.output
    original = (root / "ai-dlc.toml").read_text()
    result = CliRunner().invoke(
        app, ["agents", "connect", "--root", str(root), "--apply-plan", plan_path], env=environ
    )
    assert result.exit_code == 0, result.output
    applied = json.loads(result.output)
    assert applied["rendering"] == "pending"
    assert applied["authentication"] == "unverified"
    assert not (root / ".mcp.json").exists()
    text = (root / "ai-dlc.toml").read_text()
    assert "# Authored policy stays here." in text
    config = tomllib.loads(text)
    servers = config["agents"]["servers"]
    if representation != "empty-inline":
        assert servers[0] == manual
        assert "# kept" in text
        if representation == "multiline-inline":
            assert "# entry stays" in text
    assert servers[-1]["account"] == "work"
    assert config["roles"] == tomllib.loads(original)["roles"]
    render_agents(root, apply=True)
    assert (root / ".ai-dlc/providers/github-issues.md").is_file()
    assert (root / ".ai-dlc/providers/obsidian.md").is_file()
    assert json.loads((root / ".mcp.json").read_text())["mcpServers"]["shared"]["args"] == [
        "mcp",
        "serve",
    ]


@pytest.mark.parametrize("drift", ["source", "input", "role", "account", "plan"])
def test_stale_or_tampered_saved_plan_refuses_config_apply(project, drift):
    from ai_dlc.harness.native_composition import apply_native_connections, plan_native_connections

    root, environ = project
    source = bindings_file(root, [binding()])
    plan_path = Path(".ai-dlc/local/native-plan.json")
    plan_native_connections(root, source, environ=environ, save_plan=plan_path)
    path = root / "ai-dlc.toml"
    if drift == "source":
        path.write_text(path.read_text() + "# changed\n")
    elif drift == "input":
        source.write_text(source.read_text() + "# changed\n")
    elif drift in {"role", "account"}:
        config = tomllib.loads(path.read_text())
        if drift == "role":
            config["roles"]["tracker"] = "other"
        else:
            config["providers"]["work-tracker"]["account"] = "other"
        path.write_text(tomli_w.dumps(config))
    else:
        saved = json.loads((root / plan_path).read_text())
        saved["patch"]["servers"][0]["command"] = "tampered"
        (root / plan_path).write_text(json.dumps(saved))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        apply_native_connections(root, plan_path, environ=environ)
    assert path.read_bytes() == before
    assert not (root / ".mcp.json").exists()


def test_existing_manual_alias_with_unknown_account_is_not_assumed_compatible(project):
    from ai_dlc.harness.native_composition import plan_native_connections

    root, environ = project
    path = root / "ai-dlc.toml"
    config = tomllib.loads(path.read_text())
    config["agents"]["servers"] = [{"id": "shared", "command": "ai-dlc", "args": ["mcp", "serve"]}]
    path.write_text(tomli_w.dumps(config))
    source = bindings_file(root, [binding()])
    before = path.read_bytes()
    with pytest.raises(ValueError, match="alias|account|identity"):
        plan_native_connections(root, source, environ=environ)
    assert path.read_bytes() == before


def test_personal_servers_are_never_copied_into_project(project):
    from test_config import _write_enrollment

    from ai_dlc.environment.enrollment import EnrollmentPaths
    from ai_dlc.harness.native_composition import plan_native_connections

    root, environ = project
    config = tomllib.loads((root / "ai-dlc.toml").read_text())
    del config["agents"]
    (root / "ai-dlc.toml").write_text(tomli_w.dumps(config))
    paths = EnrollmentPaths.from_environment(environ=environ)
    _write_enrollment(
        paths,
        content=b'schema = 4\n[[agents.servers]]\nid="personal-only"\ncommand="private-tool"\n',
    )
    source = bindings_file(root, [binding()])
    result = plan_native_connections(root, source, environ=environ)
    assert [row["id"] for row in result["plan"]["patch"]["servers"]] == ["shared"]


@pytest.mark.parametrize("target", ["input", "plan"])
def test_symlink_input_or_saved_plan_refuses_without_writes(project, target):
    from ai_dlc.harness.native_composition import apply_native_connections, plan_native_connections

    root, environ = project
    source = bindings_file(root, [binding()])
    plan = Path(".ai-dlc/local/native-plan.json")
    plan_native_connections(root, source, environ=environ, save_plan=plan)
    path = source if target == "input" else root / plan
    moved = path.with_suffix(".original")
    path.rename(moved)
    path.symlink_to(moved)
    before = (root / "ai-dlc.toml").read_bytes()
    with pytest.raises((OSError, ValueError)):
        apply_native_connections(root, plan, environ=environ)
    assert (root / "ai-dlc.toml").read_bytes() == before


def test_machine_account_change_invalidates_saved_native_plan(project):
    from test_config import _write_enrollment

    from ai_dlc.environment.enrollment import EnrollmentPaths
    from ai_dlc.harness.native_composition import apply_native_connections, plan_native_connections

    root, environ = project
    paths = EnrollmentPaths.from_environment(environ=environ)
    _write_enrollment(
        paths,
        content=b"schema=4\n",
        machine='schema=4\n[providers.work-tracker]\naccount="machine-work"\n',
    )
    source = bindings_file(root, [binding(account="machine-work")])
    plan = Path(".ai-dlc/local/native-plan.json")
    plan_native_connections(root, source, environ=environ, save_plan=plan)
    paths.machine_file("workstation-01").write_text(
        'schema=4\n[providers.work-tracker]\naccount="machine-other"\n'
    )
    before = (root / "ai-dlc.toml").read_bytes()
    with pytest.raises(ValueError, match="account"):
        apply_native_connections(root, plan, environ=environ)
    assert (root / "ai-dlc.toml").read_bytes() == before


def test_binding_change_during_staging_refuses_destination_write(project, monkeypatch):
    from ai_dlc.harness import native_composition

    root, environ = project
    source = bindings_file(root, [binding()])
    plan = Path(".ai-dlc/local/native-plan.json")
    native_composition.plan_native_connections(root, source, environ=environ, save_plan=plan)
    before = (root / "ai-dlc.toml").read_bytes()
    original = native_composition.render_native_patch
    calls = 0

    def replace_input(text, alias, patch):
        nonlocal calls
        calls += 1
        rendered = original(text, alias, patch)
        if calls == 2:  # Apply rendering, after fresh-plan validation.
            source.write_text(source.read_text() + "# concurrent edit\n")
        return rendered

    monkeypatch.setattr(native_composition, "render_native_patch", replace_input)
    with pytest.raises(ValueError, match="source changed"):
        native_composition.apply_native_connections(root, plan, environ=environ)
    assert (root / "ai-dlc.toml").read_bytes() == before


def test_config_only_apply_does_not_override_authored_native_file(project):
    from ai_dlc.harness.agents import render_agents
    from ai_dlc.harness.native_composition import apply_native_connections, plan_native_connections

    root, environ = project
    authored = b'{"mcpServers":{"shared":{"command":"authored-owner"}}}\n'
    (root / ".mcp.json").write_bytes(authored)
    source = bindings_file(root, [binding()])
    plan = Path(".ai-dlc/local/native-plan.json")
    plan_native_connections(root, source, environ=environ, save_plan=plan)
    result = apply_native_connections(root, plan, environ=environ)
    assert result["rendering"] == "pending"
    assert (root / ".mcp.json").read_bytes() == authored
    with pytest.raises(ValueError, match="conflict|authored|owned"):
        render_agents(root, apply=True)
    assert (root / ".mcp.json").read_bytes() == authored
