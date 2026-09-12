"""Workspace diagnostics keep installation, activation, mounts, navigation and clients distinct."""

import asyncio
import json
import os
import shlex
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fixtures.messy_project import EXPECTED_REVIEW_POINTS, FILES, build_messy_project
from typer.testing import CliRunner

from ai_dlc import __version__
from ai_dlc.cli import app

COMMANDS = ("docs-search", "docs-read", "workspace-check")


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout


def fake_cli(directory: Path, *, version=__version__, commands=COMMANDS, delay=0) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / "ai-dlc"
    script.write_text(
        "#!/bin/sh\n"
        f"sleep {delay}\n"
        f'if [ "$1" = --version ]; then echo "ai-dlc {version}"; exit 0; fi\n'
        f'if [ "$1" = project ]; then echo "Commands: {" ".join(commands)}"; exit 0; fi\n'
        "exit 2\n"
    )
    script.chmod(0o755)
    return script


def inspect(root, **kwargs):
    from ai_dlc.documentation.workspace_diagnostics import inspect_project_workspace

    return inspect_project_workspace(root, **kwargs)


def codes(result):
    return {finding["code"] for finding in result["findings"]}


def owned_rc(authored: str, bin_dir: Path) -> str:
    from ai_dlc.harness.agents import _section

    return _section(authored, f'export PATH={shlex.quote(str(bin_dir))}:"$PATH"\n', toml=True)


def snapshot(*roots):
    return sorted(str(p) for root in roots for p in root.rglob("*") if ".git" not in p.parts)


@pytest.fixture
def machine(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    toolkit = fake_cli(tmp_path / "toolkit")
    bootstrap = tmp_path / "bootstrap"
    (bootstrap / "bin").mkdir(parents=True)
    (bootstrap / "bin/ai-dlc").symlink_to(toolkit)
    (tmp_path / "empty-bin").mkdir()
    environ = {
        "HOME": str(home),
        "SHELL": "/bin/zsh",
        "AI_DLC_BOOTSTRAP_HOME": str(bootstrap),
        "PATH": os.pathsep.join([str(tmp_path / "empty-bin"), "/usr/bin", "/bin"]),
    }
    return SimpleNamespace(home=home, bin=bootstrap / "bin", environ=environ, root=tmp_path)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "parcel"
    files = {
        "docs/index.md": "# Parcel\n\n[API](reference/api.md)\n",
        "docs/reference/api.md": (
            "# API\n\nSee [retry](../../openspec/specs/delivery/spec.md),\n"
            "[config](../../src/parcel/config.py), [gone](missing.md) and "
            "[site](https://example.com/docs).\n\n```md\n[example](../../fenced.md)\n```\n"
        ),
        "openspec/specs/delivery/spec.md": "## Requirement: Retry\n",
        "src/parcel/config.py": "SECRET_CONFIG_BODY = 3\n",
        ".gitignore": ".ai-dlc/local/\n",
    }
    for relative, body in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(body)
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-qm", "base")
    (root / ".ai-dlc/local").mkdir(parents=True)
    return root


@pytest.fixture
def vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Private.md").write_text("PRIVATE NOTE BODY\n")
    return vault


def mount(project, vault):
    from ai_dlc.documentation.vault_mount import mount_vault

    mount_vault(project, vault, "parcel", adopt=False, apply=True)


def test_missing_setup_reports_separate_scoped_findings_without_mutation(project, machine):
    before = snapshot(project, machine.root)
    result = inspect(project, environ=machine.environ)
    assert set(result) == {
        "schema",
        "project_root",
        "installation",
        "activation",
        "workspace",
        "navigation",
        "native_client",
        "findings",
        "limitations",
    }
    assert result["installation"]["status"] == "missing"
    assert result["installation"]["observed_version"] is None
    assert result["activation"]["status"] == "missing"
    assert result["workspace"] == {
        "bindings": [],
        "binding_directory_error": None,
        "vault": {"status": "not-configured", "path": None},
    }
    assert result["native_client"]["status"] == "not-assessed"
    assert codes(result) >= {
        "executable-missing",
        "activation-missing",
        "vault-not-configured",
        "native-client-not-assessed",
    }
    assert snapshot(project, machine.root) == before


def test_observed_version_is_never_replaced_by_current_process_metadata(project, machine):
    old = machine.root / "old-bin"
    fake_cli(old, version="0.3.9", commands=("docs-search",))
    environ = machine.environ | {"PATH": f"{old}{os.pathsep}{machine.environ['PATH']}"}
    installation = inspect(project, environ=environ)["installation"]
    assert installation["status"] == "different"
    assert installation["observed_version"] == "0.3.9"
    assert installation["current_process_version"] == __version__
    assert installation["commands"] == {
        "docs-search": True,
        "docs-read": False,
        "workspace-check": False,
    }
    assert installation["executable"] == str(old / "ai-dlc")


def test_probe_timeout_is_unverified(project, machine, monkeypatch):
    import ai_dlc.documentation.workspace_diagnostics as service

    slow = machine.root / "slow-bin"
    fake_cli(slow, delay=3)
    monkeypatch.setattr(service, "PROBE_TIMEOUT", 0.2)
    environ = machine.environ | {"PATH": f"{slow}{os.pathsep}{machine.environ['PATH']}"}
    installation = inspect(project, environ=environ)["installation"]
    assert installation["status"] == "unverified"
    assert installation["probes"]["version"] == "timeout"
    assert installation["observed_version"] is None


def test_unreported_version_names_commands_the_executable_lacks(project, machine):
    legacy = machine.root / "legacy-bin"
    script = fake_cli(legacy, commands=("docs-init",))
    script.write_text(script.read_text().replace('"$1" = --version', '"$1" = --unsupported'))
    environ = machine.environ | {"PATH": f"{legacy}{os.pathsep}{machine.environ['PATH']}"}
    result = inspect(project, environ=environ)
    assert result["installation"]["status"] == "unverified"
    assert result["installation"]["observed_version"] is None
    assert result["installation"]["probes"] == {"version": "failed", "help": "ok"}
    [finding] = [f for f in result["findings"] if f["code"] == "executable-unverified"]
    assert "missing commands: docs-search, docs-read, workspace-check" in finding["message"]
    assert "bootstrap" in finding["action"]


def test_configured_shell_is_distinguished_from_active_path(project, machine):
    (machine.home / ".zshrc").write_text(
        owned_rc("export SECRET_TOKEN=do-not-return\n", machine.bin)
    )
    before = snapshot(machine.root)
    result = inspect(project, environ=machine.environ)
    assert result["activation"]["status"] == "configured-for-next-shell"
    assert result["activation"]["configured"]["matches_bootstrap_bin"] is True
    assert result["installation"]["status"] == "missing"
    assert {"activation-next-shell", "executable-missing"} <= codes(result)
    assert "source" in json.dumps(result["findings"])
    assert "do-not-return" not in json.dumps(result)
    assert snapshot(machine.root) == before

    active = machine.environ | {"PATH": f"{machine.bin}{os.pathsep}{machine.environ['PATH']}"}
    result = inspect(project, environ=active)
    assert result["activation"]["status"] == "active"
    assert result["installation"]["status"] == "current"
    assert not codes(result) & {"activation-next-shell", "executable-missing"}


@pytest.mark.parametrize(
    ("case", "status", "section"),
    [
        ("stale-bin", "stale", "present"),
        ("missing-alias", "stale", "present"),
        ("modified", "unverified", "modified"),
        ("symlinked-rc", "unverified", "unreadable"),
        ("unsupported-shell", "unverified", "unsupported-shell"),
        ("absent", "missing", "absent"),
    ],
)
def test_stale_or_unprovable_activation(project, machine, case, status, section):
    rc = machine.home / ".zshrc"
    authored = "export SECRET_TOKEN=do-not-return\n"
    environ = machine.environ
    if case == "stale-bin":
        rc.write_text(owned_rc(authored, machine.root / "gone-bin"))
    elif case == "missing-alias":
        rc.write_text(owned_rc(authored, machine.bin))
        (machine.bin / "ai-dlc").unlink()
    elif case == "modified":
        rc.write_text(owned_rc(authored, machine.bin).replace("export PATH=", "export PATH=/x:"))
    elif case == "symlinked-rc":
        real = machine.root / "dotfiles-zshrc"
        real.write_text(owned_rc(authored, machine.bin))
        rc.symlink_to(real)
    elif case == "unsupported-shell":
        environ = environ | {"SHELL": "/usr/bin/fish"}
    result = inspect(project, environ=environ)
    assert result["activation"]["status"] == status
    assert result["activation"]["configured"]["section"] == section
    assert "do-not-return" not in json.dumps(result)
    assert not (machine.bin / "ai-dlc-cli").exists()


def test_mounted_repository_only_and_missing_links(project, machine, vault, monkeypatch):
    import ai_dlc.documentation.workspace_diagnostics as service

    unmounted = inspect(project, environ=machine.environ)["navigation"]
    assert {link["status"] for link in unmounted["links"]} == {
        "unmounted",
        "repository-only",
        "missing",
    }
    mount(project, vault)
    read = []
    original = service.read_bounded
    monkeypatch.setattr(
        service,
        "read_bounded",
        lambda root, rel, left: read.append(rel) or original(root, rel, left),
    )
    result = inspect(project, vault=str(vault), environ=machine.environ)
    [binding] = result["workspace"]["bindings"]
    assert binding["status"] == "connected" and binding["current_checkout"] is True
    assert [m["status"] for m in binding["mounts"]] == ["connected", "connected"]
    assert result["workspace"]["vault"] is None
    links = {
        (link["source"], link["line"], link["target"], link["status"])
        for link in result["navigation"]["links"]
    }
    assert links == {
        ("docs/index.md", 3, "reference/api.md", "mounted"),
        ("docs/reference/api.md", 3, "../../openspec/specs/delivery/spec.md", "mounted"),
        ("docs/reference/api.md", 4, "../../src/parcel/config.py", "repository-only"),
        ("docs/reference/api.md", 4, "missing.md", "missing"),
    }
    assert result["navigation"]["coverage"]["complete"] is True
    assert set(read) == {
        "docs/index.md",
        "docs/reference/api.md",
        "openspec/specs/delivery/spec.md",
    }
    serialized = json.dumps(result)
    assert "SECRET_CONFIG_BODY" not in serialized and "PRIVATE NOTE BODY" not in serialized
    assert {"repository-only-links", "missing-link-targets"} <= codes(result)
    assert not (project / "src" / "parcel" / "config.py").is_symlink()


def test_malformed_binding_is_isolated_and_link_changes_are_reported(
    project, machine, vault, tmp_path
):
    from ai_dlc.documentation.vault_mount import read_mount_bindings

    mount(project, vault)
    bindings = project / ".ai-dlc/local/vault-mounts"
    (bindings / "bad.json").write_text("{")
    gone = {"schema": 1, "project_root": str(tmp_path / "gone"), "vault_path": str(vault)}
    (bindings / "gone.json").write_text(json.dumps(gone | {"project_name": "gone"}))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    link = vault / "Projects/parcel/docs"
    link.unlink()
    link.symlink_to(elsewhere, target_is_directory=True)
    result = inspect(project, vault=str(vault), environ=machine.environ)
    statuses = {Path(b["binding_path"]).name: b["status"] for b in result["workspace"]["bindings"]}
    assert statuses.pop("bad.json") == "malformed"
    assert statuses.pop("gone.json") == "checkout-missing"
    assert list(statuses.values()) == ["attention"]
    [healthy] = [b for b in result["workspace"]["bindings"] if b.get("mounts")]
    assert [(m["root"], m["status"]) for m in healthy["mounts"]] == [
        ("docs", "changed-link"),
        ("openspec", "connected"),
    ]
    assert healthy["mounts"][0]["raw_target"] == str(elsewhere)
    assert {"binding-malformed", "binding-checkout-missing", "mount-changed-link"} <= codes(result)
    assert not (tmp_path / "gone").exists()
    with pytest.raises(ValueError):
        read_mount_bindings(project)


@pytest.mark.parametrize("state", ["unbound", "missing", "unavailable"])
def test_unbound_vault_state_without_scanning(project, machine, vault, tmp_path, state):
    selected = {
        "unbound": vault,
        "missing": tmp_path / "absent",
        "unavailable": vault / "Private.md",
    }
    result = inspect(project, vault=str(selected[state]), environ=machine.environ)
    assert result["workspace"]["vault"]["status"] == state
    assert f"vault-{state}" in codes(result)
    assert "Private.md" not in json.dumps(result).replace(str(vault / "Private.md"), "")
    assert not (vault / "Projects").exists()


def test_cli_version_and_workspace_check_share_one_result(project, machine, monkeypatch, tmp_path):
    from ai_dlc.mcp_server import make_server

    runner = CliRunner()
    version = runner.invoke(app, ["--version"])
    assert version.exit_code == 0 and version.stdout.strip() == f"ai-dlc {__version__}"
    for name, value in machine.environ.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    cli = runner.invoke(app, ["project", "workspace-check", "--root", str(project)])
    assert cli.exit_code == 0, cli.output
    server = make_server(project)
    assert "project_workspace_check" in {t.name for t in asyncio.run(server.list_tools())}
    mcp = asyncio.run(server.call_tool("project_workspace_check", {}))
    assert json.loads(cli.stdout) == json.loads(mcp[0].text)


def test_messy_project_fixture_preserves_approved_baseline(tmp_path, machine):
    from ai_dlc.documentation.document_inventory import inventory_documents

    root = build_messy_project(tmp_path / "messy")
    assert inventory_documents(root)["documents"] == [
        "README.md",
        "SETUP_OLD.md",
        "docs/adr/001-adapter.md",
        "docs/architecture-notes.md",
        "docs/architecture.md",
        "docs/configuration.md",
        "docs/deployment.md",
        "legacy/retry-experiment.md",
        "openspec/specs/delivery/spec.md",
    ]
    assert git(root, "status", "--porcelain") == b""
    assert all(any(path in point for path in FILES) for point in EXPECTED_REVIEW_POINTS)
    navigation = inspect(root, environ=machine.environ)["navigation"]
    assert {link["status"] for link in navigation["links"]} == {"unmounted"}
    with pytest.raises(ValueError):
        build_messy_project(root)


def source_environment(root: Path, checkout: Path) -> Path:
    """A bootstrap source environment that records the checkout it was synced from."""
    executable = fake_cli(root / "bin")
    (root / "ai-dlc-source-root").write_text(f"{checkout}\n")
    return executable


def test_shared_alias_is_attributed_to_the_checkout_it_runs(project, machine, tmp_path):
    other = tmp_path / "other-checkout"
    other.mkdir()
    executable = source_environment(tmp_path / "source-other", other)
    alias = machine.bin / "ai-dlc"
    alias.unlink()
    alias.symlink_to(executable)
    active = machine.environ | {"PATH": f"{machine.bin}{os.pathsep}{machine.environ['PATH']}"}

    result = inspect(project, environ=active)
    current = result["activation"]["current"]
    assert result["activation"]["status"] == "active"
    assert current["alias_checkout"] == str(other)
    assert current["alias_is_this_checkout"] is False
    assert "alias-other-checkout" in codes(result)
    assert "--publish-aliases" in json.dumps(result["findings"])


def test_shared_alias_for_this_checkout_reports_no_alias_finding(project, machine, tmp_path):
    executable = source_environment(tmp_path / "source-self", project)
    alias = machine.bin / "ai-dlc"
    alias.unlink()
    alias.symlink_to(executable)
    active = machine.environ | {"PATH": f"{machine.bin}{os.pathsep}{machine.environ['PATH']}"}

    result = inspect(project, environ=active)
    current = result["activation"]["current"]
    assert current["alias_checkout"] == str(project)
    assert current["alias_is_this_checkout"] is True
    assert "alias-other-checkout" not in codes(result)


def test_unattributed_alias_stays_unknown_rather_than_assumed(project, machine):
    active = machine.environ | {"PATH": f"{machine.bin}{os.pathsep}{machine.environ['PATH']}"}

    current = inspect(project, environ=active)["activation"]["current"]
    assert current["alias_environment"] is not None
    assert current["alias_checkout"] is None
    assert current["alias_is_this_checkout"] is None
