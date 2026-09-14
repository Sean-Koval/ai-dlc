import json
import os
import subprocess

import pytest


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
    from ai_dlc.setup.project import check_project

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

    from ai_dlc.setup.project import check_project

    repository(tmp_path)
    (tmp_path / "ai-dlc.toml").write_text('schema=4\n[checks]\nrequired=["missing"]\n')
    with pytest.raises(ValueError, match="missing"):
        check_project(tmp_path, use_mise=False)


def test_setup_resume_tracks_successful_steps_only(tmp_path):
    import pytest

    from ai_dlc.setup.project import setup_project

    (tmp_path / ".mise.toml").write_text("[tools]\n")
    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[[setup.steps]]\nid="first"\ncommand="echo run >> count"\n[[setup.steps]]\nid="second"\ncommand="test -f ready"\n'
    )
    with pytest.raises(RuntimeError, match="second"):
        setup_project(tmp_path, state_path=tmp_path / "state.db", use_mise=False)
    (tmp_path / "ready").touch()
    setup_project(tmp_path, state_path=tmp_path / "state.db", use_mise=False)
    assert (tmp_path / "count").read_text() == "run\n"


def no_runtime_anywhere(tmp_path, monkeypatch):
    """PATH and the bootstrap bin both lack mise; the real bootstrap of this machine is hidden."""
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("AI_DLC_BOOTSTRAP_HOME", str(tmp_path / "bootstrap"))


def fake_mise(directory):
    """A mise stand-in that runs `exec` commands and installs nothing."""
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / "mise"
    script.write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        '  exec) shift; [ "$1" = -- ] && shift; exec "$@" ;;\n'
        "  *) exit 0 ;;\n"
        "esac\n"
    )
    script.chmod(0o755)
    return script


def test_missing_runtime_fails_before_any_check_runs(tmp_path, monkeypatch):
    import pytest

    from ai_dlc.setup.project import RuntimeUnavailable, check_project

    root = repository(tmp_path)
    no_runtime_anywhere(tmp_path, monkeypatch)
    with pytest.raises(RuntimeUnavailable) as failure:
        check_project(root, use_mise=True)
    assert failure.value.executable == "mise"
    assert failure.value.remedy


def test_missing_runtime_reports_structured_failure_without_receipt(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from ai_dlc.cli import app

    root = repository(tmp_path)
    receipt = tmp_path / "receipts" / "local.json"
    no_runtime_anywhere(tmp_path, monkeypatch)
    result = CliRunner().invoke(
        app,
        ["project", "check", "--root", str(root), "--json", "--receipt", str(receipt)],
    )
    assert result.exit_code == 1
    assert result.exception is None or isinstance(result.exception, SystemExit)
    report = json.loads(result.stdout)
    assert report["status"] == "runtime-unavailable"
    assert report["ran"] is False
    assert report["outcomes"] == []
    assert report["executable"] == "mise"
    assert report["remedy"]
    assert "Traceback" not in result.stdout
    assert not receipt.exists()


def test_missing_runtime_human_output_names_the_remedy(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from ai_dlc.cli import app

    root = repository(tmp_path)
    no_runtime_anywhere(tmp_path, monkeypatch)
    result = CliRunner().invoke(app, ["project", "check", "--root", str(root)])
    assert result.exit_code == 1
    assert "mise is not on PATH" in result.stderr
    assert "workspace-check" in result.stderr
    assert "Traceback" not in result.stderr
    assert json.loads(result.stdout)["ran"] is False


def test_runtime_env_uses_the_bootstrap_bin_when_path_lacks_mise(tmp_path, monkeypatch, capfd):
    from ai_dlc.setup.project import runtime_env

    root = repository(tmp_path)
    no_runtime_anywhere(tmp_path, monkeypatch)
    bin_dir = tmp_path / "bootstrap/bin"
    fake_mise(bin_dir)
    env = runtime_env(root, use_mise=True)
    assert env["PATH"].split(os.pathsep)[0] == str(bin_dir)
    assert env["MISE_AUTO_INSTALL"] == "0"
    assert os.environ["PATH"] == ""
    note = capfd.readouterr().err
    assert note.count("\n") == 1
    assert note.startswith(f"note: using bootstrap runtime at {bin_dir}")
    assert "workspace-init --shell" in note
    # Per-check resolution stays silent so the note appears once per invocation.
    runtime_env(root, use_mise=True, notify=False)
    assert capfd.readouterr().err == ""


def test_runtime_env_prefers_mise_on_path_and_stays_quiet(tmp_path, monkeypatch, capfd):
    from ai_dlc.setup.project import runtime_env

    root = repository(tmp_path)
    no_runtime_anywhere(tmp_path, monkeypatch)
    fake_mise(tmp_path / "bootstrap/bin")
    on_path = tmp_path / "path-bin"
    fake_mise(on_path)
    monkeypatch.setenv("PATH", str(on_path))
    env = runtime_env(root, use_mise=True)
    assert env["PATH"] == str(on_path)
    assert capfd.readouterr().err == ""


def test_bootstrap_runtime_runs_checks_with_an_unchanged_receipt_digest(
    tmp_path, monkeypatch, capfd
):
    from ai_dlc.setup.project import check_project

    root = repository(tmp_path)
    no_runtime_anywhere(tmp_path, monkeypatch)
    bin_dir = tmp_path / "bootstrap/bin"
    fake_mise(bin_dir)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    fallback = check_project(root, use_mise=True)
    assert [x["status"] for x in fallback["outcomes"]] == ["passed", "failed"]
    assert capfd.readouterr().err.count("note: using bootstrap runtime") == 1
    monkeypatch.setenv("PATH", str(bin_dir) + ":/usr/bin:/bin")
    activated = check_project(root, use_mise=True)
    assert activated["environment_digest"] == fallback["environment_digest"]
    assert activated["checks_digest"] == fallback["checks_digest"]
    assert capfd.readouterr().err.count("note: using bootstrap runtime") == 0


def test_cli_check_writes_a_receipt_through_the_bootstrap_runtime(tmp_path, monkeypatch):
    import sys

    root = repository(tmp_path)
    (root / "ai-dlc.toml").write_text(
        'schema=4\n[checks]\nrequired=["ok"]\n[checks.commands]\nok="exit 0"\n'
    )
    no_runtime_anywhere(tmp_path, monkeypatch)
    fake_mise(tmp_path / "bootstrap/bin")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    receipt = tmp_path / "receipts" / "local.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_dlc",
            "project",
            "check",
            "--root",
            str(root),
            "--json",
            "--receipt",
            str(receipt),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert receipt.exists()
    assert json.loads(result.stdout)["outcomes"][0]["status"] == "passed"
    assert "note: using bootstrap runtime" in result.stderr


@pytest.mark.parametrize("declares_tools", [False, True])
def test_setup_activates_mise_only_when_the_project_declares_tools(
    tmp_path, monkeypatch, declares_tools
):
    from ai_dlc.setup.project import setup_project

    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text("schema = 4\n")
    if declares_tools:
        (root / ".mise.toml").write_text("[tools]\n")
    calls = tmp_path / "mise-calls.log"
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    fake = fakebin / "mise"
    fake.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{calls}"\n')
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fakebin}:{os.environ['PATH']}")

    setup_project(root, state_path=tmp_path / "state.db", use_mise=True)

    recorded = calls.read_text().splitlines() if calls.exists() else []
    if declares_tools:
        assert recorded == [f"trust {root / '.mise.toml'}", "install"]
    else:
        assert recorded == []
