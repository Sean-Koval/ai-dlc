import shutil
import subprocess

import pytest
import tomli_w


@pytest.fixture
def setup_fixture(tmp_path, monkeypatch):
    from ai_dlc import agents, project

    (tmp_path / ".mise.toml").write_text("[tools]\n")
    monkeypatch.setattr(agents, "render_agents", lambda *args, **kwargs: {"clean": True})
    monkeypatch.setattr(agents, "target_hooks", lambda *args, **kwargs: {"ready": True})
    runs = []

    def configure(command="uv sync --locked", inputs=None):
        step = {"id": "dependencies", "command": command, "verify": "test -f uv.lock"}
        if inputs is not None:
            step["inputs"] = inputs
        (tmp_path / "ai-dlc.toml").write_text(
            tomli_w.dumps({"schema": 4, "setup": {"steps": [step]}})
        )

    def run(root, command, **kwargs):
        if command.startswith("test -f"):
            return subprocess.CompletedProcess(command, 0 if (root / "uv.lock").is_file() else 1)
        runs.append(command)
        if command.startswith("uv sync"):
            (root / ".venv/bin").mkdir(parents=True, exist_ok=True)
            (root / ".venv/pyvenv.cfg").write_text("version = 3.12")
            (root / ".venv/bin/python").write_text("interpreter fixture")
        if command.startswith("npm ci"):
            (root / "node_modules").mkdir(exist_ok=True)
            (root / "node_modules/.package-lock.json").write_text("{}")
        if not (root / "uv.lock").exists():
            (root / "uv.lock").write_text("version = 1")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(project, "run_command", run)

    def setup():
        return project.setup_project(tmp_path, state_path=tmp_path / "journal.db", use_mise=False)[
            "steps"
        ][0]["status"]

    return configure, setup, runs


@pytest.mark.parametrize(
    "dependency", ["uv.lock", "pyproject.toml", "packages/service/package.json", "Cargo.lock"]
)
def test_changed_dependency_input_invalidates_setup(tmp_path, setup_fixture, dependency):
    configure, setup, runs = setup_fixture
    configure()
    path = tmp_path / dependency
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("original")
    assert setup() == "completed"
    assert setup() == "unchanged"
    path.write_text("changed")
    assert setup() == "completed"
    assert len(runs) == 2


def test_removed_python_environment_is_not_hidden_by_existing_lock(tmp_path, setup_fixture):
    configure, setup, runs = setup_fixture
    configure()
    setup()
    assert setup() == "unchanged"
    shutil.rmtree(tmp_path / ".venv")
    assert (tmp_path / "uv.lock").exists()
    assert setup() == "completed"
    assert (tmp_path / ".venv/bin/python").exists()
    assert len(runs) == 2


def test_removed_node_environment_is_not_hidden_by_existing_lock(tmp_path, setup_fixture):
    configure, setup, runs = setup_fixture
    configure("npm ci")
    (tmp_path / "package-lock.json").write_text("{}")
    setup()
    assert setup() == "unchanged"
    shutil.rmtree(tmp_path / "node_modules")
    assert setup() == "completed"
    assert len(runs) == 2


def test_generated_lock_uses_post_step_fingerprint(tmp_path, setup_fixture):
    configure, setup, runs = setup_fixture
    configure()
    assert not (tmp_path / "uv.lock").exists()
    assert setup() == "completed"
    assert setup() == "unchanged"
    assert len(runs) == 1


def test_declared_inputs_invalidate_only_when_changed(tmp_path, setup_fixture):
    configure, setup, runs = setup_fixture
    configure("prepare", inputs=["schema/*.json"])
    (tmp_path / "schema").mkdir()
    path = tmp_path / "schema/model.json"
    path.write_text("{}")
    setup()
    assert setup() == "unchanged"
    (tmp_path / "README.md").write_text("irrelevant edit")
    assert setup() == "unchanged"
    path.write_text('{"changed":true}')
    assert setup() == "completed"
    assert len(runs) == 2


def test_reverting_lock_does_not_reuse_an_obsolete_environment(tmp_path, setup_fixture):
    configure, setup, runs = setup_fixture
    configure()
    lock = tmp_path / "uv.lock"
    lock.write_text("first")
    assert setup() == "completed"
    lock.write_text("second")
    assert setup() == "completed"
    lock.write_text("first")
    assert setup() == "completed"
    assert len(runs) == 3
