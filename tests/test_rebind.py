import tomllib

import pytest
import tomli_w
from typer.testing import CliRunner

from ai_dlc.rebind import rebind


@pytest.fixture
def project(tmp_path):
    (tmp_path / "ai-dlc.toml").write_text(
        'schema = 4\n[roles]\ntracker = "linear"\n[providers.github-issues]\nkind = "github-issues"\n'
    )
    work = {
        "schema": 1,
        "id": "one",
        "title": "One",
        "scope": "Small",
        "requires_spec": False,
        "spec_reason": "No behavior change",
        "acceptance": ["Verified"],
        "reviewed": True,
        "providers": {"tracker": "linear"},
        "artifacts": {"tracker": "OLD-1"},
        "bindings": {},
    }
    path = tmp_path / ".ai-dlc/work/one.toml"
    path.parent.mkdir(parents=True)
    path.write_text(tomli_w.dumps(work))
    return tmp_path


def test_plan_retains_binding(project):
    before = (project / "ai-dlc.toml").read_bytes()
    result = rebind(project, "tracker", "github-issues")
    assert result["active_work"][0]["id"] == "one"
    assert result["active_work"][0]["provider"] == "linear"
    assert (project / "ai-dlc.toml").read_bytes() == before


def test_apply_requires_mapping(project):
    with pytest.raises(ValueError, match="mapping"):
        rebind(project, "tracker", "github-issues", apply=True)
    assert tomllib.loads((project / "ai-dlc.toml").read_text())["roles"]["tracker"] == "linear"


def test_mapping_updates_all_binding_parts(project):
    result = rebind(
        project, "tracker", "github-issues", apply=True, mappings={"one": {"tracker": "42"}}
    )
    assert result["status"] == "applied"
    work = tomllib.loads((project / ".ai-dlc/work/one.toml").read_text())
    assert work["providers"]["tracker"] == "github-issues"
    assert work["artifacts"]["tracker"] == "42"
    assert len(work["bindings"]["tracker"]) == 64


def test_empty_mapping_refused(project):
    with pytest.raises(ValueError, match="mapping"):
        rebind(project, "tracker", "github-issues", apply=True, mappings={"one": {}})


def test_rebind_same_provider_requires_explicit_artifact_mapping(project):
    with pytest.raises(ValueError, match="mapping"):
        rebind(project, "tracker", "linear", apply=True)
    assert (
        rebind(project, "tracker", "linear", apply=True, mappings={"one": {"tracker": "LINEAR-2"}})[
            "status"
        ]
        == "applied"
    )


def test_machine_configuration_preserves_unrelated_bindings(project, tmp_path):
    from ai_dlc.config import load_project, resolve_layers
    from ai_dlc.workflow import WorkService

    machine = {"schema": 4, "paths": {"vault": str(tmp_path / "vault")}}
    resolved = resolve_layers([("project", load_project(project)), ("machine", machine)]).values
    service = WorkService(project, resolved, state_path=tmp_path / "state")
    pinned = service.load("one")
    service.save(pinned)
    before = pinned["bindings"]["knowledge"]
    rebind(
        project,
        "tracker",
        "github-issues",
        apply=True,
        mappings={"one": {"tracker": "42"}},
        machine_config=machine,
    )
    work = tomllib.loads((project / ".ai-dlc/work/one.toml").read_text())
    assert work["bindings"]["knowledge"] == before
    assert "paths" not in tomllib.loads((project / "ai-dlc.toml").read_text())


def test_rebind_preview_supports_the_provider_connect_refusal_guidance(project):
    """The guided command must expose affected work without mutating its binding."""
    from ai_dlc.cli import app

    work_path = project / ".ai-dlc/work/one.toml"
    before = work_path.read_bytes()

    result = CliRunner().invoke(
        app,
        ["project", "rebind", "tracker", "linear", "--root", str(project)],
    )

    assert result.exit_code == 0, result.output
    payload = __import__("json").loads(result.stdout)
    assert payload["status"] == "planned"
    assert payload["active_work"][0]["id"] == "one"
    assert work_path.read_bytes() == before
