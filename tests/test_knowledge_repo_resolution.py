"""Knowledge record reads find the repository ``KNOWLEDGE_REPO`` names (KAN-523).

From a project checkout whose knowledge role is a vault, or unset, the MCP
``knowledge_search`` and ``knowledge_get`` tools and the ``knowledge records`` CLI read
``KNOWLEDGE_REPO``. A git provider's own ``location`` wins over it, so a customer
checkout never falls back to the team repository. With neither, they fail with an
error naming ``KNOWLEDGE_REPO`` and never read the current checkout.
"""

import json
import shutil
import subprocess

import pytest
from test_git_knowledge import FIXTURES, store  # noqa: F401
from test_mcp_surface import call
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.mcp_server import make_server


def knowledge_clone(folder):
    """An initialised knowledge repository holding one fixture record."""
    (folder / "records").mkdir(parents=True)
    (folder / "knowledge.toml").write_text("[format]\nversion = 1\n")
    source = min((FIXTURES / "1-meeting").glob("*.md"))
    (folder / "records" / source.name).write_text(source.read_text())
    subprocess.run(["git", "init", "--quiet", str(folder)], check=True)
    return folder


def project(tmp_path, roles: str = "", providers: str = ""):
    """A project checkout that itself holds records, which must never be read."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(f"schema = 4\n[roles]\n{roles}{providers}")
    shutil.copytree(FIXTURES / "1-meeting", root / "records")
    (root / "knowledge.toml").write_text("[format]\nversion = 1\n")
    return root


@pytest.fixture
def environ(store, monkeypatch):  # noqa: F811
    for key, value in store["environ"].items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("KNOWLEDGE_REPO", raising=False)
    return store


def ids(result):
    return {item["id"] for item in result["items"]}


@pytest.mark.parametrize("roles", ['knowledge = "obsidian"\n', ""])
def test_mcp_knowledge_tools_read_knowledge_repo_not_the_checkout(
    environ, tmp_path, monkeypatch, roles
):
    root = project(tmp_path, roles)
    monkeypatch.setenv("KNOWLEDGE_REPO", str(environ["clone"]))
    # The clone holds accepted.md (KEEP-MAIN-GREEN); the checkout does not.
    found, got = call(
        make_server(root),
        ("knowledge_search", {"type": "decision"}),
        ("knowledge_get", {"id": "keep-main-green"}),
    )

    assert found["status"] == "ok", found
    assert "records/accepted.md" in {item["path"] for item in found["items"]}
    assert got["status"] == "ok", got
    assert got["path"] == "records/accepted.md"


def test_mcp_knowledge_tools_fail_clearly_without_a_repository(environ, tmp_path):
    root = project(tmp_path)

    found, got = call(
        make_server(root),
        ("knowledge_search", {"type": "decision"}),
        ("knowledge_get", {"id": "keep-main-green"}),
    )

    for refused in (found, got):
        assert isinstance(refused, str), refused  # a tool error, not records of the checkout
        assert "KNOWLEDGE_REPO" in refused
        assert "never read from the current checkout" in refused


def test_a_configured_location_wins_over_knowledge_repo(environ, tmp_path, monkeypatch):
    customer = knowledge_clone(tmp_path / "customer")
    root = project(
        tmp_path,
        'knowledge = "customer"\n',
        f'[providers.customer]\nkind = "git"\nlocation = "{customer}"\n',
    )
    monkeypatch.setenv("KNOWLEDGE_REPO", str(environ["clone"]))  # the team repository

    (found,) = call(make_server(root), ("knowledge_search", {}))

    assert found["status"] == "ok", found
    assert not any("accepted" in item["path"] for item in found["items"])


def test_an_unreachable_configured_location_never_falls_back(environ, tmp_path, monkeypatch):
    missing = tmp_path / "customer-missing"
    root = project(
        tmp_path,
        'knowledge = "customer"\n',
        f'[providers.customer]\nkind = "git"\nlocation = "{missing}"\n',
    )
    monkeypatch.setenv("KNOWLEDGE_REPO", str(environ["clone"]))

    (refused,) = call(make_server(root), ("knowledge_get", {"id": "keep-main-green"}))

    assert isinstance(refused, str), refused
    assert "is not a git checkout" in refused


def test_cli_records_reads_knowledge_repo_from_a_project_checkout(environ, tmp_path, monkeypatch):
    root = project(tmp_path, 'knowledge = "obsidian"\n')
    (root / "knowledge.toml").unlink()  # an ordinary project checkout
    monkeypatch.setenv("KNOWLEDGE_REPO", str(environ["clone"]))

    result = CliRunner().invoke(
        app, ["knowledge", "records", "get", "keep-main-green", "--root", str(root)]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["path"] == "records/accepted.md"
