"""KAN-433: one install of the team harness and the knowledge repository, and its doctor.

A fake team-harness stands in for ``scripts/install_local.py``: it keeps that script's
contract (write only its own files, record them in ``.claude/team-harness.json``,
remove exactly those on ``--uninstall``). ``AI_DLC_TEAM_HARNESS`` names a real
team-harness checkout to run the round trip against the real installer as well.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.errors import RefusedError
from ai_dlc.setup import knowledge_doctor, knowledge_install

FAKE_INSTALLER = """
import hashlib, json, sys
from pathlib import Path

args = sys.argv[1:]
home = Path(args[args.index("--home") + 1])
claude = home / ".claude"
manifest = claude / "team-harness.json"
if "--apply" in args:
    skill = claude / "skills" / "team-recall" / "SKILL.md"
    ours = json.loads(manifest.read_text()).get("files", []) if manifest.exists() else []
    if skill.exists() and "skills/team-recall/SKILL.md" not in ours:
        sys.exit("refusing: skills/team-recall/SKILL.md is not ours")
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text("---\\nname: team-recall\\n---\\nRecall.\\n")
    manifest.write_text(json.dumps({
        "harness": Path(args[0]).name, "channel": args[args.index("--channel") + 1],
        "revision": 3, "harness_digest": "sha256:" + "a" * 64,
        "model": "pinned-model", "runtime_version": "9.9.9",
        "files": ["skills/team-recall/SKILL.md"],
    }))
elif "--uninstall" in args:
    for name in json.loads(manifest.read_text())["files"]:
        path = claude / name
        path.unlink()
        if not any(path.parent.iterdir()):
            path.parent.rmdir()
    manifest.unlink()
elif "--check" in args:
    sys.exit(0 if manifest.exists() else 1)
"""


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def commit_all(repo: Path) -> None:
    git(repo, "init", "--quiet", "-b", "main")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", "init")


@pytest.fixture
def world(tmp_path):
    """A scratch HOME with the person's own Claude setup, and the two repositories."""
    home = tmp_path / "home"
    claude = home / ".claude"
    (claude / "skills" / "mine").mkdir(parents=True)
    (claude / "settings.json").write_bytes(b'{\n  "model": "my-own",\n  "hooks": {}\n}\n')
    (claude / "skills" / "mine" / "SKILL.md").write_bytes(b"---\nname: mine\n---\nMy skill.\n")
    harness = tmp_path / "team-harness"
    (harness / "scripts").mkdir(parents=True)
    (harness / "harnesses" / "suite-default").mkdir(parents=True)
    (harness / "harnesses" / "suite-default" / "harness.lock").write_text("{}\n")
    (harness / "scripts" / "install_local.py").write_text(FAKE_INSTALLER)
    commit_all(harness)
    knowledge = tmp_path / "knowledge-origin"
    (knowledge / "team").mkdir(parents=True)
    (knowledge / "inbox" / "transcripts").mkdir(parents=True)
    (knowledge / "knowledge.toml").write_text(
        '[format]\nversion = 1\n\n[check]\nroots = ["team"]\n'
    )
    (knowledge / "team" / "README.md").write_text("# Team records\n")
    (knowledge / "inbox" / "transcripts" / "call.md").write_text("raw transcript\n")
    commit_all(knowledge)
    tools = tmp_path / "bin"
    tools.mkdir()
    for tool in ("claude", "uv", "gh"):
        for name in (tool, tool + ".cmd"):
            stub = tools / name
            stub.write_text("#!/bin/sh\nexit 0\n" if name == tool else "@exit /b 0\r\n")
            stub.chmod(0o755)
    environ = {
        **os.environ,
        "PATH": str(tools) + os.pathsep + os.environ.get("PATH", ""),
        "HOME": str(home),
        "USERPROFILE": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "KNOWLEDGE_REPO": knowledge.as_uri(),
        "TEAM_HARNESS_REPO": str(harness),
    }
    for name in ("TEAM_HARNESS", "TEAM_HARNESS_CHANNEL", "KNOWLEDGE_CHECKOUT"):
        environ.pop(name, None)
    return home, environ


def snapshot(home: Path) -> dict[str, bytes]:
    claude = home / ".claude"
    return {
        path.relative_to(claude).as_posix(): path.read_bytes()
        for path in sorted(claude.rglob("*"))
        if path.is_file()
    }


def test_round_trip_leaves_own_settings_and_skills_byte_identical(world):
    home, environ = world
    before = snapshot(home)
    result = knowledge_install.install(home, environ)
    assert result["status"] == "installed"
    after = snapshot(home)
    assert after["settings.json"] == before["settings.json"]
    assert after["skills/mine/SKILL.md"] == before["skills/mine/SKILL.md"]
    assert "skills/team-recall/SKILL.md" in after
    checkout = Path(result["settings"]["KNOWLEDGE_CHECKOUT"])
    assert checkout == home / "knowledge" / "knowledge-origin"
    hook = checkout / ".git" / "hooks" / "pre-commit"
    assert hook.read_text() == knowledge_install.HOOK
    knowledge_install.uninstall(home, environ)
    assert snapshot(home) == before
    assert not hook.exists() and (checkout / "knowledge.toml").exists()


def test_settings_store_names_and_urls_only(world):
    home, environ = world
    environ["ATLASSIAN_TOKEN"] = "do-not-store-me"
    knowledge_install.install(home, environ)
    stored = (home / ".config" / "ai-dlc" / knowledge_install.SETTINGS_FILE).read_text()
    assert "do-not-store-me" not in stored and "KNOWLEDGE_REPO" in stored


def test_absent_variable_is_named_and_nothing_is_written(world):
    home, environ = world
    del environ["KNOWLEDGE_REPO"]
    before = snapshot(home)
    with pytest.raises(RefusedError, match="KNOWLEDGE_REPO"):
        knowledge_install.install(home, environ)
    assert snapshot(home) == before


def test_prompts_only_for_absent_variables(world):
    home, environ = world
    knowledge = environ.pop("KNOWLEDGE_REPO")
    asked = []

    def prompt(name, about):
        asked.append(name)
        return knowledge

    knowledge_install.install(home, environ, prompt=prompt)
    assert asked == ["KNOWLEDGE_REPO"]


def test_missing_tools_are_named_before_anything_is_written(world, tmp_path):
    home, environ = world
    git_dir = Path(shutil.which("git") or "git").parent
    environ["PATH"] = str(git_dir)
    with pytest.raises(RefusedError) as raised:
        knowledge_install.install(home, environ)
    message = str(raised.value)
    for tool in ("claude", "uv", "gh"):
        if shutil.which(tool, path=str(git_dir)) is None:
            assert tool in message
    assert not (home / ".config").exists()


def test_url_with_credentials_is_refused_without_echoing_it(world):
    home, environ = world
    environ["KNOWLEDGE_REPO"] = "https://someone:hunter2@example.test/knowledge.git"
    with pytest.raises(RefusedError) as raised:
        knowledge_install.install(home, environ)
    assert "KNOWLEDGE_REPO" in str(raised.value) and "hunter2" not in str(raised.value)


def test_an_existing_hook_is_left_alone(world):
    home, environ = world
    checkout = home / "knowledge" / "knowledge-origin"
    subprocess.run(
        ["git", "clone", "--quiet", environ["KNOWLEDGE_REPO"], str(checkout)], check=True
    )
    own = checkout / ".git" / "hooks" / "pre-commit"
    own.write_text("#!/bin/sh\necho mine\n")
    result = knowledge_install.install(home, environ)
    assert own.read_text() == "#!/bin/sh\necho mine\n"
    assert any("left alone" in step for step in result["steps"])
    knowledge_install.uninstall(home, environ)
    assert own.read_text() == "#!/bin/sh\necho mine\n"


def test_another_directory_at_the_checkout_is_refused(world):
    home, environ = world
    occupied = home / "knowledge" / "knowledge-origin"
    occupied.mkdir(parents=True)
    (occupied / "notes.md").write_text("mine\n")
    with pytest.raises(RefusedError, match="KNOWLEDGE_CHECKOUT"):
        knowledge_install.install(home, environ)
    assert (occupied / "notes.md").read_text() == "mine\n"


def test_two_fresh_installs_print_identical_versions(world, tmp_path):
    home, environ = world
    second = tmp_path / "home2"
    shutil.copytree(home, second)
    other = {**environ, "HOME": str(second), "USERPROFILE": str(second)}
    other["XDG_CONFIG_HOME"] = str(second / ".config")
    other["XDG_CACHE_HOME"] = str(second / ".cache")
    lines = []
    for where, env in ((home, environ), (second, other)):
        knowledge_install.install(where, env)
        result = knowledge_doctor.doctor(where, {}, where, env)
        assert result["failed"] == [], knowledge_doctor.text(result)
        lines.append(next(line for line in result["lines"] if line["check"] == "versions"))
    assert lines[0] == lines[1]
    assert "model pinned-model" in lines[0]["detail"] and "format 1" in lines[0]["detail"]


def test_doctor_lines_and_skips(world):
    home, environ = world
    knowledge_install.install(home, environ)
    result = knowledge_doctor.doctor(home, {}, home, environ)
    statuses = {line["check"]: line["status"] for line in result["lines"]}
    assert statuses == {
        "prerequisites": "pass",
        "settings": "pass",
        "harness": "pass",
        "tracker": "skip",
        "wiki": "skip",
        "knowledge check": "pass",
        "inbox": "pass",
        "versions": "pass",
    }
    inbox = next(line for line in result["lines"] if line["check"] == "inbox")
    assert "inbox/transcripts/call.md" in inbox["detail"]


def test_doctor_says_when_drift_was_not_checked(world):
    home, environ = world
    knowledge_install.install(home, environ)
    harness = Path(environ["TEAM_HARNESS_REPO"])
    harness.rename(harness.with_name("moved"))
    result = knowledge_doctor.doctor(home, {}, home, environ)
    line = next(line for line in result["lines"] if line["check"] == "harness")
    assert line["status"] == "pass"
    assert "drift not checked" in line["detail"]


TRACKER = {
    "roles": {"tracker": "jira"},
    "providers": {
        "jira": {"kind": "jira-cloud", "token_env": "JIRA_TOKEN", "email_env": "JIRA_EMAIL"}
    },
}


def test_doctor_fails_naming_the_variable_never_the_value(world, monkeypatch):
    home, environ = world
    knowledge_install.install(home, environ)
    result = knowledge_doctor.doctor(home, TRACKER, home, environ)
    tracker = next(line for line in result["lines"] if line["check"] == "tracker")
    assert tracker == {"check": "tracker", "status": "fail", "detail": "set JIRA_TOKEN, JIRA_EMAIL"}
    assert result["status"] == "failed" and result["failed"] == ["tracker"]

    from ai_dlc.work import tracker_items

    def leak(self, **_kwargs):
        raise RuntimeError("401 for token s3cret-token-value")

    monkeypatch.setattr(tracker_items.TrackerItems, "search", leak)
    monkeypatch.setattr(tracker_items.TrackerItems, "__init__", lambda self, *a, **k: None)
    secret = {**environ, "JIRA_TOKEN": "s3cret-token-value", "JIRA_EMAIL": "me@example.test"}
    result = knowledge_doctor.doctor(home, TRACKER, home, secret)
    rendered = knowledge_doctor.text(result)
    assert "s3cret-token-value" not in rendered and "me@example.test" not in rendered
    assert "fail  tracker: jira fetched nothing; check JIRA_TOKEN, JIRA_EMAIL" in rendered


def test_doctor_cli_exits_non_zero_on_a_failing_line(world, monkeypatch):
    from ai_dlc.cli import app

    home, environ = world
    for name, value in environ.items():
        monkeypatch.setenv(name, value)
    result = CliRunner().invoke(
        app, ["knowledge", "doctor", "--home", str(home), "--root", str(home)]
    )
    assert result.exit_code == 1
    assert "fail  settings: no install recorded" in result.output
    knowledge_install.install(home, environ)
    result = CliRunner().invoke(
        app, ["knowledge", "doctor", "--home", str(home), "--root", str(home)]
    )
    assert result.exit_code == 0, result.output
    edited = home / "knowledge" / "knowledge-origin" / "knowledge.toml"
    edited.write_text("[format]\nversion = 2\n")
    result = CliRunner().invoke(
        app,
        ["doctor", "--knowledge", "--root", str(home)],
        env={"HOME": str(home), "USERPROFILE": str(home)},
    )
    assert result.exit_code == 1


@pytest.mark.skipif(
    not os.environ.get("AI_DLC_TEAM_HARNESS"), reason="set AI_DLC_TEAM_HARNESS to a checkout"
)
def test_round_trip_with_the_real_team_harness(world):
    home, environ = world
    environ["TEAM_HARNESS_REPO"] = os.environ["AI_DLC_TEAM_HARNESS"]
    environ["TEAM_HARNESS_CHANNEL"] = os.environ.get("AI_DLC_TEAM_HARNESS_CHANNEL", "stable")
    before = snapshot(home)
    knowledge_install.install(home, environ)
    manifest = json.loads((home / ".claude" / "team-harness.json").read_text())
    assert manifest["harness"] == "suite-default"
    assert snapshot(home)["skills/mine/SKILL.md"] == before["skills/mine/SKILL.md"]
    knowledge_install.uninstall(home, environ)
    assert snapshot(home) == before


def test_python_is_the_running_interpreter():
    command = knowledge_install.harness_command(
        Path("th"), "suite-default", "stable", Path("h"), "--apply"
    )
    assert command[0] == sys.executable and command[-3:] == ["--channel", "stable", "--apply"]


def test_a_global_hooks_path_gets_no_hook(world, tmp_path):
    """A hook written to a shared core.hooksPath would run in every repository."""
    home, environ = world
    shared = tmp_path / "shared-hooks"
    shared.mkdir()
    config = tmp_path / "gitconfig"
    config.write_text(f"[core]\n\thooksPath = {shared.as_posix()}\n")
    environ["GIT_CONFIG_GLOBAL"] = str(config)
    result = knowledge_install.install(home, environ)
    assert not (shared / "pre-commit").exists()
    assert any("core.hooksPath is set" in step for step in result["steps"])
    knowledge_install.uninstall(home, environ)


def test_a_harness_installed_before_is_left_on_uninstall(world):
    home, environ = world
    manifest = home / ".claude" / "team-harness.json"
    manifest.write_text('{"harness": "suite-default", "files": []}')
    knowledge_install.install(home, environ)
    knowledge_install.install(home, environ)  # a re-install keeps the first record
    result = knowledge_install.uninstall(home, environ)
    assert manifest.exists() and any("harness kept" in step for step in result["steps"])


def test_an_install_that_stops_early_can_still_be_uninstalled(world, tmp_path):
    home, environ = world
    environ["TEAM_HARNESS_REPO"] = (tmp_path / "nowhere").as_uri()
    with pytest.raises(Exception):  # noqa: B017 - the clone fails however git words it
        knowledge_install.install(home, environ)
    assert knowledge_install.uninstall(home, environ)["status"] == "uninstalled"
    assert not (home / ".config" / "ai-dlc" / knowledge_install.SETTINGS_FILE).exists()


def test_a_reinstall_that_fails_keeps_the_hook_record(world, tmp_path):
    home, environ = world
    first = knowledge_install.install(home, environ)
    hook = Path(first["settings"]["KNOWLEDGE_CHECKOUT"]) / ".git" / "hooks" / "pre-commit"
    broken = {**environ, "TEAM_HARNESS_REPO": (tmp_path / "nowhere").as_uri()}
    with pytest.raises(Exception):  # noqa: B017
        knowledge_install.install(home, broken)
    knowledge_install.uninstall(home, environ)
    assert not hook.exists()


@pytest.mark.parametrize(
    ("url", "refused"),
    [
        ("ssh://git@github.com/team/knowledge.git", False),
        ("git@github.com:team/knowledge.git", False),
        ("https://github.com/team/knowledge.git", False),
        ("https://someone@example.test/knowledge.git", True),
        ("https://x-token:abc@example.test/knowledge.git", True),
        ("ghp-token@github.com:team/knowledge.git", True),
        ("C:\\Users\\me\\knowledge", False),
    ],
)
def test_which_urls_carry_credentials(url, refused):
    assert knowledge_install.carries_credentials(url) is refused
