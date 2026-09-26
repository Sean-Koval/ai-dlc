"""Actual native-core journeys; hosted Windows is not desktop-client qualification."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import tomli_w

from ai_dlc.documentation.document_files import create_document, read_bounded, read_document
from ai_dlc.harness.agents import render_agents
from ai_dlc.setup.project import check_project, setup_project
from ai_dlc.setup.templates import adopt

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires actual native Windows/NTFS")


@pytest.fixture
def no_posix_path(monkeypatch):
    """Keep native Python/Git/System32 but remove Git Bash/MSYS utilities."""
    import shutil

    git = shutil.which("git")
    assert git
    system = Path(os.environ["SystemRoot"])
    git_directory = Path(git).parent
    if (git_directory / "sh.exe").exists():
        native_git_directory = git_directory.parent / "cmd"
        assert (native_git_directory / "git.exe").exists()
        git_directory = native_git_directory
    paths = [
        Path(sys.executable).parent,
        git_directory,
        system / "System32",
        system / "System32/WindowsPowerShell/v1.0",
    ]
    paths = [p for p in paths if not (p / "sh.exe").exists()]
    monkeypatch.setenv("PATH", os.pathsep.join(map(str, paths)))
    assert shutil.which("sh") is None
    return paths


def test_native_documents_preserve_utf8_and_exclusive_create(tmp_path, no_posix_path):
    path = tmp_path / "team spaces é" / "note.md"
    assert create_document(path, "first é\n".encode())
    assert not create_document(path, b"replacement")
    assert read_document(path) == "first é\n".encode()
    assert read_bounded(path.parent, path.name, 100)["content"] == "first é\n"
    with pytest.raises(ValueError, match="budget"):
        read_bounded(path.parent, path.name, 1)


def test_native_adoption_render_setup_and_behavior_check(tmp_path, no_posix_path):
    root = tmp_path / "project spaces é"
    root.mkdir()
    (root / "README.md").write_text("authored\n", encoding="utf-8")
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    for key, value in [("user.name", "Fixture"), ("user.email", "fixture@example.test")]:
        subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
    adopt(root, apply=True, capabilities=["agent-client"], agent_clients=["antigravity"])
    assert (root / "README.md").read_text() == "authored\n"
    render_agents(root, apply=True)
    assert render_agents(root)["clean"]
    assert (root / ".agents/rules/ai-dlc.md").is_file()
    check = root / "check.py"
    check.write_text('from pathlib import Path\nassert Path("value.txt").read_text() == "good"\n')
    config = {
        "schema": 4,
        "setup": {
            "steps": [
                {
                    "id": "prepare",
                    "command": {
                        "argv": [
                            sys.executable,
                            "-c",
                            'from pathlib import Path; Path("value.txt").write_text("good")',
                        ]
                    },
                }
            ]
        },
        "checks": {
            "required": ["behavior"],
            "commands": {"behavior": {"argv": [sys.executable, "check.py"]}},
        },
    }
    (root / "ai-dlc.toml").write_text(tomli_w.dumps(config))
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-m", "fixture"], check=True, capture_output=True
    )
    setup_project(root, use_mise=False)
    assert check_project(root, use_mise=False)["outcomes"][0]["status"] == "passed"
    (root / "value.txt").write_text("regression")
    assert check_project(root, use_mise=False)["outcomes"][0]["status"] == "failed"
    (root / "value.txt").write_text("good")
    assert check_project(root, use_mise=False)["outcomes"][0]["status"] == "passed"
