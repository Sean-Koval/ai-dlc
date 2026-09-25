"""Native stream and full runner regressions; tests never contact a model service.

Fixture captured 2026-09-25 from native Darwin arm64 Claude Code 2.1.220
(binary SHA256 8addc857f3fe64d5a0368af9ee50321b50afb4a6918ba3ef018ab84f5dbbe081,
checked against vendor manifest). Used a dummy API key and loopback SSE server;
all API responses were fixtures. Captured with -p --output-format stream-json
--verbose --include-partial-messages --model claude-sonnet-4-6, an isolated HOME,
ANTHROPIC_BASE_URL pointed at loopback and nonessential traffic disabled.
Only machine paths were normalized to /work/project and /home/agent. This proves
native stream shape, not API billing, Docker egress or task quality. Sources:
https://code.claude.com/docs/en/headless
https://code.claude.com/docs/en/cli-reference
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_evaluation_attempt import FakeDocker

ROOT = Path(__file__).resolve().parents[1]
STREAM = ROOT / "tests/fixtures/evaluation/claude-code-2.1.220.jsonl"
MODEL = "claude-sonnet-4-6"
CLIENT = {"kind": "claude-code", "version": "2.1.220", "model": MODEL, "goal_sha256": "a" * 64}


def parse(data):
    from ai_dlc.verification.evaluation import drivers

    return drivers.parse_claude_stream(data, CLIENT)


def native():
    return [json.loads(line) for line in STREAM.read_bytes().splitlines()]


def encoded(events):
    return b"".join(json.dumps(event).encode() + b"\n" for event in events)


def test_native_result_meters_all_four_token_categories_once():
    result = parse(STREAM.read_bytes())
    assert result["session_id"]
    assert result["turns"] == 1
    assert result["usage"] == {
        "input_tokens": 10,
        "output_tokens": 5,
        "cache_creation_input_tokens": 20,
        "cache_read_input_tokens": 30,
        "total_tokens": 65,
        "cost_usd": 0.000189,
    }
    assert result["complete"] is True


@pytest.mark.parametrize(
    "damage",
    [
        "missing-final",
        "truncated",
        "invalid-utf8",
        "array",
        "duplicate-final",
        "after-final",
        "missing-init",
        "wrong-model",
        "wrong-session",
        "missing-usage",
        "missing-cache",
        "negative-usage",
        "boolean-usage",
        "fractional-usage",
        "nan-cost",
        "negative-cost",
        "missing-turns",
        "duplicate-key",
    ],
)
def test_native_stream_refuses_untrustworthy_identity_or_metering(damage):
    events = native()
    if damage == "missing-final":
        data = encoded(events[:-1])
    elif damage == "truncated":
        data = STREAM.read_bytes()[:-10]
    elif damage == "invalid-utf8":
        data = b"\xff\n" + STREAM.read_bytes()
    elif damage == "array":
        data = b"[]\n" + STREAM.read_bytes()
    elif damage == "duplicate-final":
        data = encoded(events + [events[-1]])
    elif damage == "after-final":
        data = encoded(events + [{"type": "assistant"}])
    elif damage == "missing-init":
        data = encoded([e for e in events if e.get("subtype") != "init"])
    elif damage == "duplicate-key":
        data = STREAM.read_bytes().replace(b'"num_turns":1', b'"num_turns":2,"num_turns":1')
    else:
        final = events[-1]
        if damage == "wrong-model":
            next(e for e in events if e.get("subtype") == "init")["model"] = "claude-other"
        elif damage == "wrong-session":
            final["session_id"] = "another-session"
        elif damage == "missing-usage":
            del final["usage"]
        elif damage == "missing-cache":
            del final["usage"]["cache_read_input_tokens"]
        elif damage in ("negative-usage", "boolean-usage", "fractional-usage"):
            final["usage"]["input_tokens"] = {
                "negative-usage": -1,
                "boolean-usage": True,
                "fractional-usage": 1.5,
            }[damage]
        elif damage in ("nan-cost", "negative-cost"):
            final["total_cost_usd"] = float("nan") if damage == "nan-cost" else -1
        elif damage == "missing-turns":
            del final["num_turns"]
        data = encoded(events)
    with pytest.raises(ValueError, match="Claude Code"):
        parse(data)


def test_terminal_error_keeps_known_usage_but_is_not_completion():
    events = native()
    events[-1].update(subtype="error_max_turns", is_error=True, errors=["limit reached"])
    result = parse(encoded(events))
    assert result["complete"] is False
    assert result["usage"]["total_tokens"] == 65
    assert result["limit"] == "max_turns"


def declaration(tmp_path):
    profile = json.loads((ROOT / "evaluations/profiles/local-deterministic.json").read_text())
    profile.update(
        driver={"kind": "claude-code", "version": "2.1.220"},
        model=MODEL,
        credentials=["ANTHROPIC_API_KEY"],
        budgets={"max_tokens": 10000, "max_spend_usd": 10},
        egress={"hosts": ["api.anthropic.com"], "proxy_image": profile["image"]},
    )
    profile["engine"]["image"] = "sha256:" + "d" * 64
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile))
    return profile, path


class NativeDocker(FakeDocker):
    def __init__(self, stream=None, version="2.1.220", interrupted=False):
        super().__init__()
        self.stream = STREAM.read_bytes() if stream is None else stream
        self.version, self.interrupted = version, interrupted

    def __call__(self, args, **kwargs):
        from ai_dlc.verification.evaluation.attempt import Stopped

        done = super().__call__(args, **kwargs)
        if args[0] == "exec" and "claude" in args:
            if "--version" in args:
                return SimpleNamespace(
                    returncode=0, stdout=f"{self.version} (Claude Code)\n".encode(), stderr=b""
                )
            if self.interrupted:
                raise Stopped("timeout_minutes", stdout=self.stream, stderr=b"interrupted")
            return SimpleNamespace(returncode=0, stdout=self.stream, stderr=b"")
        return done


def run_native(tmp_path, monkeypatch, **kwargs):
    from ai_dlc.verification.evaluation import run

    profile, path = declaration(tmp_path)
    fake = NativeDocker(**kwargs)
    monkeypatch.setattr(run.lifecycle, "_docker", fake)
    monkeypatch.setattr(run.lifecycle.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setattr(
        run,
        "_layers",
        lambda image: ["base", "candidate"] if image == profile["engine"]["image"] else ["base"],
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "private-evaluation-key")
    out = tmp_path / "out"
    report = run.run_suite(ROOT / "evaluations/suites/smoke.json", path, out)
    return out, report, fake


def test_real_driver_runs_both_arms_through_lifecycle_and_rebuilds_usage(tmp_path, monkeypatch):
    from ai_dlc.verification.evaluation.report import build_report

    out, report, fake = run_native(tmp_path, monkeypatch)
    assert build_report(out) == report
    commands = [call for call in fake.calls if call[0] == "exec" and "-p" in call]
    assert len(commands) == 2
    goal = json.loads((out / "inputs/suite.json").read_text())["scenarios"][0]["goal"]
    for command in commands:
        assert command[-1] == goal
        assert command[command.index("--model") + 1] == MODEL
        assert command[command.index("--max-turns") + 1] == "20"
        assert "--env=ANTHROPIC_API_KEY" in command
        assert "--verbose" in command and "stream-json" in command
    assert all("ANTHROPIC_API_KEY" not in " ".join(c) for c in fake.calls if c not in commands)
    for arm in report["arms"]:
        assert arm["metrics"]["usage"] == 65
        assert arm["metrics"]["cost_usd"] == 0.000189
        assert arm["metrics"]["turns"] == 1
        assert arm["metrics"]["client"]["session_id"]
    plan = json.loads((out / "plan.json").read_text())
    assert plan["attempts"][0]["client"] == plan["attempts"][1]["client"]
    for stream in out.rglob("client-stream.jsonl"):
        assert stream.read_bytes() == STREAM.read_bytes()
    assert len(list(out.rglob("client-stream.jsonl"))) == 2
    assert not any(
        b"private-evaluation-key" in p.read_bytes() for p in out.rglob("*") if p.is_file()
    )


@pytest.mark.parametrize("damage", ["truncate", "malformed", "usage", "version", "timeout", "leak"])
def test_driver_failures_never_pass_assertions_and_keep_evidence(tmp_path, monkeypatch, damage):
    events = native()
    options = {}
    if damage == "truncate":
        options["stream"] = encoded(events[:-1])
    elif damage == "malformed":
        options["stream"] = b"\xff" + STREAM.read_bytes()
    elif damage == "usage":
        del events[-1]["usage"]
        options["stream"] = encoded(events)
    elif damage == "version":
        options["version"] = "2.1.999"
    elif damage == "timeout":
        options.update(stream=encoded(events[:-1]), interrupted=True)
    elif damage == "leak":
        events[-1]["result"] = "private-evaluation-key"
        options["stream"] = encoded(events)
    out, report, fake = run_native(tmp_path, monkeypatch, **options)
    assert all(a["outcome"] == "incomplete" for a in report["arms"])
    assert all(x["result"] != "pass" for a in report["arms"] for x in a["assertions"])
    if damage == "version":
        assert not any("-p" in call for call in fake.calls)
    else:
        assert len(list(out.rglob("client-stream.jsonl"))) == 2
    if damage == "malformed":
        assert all(p.read_bytes().startswith(b"\xff") for p in out.rglob("client-stream.jsonl"))
    assert not any(
        b"private-evaluation-key" in p.read_bytes() for p in out.rglob("*") if p.is_file()
    )


def test_rebuild_revalidates_stream_even_when_manifest_was_refreshed(tmp_path, monkeypatch):
    from ai_dlc.verification.evaluation.report import build_report, manifest_of

    out, _, _ = run_native(tmp_path, monkeypatch)
    stream = next(out.rglob("client-stream.jsonl"))
    stream.write_bytes(encoded(native()[:-1]))
    (stream.parent / "manifest.json").write_text(json.dumps(manifest_of(stream.parent)))
    arm = next(a for a in build_report(out)["arms"] if a["arm"] == stream.parent.parent.name)
    assert arm["outcome"] == "incomplete"
    assert not any(a["result"] == "pass" for a in arm["assertions"])
    assert arm["metrics"]["usage"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("model", "sonnet"),
        ("credentials", []),
        ("egress", None),
        ("driver", {"kind": "claude-code", "version": "latest"}),
    ],
)
def test_planning_refuses_ambiguous_real_client_inputs(tmp_path, field, value):
    from ai_dlc.verification.evaluation.planning import plan

    profile, _ = declaration(tmp_path)
    profile[field] = value
    suite = json.loads((ROOT / "evaluations/suites/smoke.json").read_text())
    with pytest.raises(ValueError, match=field):
        plan(suite, profile)


def test_report_does_not_round_away_small_real_costs(tmp_path, monkeypatch):
    _, report, _ = run_native(tmp_path, monkeypatch)
    costs = report["comparison"]["scenarios"]["csv-duplicate-rows"]["cost_usd"]
    assert costs == {"treatment": 0.000189, "baseline": 0.000189, "difference": 0}


def test_missing_runtime_credential_starts_nothing(tmp_path, monkeypatch):
    from ai_dlc.verification.evaluation import run

    _, path = declaration(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(run.lifecycle, "_docker", lambda *a, **kw: pytest.fail("started Docker"))
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        run.run_suite(ROOT / "evaluations/suites/smoke.json", path, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_unmetered_client_turns_are_unknown_not_the_number_of_cli_commands(tmp_path, monkeypatch):
    _, report, _ = run_native(tmp_path, monkeypatch, stream=encoded(native()[:-1]))
    assert all(a["metrics"]["turns"] is None for a in report["arms"])


def test_valid_json_with_broken_native_event_is_refused():
    events = native()
    next(e for e in events if e["type"] == "stream_event")["event"] = "broken"
    with pytest.raises(ValueError, match="Claude Code"):
        parse(encoded(events))


def test_tampered_but_parseable_usage_is_not_reported_as_metered(tmp_path, monkeypatch):
    from ai_dlc.verification.evaluation.report import build_report

    out, _, _ = run_native(tmp_path, monkeypatch)
    stream = next(out.rglob("client-stream.jsonl"))
    events = native()
    events[-1]["usage"]["input_tokens"] = 10000
    stream.write_bytes(encoded(events))
    arm = next(a for a in build_report(out)["arms"] if a["arm"] == stream.parent.parent.name)
    assert arm["metrics"]["usage"] is None


def test_attempt_spend_cap_is_identical_and_bounded_by_run_budget(tmp_path):
    from ai_dlc.verification.evaluation import drivers, planning

    profile, path = declaration(tmp_path)
    profile["budgets"]["max_spend_usd"] = 1
    suite = json.loads((ROOT / "evaluations/suites/smoke.json").read_text())
    suite["scenarios"][0]["limits"] = {"max_turns": 7, "max_spend_usd": 1.5}
    driver = drivers.load_driver(profile, path)
    for item in planning.plan(suite, profile)["attempts"]:
        command = driver.steps(item)[-1]
        assert float(command[command.index("--max-budget-usd") + 1]) == 1
        assert command[command.index("--max-turns") + 1] == "7"


def test_process_timeout_preserves_raw_partial_output(tmp_path, monkeypatch):
    import sys

    from ai_dlc.verification.evaluation.attempt import Stopped, _docker

    executable = tmp_path / "docker"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import sys,time\n"
        "sys.stdout.buffer.write(b'partial\\xff\\n');sys.stdout.flush()\n"
        "sys.stderr.write('interrupted');sys.stderr.flush()\n"
        "time.sleep(60)\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(Stopped) as stopped:
        _docker(["exec", "unused"], timeout=0.5)
    assert stopped.value.stdout == b"partial\xff\n"
    assert stopped.value.stderr == b"interrupted"


def test_nonstandard_json_constant_anywhere_in_stream_is_malformed():
    data = STREAM.read_bytes().replace(b'"ttft_ms":11', b'"ttft_ms":NaN')
    with pytest.raises(ValueError, match="Claude Code"):
        parse(data)


@pytest.mark.parametrize("field", ["cost", "tokens"])
def test_unrepresentable_native_usage_is_refused_without_crashing(field):
    events = native()
    if field == "cost":
        events[-1]["total_cost_usd"] = 10**400
    else:
        events[-1]["usage"]["input_tokens"] = 10**400
    with pytest.raises(ValueError, match="Claude Code"):
        parse(encoded(events))
