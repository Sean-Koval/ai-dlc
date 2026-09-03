import json
import subprocess


def repository(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[checks]\nrequired=["ok","bad"]\n[checks.commands]\nok="exit 0"\nbad="exit 3"\n'
    )
    (tmp_path / ".mise.toml").write_text("[tools]\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.test",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    return tmp_path


def test_failed_required_check_is_recorded_and_not_skipped(tmp_path):
    from ai_dlc.project import check_project

    root = repository(tmp_path)
    receipt = check_project(root, target="local", use_mise=False)
    assert [(x["id"], x["status"], x["exit_code"]) for x in receipt["outcomes"]] == [
        ("ok", "passed", 0),
        ("bad", "failed", 3),
    ]
    assert receipt["dirty"] is False
    assert len(receipt["commit"]) == 40
    assert json.loads(json.dumps(receipt))["required"] == ["ok", "bad"]


def test_missing_required_command_rejected_before_execution(tmp_path):
    import pytest

    from ai_dlc.project import check_project

    repository(tmp_path)
    (tmp_path / "ai-dlc.toml").write_text('schema=4\n[checks]\nrequired=["missing"]\n')
    with pytest.raises(ValueError, match="missing"):
        check_project(tmp_path, use_mise=False)


def test_setup_resume_tracks_successful_steps_only(tmp_path):
    import pytest

    from ai_dlc.project import setup_project

    (tmp_path / ".mise.toml").write_text("[tools]\n")
    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[[setup.steps]]\nid="first"\ncommand="echo run >> count"\n[[setup.steps]]\nid="second"\ncommand="test -f ready"\n'
    )
    with pytest.raises(RuntimeError, match="second"):
        setup_project(tmp_path, state_path=tmp_path / "state.db", use_mise=False)
    (tmp_path / "ready").touch()
    setup_project(tmp_path, state_path=tmp_path / "state.db", use_mise=False)
    assert (tmp_path / "count").read_text() == "run\n"
