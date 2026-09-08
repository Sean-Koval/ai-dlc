import json
import subprocess

import pytest


def test_default_conformance_runs_packaged_fixture_suite(tmp_path, monkeypatch, capsys):
    from ai_dlc import conformance

    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_providers.py").write_text("")
    monkeypatch.setattr(conformance, "KIT_ROOT", tmp_path)
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "2 passed", "")

    monkeypatch.setattr(subprocess, "run", run)
    assert conformance.main(["linear"]) == 0
    command, kwargs = calls[0]
    assert "-m" in command and "pytest" in command
    assert "-k" in command and "linear" in command
    assert kwargs["env"]["AI_DLC_TEST_TOKEN"] == "fake-credential"
    result = json.loads(capsys.readouterr().out)
    assert result["scope"] == "offline-fixtures"
    assert result["live"] is False


def test_unknown_conformance_target_is_rejected():
    from ai_dlc import conformance

    with pytest.raises(SystemExit) as error:
        conformance.main(["arbitrary-command"])
    assert error.value.code == 2


def test_live_requires_fixture_and_designated_workspace(tmp_path, monkeypatch, capsys):
    from ai_dlc import conformance

    monkeypatch.setattr(conformance, "FIXTURE_CONFIG", tmp_path / "provider.toml")
    assert conformance.main(["linear", "--live"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "unavailable"


def test_live_unsupported_subsystem_never_reports_pass(capsys):
    from ai_dlc import conformance

    assert conformance.main(["workflow", "--live"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "unavailable"
    assert result["passed"] is False


def live_linear_config(tmp_path, monkeypatch):
    from ai_dlc import conformance

    path = tmp_path / "provider.toml"
    path.write_text(
        'sandbox_workspace="team-sandbox"\n[provider]\nkind="linear"\nteam_id="team-sandbox"\ntoken_env="CONFORMANCE_TOKEN"\nhealth_reference="issue-id"\n'
    )
    monkeypatch.setattr(conformance, "FIXTURE_CONFIG", path)
    monkeypatch.setenv("AI_DLC_SANDBOX_WORKSPACE", "team-sandbox")
    monkeypatch.setenv("CONFORMANCE_TOKEN", "test-secret")
    return conformance


def test_live_linear_is_read_only_and_checks_remote_workspace(tmp_path, monkeypatch, capsys):
    from ai_dlc.providers.linear import LinearProvider

    conformance = live_linear_config(tmp_path, monkeypatch)
    calls = []

    def query(self, query, variables):
        calls.append(query)
        return {
            "issue": {
                "id": "issue-id",
                "url": "https://linear.app/test",
                "team": {"id": "team-sandbox"},
            }
        }

    monkeypatch.setattr(LinearProvider, "query", query)
    assert conformance.main(["linear", "--live"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["scope"] == "read-only-health"
    assert result["mutation_conformance"] == "unavailable"
    assert all("mutation" not in query.lower() for query in calls)
    assert "test-secret" not in json.dumps(result)


def test_live_linear_rejects_foreign_workspace(tmp_path, monkeypatch, capsys):
    from ai_dlc.providers.linear import LinearProvider

    conformance = live_linear_config(tmp_path, monkeypatch)
    monkeypatch.setattr(
        LinearProvider,
        "query",
        lambda self, query, variables: {
            "issue": {
                "id": "issue-id",
                "url": "https://linear.app/test",
                "team": {"id": "production-team"},
            }
        },
    )
    assert conformance.main(["linear", "--live"]) == 1
    assert json.loads(capsys.readouterr().out)["passed"] is False


def test_live_github_only_reads_designated_issue(tmp_path, monkeypatch, capsys):
    from ai_dlc import conformance
    from ai_dlc.providers.github_issues import GitHubIssuesProvider

    path = tmp_path / "provider.toml"
    path.write_text(
        'sandbox_workspace="sandbox/repo"\n[provider]\nkind="github-issues"\nrepository="sandbox/repo"\ntoken_env="GH_TOKEN"\nhealth_reference="12"\n'
    )
    monkeypatch.setattr(conformance, "FIXTURE_CONFIG", path)
    monkeypatch.setenv("AI_DLC_SANDBOX_WORKSPACE", "sandbox/repo")
    monkeypatch.setenv("GH_TOKEN", "fake-live-test-token")
    monkeypatch.setattr(conformance.shutil, "which", lambda command: "/fake/gh")
    calls = []

    def invoke(self, operation, payload):
        calls.append((operation, payload))
        return {"id": "12", "url": "https://github.com/sandbox/repo/issues/12", "state": "open"}

    monkeypatch.setattr(GitHubIssuesProvider, "invoke", invoke)
    assert conformance.main(["github-issues", "--live"]) == 0
    assert calls == [("read", {"reference": "12"})]
    result = json.loads(capsys.readouterr().out)
    assert result["scope"] == "read-only-health"
    assert result["full_conformance"] == "unavailable"


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("jira-cloud", {"tests/test_jira_provider.py", "tests/test_jira_workflow.py"}),
        ("plane", {"tests/test_plane_provider.py", "tests/test_plane_workflow.py"}),
        ("github-issues", {"tests/test_providers.py", "tests/test_github_projects.py"}),
    ],
)
def test_tracker_targets_include_adapter_and_lifecycle_fixtures(target, expected):
    from ai_dlc import conformance

    paths, expression = conformance.FIXTURE_TARGETS[target]
    assert set(paths) == expected
    # A legacy selection expression must not deselect the new lifecycle suite.
    assert expression == (
        "github_executable or test_github_projects" if target == "github-issues" else None
    )
    for aggregate in ("providers", "all"):
        aggregate_paths, _ = conformance.FIXTURE_TARGETS[aggregate]
        assert expected <= set(aggregate_paths)
        assert len(aggregate_paths) == len(set(aggregate_paths))


@pytest.mark.parametrize("target", ["jira-cloud", "plane"])
def test_new_tracker_live_scope_remains_explicitly_unavailable(target, capsys):
    from ai_dlc import conformance

    assert conformance.main([target, "--live"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "unavailable"
    assert result["passed"] is False


@pytest.mark.parametrize("target", ["jira-cloud", "plane", "github-issues", "all"])
def test_copied_package_runs_real_tracker_fixtures(target, tmp_path, monkeypatch, capsys):
    """Run the Dockerfile's test closure, not mocked pytest output or source collection."""
    import shlex
    import shutil
    from pathlib import Path

    from ai_dlc import conformance

    root = Path(__file__).resolve().parents[1]
    (tmp_path / "tests").mkdir()
    for line in (root / "containers/provider-tests.Dockerfile").read_text().splitlines():
        if not line.startswith("COPY "):
            continue
        fields = shlex.split(line)
        if fields[:1] == ["COPY"] and fields[-1] == "/kit/tests/":
            for source in fields[1:-1]:
                shutil.copyfile(root / source, tmp_path / "tests" / Path(source).name)
    (tmp_path / "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath=["src"]\n')
    source = tmp_path / "src/ai_dlc"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text('raise RuntimeError("repository source was imported")\n')
    monkeypatch.setattr(conformance, "KIT_ROOT", tmp_path)
    assert conformance.main([target]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["scope"] == "offline-fixtures"
    assert result["live"] is False
    assert result["passed"] is True


@pytest.mark.parametrize("target", ["jira-cloud", "plane", "github-issues"])
def test_missing_tracker_lifecycle_fixture_refuses(target, tmp_path, monkeypatch, capsys):
    from ai_dlc import conformance

    (tmp_path / "tests").mkdir()
    for name in ("test_jira_provider.py", "test_plane_provider.py", "test_providers.py"):
        (tmp_path / "tests" / name).write_text("")
    monkeypatch.setattr(conformance, "KIT_ROOT", tmp_path)
    assert conformance.main([target]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "unavailable"
