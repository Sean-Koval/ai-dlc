"""``knowledge stats`` (KAN-467): every 1.0 outcome number, against hand-counted values.

The fixture is a real git repository built here, so the review numbers come from real
commits: a merge commit, a squash merge, a closed pull request, an open one, one whose
commits were never fetched, one that touches no record, one whose reviewer moved and
retyped a record, one whose first commit is the root, and two customer pull requests a
team view must not show. The scm and tracker roles
are fakes; nothing opens a network connection.
"""

import json
import os
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.contracts import validate_response
from ai_dlc.documentation import knowledge_stats
from ai_dlc.documentation.knowledge_stats import report, stats, week_path

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
SINCE = datetime(2026, 11, 1, tzinfo=UTC)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("knowledge stats opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)


def record(id, type, status, day, owner, *, extra="", body="Body.\n", scope="team"):
    return (
        f"---\nid: {id}\ntype: {type}\nscope: {scope}\nstatus: {status}\ndate: {day}\n"
        f"owner: {owner}\nsources:\n  - {{resource: OPS-1}}\nlinks: []\n{extra}---\n{body}"
    )


def source(id, status, observed, *, resource, scope="team", extra=""):
    return (
        f"---\nid: {id}\ntype: source\nscope: {scope}\nstatus: {status}\n"
        f"date: {observed[:10]}\nowner: sean\nsources:\n  - {{resource: {resource}}}\n"
        f"links: []\nschema_version: 1\nrevision: '1'\nprovider: zoom\ntitle: Weekly sync\n"
        f"observed_at: {observed}\n{extra}---\n"
    )


class Repo:
    def __init__(self, top: Path):
        self.top = top
        top.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args, when="2026-10-01T09:00:00+00:00"):
        env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
        done = subprocess.run(
            ["git", "-C", str(self.top), *args],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert done.returncode == 0, done.stderr
        return done.stdout.strip()

    def write(self, path, text):
        target = self.top / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self, message, when="2026-11-02T09:00:00+00:00"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message, when=when)
        return self.git("rev-parse", "HEAD")


def capture_run(run_id, started, sources, ceiling=False):
    return json.dumps(
        {
            "schema_version": 1,
            "run_id": run_id,
            "started_at": started,
            "finished_at": started,
            "ceiling_reached": ceiling,
            "sources": sources,
        }
    )


@pytest.fixture
def fixture(tmp_path):
    """A knowledge repository with records under ``records/`` and the PRs that built it."""
    repo = Repo(tmp_path / "knowledge")
    r = "records"
    repo.write(f"{r}/knowledge.toml", "[format]\nversion = 1\n")
    # Health: one stale accepted decision, one stale but superseded (not counted), one
    # convention not yet stale; four Sources (one lapsed, one expiring, two fine).
    repo.write(
        f"{r}/decisions/DEC-0001.md",
        record(
            "DEC-0001",
            "decision",
            "accepted",
            "2026-03-01",
            "sean",
            extra="stale_after: 2026-10-01T00:00:00+00:00\n",
        ),
    )
    repo.write(
        f"{r}/decisions/DEC-0002.md",
        record(
            "DEC-0002",
            "decision",
            "superseded",
            "2026-02-01",
            "sean",
            extra="valid_to: 2026-03-01\nstale_after: 2026-04-01T00:00:00+00:00\n",
        ),
    )
    repo.write(
        f"{r}/conventions/CONV-0001.md",
        record(
            "CONV-0001",
            "convention",
            "active",
            "2026-11-05",
            "priya",
            extra="stale_after: 2026-12-01T00:00:00+00:00\n",
        ),
    )
    repo.write(
        f"{r}/sources/SRC-0001.md",
        source("SRC-0001", "raw", "2026-10-10T10:00:00+00:00", resource="inbox/a.vtt"),
    )
    repo.write(
        f"{r}/sources/SRC-0002.md",
        source("SRC-0002", "raw", "2026-10-20T10:00:00+00:00", resource="inbox/b.vtt"),
    )
    repo.write(
        f"{r}/sources/SRC-0003.md",
        source("SRC-0003", "processed", "2026-10-10T10:00:00+00:00", resource="inbox/c.vtt"),
    )
    repo.write(
        f"{r}/sources/SRC-0004.md",
        source("SRC-0004", "raw", "2026-11-10T10:00:00+00:00", resource="inbox/d.vtt"),
    )
    # A customer record: invisible to a team-scope view.
    repo.write(
        f"{r}/projects/alpha/LES-0009.md",
        record(
            "LES-0009",
            "lesson",
            "open",
            "2026-11-07",
            "zed",
            scope="project",
            extra="boundary: customer\nproject: alpha\n",
        ),
    )
    # A customer Source: its capture cost stays out of a team view.
    repo.write(
        f"{r}/projects/alpha/SRC-0009.md",
        source(
            "SRC-0009",
            "processed",
            "2026-11-02T10:00:00+00:00",
            resource="inbox/alpha.vtt",
            scope="project",
            extra="boundary: customer\nproject: alpha\n",
        ),
    )
    # Agent loop: the scorecard template, one scorecard before `since`, one after.
    repo.write("evals/agent-run/scorecard.md", "# Scorecard template\n")
    repo.write("evals/agent-run/KAN-0.md", "# Old run\n")
    base = repo.commit("base", when="2026-10-01T09:00:00+00:00")
    repo.write("evals/agent-run/KAN-1.md", "# KAN-1 run\n")
    repo.commit("scorecard for KAN-1", when="2026-11-03T09:00:00+00:00")
    # Capture: two runs since, one before, and one unreadable file.
    repo.write(
        "runs/capture/2026-10-20.json",
        capture_run(
            "r0",
            "2026-10-20T02:00:00+00:00",
            [
                {"id": "old", "kind": "chat", "outcome": "extracted", "cost_usd": 9.0},
            ],
        ),
    )
    repo.write(
        "runs/capture/2026-11-02.json",
        capture_run(
            "r1",
            "2026-11-02T02:00:00+00:00",
            [
                {
                    "id": "t1",
                    "kind": "transcript",
                    "outcome": "extracted",
                    "input_tokens": 10000,
                    "output_tokens": 2000,
                    "cost_usd": 0.30,
                    "duration_seconds": 3600,
                },
                {
                    "id": "t2",
                    "kind": "transcript",
                    "outcome": "extracted",
                    "input_tokens": 6000,
                    "output_tokens": 1000,
                    "cost_usd": 0.15,
                    "duration_seconds": 1800,
                },
                {"id": "c1", "kind": "chat", "outcome": "filtered"},
                {"id": "c2", "kind": "chat", "outcome": "filtered"},
                {"id": "c3", "kind": "chat", "outcome": "deferred"},
                {
                    "id": "SRC-0009",
                    "kind": "transcript",
                    "outcome": "extracted",
                    "input_tokens": 50000,
                    "cost_usd": 2.0,
                    "duration_seconds": 7200,
                },
            ],
            ceiling=True,
        ),
    )
    repo.write(
        "runs/capture/2026-11-03.json",
        capture_run(
            "r2",
            "2026-11-03T02:00:00+00:00",
            [
                {
                    "id": "c3",
                    "kind": "chat",
                    "outcome": "extracted",
                    "input_tokens": 3000,
                    "output_tokens": 500,
                    "cost_usd": 0.05,
                },
                {
                    "id": "n1",
                    "kind": "note",
                    "outcome": "failed",
                    "input_tokens": 100,
                    "cost_usd": 0.01,
                },
            ],
        ),
    )
    repo.write("runs/capture/bad.json", "{}")
    main = repo.commit("run logs", when="2026-11-03T10:00:00+00:00")

    # PR 1: merge commit. Extracts two records; the reviewer edits one.
    repo.git("checkout", "-q", "-b", "pr1")
    repo.write(
        f"{r}/decisions/dec-a.md", record("dec-a", "decision", "proposed", "2026-11-04", "sean")
    )
    repo.write(f"{r}/lessons/les-a.md", record("les-a", "lesson", "open", "2026-11-04", "priya"))
    first1 = repo.commit("extract SRC-0003")
    repo.write(
        f"{r}/decisions/dec-a.md", record("dec-a", "decision", "accepted", "2026-11-04", "sean")
    )
    repo.commit("review: accept")
    repo.git("checkout", "-q", "main")
    repo.git(
        "merge",
        "-q",
        "--no-ff",
        "pr1",
        "-m",
        "Merge pull request #1",
        when="2026-11-05T04:00:00+00:00",
    )
    merge1 = repo.git("rev-parse", "HEAD")

    # PR 2: squash merge. Extracts three records; the reviewer drops one.
    repo.git("checkout", "-q", "-b", "pr2")
    repo.write(f"{r}/questions/q-b.md", record("q-b", "question", "open", "2026-11-05", "sean"))
    repo.write(f"{r}/actions/act-b.md", record("act-b", "action", "open", "2026-11-06", "dana"))
    repo.write(f"{r}/lessons/les-b.md", record("les-b", "lesson", "open", "2026-11-06", "dana"))
    first2 = repo.commit("extract SRC-0004")
    repo.git("rm", "-q", f"{r}/lessons/les-b.md")
    repo.commit("review: drop les-b")
    repo.git("checkout", "-q", "main")
    repo.git("merge", "-q", "--squash", "pr2")
    merge2 = repo.commit("records from SRC-0004 (#2)", when="2026-11-07T12:00:00+00:00")

    # PR 7: merge commit. The reviewer moves a lesson to decisions/ and retypes it: edited.
    repo.git("checkout", "-q", "-b", "pr7")
    repo.write(f"{r}/lessons/les-f.md", record("les-f", "lesson", "open", "2026-11-08", "sean"))
    first7 = repo.commit("extract chat c9")
    repo.git("mv", f"{r}/lessons/les-f.md", f"{r}/decisions/les-f.md")
    repo.write(
        f"{r}/decisions/les-f.md", record("les-f", "decision", "accepted", "2026-11-08", "sean")
    )
    repo.commit("review: this is a decision")
    repo.git("checkout", "-q", "main")
    repo.git(
        "merge",
        "-q",
        "--no-ff",
        "pr7",
        "-m",
        "Merge pull request #7",
        when="2026-11-08T12:00:00+00:00",
    )
    merge7 = repo.git("rev-parse", "HEAD")

    # PR 3: closed without merging. Its one record counts as dropped.
    repo.git("checkout", "-q", "-b", "pr3", main)
    repo.write(f"{r}/lessons/les-c.md", record("les-c", "lesson", "open", "2026-11-07", "sean"))
    first3 = repo.commit("extract chat c3")
    # PR 4: still open.
    repo.git("checkout", "-q", "-b", "pr4", main)
    repo.write(f"{r}/lessons/les-d.md", record("les-d", "lesson", "open", "2026-11-09", "sean"))
    first4 = repo.commit("extract t2")
    # PR 9: open, a customer record outside projects/: visible to no view.
    repo.git("checkout", "-q", "-b", "pr9", main)
    repo.write(
        f"{r}/lessons/les-g.md",
        record(
            "les-g",
            "lesson",
            "open",
            "2026-11-12",
            "zed",
            scope="project",
            extra="boundary: customer\nproject: alpha\n",
        ),
    )
    first9 = repo.commit("extract a customer call")
    repo.git("checkout", "-q", "main")

    prs = [
        {
            "number": 1,
            "title": "Records from SRC-0003",
            "state": "merged",
            "created_at": "2026-11-04T08:00:00Z",
            "merged_at": "2026-11-05T04:00:00Z",
            "closed_at": "2026-11-05T04:00:00Z",
            "files": [f"{r}/decisions/dec-a.md", f"{r}/lessons/les-a.md"],
            "first_commit": first1,
            "merge_commit": merge1,
        },
        {
            "number": 2,
            "title": "Records from SRC-0004",
            "state": "merged",
            "created_at": "2026-11-05T00:00:00Z",
            "merged_at": "2026-11-07T12:00:00Z",
            "closed_at": "2026-11-07T12:00:00Z",
            "files": [f"{r}/questions/q-b.md", f"{r}/actions/act-b.md"],
            "first_commit": first2,
            "merge_commit": merge2,
        },
        {
            "number": 3,
            "title": "Records from chat c3",
            "state": "closed",
            "created_at": "2026-11-07T00:00:00Z",
            "closed_at": "2026-11-07T05:00:00Z",
            "files": [f"{r}/lessons/les-c.md"],
            "first_commit": first3,
        },
        {
            "number": 4,
            "title": "Records from t2",
            "state": "open",
            "created_at": "2026-11-10T12:00:00Z",
            "files": [f"{r}/lessons/les-d.md"],
            "first_commit": first4,
        },
        {
            "number": 5,
            "title": "Weekly report",
            "state": "merged",
            "created_at": "2026-11-08T00:00:00Z",
            "merged_at": "2026-11-08T01:00:00Z",
            "files": ["reports/2026-W45.md", f"{r}/index.md"],
            "first_commit": first4,
            "merge_commit": merge2,
        },
        {
            "number": 6,
            "title": "Records from a fork",
            "state": "merged",
            "created_at": "2026-11-08T00:00:00Z",
            "merged_at": "2026-11-09T06:00:00Z",
            "files": [f"{r}/lessons/les-e.md"],
            "first_commit": "f" * 40,
            "merge_commit": "e" * 40,
        },
        {
            "number": 7,
            "title": "Records from chat c9",
            "state": "merged",
            "created_at": "2026-11-08T00:00:00Z",
            "merged_at": "2026-11-08T12:00:00Z",
            "files": [f"{r}/decisions/les-f.md"],
            "first_commit": first7,
            "merge_commit": merge7,
        },
        {
            "number": 8,
            "title": "Alpha Corp outage call",  # a customer's name: never listed
            "state": "merged",
            "created_at": "2026-11-09T00:00:00Z",
            "merged_at": "2026-11-09T02:00:00Z",
            "files": [f"{r}/projects/alpha/LES-0010.md"],
            "first_commit": "d" * 40,
            "merge_commit": "c" * 40,
        },
        {
            "number": 9,
            "title": "Alpha Corp planning call",
            "state": "open",
            "created_at": "2026-11-12T00:00:00Z",
            "files": [f"{r}/lessons/les-g.md"],
            "first_commit": first9,
        },
        {
            "number": 10,
            "title": "Seed the repository",
            "state": "merged",
            "created_at": "2026-11-09T00:00:00Z",
            "merged_at": "2026-11-09T01:00:00Z",
            "files": [f"{r}/decisions/DEC-0001.md"],
            "first_commit": base,  # the root commit has no parent to compare against
            "merge_commit": merge1,
        },
    ]
    agent_prs = [
        {
            "number": 11,
            "title": "KAN-1: add the thing",
            "state": "merged",
            "created_at": "2026-11-02T00:00:00Z",
            "first_push_checks": "success",
        },
        {
            "number": 12,
            "title": "KAN-2 fix the other thing",
            "state": "open",
            "created_at": "2026-11-03T00:00:00Z",
            "first_push_checks": "failure",
        },
        {
            "number": 13,
            "title": "KAN-3: no checks yet",
            "state": "open",
            "created_at": "2026-11-03T00:00:00Z",
            "first_push_checks": "none",
        },
        {
            "number": 14,
            "title": "KAN-9: a person's ticket",
            "state": "open",
            "created_at": "2026-11-03T00:00:00Z",
            "first_push_checks": "success",
        },
        {
            "number": 15,
            "title": "chore: bump",
            "state": "merged",
            "created_at": "2026-11-03T00:00:00Z",
            "first_push_checks": "success",
        },
    ]
    # Jira-shaped: the id is numeric and the key is only in the URL.
    tickets = [
        {
            "id": str(10000 + n),
            "url": f"https://jira.example.invalid/browse/KAN-{n}",
            "state": "open",
        }
        for n in (1, 2, 3)
    ]
    for listing in (prs, agent_prs):  # the fakes speak the scm contract
        validate_response("pull_requests", {"pull_requests": listing})
    return {
        "repo": repo,
        "records": repo.top / r,
        "prs": prs,
        "agent_prs": agent_prs,
        "tickets": tickets,
    }


def measure(fixture, **overrides):
    seen = []

    def listing(prs):
        def call(since):
            seen.append(since)
            return [pr for pr in prs if datetime.fromisoformat(pr["created_at"]) >= since]

        return call

    options = {
        "now": NOW,
        "pull_requests": listing(fixture["prs"]),
        "agent_pull_requests": listing(fixture["agent_prs"]),
        "agent_tickets": lambda: fixture["tickets"],
        **overrides,
    }
    result = stats(fixture["records"], SINCE, **options)
    assert all(moment == SINCE for moment in seen)
    return result


def test_capture_counts_each_source_once_by_its_last_outcome(fixture):
    capture = measure(fixture)["capture"]
    assert capture | {"invalid_run_logs": None} == {
        "runs": 2,
        "ceiling_reached": 1,
        "sources_pulled": 6,  # t1 t2 c1 c2 c3 n1; c3 deferred then extracted
        "sources_filtered": 2,
        "sources_extracted": 3,
        "sources_deferred": 0,
        "sources_failed": 1,
        "tokens": 22600,
        "cost_usd": 0.51,
        "tokens_per_source": 7533,
        "cost_per_source_usd": 0.17,
        "transcript_hours": 1.5,
        "cost_per_transcript_hour_usd": 0.3,
        "invalid_run_logs": None,
    }
    (bad,) = capture["invalid_run_logs"]
    assert bad["path"] == "runs/capture/bad.json"


def test_review_times_and_reviewer_edits_match_the_git_history(fixture):
    review = measure(fixture)["review"]
    rows = {row["number"]: row for row in review.pop("by_pull_request")}
    assert review == {
        "available": True,
        "pull_requests": 7,  # #5 touches only a report and an index; #8, #9 are hidden
        "decided": 6,
        "open": 1,
        "open_over_48h": 1,  # #4, open 72 hours
        "median_hours_to_decision": 16.0,  # 20, 60, 5, 30, 12 and 1 hours
        "within_48h_pct": 71.4,  # 5 of 7: #2 took 60 hours and #4 is past 48 unanswered
        "records_extracted": 7,
        "records_kept": 3,
        "records_edited": 2,  # dec-a; les-f moved and retyped
        "records_dropped": 2,
        "edited_pct": 28.6,
        "dropped_pct": 28.6,
        "edited_or_dropped_pct": 57.1,
        "unmeasured": [6, 10],  # commits not fetched; a root first commit
        "hidden_customer": 2,
    }
    assert (rows[1]["extracted"], rows[1]["edited"], rows[1]["dropped"]) == (2, 1, 0)
    assert (rows[2]["extracted"], rows[2]["edited"], rows[2]["dropped"]) == (3, 0, 1)
    assert (rows[3]["extracted"], rows[3]["dropped"]) == (1, 1)
    assert rows[4]["open_hours"] == 72.0 and rows[4]["extracted"] is None
    assert rows[7]["extracted"] == 1 and rows[7]["edited"] == 1
    assert 5 not in rows and 8 not in rows and 9 not in rows


def test_customer_pull_requests_are_counted_only_hidden_in_a_team_view(fixture):
    result = measure(fixture)
    text = json.dumps(result) + "\n".join(report(result))
    assert "Alpha Corp" not in text and "les-g" not in text
    assert result["capture"]["sources_pulled"] == 6  # SRC-0009 is a customer Source
    alpha = measure(fixture, project="alpha")
    assert alpha["review"]["hidden_customer"] == 1  # #9 sits outside projects/alpha/
    assert {row["number"] for row in alpha["review"]["by_pull_request"]} >= {8}
    assert alpha["capture"]["sources_pulled"] == 7


def test_agent_loop_counts_tickets_their_prs_first_push_and_scorecards(fixture):
    agent = measure(fixture)["agent_loop"]
    assert agent == {
        "tickets": 3,
        "pull_requests": 3,  # KAN-1, KAN-2, KAN-3; not KAN-9 or the chore
        "first_push_green": 1,
        "first_push_green_pct": 50.0,  # KAN-3 has no checks yet
        "scorecards": 1,  # KAN-1; KAN-0 predates since, scorecard.md is the template
        "scorecard_files": ["evals/agent-run/KAN-1.md"],
        "reasons": [],
    }


def test_health_counts_stale_records_expiring_sources_and_authors(fixture):
    health = measure(fixture)["health"]
    assert [entry["id"] for entry in health["stale"]] == ["DEC-0001"]
    assert health["records_past_stale_after"] == 1
    assert [entry["id"] for entry in health["expired"]] == ["SRC-0001"]
    assert [entry["id"] for entry in health["expiring"]] == ["SRC-0002"]
    # Since Nov 1 on main: CONV-0001, les-a (priya); dec-a, q-b, les-f (sean); act-b (dana).
    # The customer lesson by zed stays out of a team view.
    assert health["records_by_author"] == {"sean": 3, "priya": 2, "dana": 1}
    alpha = measure(fixture, project="alpha")["health"]
    assert alpha["records_by_author"]["zed"] == 1


def test_missing_roles_leave_their_numbers_unmeasured_and_the_rest_computed(fixture):
    result = stats(fixture["records"], SINCE, now=NOW)
    assert result["review"] == {
        "available": False,
        "reason": "no scm provider: select one for the scm role",
    }
    agent = result["agent_loop"]
    assert agent["tickets"] is None and agent["scorecards"] == 1
    assert agent["reasons"] == ["no tracker provider: select one for the tracker role"]
    assert result["capture"]["sources_extracted"] == 3
    text = "\n".join(report(result))
    assert "Not measured: no scm provider" in text and "n/a" in text


def test_report_is_markdown_with_every_section(fixture):
    text = "\n".join(report(measure(fixture)))
    for heading in ("## Capture", "## Review", "## Agent loop", "## Health"):
        assert heading in text
    assert "Sources pulled: 6; filtered 2; extracted 3" in text
    assert "within 48 h: 71.4%" in text
    assert "dropped 2 (28.6%)" in text
    assert "Not measured (commits not fetched, or no parent commit): #6, #10" in text
    assert "Left out: 2 pull requests with customer records" in text
    assert "Records by author: sean 3, priya 2, dana 1" in text
    assert week_path(NOW) == "reports/2026-W46.md"


def test_cli_prints_json_and_writes_the_report_without_providers(fixture, tmp_path):
    out = tmp_path / "out/2026-W46.md"
    result = CliRunner().invoke(
        app,
        [
            "knowledge",
            "stats",
            str(fixture["records"]),
            "--since",
            "2026-11-01",
            "--root",
            str(tmp_path),
            "--report",
            str(out),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["capture"]["sources_extracted"] == 3
    assert data["review"]["available"] is False
    assert out.read_text().startswith("# Knowledge system outcomes, 2026-11-01 to ")


def test_roles_wire_only_scm_and_tracker(monkeypatch, tmp_path):
    calls = []

    class Fake:
        def __init__(self, config, root=None, environ=None):
            pass

        def get(self, id):
            calls.append(("get", id))
            return self

        def scm_for(self, root, repository, base):
            calls.append(("scm_for", repository))
            return self

        def pull_requests(self, since, limit):
            json.dumps({"since": since, "limit": limit})  # crosses a process boundary as JSON
            return {"pull_requests": []}

        def invoke(self, provider, operation, payload):
            calls.append((provider, operation, payload))
            key = "KAN-1" if payload["labels"] == ["exec:agent"] else "KAN-2"
            item = {"id": "1", "url": f"https://j.example.invalid/browse/{key}", "state": "open"}
            return {"items": [item], "complete": key == "KAN-1"}

    monkeypatch.setattr("ai_dlc.providers.Registry", Fake)
    config = {"roles": {"scm": "github", "tracker": "jira-cloud", "wiki": "confluence"}}
    wired = knowledge_stats.from_roles(config, tmp_path, agent_repositories=["o/agents"])
    assert set(wired) == {"pull_requests", "agent_pull_requests", "agent_tickets"}
    assert wired["pull_requests"](SINCE) == []
    assert wired["agent_pull_requests"](SINCE) == []
    tickets = wired["agent_tickets"]()
    assert [item["url"][-5:] for item in tickets["items"]] == ["KAN-1", "KAN-2"]
    assert tickets["complete"] is False
    assert ("jira-cloud", "query", {"labels": ["exec:agent"], "limit": 50}) in calls
    assert ("jira-cloud", "query", {"labels": ["lane:agent"], "limit": 50}) in calls
    assert ("scm_for", "o/agents") in calls
    assert not any("confluence" in str(call) for call in calls)
    assert knowledge_stats.from_roles(None, tmp_path) == {}


def test_github_scm_lists_pull_requests_with_first_push_checks(monkeypatch, tmp_path):
    from ai_dlc.providers.scm import GitHubSCM

    pages = {
        "repos/o/k/pulls?state=all&sort=created&direction=desc&per_page=100&page=1": [
            {
                "number": 3,
                "title": "New",
                "state": "open",
                "created_at": "2026-11-10T00:00:00Z",
                "merged_at": None,
                "closed_at": None,
            },
            {
                "number": 2,
                "title": "Merged",
                "state": "closed",
                "created_at": "2026-11-05T00:00:00Z",
                "merged_at": "2026-11-06T00:00:00Z",
                "closed_at": "2026-11-06T00:00:00Z",
                "merge_commit_sha": "m2",
            },
            {
                "number": 1,
                "title": "Old",
                "state": "closed",
                "created_at": "2026-10-01T00:00:00Z",
                "merged_at": None,
                "closed_at": "2026-10-02T00:00:00Z",
            },
        ],
        "repos/o/k/pulls/3/files?per_page=100": [{"filename": "records/a.md"}],
        "repos/o/k/pulls/3/commits?per_page=100": [{"sha": "c3"}],
        "repos/o/k/commits/c3/check-runs?filter=all&per_page=100": {
            "check_runs": [{"id": 1, "name": "test", "status": "in_progress", "conclusion": None}]
        },
        "repos/o/k/pulls/2/files?per_page=100": [{"filename": "records/b.md"}],
        "repos/o/k/pulls/2/commits?per_page=100": [{"sha": "a"}, {"sha": "b"}],
        "repos/o/k/commits/a/check-runs?filter=all&per_page=100": {"check_runs": []},
        "repos/o/k/commits/b/check-runs?filter=all&per_page=100": {
            "check_runs": [  # a re-run went green later; the first push still failed
                {"id": 9, "name": "test", "status": "completed", "conclusion": "success"},
                {"id": 7, "name": "lint", "status": "completed", "conclusion": "success"},
                {"id": 8, "name": "test", "status": "completed", "conclusion": "failure"},
            ]
        },
    }
    scm = GitHubSCM(tmp_path, {"scm": {"repository": "o/k"}})
    monkeypatch.setattr(scm, "api", lambda path: pages[path])
    found = scm.pull_requests("2026-11-01T00:00:00+00:00")
    listed = validate_response("pull_requests", {"pull_requests": found})["pull_requests"]
    assert [(pr["number"], pr["state"], pr["first_push_checks"]) for pr in listed] == [
        (3, "open", "pending"),
        (2, "merged", "failure"),
    ]
    assert listed[1]["first_commit"] == "a" and listed[1]["merge_commit"] == "m2"
