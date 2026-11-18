"""Knowledge reads return customer records only from a customer repository (KAN-524).

A team repository whose ``[check] roots`` leave out ``projects/`` used to pass a
``boundary: customer`` record and return its body to ``get``/``search`` with
``project=<customer>``. Reads now refuse it unless ``knowledge.toml`` declares
``[repo] boundary = "customer"``, and a relative git ``location`` is relative to the
configuration's directory, never the working directory.
"""

import subprocess

import pytest
from test_git_knowledge import record
from test_mcp_surface import call

from ai_dlc.documentation.knowledge import Knowledge
from ai_dlc.documentation.knowledge_check import CUSTOMER_READ
from ai_dlc.mcp_server import make_server
from ai_dlc.providers import Registry

PIN = "[format]\nversion = 1\n"
TEAM = PIN + '[check]\nroots = ["records"]\n'
CUSTOMER = PIN + '[repo]\nboundary = "customer"\nproject = "alpha"\n'


def knowledge_repo(folder, toml=TEAM):
    """A git checkout with one team record and one alpha customer record."""
    (folder / "records").mkdir(parents=True)
    (folder / "projects/alpha").mkdir(parents=True)
    (folder / "knowledge.toml").write_text(toml)
    (folder / "records/team.md").write_text(record("team-lesson", "lesson", tags=["splunk"]))
    customer = {"scope": "project", "boundary": "customer", "tags": ["splunk"]}
    (folder / "projects/alpha/gotcha.md").write_text(record("alpha-gotcha", "lesson", **customer))
    subprocess.run(["git", "init", "--quiet", str(folder)], check=True)
    return folder


def git_provider(root, location):
    config = {
        "roles": {"knowledge": "team"},
        "providers": {"team": {"kind": "git", "location": location}},
    }
    return Registry(config, root=root, environ={}).get("team")


@pytest.mark.parametrize("reader", ["git", "vault"])
def test_a_team_repository_refuses_its_customer_records(tmp_path, reader):
    repo = knowledge_repo(tmp_path / "team")
    store = git_provider(tmp_path, str(repo)) if reader == "git" else Knowledge(repo)

    with pytest.raises(ValueError, match="their customer's own repository"):
        store.get("alpha-gotcha", project="alpha")
    with pytest.raises(LookupError):
        store.get("alpha-gotcha")  # no project: not found, as before
    found = store.search(labels=["splunk"], project="alpha")
    assert [item["id"] for item in found["items"]] == ["team-lesson"]
    assert found["refused"] == {"count": 1, "reason": CUSTOMER_READ}
    assert "refused" not in store.search(labels=["splunk"], project="beta")


@pytest.mark.parametrize("reader", ["git", "vault"])
def test_a_customer_repository_returns_its_records_to_its_project(tmp_path, reader):
    repo = knowledge_repo(tmp_path / "alpha", CUSTOMER)
    store = git_provider(tmp_path, str(repo)) if reader == "git" else Knowledge(repo)

    assert store.get("alpha-gotcha", project="alpha")["path"] == "projects/alpha/gotcha.md"
    found = store.search(labels=["splunk"], project="alpha")
    assert {item["id"] for item in found["items"]} == {"alpha-gotcha", "team-lesson"}
    assert "refused" not in found
    with pytest.raises(LookupError):
        store.get("alpha-gotcha", project="beta")


def test_a_malformed_repo_declaration_returns_no_customer_record(tmp_path):
    repo = knowledge_repo(tmp_path / "x", PIN + '[repo]\nboundary = "customer"\n')
    with pytest.raises(ValueError, match="their customer's own repository"):
        git_provider(tmp_path, str(repo)).get("alpha-gotcha", project="alpha")


def test_mcp_tools_refuse_a_team_repositorys_customer_record(tmp_path):
    repo = knowledge_repo(tmp_path / "team")
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(
        f'schema = 4\n[roles]\nknowledge = "team"\n[providers.team]\nkind = "git"\nlocation = "{repo}"\n'
    )
    got, found = call(
        make_server(root),
        ("knowledge_get", {"id": "alpha-gotcha", "project": "alpha"}),
        ("knowledge_search", {"labels": ["splunk"], "project": "alpha"}),
    )
    assert got["status"] == "refused" and "customer's own repository" in got["reason"]
    assert "body" not in got
    assert found["status"] == "ok" and found["refused"]["count"] == 1
    assert [item["id"] for item in found["items"]] == ["team-lesson"]


def test_a_relative_location_is_relative_to_the_configuration_not_the_cwd(tmp_path, monkeypatch):
    root = tmp_path / "project"
    knowledge_repo(root / "knowledge", CUSTOMER)
    elsewhere = knowledge_repo(tmp_path / "elsewhere")  # a team checkout the shell is in
    monkeypatch.chdir(elsewhere)

    provider = git_provider(root, "knowledge")
    assert provider.repository_root() == (root / "knowledge").resolve()
    assert provider.get("alpha-gotcha", project="alpha")["path"] == "projects/alpha/gotcha.md"
    assert git_provider(root, ".").location == str(root / ".")
    assert git_provider(root, str(elsewhere)).repository_root() == elsewhere.resolve()


def test_knowledge_repo_variable_keeps_naming_a_path_from_the_shell(tmp_path, monkeypatch):
    from ai_dlc.documentation.knowledge_service import KnowledgeRecords

    knowledge_repo(tmp_path / "team")
    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.chdir(tmp_path)
    records = KnowledgeRecords(root, {"roles": {}}, environ={"KNOWLEDGE_REPO": "team"})
    assert records.get("team-lesson")["path"] == "records/team.md"


@pytest.mark.parametrize("reader", ["git", "vault"])
def test_a_customer_repository_refuses_another_customers_record(tmp_path, reader):
    # alpha's repository wrongly holding a beta record: reads refuse it without a check run.
    repo = knowledge_repo(tmp_path / "alpha", CUSTOMER)
    (repo / "projects/beta").mkdir()
    beta = {"scope": "project", "boundary": "customer", "tags": ["splunk"]}
    (repo / "projects/beta/secret.md").write_text(record("beta-secret", "lesson", **beta))
    store = git_provider(tmp_path, str(repo)) if reader == "git" else Knowledge(repo)

    with pytest.raises(ValueError, match="their customer's own repository"):
        store.get("beta-secret", project="beta")
    found = store.search(labels=["splunk"], project="beta")
    assert [item["id"] for item in found["items"]] == ["team-lesson"]
    assert found["refused"]["count"] == 1
    assert store.get("alpha-gotcha", project="alpha")["path"] == "projects/alpha/gotcha.md"
