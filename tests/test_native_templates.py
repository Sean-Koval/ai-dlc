"""Generic/Python consumers use the same shell-free commands on every platform."""

import os
import shutil
import subprocess
import sys
import tomllib

import pytest
import tomli_w

from ai_dlc.files import run_git
from ai_dlc.setup.commands import parse_command
from ai_dlc.setup.project import check_project, run_command, setup_project
from ai_dlc.setup.templates import adopt


@pytest.fixture
def offline_python(tmp_path, monkeypatch):
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    monkeypatch.setenv(
        "PATH", str(os.path.dirname(sys.executable)) + os.pathsep + os.environ["PATH"]
    )
    monkeypatch.setenv("UV_OFFLINE", "1")
    monkeypatch.setenv("UV_PYTHON", sys.executable)
    monkeypatch.setenv("UV_PYTHON_DOWNLOADS", "never")
    monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path / "uv-cache"))


@pytest.mark.parametrize(
    "preset,initialize", [("generic", False), ("python", False), ("python", True)]
)
def test_generated_generic_python_commands_do_not_require_a_shell(tmp_path, preset, initialize):
    adopt(tmp_path, preset, apply=True, initialize=initialize, capabilities=[])
    config = tomllib.loads((tmp_path / "ai-dlc.toml").read_text(encoding="utf-8"))
    commands = list(config["checks"]["commands"].values())
    for step in config["setup"]["steps"]:
        commands.extend([step["command"], step["verify"]])
    assert commands
    assert all(parse_command(command).shell is None for command in commands)


def test_python_adoption_requires_lock_without_changing_authored_project(tmp_path, offline_python):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="authored"\nversion="1"\nrequires-python=">=3.12"\n'
        "dependencies=[]\n[tool.uv]\npackage=false\n",
        encoding="utf-8",
        newline="\n",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_authored.py").write_text(
        "# authored acceptance tests\n", encoding="utf-8", newline="\n"
    )
    original = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert adopt(tmp_path, "python", apply=True, capabilities=[])["status"] == "applied"
    result = subprocess.run(
        [sys.executable, "scripts/setup_python.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "uv.lock" in result.stderr and "required" in result.stderr
    assert not (tmp_path / "uv.lock").exists()
    assert not (tmp_path / ".venv").exists()
    assert all(path.read_bytes() == body for path, body in original.items())


@pytest.mark.parametrize("environment", [".venv", "chosen environment é"])
def test_python_setup_retries_removed_environment_without_changing_lock(
    tmp_path, offline_python, monkeypatch, environment
):
    root = tmp_path / "Python space é"
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", environment)
    adopt(root, "python", apply=True, initialize=True, capabilities=[])
    state = tmp_path / "setup.db"
    first = setup_project(root, state_path=state, use_mise=False)
    assert first["steps"] == [{"id": "dependencies", "status": "completed"}]
    locked = (root / "uv.lock").read_bytes()
    second = setup_project(root, state_path=state, use_mise=False)
    assert second["steps"] == [{"id": "dependencies", "status": "unchanged"}]
    shutil.rmtree(root / environment)
    recovered = setup_project(root, state_path=state, use_mise=False)
    assert recovered["steps"] == [{"id": "dependencies", "status": "completed"}]
    assert (root / environment / "pyvenv.cfg").is_file()
    assert (root / "uv.lock").read_bytes() == locked


def test_python_required_behavior_fails_and_recovers_without_installing(tmp_path, offline_python):
    root = tmp_path / "Python consumer é"
    adopt(root, "python", apply=True, initialize=True, capabilities=[])
    setup_project(root, state_path=tmp_path / "setup.db", use_mise=False)
    run_git(root, "init", "-q")
    run_git(root, "add", ".")
    run_git(
        root,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.test",
        "commit",
        "-qm",
        "fixture",
    )
    baseline = check_project(root, use_mise=False)
    assert all(item["status"] == "passed" for item in baseline["outcomes"])
    source = root / "src/main.py"
    original = source.read_bytes()
    source.write_text('print("Regression")\n', encoding="utf-8", newline="\n")
    failed = check_project(root, use_mise=False)
    outcomes = {item["id"]: item["status"] for item in failed["outcomes"]}
    assert outcomes["language-check"] == "passed"
    assert outcomes["application-tests"] == "failed"
    source.write_bytes(original)
    restored = check_project(root, use_mise=False)
    assert all(item["status"] == "passed" for item in restored["outcomes"])
    locked = (root / "uv.lock").read_bytes()
    shutil.rmtree(root / ".venv")
    config = tomllib.loads((root / "ai-dlc.toml").read_text(encoding="utf-8"))
    assert (
        run_command(
            root, config["checks"]["commands"]["application-tests"], use_mise=False
        ).returncode
        != 0
    )
    assert not (root / ".venv").exists()
    assert (root / "uv.lock").read_bytes() == locked


def test_python_missing_interpreter_is_not_recreated_by_a_check(tmp_path, offline_python):
    root = tmp_path / "consumer"
    adopt(root, "python", apply=True, initialize=True, capabilities=[])
    setup_project(root, state_path=tmp_path / "setup.db", use_mise=False)
    interpreter = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    interpreter.unlink()
    config = tomllib.loads((root / "ai-dlc.toml").read_text(encoding="utf-8"))
    result = run_command(root, config["checks"]["commands"]["application-tests"], use_mise=False)
    assert result.returncode != 0
    assert not interpreter.exists()


def test_python_setup_refuses_stale_lock_without_resolving_it(tmp_path, offline_python):
    root = tmp_path / "consumer"
    adopt(root, "python", apply=True, initialize=True, capabilities=[])
    setup_project(root, state_path=tmp_path / "setup.db", use_mise=False)
    locked = (root / "uv.lock").read_bytes()
    manifest = root / "pyproject.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace('version = "0.1.0"', 'version = "0.2.0"'),
        encoding="utf-8",
        newline="\n",
    )
    config = tomllib.loads((root / "ai-dlc.toml").read_text(encoding="utf-8"))
    result = run_command(root, config["setup"]["steps"][0]["command"], use_mise=False)
    assert result.returncode != 0
    assert (root / "uv.lock").read_bytes() == locked


@pytest.mark.parametrize("condition", ["missing", "empty", "all-skipped"])
def test_python_required_application_check_refuses_vacuous_success(
    tmp_path, offline_python, condition
):
    root = tmp_path / "consumer"
    adopt(root, "python", apply=True, initialize=True, capabilities=[])
    setup_project(root, state_path=tmp_path / "setup.db", use_mise=False)
    tests = root / "tests"
    if condition == "missing":
        shutil.rmtree(tests)
    elif condition == "empty":
        (tests / "test_main.py").unlink()
    else:
        (tests / "test_main.py").write_text(
            'import unittest\n@unittest.skip("deliberate fixture")\n'
            'class Behavior(unittest.TestCase):\n    def test_output(self):\n        self.fail("not run")\n',
            encoding="utf-8",
            newline="\n",
        )
    config = tomllib.loads((root / "ai-dlc.toml").read_text(encoding="utf-8"))
    command = config["checks"]["commands"]["application-tests"]
    locked = (root / "uv.lock").read_bytes()
    assert run_command(root, command, use_mise=False).returncode != 0
    assert (root / "uv.lock").read_bytes() == locked


def test_generic_team_acceptance_fails_and_recovers_through_required_checks(
    tmp_path, offline_python
):
    root = tmp_path / "Generic consumer é"
    adopt(root, apply=True, capabilities=[])
    config_path = root / "ai-dlc.toml"
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    config["checks"]["required"].append("team-acceptance")
    config["checks"]["commands"]["team-acceptance"] = {"argv": [sys.executable, "acceptance.py"]}
    config_path.write_text(tomli_w.dumps(config), encoding="utf-8", newline="\n")
    authored = root / "acceptance.py"
    authored.write_text(
        'from pathlib import Path\nassert Path("result.txt").read_text() == "expected"\n',
        encoding="utf-8",
        newline="\n",
    )
    (root / "result.txt").write_text("expected", encoding="utf-8", newline="\n")
    setup_project(root, state_path=tmp_path / "setup.db", use_mise=False)
    run_git(root, "init", "-q")
    run_git(root, "add", ".")
    run_git(
        root,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.test",
        "commit",
        "-qm",
        "fixture",
    )
    assert all(
        item["status"] == "passed" for item in check_project(root, use_mise=False)["outcomes"]
    )
    (root / "result.txt").write_text("regressed", encoding="utf-8", newline="\n")
    failed = check_project(root, use_mise=False)
    assert failed["outcomes"][-1]["id"] == "team-acceptance"
    assert failed["outcomes"][-1]["status"] == "failed"
    (root / "result.txt").write_text("expected", encoding="utf-8", newline="\n")
    assert all(
        item["status"] == "passed" for item in check_project(root, use_mise=False)["outcomes"]
    )
    assert tomllib.loads(config_path.read_text(encoding="utf-8"))["checks"] == config["checks"]
