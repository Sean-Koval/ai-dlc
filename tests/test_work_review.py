"""`work review`: the explicit, recorded review step that publish and start require."""

import asyncio
import json
import tomllib
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

RECORD = (
    'schema = 1\nid = "{id}"\ntitle = "Ship it"\nscope = "Small change"\n'
    'requires_spec = false\nspec_reason = "No behavior change"\n'
    'acceptance = ["Tests pass"]\nreviewed = false\ndepends_on = {depends}\n'
    'requirements = []\n\n[providers]\ntracker = "fake"\n\n[artifacts]\n'
)
NOW = datetime(2026, 11, 6, 14, 30, 5, tzinfo=UTC)


def write_record(root, work_id="one", *, depends=(), text=None):
    folder = root / ".ai-dlc/work"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{work_id}.toml"
    path.write_text(text or RECORD.format(id=work_id, depends=json.dumps(list(depends))))
    return path


class Tracker:
    def __init__(self):
        self.created = 0

    def invoke(self, operation, payload):
        if operation == "find":
            return {"items": []}
        if operation == "create":
            self.created += 1
            return {"id": "7", "url": "https://issues/7", "state": "open"}
        return {"id": "7", "url": "https://issues/7", "state": "open"}


class Registry:
    def __init__(self, provider):
        self.provider = provider

    def get(self, provider_id):
        return self.provider


def make_service(root, tracker=None):
    from ai_dlc.work.workflow import WorkService

    return WorkService(root, {}, state_path=root / "state", registry=Registry(tracker or Tracker()))


def test_review_records_who_and_when_then_publish_proceeds(tmp_path):
    path = write_record(tmp_path)
    before = tomllib.loads(path.read_text())
    tracker = Tracker()
    service = make_service(tmp_path, tracker)

    result = service.review("one", " human:sean ", now=NOW)

    assert result == {
        "status": "reviewed",
        "work_id": "one",
        "path": ".ai-dlc/work/one.toml",
        "dependencies": [],
        "reviewed_by": "human:sean",
        "reviewed_at": "2026-11-06T14:30:05Z",
    }
    after = tomllib.loads(path.read_text())
    assert after == {
        **before,
        "reviewed": True,
        "reviewed_by": "human:sean",
        "reviewed_at": "2026-11-06T14:30:05Z",
    }
    # No binding is pinned by review; publishing still does that.
    assert "bindings" not in after
    keys = list(after)
    assert keys[keys.index("reviewed") + 1 : keys.index("reviewed") + 3] == [
        "reviewed_by",
        "reviewed_at",
    ]
    assert not (tmp_path / "state").exists()

    service.publish("one")
    assert tracker.created == 1
    published = tomllib.loads(path.read_text())
    assert published["reviewed_by"] == "human:sean"
    assert published["artifacts"]["tracker"] == "7"


def test_review_is_idempotent_and_keeps_the_first_reviewer(tmp_path):
    path = write_record(tmp_path)
    service = make_service(tmp_path)
    service.review("one", "human:sean", now=NOW)
    text = path.read_text()

    again = service.review("one", "human:pat")

    assert again["status"] == "already reviewed"
    assert again["reviewed_by"] == "human:sean"
    assert path.read_text() == text


def test_review_of_a_hand_reviewed_record_changes_nothing(tmp_path):
    path = write_record(tmp_path)
    path.write_text(path.read_text().replace("reviewed = false", "reviewed = true"))
    text = path.read_text()

    result = make_service(tmp_path).review("one", "human:sean")

    assert result["status"] == "already reviewed"
    assert result["reviewed_by"] is None
    assert path.read_text() == text


@pytest.mark.parametrize(
    ("field", "old", "new"),
    [
        ("title", '"Ship it"', '"TODO: state title"'),
        ("scope", '"Small change"', '"TODO: state scope"'),
        ("spec_reason", '"No behavior change"', '"TODO: record the specification decision"'),
        ("acceptance", '["Tests pass"]', '["TODO: state acceptance"]'),
    ],
)
def test_review_refuses_draft_placeholders(tmp_path, field, old, new):
    from ai_dlc.errors import RefusedError

    path = write_record(tmp_path)
    path.write_text(path.read_text().replace(old, new, 1))
    text = path.read_text()

    with pytest.raises(RefusedError, match=f"TODO placeholders in {field}"):
        make_service(tmp_path).review("one", "human:sean")
    assert path.read_text() == text


def test_review_validates_the_dependency_closure(tmp_path):
    from ai_dlc.errors import RefusedError

    path = write_record(tmp_path, depends=["base"])
    text = path.read_text()
    service = make_service(tmp_path)

    with pytest.raises(RefusedError, match="Work validation failed: Work base"):
        service.review("one", "human:sean")
    assert path.read_text() == text

    write_record(tmp_path, "base")
    result = service.review("one", "human:sean", now=NOW)
    assert result["dependencies"] == ["base"]
    # Reviewing a record does not review the work it depends on.
    assert tomllib.loads((tmp_path / ".ai-dlc/work/base.toml").read_text())["reviewed"] is False


def test_review_refuses_an_invalid_record(tmp_path):
    from ai_dlc.errors import RefusedError

    path = write_record(tmp_path)
    path.write_text(path.read_text().replace('scope = "Small change"\n', ""))

    with pytest.raises(RefusedError, match="Work validation failed"):
        make_service(tmp_path).review("one", "human:sean")


def test_review_refuses_a_started_record(tmp_path):
    from ai_dlc.errors import RefusedError

    path = write_record(tmp_path)
    path.write_text(path.read_text() + 'branch = "work/one"\n')
    text = path.read_text()

    with pytest.raises(RefusedError, match="already started on work/one"):
        make_service(tmp_path).review("one", "human:sean")
    assert path.read_text() == text


@pytest.mark.parametrize(
    ("work_id", "reviewer", "message"),
    [
        ("../one", "human:sean", "Unsafe work ID"),
        ("missing", "human:sean", "No work record"),
        ("one", "  ", "Reviewer must be"),
        ("one", "two\nlines", "Reviewer must be"),
    ],
)
def test_review_refuses_bad_input_before_reading(tmp_path, work_id, reviewer, message):
    from ai_dlc.errors import RefusedError

    path = write_record(tmp_path)
    text = path.read_text()

    with pytest.raises(RefusedError, match=message):
        make_service(tmp_path).review(work_id, reviewer)
    assert path.read_text() == text


@pytest.mark.parametrize(
    ("field", "value"),
    [("reviewed_by", ""), ("reviewed_at", "yesterday"), ("reviewed_at", "2026-11-06 14:30")],
)
def test_record_review_fields_are_validated(field, value):
    from pydantic import ValidationError

    from ai_dlc.work.workflow import Work

    raw = tomllib.loads(RECORD.format(id="one", depends="[]"))
    with pytest.raises(ValidationError):
        Work.model_validate({**raw, field: value})


def test_unrecorded_review_fields_are_omitted_from_saved_records():
    from ai_dlc.work.workflow import Work

    raw = tomllib.loads(RECORD.format(id="one", depends="[]"))
    dumped = Work.model_validate(raw).model_dump(by_alias=True)

    assert "reviewed_by" not in dumped
    assert "reviewed_at" not in dumped


def test_cli_review_defaults_to_the_author_and_reports_refusals_in_one_line(tmp_path, monkeypatch):
    from ai_dlc.cli import app

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("AI_DLC_AUTHOR", "human:sean")
    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    path = write_record(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["work", "review", "one", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["reviewed_by"] == "human:sean"
    assert tomllib.loads(path.read_text())["reviewed"] is True

    write_record(tmp_path, "two")
    named = runner.invoke(
        app, ["work", "review", "two", "--reviewer", "Pat", "--root", str(tmp_path)]
    )
    assert named.exit_code == 0, named.output
    assert json.loads(named.stdout)["reviewed_by"] == "Pat"

    refused = runner.invoke(app, ["work", "review", "missing", "--root", str(tmp_path)])
    assert refused.exit_code == 2
    assert refused.stdout == ""
    assert refused.stderr.strip().count("\n") == 0
    assert refused.stderr.startswith("Error: No work record")


def test_mcp_exposes_the_review_service(tmp_path, monkeypatch):
    from ai_dlc.mcp_server import make_server

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("AI_DLC_AUTHOR", "agent:test@sha256:1")
    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    path = write_record(tmp_path)
    server = make_server(tmp_path)

    assert "work_review" in {tool.name for tool in asyncio.run(server.list_tools())}
    asyncio.run(server.call_tool("work_review", {"work_id": "one"}))

    assert tomllib.loads(path.read_text())["reviewed_by"] == "agent:test@sha256:1"
