"""Prerequisite failures are refusals that say what to do, never tracebacks."""

import hashlib
import json
import shutil

import pytest
from typer.testing import CliRunner

from ai_dlc.files import assets


def test_skill_digest_mismatch_names_the_lock_file_and_both_digests(tmp_path, monkeypatch):
    from ai_dlc.harness import agents

    base = tmp_path / "agents"
    shutil.copytree(assets("agents"), base)
    name = sorted(p.parent.name for p in (base / "skills").glob("*/SKILL.md"))[0]
    skill = base / "skills" / name / "SKILL.md"
    skill.write_text(skill.read_text() + "\nedited\n")
    recorded = json.loads((base / "skills.lock.json").read_text())["skills"][name]["sha256"]
    monkeypatch.setattr(agents, "assets", lambda _: base)
    with pytest.raises(ValueError, match="skill digest mismatch") as raised:
        agents._skill_sources({})
    message = str(raised.value)
    assert name in message and "skills.lock.json" in message
    assert recorded in message
    assert hashlib.sha256(skill.read_bytes()).hexdigest() in message


def test_adopt_without_git_is_a_one_line_refusal(tmp_path, monkeypatch):
    from ai_dlc.cli import app

    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    done = CliRunner().invoke(app, ["project", "adopt", "--root", str(tmp_path)])
    assert done.exit_code == 2, done.output
    assert done.exception is None or isinstance(done.exception, SystemExit)
    assert "git is not available" in done.stderr
    assert "Traceback" not in done.output
