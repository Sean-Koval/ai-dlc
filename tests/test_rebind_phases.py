"""Pure phase helpers extracted from the provider rebind."""

from pathlib import Path

import pytest

from ai_dlc.setup.rebind import (
    _plan_rebind,
    _validate_connection_plan_request,
    _validate_mappings,
)


def _work(work_id, artifacts, bindings=None):
    return {
        "id": work_id,
        "providers": {"tracker": "github-issues"},
        "bindings": bindings or {},
        "artifacts": artifacts,
    }


def test_plan_rebind_lists_retained_work_with_role_artifacts_only():
    items = [
        (
            ".ai-dlc/work/one.toml",
            _work("one", {"tracker": "org/repo#1", "pr": "org/repo#9"}, {"tracker": "abc"}),
            "github-issues",
        ),
        (".ai-dlc/work/two.toml", _work("two", {"pr": "org/repo#10"}), "github-issues"),
    ]
    plan = _plan_rebind("tracker", "linear", items)
    assert list(plan) == ["status", "role", "provider", "active_work", "completion_policy"]
    assert plan["status"] == "planned"
    assert plan["role"] == "tracker"
    assert plan["provider"] == "linear"
    assert plan["active_work"] == [
        {
            "id": "one",
            "provider": "github-issues",
            "binding": "abc",
            "artifacts": {"tracker": "org/repo#1"},
        },
        {"id": "two", "provider": "github-issues", "binding": None, "artifacts": {}},
    ]
    assert _plan_rebind("scm", "github", [])["active_work"] == []


def test_validate_mappings_requires_exact_replacement_per_expected_artifact():
    items = [
        (".ai-dlc/work/one.toml", _work("one", {"tracker": "org/repo#1"}), "github-issues"),
        (".ai-dlc/work/two.toml", _work("two", {"pr": "org/repo#10"}), "github-issues"),
    ]
    mappings = {"one": {"tracker": "LIN-1"}, "two": {"tracker": "LIN-2"}}
    assert _validate_mappings("tracker", mappings, items) == mappings


def test_validate_mappings_rejects_unknown_missing_and_blank_replacements():
    items = [(".ai-dlc/work/one.toml", _work("one", {"tracker": "org/repo#1"}), "github-issues")]
    with pytest.raises(ValueError, match=r"Unknown work mapping: \['ghost'\]"):
        _validate_mappings("tracker", {"ghost": {"tracker": "LIN-1"}}, items)
    with pytest.raises(ValueError, match=r"required for one: \['tracker'\]"):
        _validate_mappings("tracker", {}, items)
    with pytest.raises(ValueError, match="required for one"):
        _validate_mappings("tracker", {"one": {"tracker": "  "}}, items)
    with pytest.raises(ValueError, match="required for one"):
        _validate_mappings("tracker", {"one": {"tracker": "LIN-1", "extra": "x"}}, items)


def test_validate_mappings_scm_role_requires_every_present_artifact():
    items = [(".ai-dlc/work/one.toml", _work("one", {"pr": "#1", "branch": "b"}), "github")]
    with pytest.raises(ValueError, match=r"\['branch', 'pr'\]"):
        _validate_mappings("scm", {"one": {"pr": "#2"}}, items)
    assert _validate_mappings("scm", {"one": {"pr": "#2", "branch": "c"}}, items) == {
        "one": {"pr": "#2", "branch": "c"}
    }


def test_validate_connection_plan_request_only_for_linear_tracker():
    plan = Path("connection.toml")
    _validate_connection_plan_request("tracker", "linear", {"roles": {"tracker": "linear"}}, plan)
    _validate_connection_plan_request("scm", "github", {}, None)
    with pytest.raises(ValueError, match="requires rebind tracker linear"):
        _validate_connection_plan_request("scm", "linear", {"roles": {"tracker": "linear"}}, plan)
    with pytest.raises(ValueError, match="selected tracker to be linear"):
        _validate_connection_plan_request(
            "tracker", "linear", {"roles": {"tracker": "github-issues"}}, plan
        )
