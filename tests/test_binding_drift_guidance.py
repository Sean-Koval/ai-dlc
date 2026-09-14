"""Binding drift explains active remediation without rewriting historical records."""

import json

import pytest
import tomli_w
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.work.workflow import resolve_work


def record():
    return {
        "schema": 1,
        "id": "one",
        "title": "One",
        "scope": "A reviewed task",
        "requires_spec": False,
        "spec_reason": "Internal change",
        "acceptance": ["Done"],
        "reviewed": True,
        "bindings": {"scm": "0" * 64},
    }


def test_drift_refusal_names_role_active_review_and_historical_validation():
    with pytest.raises(ValueError) as failure:
        resolve_work(record(), {}, "one")
    message = str(failure.value)
    assert message.startswith("Provider binding drift for scm:")
    assert "different scm configuration" in message
    assert ".ai-dlc/work/one.toml" in message
    assert "only the drifted scm binding" in message
    assert "ai-dlc work validate one" in message
    assert "finished records keep historical bindings" in message
    assert "ai-dlc work validate --all" in message
    assert "project rebind" not in message


def test_single_record_drift_has_hint_and_all_records_remain_unchanged(tmp_path):
    (tmp_path / "ai-dlc.toml").write_text("schema = 4\n")
    path = tmp_path / ".ai-dlc/work/one.toml"
    path.parent.mkdir(parents=True)
    path.write_text(tomli_w.dumps(record()))
    before = path.read_bytes()
    result = CliRunner().invoke(app, ["work", "validate", "one", "--root", str(tmp_path)])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["hint"].startswith("Provider binding drift for scm:")
    assert "ai-dlc work validate --all" in payload["hint"]
    assert path.read_bytes() == before
    all_records = CliRunner().invoke(app, ["work", "validate", "--all", "--root", str(tmp_path)])
    assert all_records.exit_code == 0, all_records.output
    assert "hint" not in json.loads(all_records.stdout)
    assert path.read_bytes() == before


def test_non_drift_validation_error_does_not_get_hint(tmp_path):
    (tmp_path / "ai-dlc.toml").write_text("schema = 4\n")
    result = CliRunner().invoke(app, ["work", "validate", "missing", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "hint" not in json.loads(result.stdout)
