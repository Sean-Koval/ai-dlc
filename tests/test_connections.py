"""Shared onboarding behavior with real local files and fixture remote discovery."""

import copy
import hashlib
import json

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app


@pytest.fixture
def connection(tmp_path, monkeypatch):
    from ai_dlc.provider_definitions import DEFINITIONS, ConnectionHandler, ProviderDefinition

    path = tmp_path / "ai-dlc.toml"
    path.write_text(
        'schema=4\n# authored\n[roles]\ntracker="work"\n[providers.work]\nkind="third"\n'
    )
    remote = {
        "schema": 1,
        "complete": True,
        "account": {"id": "account-1"},
        "resources": {"project": [{"id": "P1", "name": "Team work"}]},
    }
    calls = []

    def discover(config, alias, *, environ):
        calls.append(alias)
        return copy.deepcopy(remote)

    def configure(discovery, selected):
        return {"project_id": selected["project"], "account_id": discovery["account"]["id"]}

    monkeypatch.setitem(
        DEFINITIONS,
        "third",
        ProviderDefinition(
            kind="third",
            roles=("tracker",),
            selection_keys=frozenset({"project"}),
            handler=ConnectionHandler(discover=discover, configure=configure),
        ),
    )
    return tmp_path, path, remote, calls


def invoke(root, *args):
    return CliRunner().invoke(app, ["provider", "connect", "work", "--root", str(root), *args])


def test_third_handler_uses_common_discovery_saved_plan_and_authored_apply(connection):
    root, config, _, calls = connection
    before = config.read_bytes()
    result = invoke(root)
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["status"] == "discovered"
    assert config.read_bytes() == before
    planned = invoke(
        root, "--select", "project=Team work", "--plan-file", ".ai-dlc/local/plan.json"
    )
    assert planned.exit_code == 0, planned.output
    plan = json.loads(planned.output)["plan"]
    assert plan["selected"] == {"project": "P1"}
    assert plan["before_digest"] == hashlib.sha256(before).hexdigest()
    assert config.read_bytes() == before
    applied = invoke(root, "--plan-file", ".ai-dlc/local/plan.json", "--apply")
    assert applied.exit_code == 0, applied.output
    assert json.loads(applied.output)["status"] == "applied"
    assert "# authored\n" in config.read_text()
    assert 'project_id = "P1"' in config.read_text()
    assert calls == ["work", "work", "work"]


@pytest.mark.parametrize("change", ["account", "membership", "source", "work", "incomplete"])
def test_common_apply_refuses_drift_without_configuration_write(connection, change):
    root, config, remote, _ = connection
    assert (
        invoke(
            root, "--select", "project=Team work", "--plan-file", ".ai-dlc/local/p.json"
        ).exit_code
        == 0
    )
    if change == "account":
        remote["account"]["id"] = "another-account"
    elif change == "membership":
        remote["resources"]["project"] = [{"id": "P2", "name": "Team work"}]
    elif change == "source":
        config.write_text(config.read_text() + "# new authored comment\n")
    elif change == "work":
        directory = root / ".ai-dlc/work"
        directory.mkdir()
        (directory / "new.toml").write_text('id="new"\n')
    else:
        remote["complete"] = False
    before = config.read_bytes()
    result = invoke(root, "--plan-file", ".ai-dlc/local/p.json", "--apply")
    assert result.exit_code != 0
    assert config.read_bytes() == before


@pytest.mark.parametrize(
    "args",
    [
        ["--select", "project=A", "--select", "project=B"],
        ["--select", "project=A", "--project", "A"],
        ["--select", "unknown=credential-sentinel"],
        ["--select", "project="],
        ["--select", "missing-equals"],
        ["--select", "project=P1", "--apply", "--plan-file", ".ai-dlc/local/p.json"],
    ],
)
def test_generic_selection_errors_precede_discovery_and_do_not_echo_values(connection, args):
    root, config, _, calls = connection
    before = config.read_bytes()
    result = invoke(root, *args)
    assert result.exit_code != 0
    assert "credential-sentinel" not in result.output
    assert calls == []
    assert config.read_bytes() == before


@pytest.mark.parametrize("damage", ["ambiguous", "incomplete", "duplicate_id"])
def test_common_discovery_refuses_ambiguous_or_incomplete_resources(connection, damage):
    root, config, remote, _ = connection
    if damage == "incomplete":
        remote["complete"] = False
    else:
        remote["resources"]["project"].append(
            {"id": "P1" if damage == "duplicate_id" else "P2", "name": "Team work"}
        )
    before = config.read_bytes()
    result = invoke(root, "--select", "project=Team work", "--plan-file", ".ai-dlc/local/p.json")
    assert result.exit_code != 0
    assert config.read_bytes() == before
    assert not (root / ".ai-dlc/local/p.json").exists()


def test_common_saved_plan_is_exclusive_and_bound_tracker_change_is_refused(connection):
    root, config, _, _ = connection
    plan_path = root / ".ai-dlc/local/p.json"
    assert invoke(root, "--select", "project=P1", "--plan-file", str(plan_path)).exit_code == 0
    plan_before = plan_path.read_bytes()
    assert invoke(root, "--select", "project=P1", "--plan-file", str(plan_path)).exit_code != 0
    assert plan_path.read_bytes() == plan_before
    directory = root / ".ai-dlc/work"
    directory.mkdir()
    (directory / "bound.toml").write_text('id="bound"\n[artifacts]\ntracker="T1"\n')
    before = config.read_bytes()
    assert invoke(root, "--select", "project=P1").exit_code != 0
    assert config.read_bytes() == before


def test_definition_without_setup_does_not_change_lifecycle_configuration(connection, monkeypatch):
    from ai_dlc.provider_definitions import DEFINITIONS, ProviderDefinition

    root, config, _, calls = connection
    monkeypatch.setitem(DEFINITIONS, "third", ProviderDefinition(kind="third", roles=("tracker",)))
    before = config.read_bytes()
    result = invoke(root)
    assert result.exit_code != 0
    assert "not supported" in result.output
    assert config.read_bytes() == before
    assert calls == []


def test_common_facade_preserves_unrelated_project_setting(connection):
    from ai_dlc.connections import apply_connection, discover_connection, plan_connection

    root, config, _, _ = connection
    config.write_text(config.read_text() + 'project="authored-project" # keep\n')
    assert discover_connection(root, "work", environ={})["status"] == "discovered"
    saved = plan_connection(
        root, "work", {"project": "P1"}, environ={}, plan_file=root / ".ai-dlc/local/p.json"
    )
    apply_connection(root, "work", saved["plan_file"], environ={})
    assert 'project="authored-project" # keep' in config.read_text()


@pytest.mark.parametrize(
    "mode", ["inline", "plan-symlink", "lock-source", "lock-work", "secret-metadata"]
)
def test_common_writer_refuses_unsafe_or_changed_inputs(connection, monkeypatch, mode):
    from contextlib import contextmanager

    from ai_dlc import connections

    root, config, remote, _ = connection
    if mode == "inline":
        config.write_text('schema=4\n[providers]\nwork={kind="third"}\n')
    elif mode == "secret-metadata":
        remote["account"]["token"] = "credential-sentinel"
    plan = root / ".ai-dlc/local/p.json"
    if mode == "plan-symlink":
        plan.parent.mkdir(parents=True)
        target = root / "authored.json"
        target.write_text("authored")
        plan.symlink_to(target)
    before = config.read_bytes()
    planned = invoke(root, "--select", "project=P1", "--plan-file", str(plan))
    if mode.startswith("lock-"):
        assert planned.exit_code == 0, planned.output
        original_lock = connections.project_write_lock

        @contextmanager
        def changed_lock(project):
            with original_lock(project):
                if mode == "lock-source":
                    config.write_bytes(before + b"# authored after preview\n")
                else:
                    directory = root / ".ai-dlc/work"
                    directory.mkdir()
                    (directory / "bound.toml").write_text('id="late"\n[artifacts]\ntracker="T1"\n')
                yield

        monkeypatch.setattr(connections, "project_write_lock", changed_lock)
        result = invoke(root, "--plan-file", str(plan), "--apply")
        assert result.exit_code != 0
        assert config.read_bytes() == before + (
            b"# authored after preview\n" if mode == "lock-source" else b""
        )
    else:
        assert planned.exit_code != 0
        assert "credential-sentinel" not in planned.output
        assert config.read_bytes() == before
        if mode == "plan-symlink":
            assert target.read_text() == "authored"
