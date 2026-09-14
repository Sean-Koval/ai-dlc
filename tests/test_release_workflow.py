"""First-use release verification must initialize before checking CI freshness."""

import shlex
from pathlib import Path

import yaml

from ai_dlc.setup.project import setup_project

ROOT = Path(__file__).resolve().parents[1]


def consumer_steps():
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    return workflow["jobs"]["verify-published"]["steps"]


def test_manual_release_replay_cannot_build_or_publish_even_from_a_tag():
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    jobs = workflow["jobs"]
    assert jobs["publish"]["if"] == "github.event_name == 'push' && github.ref_type == 'tag'"
    assert "inputs.verify_published_tag" in jobs["package"]["if"]
    condition = jobs["verify-published"]["if"]
    assert "!cancelled()" in condition
    assert "github.event_name == 'workflow_dispatch'" in condition
    assert "inputs.verify_published_tag != ''" in condition
    assert "needs.package.result == 'success'" in condition
    assert "needs.publish.result == 'success'" in condition
    assert "inputs.verify_published_tag" in jobs["verify-published"]["env"]["RELEASE_TAG"]
    script = consumer_steps()[0]["run"]
    assert 'gh release download "$RELEASE_TAG"' in script
    assert "${{ github.ref_name }}" not in script


def bootstrap_target(script):
    commands = [shlex.split(line) for line in script.splitlines() if line.strip()]
    bootstrap = next(
        command for command in commands if command[:2] == ["sh", "scripts/bootstrap.sh"]
    )
    return bootstrap[bootstrap.index("--target") + 1] if "--target" in bootstrap else "local"


def test_release_seed_first_setup_initializes_generated_files(tmp_path):
    """The workflow's selected target must accept a seed with no generated files."""
    (tmp_path / "ai-dlc.toml").write_text("schema = 4\n")
    result = setup_project(
        tmp_path, bootstrap_target(consumer_steps()[0]["run"]), state_path=tmp_path / "state.db"
    )
    assert result["ready"]
    assert (tmp_path / "AGENTS.md").exists()
    assert setup_project(tmp_path, "github-actions", state_path=tmp_path / "state.db")[
        "agent_configuration"
    ]["clean"]


def test_release_demo_bootstraps_before_required_ci_checks(tmp_path):
    """A generated consumer needs setup before its explicit CI verification."""
    script = consumer_steps()[1]["run"]
    commands = [shlex.split(line) for line in script.splitlines() if line.strip()]
    setup_index = next(
        (i for i, command in enumerate(commands) if command[:2] == ["sh", "scripts/bootstrap.sh"]),
        None,
    )
    check_index = next(
        i for i, command in enumerate(commands) if command[:3] == ["ai-dlc", "project", "check"]
    )
    assert setup_index is not None, "The generated demo never runs release-mode bootstrap"
    assert setup_index < check_index
    assert commands[check_index][-2:] == ["--target", "github-actions"]
    (tmp_path / "ai-dlc.toml").write_text("schema = 4\n")
    assert setup_project(tmp_path, bootstrap_target(script), state_path=tmp_path / "state.db")[
        "ready"
    ]
    assert setup_project(tmp_path, "github-actions", state_path=tmp_path / "state.db")[
        "agent_configuration"
    ]["clean"]
