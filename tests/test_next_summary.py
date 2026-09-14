"""The offline what-next summary: derived states, exact text, CLI, context and hook."""

import json
import time

from typer.testing import CliRunner

RECORD = (
    'schema = 1\nid = "{id}"\ntitle = "Title"\nscope = "Scope"\nrequires_spec = {spec}\n'
    'spec_reason = "Reason"\nacceptance = ["Done"]\nreviewed = true\n[artifacts]\n{artifacts}'
)


def write_record(root, work_id, *, requires_spec=True, **artifacts):
    directory = root / ".ai-dlc/work"
    directory.mkdir(parents=True, exist_ok=True)
    lines = "".join(f'{key} = "{value}"\n' for key, value in artifacts.items())
    (directory / f"{work_id}.toml").write_text(
        RECORD.format(id=work_id, spec="true" if requires_spec else "false", artifacts=lines)
    )


def project(root):
    (root / "ai-dlc.toml").write_text(
        'schema = 4\n[project]\nname = "demo"\n[checks]\nrequired = ["lint", "test"]\n'
    )
    (root / "openspec/changes/archive/2026-09-01-done").mkdir(parents=True)
    (root / "openspec/changes/open-change").mkdir(parents=True)
    write_record(root, "draft")
    write_record(root, "provider-identity-projection", tracker="https://example.com/issues/62")
    write_record(
        root,
        "unarchived",
        tracker="61",
        pr="https://github.com/example/repo/pull/71",
        spec="openspec/changes/open-change",
    )
    write_record(
        root,
        "work-artifact-validation",
        tracker="68",
        pr="https://github.com/example/repo/pull/70",
        spec="openspec/changes/archive/2026-09-01-done",
    )
    write_record(
        root,
        "no-spec",
        requires_spec=False,
        tracker="ENG-9",
        pr="https://github.com/example/repo/pull/72",
    )
    return root


EXPECTED = """Active work (4 of 5 records; tracker not consulted)
  provider-identity-...      in progress         #62      next: ai-dlc work pr provider-identity-projection
  unarchived                 awaiting merge, archive first pr #71   next: openspec archive open-change --yes
  no-spec                    awaiting merge      pr #72   next: ai-dlc work finish no-spec
  work-artifact-validation   awaiting merge      pr #70   next: ai-dlc work finish work-artifact-validation
Required checks: lint test
Run: ai-dlc project check --required
"""


def test_each_state_is_derived_from_local_artifacts_and_rendered_exactly(tmp_path):
    from ai_dlc.work.summary import render_next, summarize_next

    root = project(tmp_path)
    summary = summarize_next(root)
    assert summary["status"] == "ok"
    assert summary["tracker_consulted"] is False
    assert summary["total"] == 5
    assert [(r["id"], r["state"]) for r in summary["records"]] == [
        ("provider-identity-projection", "in progress"),
        ("unarchived", "awaiting merge, archive first"),
        ("no-spec", "awaiting merge"),
        ("work-artifact-validation", "awaiting merge"),
    ]
    assert summary["records"][0] == {
        "id": "provider-identity-projection",
        "state": "in progress",
        "tracker": "https://example.com/issues/62",
        "pr": None,
        "next": "ai-dlc work pr provider-identity-projection",
    }
    assert summary["errors"] == []
    assert render_next(summary) == EXPECTED

    everything = summarize_next(root, include_all=True)
    assert [(r["id"], r["state"]) for r in everything["records"]][-1] == ("draft", "unpublished")
    assert everything["records"][-1]["next"] == "ai-dlc work publish draft"
    assert everything["records"][-1]["tracker"] is None
    assert (
        "  draft                      unpublished         -        next: ai-dlc work publish draft\n"
        in (render_next(everything))
    )
    assert render_next(everything).startswith("Active work (5 of 5 records; tracker not consulted)")


def test_unreadable_records_are_reported_without_blocking_the_summary(tmp_path):
    from ai_dlc.work.summary import render_next, summarize_next

    root = project(tmp_path)
    (root / ".ai-dlc/work/broken.toml").write_text("only_a_title = true\n")
    summary = summarize_next(root)
    assert summary["status"] == "ok"
    assert summary["total"] == 6
    assert len(summary["records"]) == 4
    assert summary["errors"] and summary["errors"][0].startswith("Work broken:")
    text = render_next(summary)
    assert text.startswith("Active work (4 of 6 records; tracker not consulted)")
    assert text.endswith(
        "Run: ai-dlc project check --required\nProblems: 1 record(s); run ai-dlc work validate --all\n"
    )


def test_next_command_prints_text_or_json_offline(tmp_path, monkeypatch):
    from ai_dlc.cli import app

    root = project(tmp_path)
    monkeypatch.setenv("PATH", "")
    started = time.monotonic()
    result = CliRunner().invoke(app, ["next", "--root", str(root)])
    assert time.monotonic() - started < 1.0
    assert result.exit_code == 0, result.output
    assert result.output == EXPECTED

    result = CliRunner().invoke(app, ["next", "--root", str(root), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert [record["id"] for record in payload["records"]] == [
        "provider-identity-projection",
        "unarchived",
        "no-spec",
        "work-artifact-validation",
    ]
    assert set(payload["records"][0]) == {"id", "state", "tracker", "pr", "next"}

    result = CliRunner().invoke(app, ["next", "--root", str(root), "--all"])
    assert result.output.startswith("Active work (5 of 5 records; tracker not consulted)")


def test_context_brief_prints_the_summary_and_plain_context_is_unchanged(tmp_path):
    from ai_dlc.cli import app
    from ai_dlc.work.workflow import build_context

    root = project(tmp_path)
    full = build_context(root)
    assert [record["id"] for record in full["work"]][:2] == ["draft", "no-spec"]
    assert full["required"] == ["lint", "test"]
    result = CliRunner().invoke(app, ["context", "--root", str(root)])
    assert result.exit_code == 0, result.output
    assert result.output == json.dumps(full, indent=2) + "\n"

    brief = build_context(root, brief=True)
    assert brief["status"] == "ok"
    assert brief["text"] == EXPECTED
    result = CliRunner().invoke(app, ["context", "--root", str(root), "--brief"])
    assert result.exit_code == 0, result.output
    assert result.output == EXPECTED


def test_session_start_hook_includes_the_first_ten_lines(tmp_path):
    from ai_dlc.harness.hooks import handle_hook

    root = project(tmp_path)
    for index in range(12):
        write_record(root, f"extra-{index:02d}", tracker=str(index))
    context = handle_hook(root, "session-start", {})["context"]
    lines = context.splitlines()
    assert lines[0] == "Read AGENTS.md and .ai-dlc/work; run ai-dlc next for the full summary."
    assert lines[1] == "Active work (16 of 17 records; tracker not consulted)"
    assert len(lines) == 11
    assert all("in progress" in line for line in lines[2:11])

    fallback = handle_hook(tmp_path / "absent", "session-start", {})["context"]
    assert fallback == "Read AGENTS.md and .ai-dlc/work; run ai-dlc next for the full summary."
