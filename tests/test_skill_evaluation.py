import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def declaration(tmp_path, *, budget=100, repetitions=2):
    (tmp_path / "skills/example").mkdir(parents=True)
    (tmp_path / "skills/example/SKILL.md").write_text("Use evidence, preserve uncertainty.")
    (tmp_path / "scenarios.json").write_text(
        json.dumps(
            [{"skill": "example", "prompt": "What is done?", "expected": "Require evidence."}]
        )
    )
    path = tmp_path / "evaluation.toml"
    path.write_text(f"""schema = 1
status = "pending"
model = "gpt-5.6-sol"
reasoning_effort = "high"
repetitions = {repetitions}
max_output_tokens = 10
max_total_tokens = {budget}
require_control = true
require_human_review = true
credential_env = "SKILL_EVALUATION_TEST_KEY"
api_url = "https://api.openai.com/v1/responses"
scenarios = "scenarios.json"
""")
    return path


def test_dry_run_prints_all_pairs_with_empty_path_and_no_credential():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_skill_evaluation.py"), "--dry-run"],
        env={"PATH": ""},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["max_total_tokens"] == 200000
    assert len(output["requests"]) == 80
    assert [r["variant"] for r in output["requests"][:10]] == ["control"] * 5 + ["skill"] * 5
    assert len(output["requests"][0]["request"]["input"]) == 1
    assert len(output["requests"][5]["request"]["input"]) == 2


def test_dry_run_does_not_construct_client_or_read_credential(tmp_path, monkeypatch):
    from ai_dlc.harness.skill_evaluation import run

    def forbidden(*args, **kwargs):
        raise AssertionError("dry run must not construct a client")

    class NoEnvironment(dict):
        def get(self, *args):
            raise AssertionError("dry run must not read credential environment")

    import socket

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(os, "environ", NoEnvironment())
    result = run(declaration(tmp_path), dry_run=True, client_factory=forbidden)
    assert len(result["requests"]) == 4
    assert not (tmp_path / "evaluations").exists()


def test_missing_credential_refuses_before_client_or_output(tmp_path, monkeypatch):
    from ai_dlc.harness.skill_evaluation import run

    monkeypatch.delenv("SKILL_EVALUATION_TEST_KEY", raising=False)
    with pytest.raises(ValueError, match="SKILL_EVALUATION_TEST_KEY"):
        run(declaration(tmp_path), client_factory=lambda *args: pytest.fail("client constructed"))
    assert not (tmp_path / "evaluations").exists()


class RecordedClient:
    def count_input_tokens(self, request):
        return 10

    def complete(self, request):
        return ' {"output": [{"text": "verbatim result"}], "usage": {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13}}\n'


def test_run_reserves_input_and_output_and_preserves_raw_unscored_evidence(tmp_path, monkeypatch):
    from ai_dlc.harness.skill_evaluation import run

    monkeypatch.setenv("SKILL_EVALUATION_TEST_KEY", "fake-credential-not-written")
    config = declaration(tmp_path, budget=25)
    before = config.read_bytes()
    out = tmp_path / "run"
    result = run(config, output=out, client_factory=lambda *args: RecordedClient())
    assert result["stop_reason"] == "budget-exhausted"
    assert result["total_tokens"] == 13
    assert len(result["transcripts"]) == 1
    assert len(result["unsent"]) == 3
    transcript = json.loads((out / "example/0-control-1.json").read_text())
    assert transcript["response_json"] == RecordedClient().complete({})
    assert transcript["request"]["max_output_tokens"] == 10
    assert transcript["request"]["reasoning"] == {"effort": "high"}
    assert transcript["expected"] == "Require evidence."
    assert "0-control-1.json" in (out / "review-sheet.md").read_text()
    assert config.read_bytes() == before
    for path in out.rglob("*"):
        if path.is_file():
            assert "fake-credential-not-written" not in path.read_text()
            if path.suffix == ".json":
                assert not {"pass", "fail", "score"} & json.loads(path.read_text()).keys()
    with pytest.raises(FileExistsError):
        run(config, output=out, client_factory=lambda *args: pytest.fail("must refuse overwrite"))


def test_unavailable_usage_stops_after_preserving_response(tmp_path, monkeypatch):
    from ai_dlc.harness.skill_evaluation import run

    class MissingUsage(RecordedClient):
        def complete(self, request):
            return '{"output": []}'

    monkeypatch.setenv("SKILL_EVALUATION_TEST_KEY", "fake")
    result = run(
        declaration(tmp_path), output=tmp_path / "run", client_factory=lambda *args: MissingUsage()
    )
    assert result["stop_reason"] == "usage-unavailable"
    assert result["reserved_tokens"] == 20
    assert len(result["transcripts"]) == 1
    assert len(result["unsent"]) == 3


def test_human_review_cannot_be_disabled(tmp_path):
    from ai_dlc.harness.skill_evaluation import run

    config = declaration(tmp_path)
    config.write_text(
        config.read_text().replace("require_human_review = true", "require_human_review = false")
    )
    with pytest.raises(ValueError, match="human review"):
        run(config, dry_run=True)


def test_complete_protocol_records_every_control_and_treatment(tmp_path, monkeypatch):
    from ai_dlc.harness.skill_evaluation import run

    monkeypatch.setenv("SKILL_EVALUATION_TEST_KEY", "fake")
    out = tmp_path / "run"
    result = run(declaration(tmp_path), output=out, client_factory=lambda *args: RecordedClient())
    assert result["stop_reason"] is None
    assert result["total_tokens"] == 52
    paths = [item["path"] for item in result["transcripts"]]
    assert paths == [
        "example/0-control-1.json",
        "example/0-control-2.json",
        "example/0-skill-1.json",
        "example/0-skill-2.json",
    ]
    control = json.loads((out / paths[0]).read_text())["request"]["input"]
    treatment = json.loads((out / paths[2]).read_text())["request"]["input"]
    assert control == [{"role": "user", "content": "What is done?"}]
    assert treatment == [
        {"role": "system", "content": "Use evidence, preserve uncertainty."},
        *control,
    ]


def test_budget_stop_before_first_call_retains_expected_scenarios(tmp_path, monkeypatch):
    from ai_dlc.harness.skill_evaluation import run

    class NoCompletion(RecordedClient):
        def complete(self, request):
            pytest.fail("call exceeds total budget")

    monkeypatch.setenv("SKILL_EVALUATION_TEST_KEY", "fake")
    result = run(
        declaration(tmp_path, budget=19),
        output=tmp_path / "run",
        client_factory=lambda *args: NoCompletion(),
    )
    assert result["transcripts"] == []
    assert result["scenarios"] == [
        {"skill": "example", "scenario_index": 0, "expected": "Require evidence."}
    ]
    assert result["stop_reason"] == "budget-exhausted"


def test_failed_response_is_retained_before_run_stops(tmp_path, monkeypatch):
    from ai_dlc.harness.skill_evaluation import run

    class ErrorResponse(RecordedClient):
        def complete(self, request):
            return '{"error":{"message":"unavailable"}}'

    monkeypatch.setenv("SKILL_EVALUATION_TEST_KEY", "fake")
    out = tmp_path / "run"
    result = run(declaration(tmp_path), output=out, client_factory=lambda *args: ErrorResponse())
    assert result["stop_reason"] == "usage-unavailable"
    assert (
        json.loads((out / result["transcripts"][0]["path"]).read_text())["response_json"]
        == '{"error":{"message":"unavailable"}}'
    )


def test_failed_client_setup_leaves_no_empty_run_directory(tmp_path, monkeypatch):
    from ai_dlc.harness.skill_evaluation import run

    monkeypatch.setenv("SKILL_EVALUATION_TEST_KEY", "fake")
    output = tmp_path / "run"

    def invalid(*args):
        raise ValueError("invalid endpoint")

    with pytest.raises(ValueError, match="invalid endpoint"):
        run(declaration(tmp_path), output=output, client_factory=invalid)
    assert not output.exists()


def test_report_actual_usage_if_provider_violates_reserved_budget(tmp_path, monkeypatch):
    from ai_dlc.harness.skill_evaluation import run

    class ViolatedBudget(RecordedClient):
        def complete(self, request):
            return '{"usage":{"input_tokens":10,"output_tokens":30,"total_tokens":40}}'

    monkeypatch.setenv("SKILL_EVALUATION_TEST_KEY", "fake")
    result = run(
        declaration(tmp_path),
        output=tmp_path / "run",
        client_factory=lambda *args: ViolatedBudget(),
    )
    assert result["stop_reason"] == "usage-contract-violation"
    assert result["total_tokens"] == 40
    assert len(result["transcripts"]) == 1


def test_declaration_refuses_embedded_credentials_even_for_dry_run(tmp_path):
    from ai_dlc.harness.skill_evaluation import run

    config = declaration(tmp_path)
    config.write_text(config.read_text() + '\napi_key = "must-not-be-read"\n')
    with pytest.raises(ValueError, match="Unknown evaluation settings"):
        run(config, dry_run=True)
    config.write_text(
        config.read_text()
        .replace('\napi_key = "must-not-be-read"\n', "")
        .replace("https://api.openai.com", "https://user:password@api.openai.com")
    )
    with pytest.raises(ValueError, match="without credentials"):
        run(config, dry_run=True)
