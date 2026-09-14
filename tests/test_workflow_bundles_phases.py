"""Pure bundle import phases: apply argument checks and filesystem error shaping."""

import pytest

from ai_dlc.harness.workflow_bundles import _check_apply_request, _filesystem_failure

COMMIT = "0123456789abcdef0123456789abcdef01234567"


def test_check_apply_request_accepts_preview_and_matching_apply():
    _check_apply_request(False, None, COMMIT)
    _check_apply_request(True, COMMIT, COMMIT)


def test_check_apply_request_rejects_expected_commit_without_apply():
    with pytest.raises(ValueError, match="expected commit requires apply"):
        _check_apply_request(False, COMMIT, COMMIT)


@pytest.mark.parametrize("expected", [None, "abc", COMMIT.upper(), COMMIT + "0"])
def test_check_apply_request_requires_full_commit_for_apply(expected):
    with pytest.raises(ValueError, match="40-character expected commit"):
        _check_apply_request(True, expected, COMMIT)


def test_check_apply_request_rejects_mismatched_commit():
    with pytest.raises(ValueError, match="does not match the reviewed commit"):
        _check_apply_request(True, COMMIT, "f" * 40)


def test_filesystem_failure_keeps_only_import_notes():
    original = OSError("disk detail")
    original.add_note("Bundle import retained .ai-dlc/bundles/x; inspect before removal.")
    original.add_note("unrelated diagnostic")
    error = _filesystem_failure(original)
    assert type(error) is ValueError
    assert str(error) == "bundle filesystem operation failed"
    assert error.__notes__ == ["Bundle import retained .ai-dlc/bundles/x; inspect before removal."]


def test_filesystem_failure_without_notes():
    error = _filesystem_failure(OSError("plain"))
    assert str(error) == "bundle filesystem operation failed"
    assert not getattr(error, "__notes__", [])
