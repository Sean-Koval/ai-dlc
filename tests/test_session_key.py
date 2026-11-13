"""Session join key (KAN-463): derived at session start, carried by commits and the PR."""

from __future__ import annotations

import json
import tomllib

import pytest
from fixtures.git import git
from test_hooks import initialize_hook_project, write_work_record
from typer.testing import CliRunner

from ai_dlc.work.session_key import (
    ENV_KEY,
    SessionKey,
    collect_into_record,
    current_session_key,
    derive,
    find_sessions,
    local_session_keys,
    local_sessions_path,
    pull_request_session_keys,
    read_session_keys,
    tracker_key,
)

JIRA_URL = "https://example.atlassian.net/browse/KAN-7"


def test_key_round_trips_and_allows_empty_parts():
    key = SessionKey("KAN-7", "kan-7-join", "0b6c1d2e")
    assert str(key) == "aidlc1:KAN-7:kan-7-join:0b6c1d2e"
    assert SessionKey.parse(str(key)) == key
    assert SessionKey.parse("aidlc1::work:s1") == SessionKey("", "work", "s1")
    assert SessionKey.parse("aidlc1:KAN-7:work") is None
    assert SessionKey.parse("aidlc1:a b:work:s") is None
    assert SessionKey.parse("aidlc2:KAN-7:work:s") is None


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        (JIRA_URL, "KAN-7"),
        ("https://github.com/o/r/issues/15", "15"),
        ("KAN-7", "KAN-7"),
        ("177", "177"),
        ("", ""),
        ("not a key", ""),
    ],
)
def test_tracker_key_takes_the_bare_ticket(reference, expected):
    assert tracker_key(reference) == expected


def test_read_session_keys_finds_trailers_and_skips_malformed_lines():
    text = (
        "feat: thing\n\nbody\n\n"
        "Work-Session: aidlc1:KAN-7:w:s1\n"
        "Work-Session: not-a-key\n"
        "Work-Session: aidlc1:KAN-7:w:s1\n"
        "Work-Session: aidlc1::w:s2\n"
    )
    assert read_session_keys(text) == [
        SessionKey("KAN-7", "w", "s1"),
        SessionKey("", "w", "s2"),
    ]
    assert read_session_keys("") == []
    assert current_session_key({ENV_KEY: "aidlc1:KAN-7:w:s1"}) == SessionKey("KAN-7", "w", "s1")
    assert current_session_key({}) is None


def test_derive_uses_branch_ticket_without_a_record_and_replaces_unsafe_session(tmp_path):
    key = derive(tmp_path, "KAN-12-fix-thing", "has space")
    assert (key.tracker, key.work_id) == ("KAN-12", "")
    assert len(key.session_id) == 32
    untracked = derive(tmp_path, "topic", "s1")
    assert untracked == SessionKey("", "", "s1")


def test_session_start_exports_records_and_joins_commit_and_pr(tmp_path, monkeypatch):
    from ai_dlc.cli import app
    from ai_dlc.harness.hooks import handle_hook
    from ai_dlc.work.traceability import render_pull_request_body

    root = tmp_path / "project"
    initialize_hook_project(root, None)
    write_work_record(root, "kan-7-join", artifacts={"branch": "topic", "tracker": JIRA_URL})
    env_file = tmp_path / "claude.env"
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))

    record_path = root / ".ai-dlc/work/kan-7-join.toml"
    record_before = record_path.read_text()

    context = handle_hook(root, "session-start", {"session_id": "sess-1"})["context"]

    expected = "aidlc1:KAN-7:kan-7-join:sess-1"
    assert f"Session join key: {expected}." in context
    assert read_session_keys(context) == [SessionKey.parse(expected)]
    exported = env_file.read_text()
    assert f"export AI_DLC_SESSION_KEY={expected}\n" in exported
    assert "export AI_DLC_TRACKER_KEY=KAN-7\n" in exported
    assert "export AI_DLC_WORK_ID=kan-7-join\n" in exported
    # The tracked record is untouched; the key goes to the ignored local log.
    assert record_path.read_text() == record_before
    assert local_session_keys(root, "kan-7-join") == [expected]

    # A second start of the same session neither duplicates the log entry nor fails.
    handle_hook(root, "session-start", {"session_id": "sess-1"})
    assert len(local_sessions_path(root, "kan-7-join").read_text().splitlines()) == 1

    # The agent commits with the trailer; the PR body collects the logged key.
    git(root, "commit", "--allow-empty", "-m", f"feat: work\n\nWork-Session: {expected}")
    message = git(root, "log", "-1", "--format=%B")
    record = tomllib.loads(record_path.read_text())
    keys = pull_request_session_keys(record, env={}, root=root)
    body = render_pull_request_body(record, session_keys=keys)
    assert read_session_keys(message) == read_session_keys(body) == [SessionKey.parse(expected)]

    # work show resolves the key, the session ID and the ticket back to the record.
    for query in (expected, "sess-1", "KAN-7", "kan-7-join"):
        shown = find_sessions(root, query)
        assert [item["work_id"] for item in shown] == ["kan-7-join"], query
        assert shown[0]["tracker"] == "KAN-7"
        assert shown[0]["sessions"][0]["session_id"] == "sess-1"
        assert shown[0]["sessions"][0]["recorded"] is False
    assert find_sessions(root, "sess-unknown") == []
    result = CliRunner().invoke(app, ["work", "show", "sess-1", "--root", str(root)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["work"][0]["sessions"][0]["key"] == expected

    # Finishing copies the logged keys into the record once.
    assert collect_into_record(root, "kan-7-join") == [expected]
    assert collect_into_record(root, "kan-7-join") == []
    assert tomllib.loads(record_path.read_text())["sessions"] == [expected]
    assert find_sessions(root, "sess-1")[0]["sessions"] == [
        {"key": expected, "session_id": "sess-1", "tracker": "KAN-7", "recorded": True}
    ]


def test_hooks_install_is_opt_in_appends_the_trailer_and_keeps_foreign_hooks(tmp_path, monkeypatch):
    from ai_dlc.cli import app
    from ai_dlc.work.commit_hook import MARKER, hook_path

    root = tmp_path / "project"
    initialize_hook_project(root, None)
    hook = hook_path(root)
    assert not hook.exists()  # nothing is installed until asked

    result = CliRunner().invoke(app, ["work", "hooks", "install", "--root", str(root)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["status"] == "installed"
    assert MARKER in hook.read_text()
    again = CliRunner().invoke(app, ["work", "hooks", "install", "--root", str(root)])
    assert json.loads(again.output)["status"] == "unchanged"

    key = "aidlc1:KAN-7:w:s1"
    monkeypatch.setenv(ENV_KEY, key)
    git(root, "commit", "--allow-empty", "-m", "feat: one")
    git(root, "commit", "--allow-empty", "-m", f"feat: two\n\nWork-Session: {key}")
    monkeypatch.delenv(ENV_KEY)
    git(root, "commit", "--allow-empty", "-m", "feat: three")
    log = git(root, "log", "-3", "--format=%B%x00")
    three, two, one = (part.strip() for part in log.split("\x00")[:3])
    assert read_session_keys(one) == read_session_keys(two) == [SessionKey.parse(key)]
    assert two.count("Work-Session:") == 1
    assert "Work-Session" not in three

    hook.write_text("#!/bin/sh\nexit 0\n")
    refused = CliRunner().invoke(app, ["work", "hooks", "install", "--root", str(root)])
    assert refused.exit_code != 0
    assert "not written by ai-dlc" in refused.output
    assert hook.read_text() == "#!/bin/sh\nexit 0\n"


def test_session_without_ticket_gets_empty_tracker_part(tmp_path, monkeypatch):
    from ai_dlc.harness.hooks import handle_hook

    root = tmp_path / "project"
    initialize_hook_project(root, None)
    write_work_record(root, "untracked", artifacts={"branch": "topic"})
    env_file = tmp_path / "claude.env"
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))

    context = handle_hook(root, "session-start", {"session_id": "s2"})["context"]

    assert "Session join key: aidlc1::untracked:s2." in context
    assert "\nWork-Session: aidlc1::untracked:s2" in context
    assert "export AI_DLC_TRACKER_KEY=''\n" in env_file.read_text()


def test_existing_key_is_kept_and_not_reexported(tmp_path, monkeypatch):
    from ai_dlc.harness.hooks import handle_hook

    root = tmp_path / "project"
    initialize_hook_project(root, None)
    env_file = tmp_path / "claude.env"
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
    monkeypatch.setenv(ENV_KEY, "aidlc1:KAN-9:elsewhere:hangar-job")

    context = handle_hook(root, "session-start", {"session_id": "s3"})["context"]

    assert "Session join key: aidlc1:KAN-9:elsewhere:hangar-job." in context
    assert read_session_keys(context) == [SessionKey("KAN-9", "elsewhere", "hangar-job")]
    assert not env_file.exists()


@pytest.mark.parametrize(
    "values",
    [
        {ENV_KEY: "aidlc2:KAN-9:w:s:extra"},
        {ENV_KEY: "aidlc1:KAN 9:broken"},
        {"AI_DLC_TRACKER_KEY": "KAN-9", "AI_DLC_WORK_ID": "w"},
        {"AI_DLC_SESSION_ID": ""},
    ],
    ids=["unknown-prefix", "malformed", "components-only", "empty-component"],
)
def test_any_preset_variable_blocks_export_and_is_preserved(tmp_path, monkeypatch, values):
    from ai_dlc.harness.hooks import handle_hook

    root = tmp_path / "project"
    initialize_hook_project(root, None)
    write_work_record(root, "kan-9", artifacts={"branch": "topic", "tracker": "KAN-9"})
    env_file = tmp_path / "claude.env"
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    context = handle_hook(root, "session-start", {"session_id": "s4"})["context"]

    assert not env_file.exists()
    assert not (root / ".ai-dlc/local/sessions").exists()
    assert "kept as they are" in context
    assert read_session_keys(context) == []
    if values.get(ENV_KEY, "").startswith("aidlc2:"):
        assert "\nWork-Session: aidlc2:KAN-9:w:s:extra" in context


def test_work_record_rejects_malformed_session_and_omits_empty_list():
    from ai_dlc.work.workflow import Work

    base = {
        "schema": 1,
        "id": "w",
        "title": "W",
        "scope": "s",
        "requires_spec": False,
        "spec_reason": "r",
        "acceptance": ["a"],
    }
    assert "sessions" not in Work.model_validate(base).model_dump(by_alias=True)
    with pytest.raises(ValueError, match="session join keys"):
        Work.model_validate({**base, "sessions": ["free text"]})


def test_pr_keys_fall_back_to_a_key_without_session():
    work = {"id": "w", "artifacts": {"branch": "KAN-3-thing"}}
    assert pull_request_session_keys(work, env={}) == ["aidlc1:KAN-3:w:"]
    current = {ENV_KEY: "aidlc1:KAN-3:w:s9"}
    recorded = {**work, "sessions": ["aidlc1:KAN-3:w:s1"]}
    assert pull_request_session_keys(recorded, env=current) == [
        "aidlc1:KAN-3:w:s1",
        "aidlc1:KAN-3:w:s9",
    ]
