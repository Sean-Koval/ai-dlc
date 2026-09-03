def test_hook_blocks_supported_unbound_push_and_does_not_loop(tmp_path):
    from ai_dlc.hooks import handle_hook

    payload = {
        "tool_name": "exec_command",
        "tool_input": {"cmd": "git push origin main"},
        "session_id": "s1",
    }
    assert handle_hook(tmp_path, "pre-tool", payload)["decision"] == "deny"
    payload["tool_input"]["cmd"] = "git status"
    assert handle_hook(tmp_path, "pre-tool", payload)["decision"] == "allow"
    assert handle_hook(tmp_path, "stop", payload)["reminder"]
    assert not handle_hook(tmp_path, "stop", payload)["reminder"]


def test_required_unsupported_path_is_reported():
    from ai_dlc.hooks import classify_command

    assert classify_command("git -C elsewhere push") == "unsupported"
    assert classify_command("gh pr create --title 'hi'") == "bound-operation"
    assert classify_command("echo 'git push'") == "ordinary"


def test_destructive_flags_and_spec_warning(tmp_path):
    from ai_dlc.hooks import classify_command, handle_hook

    for command in [
        "git reset --hard HEAD~1",
        "git clean -dfx",
        "git push --force origin main",
        "git push -f origin main",
        "git push --delete origin branch",
    ]:
        assert classify_command(command) == "destructive"
    response = handle_hook(
        tmp_path,
        "pre-tool",
        {"tool_name": "Edit", "tool_input": {"file_path": str(tmp_path / "docs/specs/feature.md")}},
    )
    assert response["decision"] == "allow"
    assert "warning" in response
