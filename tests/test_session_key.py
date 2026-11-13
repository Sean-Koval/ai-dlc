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
    current_session_key,
    derive,
    find_sessions,
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

    context = handle_hook(root, "session-start", {"session_id": "sess-1"})["context"]

    expected = "aidlc1:KAN-7:kan-7-join:sess-1"
    assert f"Session join key: {expected}." in context
    exported = env_file.read_text()
    assert f"export AI_DLC_SESSION_KEY={expected}\n" in exported
    assert "export AI_DLC_TRACKER_KEY=KAN-7\n" in exported
    assert "export AI_DLC_WORK_ID=kan-7-join\n" in exported
    record = tomllib.loads((root / ".ai-dlc/work/kan-7-join.toml").read_text())
    assert record["sessions"] == [expected]

    # A second start of the same session neither duplicates the record entry nor fails.
    handle_hook(root, "session-start", {"session_id": "sess-1"})
    record = tomllib.loads((root / ".ai-dlc/work/kan-7-join.toml").read_text())
    assert record["sessions"] == [expected]

    # The agent commits with the trailer from its environment; the PR body carries it too.
    monkeypatch.setenv(ENV_KEY, expected)
    git(root, "add", "--", ".ai-dlc/work/kan-7-join.toml")
    git(root, "commit", "-m", f"feat: work\n\nWork-Session: {expected}")
    message = git(root, "log", "-1", "--format=%B")
    body = render_pull_request_body(record, session_keys=pull_request_session_keys(record))
    assert read_session_keys(message) == read_session_keys(body) == [SessionKey.parse(expected)]

    # work show resolves the key, the session ID and the ticket back to the record.
    for query in (expected, "sess-1", "KAN-7", "kan-7-join"):
        shown = find_sessions(root, query)
        assert [item["work_id"] for item in shown] == ["kan-7-join"], query
        assert shown[0]["tracker"] == "KAN-7"
        assert shown[0]["sessions"][0]["session_id"] == "sess-1"
    assert find_sessions(root, "sess-unknown") == []
    result = CliRunner().invoke(app, ["work", "show", "sess-1", "--root", str(root)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["work"][0]["sessions"][0]["key"] == expected


def test_session_without_ticket_gets_empty_tracker_part(tmp_path, monkeypatch):
    from ai_dlc.harness.hooks import handle_hook

    root = tmp_path / "project"
    initialize_hook_project(root, None)
    write_work_record(root, "untracked", artifacts={"branch": "topic"})
    env_file = tmp_path / "claude.env"
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))

    context = handle_hook(root, "session-start", {"session_id": "s2"})["context"]

    assert "Session join key: aidlc1::untracked:s2." in context
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
    assert not env_file.exists()


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
