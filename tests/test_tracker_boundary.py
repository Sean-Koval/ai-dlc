"""GitHub Issues defaults, the removed Linear adapter, unsupported Plane and finish-only writes."""

import subprocess
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

REPOSITORY = Path(__file__).resolve().parents[1]
REMOVAL = "Linear tracker adapter was removed"


def _git(root, *args):
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=True
    ).stdout.strip()


def _init_git(root):
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    (root / ".gitignore").write_text("state/\n")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "initial")


def _record(root, tracker="fake", artifacts=""):
    folder = root / ".ai-dlc/work"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "one.toml"
    path.write_text(
        'schema=1\nid="one"\ntitle="One"\nscope="small"\nrequires_spec=false\n'
        'spec_reason="No behavior change"\nacceptance=["Tests pass"]\nreviewed=true\n'
        f'[providers]\ntracker="{tracker}"\n' + artifacts
    )
    return path


def _rendered_text(root):
    return "".join(
        path.read_text(errors="ignore")
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    )


def test_project_init_defaults_to_github_issues_without_linear(tmp_path):
    from ai_dlc.cli import app

    target = tmp_path / "project"
    result = CliRunner().invoke(app, ["project", "init", str(target), "--preset", "generic"])

    assert result.exit_code == 0, result.output
    config = tomllib.loads((target / "ai-dlc.toml").read_text())
    assert config["roles"]["tracker"] == "github-issues"
    assert "linear" not in config.get("providers", {})
    assert "LINEAR_API_KEY" not in _rendered_text(target)


def test_copier_template_defaults_render_no_linear_credential(tmp_path):
    import copier

    from ai_dlc.setup.templates import assets

    target = tmp_path / "copied"
    copier.run_copy(
        str(assets("project-templates")),
        target,
        data={"project_name": "project-copied"},
        defaults=True,
        quiet=True,
        skip_tasks=True,
    )

    text = _rendered_text(target)
    assert "LINEAR_API_KEY" not in text
    answers = (target / ".copier-answers.yml").read_text()
    assert "tracker: github-issues" in answers


def test_packaged_defaults_and_catalogs_do_not_select_linear():
    import json

    from ai_dlc.setup.templates import assets, plan_toolset

    assert plan_toolset()["roles"]["tracker"] == "github-issues"
    assert tomllib.loads((assets("profiles") / "base.toml").read_text())["roles"]["tracker"] == (
        "github-issues"
    )
    assert "linear" not in tomllib.loads((assets("modules") / "catalog.toml").read_text())
    components = json.loads((assets("modules") / "components.json").read_text())["components"]
    assert "linear" not in {component["id"] for component in components}


def test_repository_validates_linear_history_without_a_linear_provider():
    """Finished records keep their historical tracker binding; validation never resolves it."""
    from ai_dlc.work.workflow import validate_work_records

    config = tomllib.loads((REPOSITORY / "ai-dlc.toml").read_text())
    assert "linear" not in config.get("providers", {})
    historical = [
        path.stem
        for path in sorted((REPOSITORY / ".ai-dlc/work").glob("*.toml"))
        if tomllib.loads(path.read_text()).get("providers", {}).get("tracker") == "linear"
    ]
    assert len(historical) >= 5

    result = validate_work_records(REPOSITORY)

    assert result["valid"], result["errors"]
    assert set(historical) <= set(result["records"])


def test_work_start_refuses_a_linear_tracker_with_typed_exit_status(tmp_path):
    from ai_dlc.cli import app

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\ntracker="linear"\n[providers.linear]\ntoken_env="LINEAR_API_KEY"\n'
    )
    record = _record(tmp_path, tracker="linear")
    _init_git(tmp_path)
    before = record.read_bytes()

    result = CliRunner().invoke(
        app,
        ["work", "start", "one", "--root", str(tmp_path)],
        env={"XDG_STATE_HOME": str(tmp_path / "state"), "LINEAR_API_KEY": "unused"},
    )

    assert result.exit_code == 2, result.output
    assert REMOVAL in result.output
    assert "github-issues or jira-cloud" in result.output
    assert record.read_bytes() == before
    assert _git(tmp_path, "branch", "--show-current") == "main"


def test_rebind_to_linear_is_refused_but_rebind_away_needs_no_linear_reads(tmp_path):
    from ai_dlc.providers import RemovedProviderError
    from ai_dlc.setup.rebind import rebind

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\ntracker="linear"\n[providers.github-issues]\nrepository="acme/app"\n'
    )
    _record(tmp_path, tracker="linear", artifacts='[artifacts]\ntracker="LIN-1"\n')

    with pytest.raises(RemovedProviderError):
        rebind(tmp_path, "tracker", "linear")

    plan = rebind(tmp_path, "tracker", "github-issues")
    assert [item["id"] for item in plan["active_work"]] == ["one"]
    applied = rebind(
        tmp_path, "tracker", "github-issues", apply=True, mappings={"one": {"tracker": "7"}}
    )
    assert applied["status"] == "applied"
    record = tomllib.loads((tmp_path / ".ai-dlc/work/one.toml").read_text())
    assert record["providers"]["tracker"] == "github-issues"
    assert record["artifacts"]["tracker"] == "7"


def test_doctor_reports_removed_and_unsupported_trackers():
    from ai_dlc.providers import REMOVED_PROVIDER_KINDS
    from ai_dlc.setup.provision import _configuration_gaps, _provider_support

    linear = {"roles": {"tracker": "linear"}, "providers": {}}
    assert REMOVED_PROVIDER_KINDS["linear"] in _configuration_gaps(linear)
    plane = {"roles": {"tracker": "tickets"}, "providers": {"tickets": {"kind": "plane"}}}
    assert _provider_support(plane) == [
        {
            "role": "tracker",
            "provider": "tickets",
            "kind": "plane",
            "status": "unsupported, unqualified",
        }
    ]
    assert _provider_support({"roles": {"tracker": "github-issues"}}) == []


def test_plane_scaffold_requires_explicit_unsupported_opt_in(tmp_path):
    from ai_dlc.cli import app
    from ai_dlc.provider_definitions import DEFINITIONS

    assert DEFINITIONS["plane"].supported is False
    refused = tmp_path / "refused"
    result = CliRunner().invoke(app, ["project", "init", str(refused), "--tracker", "plane"])
    assert result.exit_code == 2, result.output
    assert "--allow-unsupported" in result.output
    assert not (refused / "ai-dlc.toml").exists()

    allowed = tmp_path / "allowed"
    result = CliRunner().invoke(
        app, ["project", "init", str(allowed), "--tracker", "plane", "--allow-unsupported"]
    )
    assert result.exit_code == 0, result.output
    assert tomllib.loads((allowed / "ai-dlc.toml").read_text())["roles"]["tracker"] == "plane"


def test_scaffold_refuses_removed_linear_selection():
    from ai_dlc.providers import RemovedProviderError
    from ai_dlc.setup.templates import plan_toolset

    with pytest.raises(RemovedProviderError, match=REMOVAL):
        plan_toolset(providers={"tracker": "linear"})


@pytest.mark.parametrize(
    "layer, data, accepted",
    [
        ("project", {"work": {"tracker_writes": "finish-only"}}, True),
        ("base", {"work": {"tracker_writes": "lifecycle"}}, True),
        ("project", {"work": {"tracker_writes": "never"}}, False),
        ("project", {"work": {"other": True}}, False),
        ("personal", {"work": {"tracker_writes": "finish-only"}}, False),
        ("machine", {"work": {"tracker_writes": "finish-only"}}, False),
    ],
)
def test_tracker_writes_setting_is_scoped_and_validated(layer, data, accepted):
    from ai_dlc.config import SCHEMA, _validate

    document = {"schema": SCHEMA, **data}
    if accepted:
        _validate(layer, document)
    else:
        with pytest.raises(ValueError, match="work"):
            _validate(layer, document)


class RecordingTracker:
    """A fake tracker that records every operation it receives."""

    def __init__(self, state="open"):
        self.calls = []
        self.item = {"id": "1", "url": "https://issues/1", "state": state}

    def invoke(self, operation, data):
        self.calls.append(operation)
        if operation == "find":
            return {"items": []}
        if operation == "transition":
            self.item["state"] = data["state"]
        return dict(self.item)


def _service(root, tracker, config):
    from ai_dlc.providers import Registry
    from ai_dlc.work.workflow import WorkService

    registry = Registry()
    registry.register("fake", tracker)
    return WorkService(root, config, state_path=root / "state", registry=registry)


@pytest.mark.parametrize("published", [True, False])
def test_finish_only_start_makes_no_tracker_mutation(tmp_path, published):
    _record(tmp_path)
    _init_git(tmp_path)
    tracker = RecordingTracker()
    service = _service(tmp_path, tracker, {"work": {"tracker_writes": "finish-only"}})
    if published:
        service.publish("one")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-q", "-m", "publish")
    tracker.calls.clear()

    result = service.start("one")

    assert not {"create", "transition", "comment", "append"} & set(tracker.calls)
    assert tracker.calls == (["read"] if published else [])
    assert result["status"] == "started"
    assert result["branch"] == "work/one"
    assert result["tracker_transition"]["skipped"] is True
    assert (result["tracker"] is not None) is published
    assert tracker.item["state"] == "open"


def test_lifecycle_default_start_still_transitions(tmp_path):
    _record(tmp_path)
    _init_git(tmp_path)
    tracker = RecordingTracker()
    service = _service(tmp_path, tracker, {})

    result = service.start("one")

    assert "transition" in tracker.calls
    assert result["tracker_transition"]["state"] == "in_progress"


def test_finish_on_an_already_closed_ticket_reconciles(tmp_path, monkeypatch):
    from ai_dlc.work import workflow

    class SCM:
        def __init__(self, root, config):
            pass

        def merged(self, reference):
            return {"sha": "trusted-merge", "pr": {"merged": True}}

        def ci(self, sha):
            return {"sha": sha, "run_id": 7, "receipt": {"trusted_fixture": True}}

    monkeypatch.setattr(workflow, "GitHubSCM", SCM)
    _record(tmp_path)
    tracker = RecordingTracker()
    service = _service(tmp_path, tracker, {"work": {"tracker_writes": "finish-only"}})
    service.publish("one")
    tracker.item["state"] = "closed"  # A hangar delivery closed the ticket first.
    tracker.calls.clear()

    result = service.finish("one")

    assert result["status"] == "completed"
    assert result["tracker"]["state"] == "closed"
    assert "transition" not in tracker.calls
