"""``knowledge stats``: the 1.0 outcome numbers, from git, pull requests and the run log.

1.0 is judged on outcomes, not tickets closed (KAN-467). Every number comes from data
the system already writes, so there is no new store:

- **Capture**, from the run log the nightly batch (KAN-458) writes where it runs, one
  :class:`CaptureRun` per line, given with ``log``; v0.1 does not commit it.
- **Review**, from the records pull requests the ``scm`` role lists and from git: hours
  from open to merge or close, and how many extracted records the reviewer edited or
  dropped (each record as the pull request's first commit had it, against the merge).
- **Agent loop**, from ``exec:agent`` tickets (the ``tracker`` role), the pull requests
  whose title starts with one of their keys (the ``scm`` role), and scorecards committed
  under ``evals/agent-run/`` (KAN-449).
- **Health**, from the records on disk: records past ``stale_after``, Sources whose
  payload expires before anyone processed them, and records per author.

Only the ``scm`` and ``tracker`` roles are called; a missing role leaves its numbers
``None`` with a reason, and every other number is still computed. The service takes
plain callables, so the CLI wires providers and tests pass fakes.
"""

import subprocess
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from statistics import median
from typing import Any, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from ai_dlc.documentation import knowledge_bundle
from ai_dlc.documentation.knowledge_check import project_of, visible_in
from ai_dlc.documentation.knowledge_notes import split
from ai_dlc.documentation.knowledge_records import (
    TYPES,
    KnowledgeRecord,
    okf_status,
    payload_expires,
)
from ai_dlc.files import run_git

"""Where the capture batch writes one JSON file per run, relative to the repository."""
SCORECARDS = "evals/agent-run"
"""Where KAN-449 commits one scorecard per agent run; ``scorecard.md`` is the template."""
REVIEW_HOURS = 48
PAYLOAD_DAYS = 30
"""A raw payload expires this many days after capture (KAN-458)."""
EXPIRY_WARNING_DAYS = 7
NOT_RECORDS = ("runs/", "reports/", "evals/", "templates/", ".github/")
AGENT_LABELS = ("exec:agent", "lane:agent")  # lane:agent is accepted until KAN-326
TICKET_LIMIT = 50  # the tracker query contract's page size; it has no cursor

PullRequests = Callable[[datetime], list[dict[str, Any]]]
Tickets = Callable[[], list[dict[str, Any]] | dict[str, Any]]


USAGE = ("input_tokens", "output_tokens", "cost_usd")
UNKNOWN = "null: unknown; a failed Source that leaves it out is unknown too, others spent 0"


class CaptureEntry(BaseModel):
    """One Source in one capture run."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, description="the Source record's id or slug")
    kind: Literal["transcript", "chat", "note", "other"] = Field(
        description="other: a provider that is none of the three"
    )
    outcome: Literal["extracted", "filtered", "deferred", "failed"] = Field(
        description="deferred: left in the inbox because the token ceiling was reached"
    )
    input_tokens: int | None = Field(default=0, ge=0, description=UNKNOWN)
    output_tokens: int | None = Field(default=0, ge=0, description=UNKNOWN)
    cost_usd: float | None = Field(default=0, ge=0, description=UNKNOWN)
    duration_seconds: float | None = Field(
        default=None, ge=0, description="the recording's length, for transcripts"
    )
    pull_request: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _failed_usage_is_unknown(self) -> Self:
        """A failed Source that reports no usage spent an unknown amount, not nothing."""
        if self.outcome == "failed":
            for name in USAGE:
                if name not in self.model_fields_set:
                    setattr(self, name, None)
        return self

    def usage_known(self) -> bool:
        return all(getattr(self, name) is not None for name in USAGE)


class CaptureRun(BaseModel):
    """One line of the capture run log: what one capture batch run pulled, kept and spent."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    run_id: str = Field(min_length=1)
    started_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    ceiling_reached: bool = False
    sources: list[CaptureEntry] = Field(default_factory=list)


def run_log_schema() -> dict[str, Any]:
    """The generated ``contracts/capture-run.schema.json``."""
    return CaptureRun.model_json_schema()


def stats(
    root: Path | str,
    since: date | datetime,
    *,
    now: datetime | None = None,
    pull_requests: PullRequests | None = None,
    agent_pull_requests: PullRequests | None = None,
    agent_tickets: Tickets | None = None,
    project: str | None = None,
    log: Path | str | None = None,
) -> dict[str, Any]:
    """Measure the knowledge repository holding the records directory ``root``; read-only.

    ``log`` is the capture batch's run log where the batch runs (v0.1 does not commit
    it): a ``.jsonl`` file of capture runs, one ``.json`` run, or a folder of either.
    Without it, capture is reported as not measured. A missing or wrong-shaped log is
    an error, so a bad log never reads as a quiet week.

    ``pull_requests`` lists the knowledge repository's pull requests opened since a
    moment; ``agent_pull_requests`` lists those of the repositories agents work in
    (default: the same); ``agent_tickets`` lists ``exec:agent`` tickets. Health counts
    only records a view of ``project`` may show (KAN-465): by default, no customer record.
    """
    folder = Path(root).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError(f"records directory not found: {root}")
    start = _moment(since)
    end = now or datetime.now(UTC)
    repo = _toplevel(folder)
    prefix = folder.relative_to(repo).as_posix() if repo else ""
    prefix = "" if prefix == "." else prefix + "/"
    scan = knowledge_bundle._scan(folder)
    records = [item for item in scan.records if visible_in(item.record, item.relative, project)]
    hidden = {item.record.id for item in scan.records} - {item.record.id for item in records}
    knowledge_prs, scm_reason = _ask(pull_requests, start, role="scm")
    agent_prs, agent_reason = knowledge_prs, scm_reason
    if agent_pull_requests is not None:
        agent_prs, agent_reason = _ask(agent_pull_requests, start, role="scm")
    tickets, tracker_reason = _ask(agent_tickets, role="tracker")
    return {
        "status": "ok",
        "since": start.isoformat(),
        "until": end.isoformat(),
        "capture": _capture(log, start, end, hidden),
        "review": _review(repo, prefix, knowledge_prs, end, scm_reason, project),
        "agent_loop": _agent_loop(repo, start, agent_prs, tickets, agent_reason, tracker_reason),
        "health": _health(records, start, end),
    }


def _ask(call: Callable[..., Any] | None, *args: Any, role: str) -> tuple[Any, str | None]:
    """Call a role; a role not selected, or one that fails, leaves its numbers unmeasured."""
    if call is None:
        return None, f"no {role} provider: select one for the {role} role"
    try:
        return call(*args), None
    except Exception as exc:  # noqa: BLE001 - a provider's failure must not hide the rest
        first = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        return None, f"{role} role failed: {first}"


def _moment(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.combine(value, time.min, tzinfo=UTC)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_git(repo, *args, check=False, context="knowledge stats")


def _toplevel(folder: Path) -> Path | None:
    result = _git(folder, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def _ratio(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def _money(value: float) -> float:
    return round(value, 4)


# Capture -----------------------------------------------------------------------------


def runs(log: Path | str, start: datetime, end: datetime) -> list[CaptureRun]:
    """Capture runs in ``log`` that started in ``[start, end)``, oldest first.

    Every line must be a capture run (``contracts/capture-run.schema.json``); the first
    that is not stops the measurement with its file and line.
    """
    where = Path(log).expanduser()
    if where.is_dir():
        files = sorted([*where.glob("*.jsonl"), *where.glob("*.json")])
    elif where.is_file():
        files = [where]
    else:
        raise ValueError(f"capture run log not found: {log}")
    found: list[CaptureRun] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        chunks = (
            [(number, line) for number, line in enumerate(text.splitlines(), 1) if line.strip()]
            if path.suffix == ".jsonl"
            else [(1, text)]
        )
        for number, chunk in chunks:
            try:
                run = CaptureRun.model_validate_json(chunk)
            except ValidationError as exc:
                error = exc.errors()[0]
                field = ".".join(str(part) for part in error["loc"])
                detail = f"{field}: {error['msg']}" if field else error["msg"]
                raise ValueError(
                    f"{path}:{number} is not a capture run ({detail}); "
                    "expected contracts/capture-run.schema.json"
                ) from None
            if start <= run.started_at < end:
                found.append(run)
    found.sort(key=lambda run: run.started_at)
    return found


def _capture(
    log: Path | str | None,
    start: datetime,
    end: datetime,
    hidden: frozenset[str] | set[str] = frozenset(),
) -> dict[str, Any]:
    """``hidden`` Sources (customer records another view may not show) are left out."""
    if log is None:
        return {
            "available": False,
            "reason": "no capture run log: run stats where the capture batch runs, with --log",
        }
    found = runs(log, start, end)
    last: dict[str, CaptureEntry] = {}
    tokens = cost = 0.0
    hours = transcript_cost = 0.0
    unknown = 0  # Source entries whose usage is unknown; the totals leave them out
    for run in found:
        for entry in run.sources:
            if entry.id in hidden:
                continue
            last[entry.id] = entry
            if not entry.usage_known():
                unknown += 1
            tokens += (entry.input_tokens or 0) + (entry.output_tokens or 0)
            cost += entry.cost_usd or 0
            if entry.kind == "transcript":
                transcript_cost += entry.cost_usd or 0
    for entry in last.values():
        if entry.kind == "transcript" and entry.outcome == "extracted":
            hours += (entry.duration_seconds or 0) / 3600
    outcomes = Counter(entry.outcome for entry in last.values())
    extracted = outcomes["extracted"]
    return {
        "available": True,
        "runs": len(found),
        "ceiling_reached": sum(run.ceiling_reached for run in found),
        "sources_pulled": len(last),
        "sources_filtered": outcomes["filtered"],
        "sources_extracted": extracted,
        "sources_deferred": outcomes["deferred"],
        "sources_failed": outcomes["failed"],
        "tokens": int(tokens),
        "cost_usd": _money(cost),
        "usage_unknown": unknown,
        "tokens_per_source": round(tokens / extracted) if extracted else None,
        "cost_per_source_usd": _money(cost / extracted) if extracted else None,
        "transcript_hours": round(hours, 2),
        "cost_per_transcript_hour_usd": _money(transcript_cost / hours) if hours else None,
    }


# Review ------------------------------------------------------------------------------


def _is_record_path(path: str, prefix: str) -> bool:
    if not path.startswith(prefix) or not path.endswith(".md"):
        return False
    inner = path[len(prefix) :]
    name = inner.rsplit("/", 1)[-1]
    return name not in ("index.md", "README.md") and not inner.startswith(NOT_RECORDS)


def _record_text(repo: Path, sha: str, path: str) -> str | None:
    """The file at ``sha`` when it is a knowledge record, else ``None``."""
    shown = _git(repo, "show", f"{sha}:{path}")
    if shown.returncode:
        return None
    try:
        data, _raw, _body = split(shown.stdout)
    except ValueError:
        return None
    if not isinstance(data, dict) or data.get("type") not in TYPES:
        return None
    return "\n".join(line.rstrip() for line in shown.stdout.strip().splitlines())


def _has(repo: Path | None, revision: str | None) -> bool:
    return bool(
        repo
        and revision
        and _git(repo, "rev-parse", "-q", "--verify", f"{revision}^{{commit}}").returncode == 0
    )


def _record_id(text: str) -> str | None:
    data = split(text)[0]
    value = data.get("id") if isinstance(data, dict) else None
    return value if isinstance(value, str) else None


def _hidden(repo: Path | None, pr: dict[str, Any], prefix: str, project: str | None) -> bool | None:
    """Whether a records pull request touches a record a view of ``project`` may not show.

    A path under another project's ``projects/<name>/`` hides it before any read. The
    records are then checked for ``boundary: customer`` (KAN-465) as the first commit
    had them and, once merged, as the merge has them, so a reviewer's later boundary
    counts, and one the reviewer deleted or renamed away still does. Only the pull
    request's own commits and files are read, however it was merged. ``None`` when
    those commits, or the first commit's parent, are not fetched: the boundary is
    unknown.
    """
    paths = [path for path in pr.get("files", []) if _is_record_path(path, prefix)]
    if any(project_of(path[len(prefix) :]) not in (None, project) for path in paths):
        return True
    first, merge = pr.get("first_commit"), pr.get("merge_commit")
    if (
        not _has(repo, first)
        or not _has(repo, f"{first}^")
        or (pr.get("state") == "merged" and not _has(repo, merge))
    ):
        return None  # the first commit's own files can't be read, as in a shallow clone
    assert repo is not None and first is not None
    # The first commit as it was: the final file list misses a record the reviewer
    # deleted or renamed. ``first^..first`` is the pull request's own commit, so a
    # squash merge does not pull in other records.
    own = _git(repo, "diff", "--name-only", "--no-renames", f"{first}^", first)
    firsts = (
        [n for n in own.stdout.splitlines() if _is_record_path(n, prefix)]
        if own.returncode == 0
        else []
    )
    if any(project_of(name[len(prefix) :]) not in (None, project) for name in firsts):
        return True
    seen = [(first, path) for path in dict.fromkeys([*paths, *firsts])]
    if pr.get("state") == "merged":
        # The pull request's own files, which end where the reviewer left them: a diff
        # from the first commit would also take in records other pull requests landed
        # on main in between, as a squash merge sits on top of them.
        seen += [(merge, path) for path in paths]
    for sha, path in seen:
        text = _record_text(repo, sha, path)
        header = split(text)[0] if text is not None else None
        if isinstance(header, dict) and not visible_in(header, path[len(prefix) :], project):
            return True
    return False


def _extracted(repo: Path, first: str, prefix: str) -> dict[str, str]:
    """Records, by id, that the pull request's first commit added or changed."""
    changed = _git(repo, "diff", "--name-only", "--no-renames", f"{first}^", first)
    names = changed.stdout.splitlines() if changed.returncode == 0 else []
    found = {}
    for name in names:
        if _is_record_path(name, prefix):
            text = _record_text(repo, first, name)
            if text is not None and (record_id := _record_id(text)):
                found[record_id] = text
    return found


def _merged(
    repo: Path, merge: str, names: list[str], prefix: str, wanted: set[str]
) -> dict[str, str]:
    """The ``wanted`` records at ``merge``, by id, wherever the reviewer moved them.

    ``names`` is the pull request's own file list, which ends where the reviewer left
    them; a diff from the first commit would take in other pull requests' records.
    """
    found = {}
    for name in names:
        if _is_record_path(name, prefix):
            text = _record_text(repo, merge, name)
            record_id = _record_id(text) if text is not None else None
            if text is not None and record_id in wanted:
                found[record_id] = text
    return found


def _review(
    repo: Path | None,
    prefix: str,
    prs: list[dict[str, Any]] | None,
    now: datetime,
    reason: str | None,
    project: str | None = None,
) -> dict[str, Any]:
    if prs is None:
        return {"available": False, "reason": reason}
    rows = []
    kept = edited = dropped = hidden = 0
    unmeasured = []
    for pr in sorted(prs, key=lambda pr: pr["number"]):
        if not any(_is_record_path(path, prefix) for path in pr.get("files", [])):
            continue
        boundary = _hidden(repo, pr, prefix, project)
        if boundary:
            hidden += 1  # counted, never listed: its title may name a customer
            continue
        created = _parse(pr["created_at"])
        assert created is not None
        ended = _parse(pr.get("merged_at") or pr.get("closed_at"))
        hours = round((ended - created).total_seconds() / 3600, 1) if ended else None
        row: dict[str, Any] = {
            "number": pr["number"],
            # A pull request whose records can't be read may be a customer's: no title.
            "title": pr.get("title", "") if boundary is False else None,
            "state": pr["state"],
            "hours_to_decision": hours,
            "open_hours": None if ended else round((now - created).total_seconds() / 3600, 1),
            "extracted": None,
            "edited": None,
            "dropped": None,
        }
        rows.append(row)
        if pr["state"] == "open":
            continue
        first, merge = pr.get("first_commit"), pr.get("merge_commit")
        if (
            not _has(repo, first)
            or not _has(repo, f"{first}^")
            or (pr["state"] == "merged" and not _has(repo, merge))
        ):
            unmeasured.append(pr["number"])
            continue
        assert repo is not None and first is not None
        before = _extracted(repo, first, prefix)
        after = (
            _merged(repo, merge, pr.get("files", []), prefix, set(before))
            if pr["state"] == "merged" and merge
            else {}
        )
        mine = Counter(
            "dropped"
            if record_id not in after
            else "kept"
            if after[record_id] == text
            else "edited"
            for record_id, text in before.items()
        )
        row.update(extracted=len(before), edited=mine["edited"], dropped=mine["dropped"])
        kept += mine["kept"]
        edited += mine["edited"]
        dropped += mine["dropped"]
    decided = [row["hours_to_decision"] for row in rows if row["hours_to_decision"] is not None]
    waiting = [row for row in rows if row["open_hours"] is not None]
    late = sum(row["open_hours"] > REVIEW_HOURS for row in waiting)
    # A pull request still open past 48 hours has already missed the 48-hour bar.
    within = sum(hours <= REVIEW_HOURS for hours in decided)
    measured = kept + edited + dropped
    return {
        "available": True,
        "pull_requests": len(rows),
        "decided": len(decided),
        "open": len(waiting),
        "open_over_48h": late,
        "median_hours_to_decision": round(median(decided), 1) if decided else None,
        "within_48h_pct": _ratio(within, len(decided) + late),
        "records_extracted": measured,
        "records_kept": kept,
        "records_edited": edited,
        "records_dropped": dropped,
        "edited_pct": _ratio(edited, measured),
        "dropped_pct": _ratio(dropped, measured),
        "edited_or_dropped_pct": _ratio(edited + dropped, measured),
        "unmeasured": unmeasured,
        "hidden_customer": hidden,
        "by_pull_request": rows,
    }


def _parse(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


# Agent loop --------------------------------------------------------------------------


def _scorecards(repo: Path | None, start: datetime) -> list[str] | None:
    if repo is None:
        return None
    log = _git(
        repo,
        "log",
        f"--since={start.isoformat()}",
        "--diff-filter=A",
        "--no-renames",
        "--name-only",
        "--format=",
        "--",
        SCORECARDS,
    )
    if log.returncode:
        return None
    names = {
        name
        for name in log.stdout.splitlines()
        if name.endswith(".md") and name.rsplit("/", 1)[-1] != "scorecard.md"
    }
    return sorted(name for name in names if (repo / name).is_file())


def _agent_loop(
    repo: Path | None,
    start: datetime,
    prs: list[dict[str, Any]] | None,
    tickets: list[dict[str, Any]] | dict[str, Any] | None,
    scm_reason: str | None,
    tracker_reason: str | None,
) -> dict[str, Any]:
    cards = _scorecards(repo, start)
    found: dict[str, Any] = {
        "tickets": None,
        "pull_requests": None,
        "first_push_green": None,
        "first_push_green_pct": None,
        "scorecards": None if cards is None else len(cards),
        "scorecard_files": cards,
        "reasons": [],
    }
    if tickets is None:
        found["reasons"].append(tracker_reason)
        return found
    if isinstance(tickets, dict) and not tickets.get("complete", True):
        found["reasons"].append(
            f"the tracker returned only its {TICKET_LIMIT} most recently updated tickets "
            "per label, so tickets and their pull requests may be undercounted"
        )
    items: list[dict[str, Any]] = (
        tickets.get("items") or [] if isinstance(tickets, dict) else list(tickets)
    )
    keys = {_item_key(item) for item in items}
    found["tickets"] = len(keys)
    if prs is None:
        found["reasons"].append(scm_reason)
        return found
    mine = [pr for pr in prs if _ticket_key(pr.get("title", "")) in keys]
    checked = [pr for pr in mine if pr.get("first_push_checks", "none") in ("success", "failure")]
    green = sum(pr["first_push_checks"] == "success" for pr in checked)
    found.update(
        pull_requests=len(mine),
        first_push_green=green,
        first_push_green_pct=_ratio(green, len(checked)),
    )
    return found


def _item_key(item: dict[str, Any]) -> str:
    """The ticket key a pull request title carries: Jira's ``id`` is numeric, its URL ends in the key."""
    url = str(item.get("url") or "")
    if "/browse/" in url:
        return url.rsplit("/browse/", 1)[1].split("?", 1)[0].strip("/")
    return str(item.get("key") or item["id"])


def _ticket_key(title: str) -> str | None:
    head = title.strip().split(":", 1)[0].split(" ", 1)[0]
    parts = head.split("-")
    if len(parts) == 2 and parts[0].isupper() and parts[0].isalnum() and parts[1].isdigit():
        return head
    return None


# Health ------------------------------------------------------------------------------


def _health(items: Iterable[Any], start: datetime, now: datetime) -> dict[str, Any]:
    stale = []
    expiring = []
    lapsed = []
    authors: Counter[str] = Counter()
    warn = now + timedelta(days=EXPIRY_WARNING_DAYS)
    for item in items:
        record: KnowledgeRecord = item.record
        if record.type == "source":
            if record.status == "raw" and payload_expires(record):
                captured = record.observed_at or _moment(record.date)
                expires = captured + timedelta(days=PAYLOAD_DAYS)
                entry = {"id": record.id, "path": item.relative, "expires": expires.isoformat()}
                if expires <= now:
                    lapsed.append(entry)
                elif expires <= warn:
                    expiring.append(entry)
            continue
        if record.stale_after and record.stale_after < now and okf_status(record) != "deprecated":
            stale.append(
                {
                    "id": record.id,
                    "path": item.relative,
                    "stale_after": record.stale_after.isoformat(),
                }
            )
        if _moment(record.date) >= start:
            authors[record.author or record.owner] += 1
    return {
        "records_past_stale_after": len(stale),
        "stale": stale,
        "sources_expiring_unprocessed": len(expiring),
        "expiring": expiring,
        "sources_expired_unprocessed": len(lapsed),
        "expired": lapsed,
        "records_by_author": dict(sorted(authors.items(), key=lambda pair: (-pair[1], pair[0]))),
    }


# Report ------------------------------------------------------------------------------


def _show(value: Any, unit: str = "") -> str:
    if value is None:
        return "n/a"
    return f"{value}{unit}"


def report(result: dict[str, Any]) -> list[str]:
    """The weekly Markdown report (``reports/<iso-week>.md``) and the plain-text answer."""
    capture, review = result["capture"], result["review"]
    agent, health = result["agent_loop"], result["health"]
    since, until = result["since"][:10], result["until"][:10]
    out = [f"# Knowledge system outcomes, {since} to {until}", "", "## Capture", ""]
    out += (
        [f"- Not measured: {capture['reason']}"]
        if not capture["available"]
        else [
            f"- Runs: {capture['runs']} ({capture['ceiling_reached']} hit the token ceiling)",
            (
                f"- Sources pulled: {capture['sources_pulled']}; filtered "
                f"{capture['sources_filtered']}; extracted {capture['sources_extracted']}; "
                f"deferred {capture['sources_deferred']}; failed {capture['sources_failed']}"
            ),
            f"- Tokens: {capture['tokens']}; cost ${capture['cost_usd']}"
            + (
                f" (not counting {capture['usage_unknown']} with unknown usage)"
                if capture["usage_unknown"]
                else ""
            ),
            (
                f"- Per extracted Source: {_show(capture['tokens_per_source'])} tokens, "
                f"${_show(capture['cost_per_source_usd'])}"
            ),
            (
                f"- Per transcript hour: ${_show(capture['cost_per_transcript_hour_usd'])} "
                f"over {capture['transcript_hours']} h"
            ),
        ]
    )
    out += ["", "## Review", ""]
    if not review["available"]:
        out.append(f"- Not measured: {review['reason']}")
    else:
        out += [
            (
                f"- Records pull requests: {review['pull_requests']} "
                f"({review['decided']} decided, {review['open']} open, "
                f"{review['open_over_48h']} open over 48 h)"
            ),
            (
                f"- Median hours to merge or close: {_show(review['median_hours_to_decision'])}; "
                f"within 48 h: {_show(review['within_48h_pct'], '%')}"
            ),
            (
                f"- Extracted records: {review['records_extracted']}; edited "
                f"{review['records_edited']} ({_show(review['edited_pct'], '%')}); dropped "
                f"{review['records_dropped']} ({_show(review['dropped_pct'], '%')})"
            ),
        ]
        if review["unmeasured"]:
            numbers = ", ".join(f"#{n}" for n in review["unmeasured"])
            out.append(f"- Not measured (commits not fetched, or no parent commit): {numbers}")
        if review["hidden_customer"]:
            out.append(
                f"- Left out: {review['hidden_customer']} pull requests with customer records "
                "this view may not show"
            )
    out += ["", "## Agent loop", ""]
    out += [
        f"- Tickets labelled exec:agent or lane:agent: {_show(agent['tickets'])}",
        (
            f"- Pull requests for them: {_show(agent['pull_requests'])}; checks green on first "
            f"push: {_show(agent['first_push_green'])} ({_show(agent['first_push_green_pct'], '%')})"
        ),
        f"- Scorecards committed: {_show(agent['scorecards'])}",
    ]
    out += [f"- Not measured: {reason}" for reason in agent["reasons"]]
    out += ["", "## Health", ""]
    out += [
        f"- Records past stale_after: {health['records_past_stale_after']}",
        (
            f"- Sources expiring within {EXPIRY_WARNING_DAYS} days, unprocessed: "
            f"{health['sources_expiring_unprocessed']}; already expired unprocessed: "
            f"{health['sources_expired_unprocessed']}"
        ),
        "- Records by author: "
        + (
            ", ".join(f"{name} {count}" for name, count in health["records_by_author"].items())
            or "none"
        ),
    ]
    return out


def week_path(moment: datetime) -> str:
    """``reports/<iso-week>.md`` for the week holding ``moment``, e.g. ``reports/2026-W46.md``."""
    year, week, _day = moment.isocalendar()
    return f"reports/{year}-W{week:02d}.md"


# Roles -------------------------------------------------------------------------------


def from_roles(
    config: dict[str, Any] | None,
    root: Path,
    *,
    agent_repositories: Iterable[str] = (),
    base: str = "main",
    registry: Any = None,
) -> dict[str, Any]:
    """The ``pull_requests``, ``agent_pull_requests`` and ``agent_tickets`` callables.

    Built from the project's ``scm`` and ``tracker`` roles only, so ``stats`` needs no
    other credential. A role that is not selected gives ``None``, and that section says so.
    ``registry`` replaces the project's providers, as the MCP server's does in tests.
    """
    from ai_dlc.providers import Registry

    if not config:
        return {}
    registry = registry if registry is not None else Registry(config, root=root)
    roles = config.get("roles", {})
    wired: dict[str, Any] = {}
    scm_id = roles.get("scm")
    if scm_id:
        wired["pull_requests"] = _scm_lister(lambda: registry.get(scm_id))
        repositories = list(agent_repositories)
        if repositories:
            listers = [
                _scm_lister(lambda name=name: registry.scm_for(root, name, base))
                for name in repositories
            ]
            wired["agent_pull_requests"] = lambda since: [
                pr for lister in listers for pr in lister(since)
            ]
    tracker_id = roles.get("tracker")
    if tracker_id:

        def tickets() -> dict[str, Any]:
            items: dict[str, dict[str, Any]] = {}
            complete = True
            for label in AGENT_LABELS:  # labels in one query must all match, so one each
                page = registry.invoke(
                    tracker_id, "query", {"labels": [label], "limit": TICKET_LIMIT}
                )
                complete = complete and page.get("complete", True) is not False
                for item in page["items"]:
                    items.setdefault(_item_key(item), item)
            return {"items": list(items.values()), "complete": complete}

        wired["agent_tickets"] = tickets
    return wired


def _scm_lister(provider: Callable[[], Any]) -> PullRequests:
    from ai_dlc.contracts import validate_request, validate_response

    def listing(since: datetime) -> list[dict[str, Any]]:
        payload = validate_request("pull_requests", {"since": since.isoformat()}).payload
        # Providers behind a process boundary get JSON, so the moment travels as text.
        found = provider().pull_requests(since=since.isoformat(), limit=payload["limit"])
        if isinstance(found, dict):
            found = found.get("pull_requests", [])
        return validate_response("pull_requests", {"pull_requests": found})["pull_requests"]

    return listing
