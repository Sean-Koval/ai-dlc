from ai_dlc.documentation.knowledge import Knowledge
from ai_dlc.harness.hooks import handle_hook


def test_recall_is_bounded_read_only_and_skips_other_notes(tmp_path):
    (tmp_path / "learnings").mkdir()
    for i in range(8):
        (tmp_path / f"learnings/{i}.md").write_text(
            "<!-- ai-dlc:op:hash -->\n---\nwork: example\n---\nUseful retry lesson\n"
        )
    (tmp_path / "private.md").write_text("retry secrets")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    found = Knowledge(tmp_path).recall(["retry"])
    assert len(found) == 5
    assert all(n["path"].startswith("learnings/") for n in found)
    assert all(n["first_line"] == "Useful retry lesson" for n in found)
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert Knowledge(tmp_path).recall(["unmatched"]) == []
    assert Knowledge(tmp_path).recall(["retry"], limit=0) == []


def test_stop_friction_threshold_and_session_isolation(tmp_path):
    for i in range(3):
        handle_hook(
            tmp_path,
            "pre-tool",
            {
                "session_id": "../../one",
                "tool_name": "Bash",
                "tool_input": {"command": f"git reset --hard HEAD~{i}"},
            },
        )
        if i == 1:
            assert "friction" not in handle_hook(tmp_path, "stop", {"session_id": "../../one"})
    result = handle_hook(tmp_path, "stop", {"session_id": "../../one"})
    assert "3 refusals" in result["friction"]
    assert "knowledge note learnings/" in result["friction"]
    assert "friction" not in handle_hook(tmp_path, "stop", {"session_id": "other"})
    assert len(list((tmp_path / ".ai-dlc/local/session").glob("*.json"))) == 1


def test_repeated_commands_and_failed_work_result_count(tmp_path):
    payload = {
        "session_id": "s",
        "tool_name": "Bash",
        "tool_input": {"command": "ai-dlc work finish one"},
    }
    handle_hook(tmp_path, "pre-tool", payload)
    handle_hook(tmp_path, "pre-tool", payload)
    handle_hook(tmp_path, "pre-tool", payload)
    handle_hook(tmp_path, "post-tool", {**payload, "tool_response": {"status": "blocked"}})
    assert "3 refusals" in handle_hook(tmp_path, "stop", payload)["friction"]


def test_session_start_without_vault_stays_quiet(tmp_path):
    assert "learnings" not in handle_hook(tmp_path, "session-start", {})


def test_session_start_recalls_only_bound_work(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from ai_dlc import config
    from ai_dlc.files import run_git

    run_git(tmp_path, "init", "-b", "work/retries")
    vault = tmp_path / "vault"
    (vault / "learnings").mkdir(parents=True)
    (vault / "learnings/retry.md").write_text("Retry lessons")
    records = tmp_path / ".ai-dlc/work"
    records.mkdir(parents=True)
    (records / "one.toml").write_text(
        'title="Retry operations"\n[artifacts]\nbranch="work/retries"\n'
    )
    monkeypatch.setattr(
        config,
        "resolve_runtime",
        lambda root: SimpleNamespace(values={"paths": {"vault": str(vault)}}),
    )
    result = handle_hook(tmp_path, "session-start", {"session_id": "one"})
    assert "learnings/retry.md: Retry lessons" in result["context"]
    assert not (tmp_path / ".ai-dlc/local/session").exists()


def test_recall_matches_spec_name_and_skips_symlinks(tmp_path):
    from ai_dlc.documentation.learnings import recall_work

    vault = tmp_path / "vault"
    (vault / "learnings").mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("spec-widget hidden")
    (vault / "learnings/external.md").symlink_to(outside)
    (vault / "learnings/lesson.md").write_text("spec-widget lesson")
    result = recall_work(
        {"artifacts": {"spec": "openspec/changes/spec-widget"}},
        {"paths": {"vault": str(vault)}},
        None,
    )
    assert result == [{"path": "learnings/lesson.md", "first_line": "spec-widget lesson"}]


def test_stop_cli_emits_friction_when_general_reminder_already_sent(tmp_path):
    import json

    from typer.testing import CliRunner

    from ai_dlc.cli import app

    payload = {"session_id": "cli", "tool_name": "Bash", "tool_input": {"command": "rm file"}}
    handle_hook(tmp_path, "stop", payload)
    for _ in range(3):
        handle_hook(tmp_path, "pre-tool", payload)
    result = CliRunner().invoke(
        app, ["hook", "stop", "--root", str(tmp_path)], input=json.dumps(payload)
    )
    assert result.exit_code == 0
    assert "consider a learning note" in result.output


def test_short_title_recall(tmp_path):
    from ai_dlc.documentation.learnings import recall_work

    (tmp_path / "learnings").mkdir()
    (tmp_path / "learnings/api.md").write_text("API design lesson")
    assert recall_work({"title": "API"}, {"paths": {"vault": str(tmp_path)}}, None) == [
        {"path": "learnings/api.md", "first_line": "API design lesson"}
    ]


def test_shell_stdout_and_mcp_gate_refusals_are_counted(tmp_path):
    import json

    handle_hook(
        tmp_path,
        "post-tool",
        {
            "session_id": "real",
            "tool_name": "Bash",
            "tool_input": {"command": "ai-dlc work finish one"},
            "tool_response": {"stdout": json.dumps({"status": "blocked"}), "exit_code": 1},
        },
    )
    handle_hook(
        tmp_path,
        "post-tool",
        {
            "session_id": "real",
            "tool_name": "mcp__ai_dlc__work_finish",
            "tool_input": {"work_id": "one"},
            "tool_response": {"status": "blocked"},
        },
    )
    assert "friction" not in handle_hook(tmp_path, "stop", {"session_id": "real"})
    handle_hook(
        tmp_path,
        "post-tool",
        {
            "session_id": "real",
            "tool_name": "mcp__ai_dlc__work_finish",
            "tool_input": {"work_id": "one"},
            "tool_response": {"content": [{"type": "text", "text": '{"status":"blocked"}'}]},
        },
    )
    assert "3 refusals" in handle_hook(tmp_path, "stop", {"session_id": "real"})["friction"]


def test_missing_session_identity_does_not_mix_sessions(tmp_path):
    handle_hook(tmp_path, "pre-tool", {"tool_name": "Bash", "tool_input": {"command": "rm file"}})
    assert not (tmp_path / ".ai-dlc/local/session").exists()
