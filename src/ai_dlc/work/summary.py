"""Offline what-next summary derived from local work records.

States come from each record's ``tracker``, ``pr`` and ``spec`` artifacts alone. The
tracker is never consulted, so the summary cannot know whether a record was finished:
a record with a pull request and an archived change is printed as awaiting merge with
the finish command as its next step, and the header says so.
"""

from pathlib import Path
from urllib.parse import urlsplit

from ai_dlc.config import load_project
from ai_dlc.work.workflow import read_work_records

UNPUBLISHED = "unpublished"
IN_PROGRESS = "in progress"
ARCHIVE_FIRST = "awaiting merge, archive first"
AWAITING_MERGE = "awaiting merge"
# Most actionable first: the session-start hook shows only the first ten lines.
STATE_ORDER = (IN_PROGRESS, ARCHIVE_FIRST, AWAITING_MERGE, UNPUBLISHED)
CHECK_COMMAND = "ai-dlc project check --required"
PROBLEMS_COMMAND = "ai-dlc work validate --all"

_CHANGES = "openspec/changes/"
_ARCHIVE = "openspec/changes/archive/"


def _spec_archived(record: dict) -> tuple[bool, str | None]:
    """Whether nothing local remains to archive, and the unarchived change ID if any."""
    if not record["requires_spec"]:
        return True, None
    spec = record["artifacts"].get("spec", "")
    if spec.startswith(_CHANGES) and not spec.startswith(_ARCHIVE):
        change = spec[len(_CHANGES) :].strip("/").split("/")[0]
        return False, change or None
    return True, None


def derive_state(record: dict) -> tuple[str, str]:
    """Classify one validated record and name its next command."""
    work_id = record["id"]
    artifacts = record["artifacts"]
    if not artifacts.get("tracker"):
        return UNPUBLISHED, f"ai-dlc work publish {work_id}"
    if not artifacts.get("pr"):
        return IN_PROGRESS, f"ai-dlc work pr {work_id}"
    archived, change = _spec_archived(record)
    if archived:
        return AWAITING_MERGE, f"ai-dlc work finish {work_id}"
    if change:
        return ARCHIVE_FIRST, f"openspec archive {change} --yes"
    return ARCHIVE_FIRST, f"ai-dlc work link {work_id} spec <archived change>"


def summarize_next(root: Path, include_all: bool = False) -> dict:
    """Read every record offline and derive its state; nothing outside the tree is probed."""
    root = Path(root)
    config = load_project(root)
    records, errors = read_work_records(root.resolve())
    rows = []
    for record in records.values():
        state, command = derive_state(record)
        if state == UNPUBLISHED and not include_all:
            continue
        rows.append(
            {
                "id": record["id"],
                "state": state,
                "tracker": record["artifacts"].get("tracker") or None,
                "pr": record["artifacts"].get("pr") or None,
                "next": command,
            }
        )
    rows.sort(key=lambda row: (STATE_ORDER.index(row["state"]), row["id"]))
    directory = root / ".ai-dlc/work"
    return {
        "status": "ok",
        "tracker_consulted": False,
        "total": len(list(directory.glob("*.toml"))) if directory.is_dir() else 0,
        "records": rows,
        "required": list(config.get("checks", {}).get("required", [])),
        "check": CHECK_COMMAND,
        "errors": errors,
    }


def _short_id(work_id: str) -> str:
    return work_id if len(work_id) <= 24 else work_id[:18] + "..."


def _short_reference(reference: str | None) -> str:
    """The trailing number of a URL or bare reference, prefixed with ``#``."""
    if not reference:
        return "-"
    leaf = urlsplit(reference).path.rstrip("/").rsplit("/", 1)[-1] or reference
    return f"#{leaf}" if leaf.isdigit() else leaf


def render_next(summary: dict) -> str:
    """Render the fixed plain-text shape; no colour codes."""
    lines = [
        (
            f"Active work ({len(summary['records'])} of {summary['total']} records; "
            "tracker not consulted)"
        )
    ]
    for row in summary["records"]:
        reference = (
            f"pr {_short_reference(row['pr'])}" if row["pr"] else _short_reference(row["tracker"])
        )
        lines.append(
            f"  {_short_id(row['id']):<26} {row['state']:<19} {reference:<8} next: {row['next']}"
        )
    lines.append("Required checks: " + " ".join(summary["required"]))
    lines.append(f"Run: {summary['check']}")
    if summary["errors"]:
        problems = len({error.split(":", 1)[0] for error in summary["errors"]})
        lines.append(f"Problems: {problems} record(s); run {PROBLEMS_COMMAND}")
    return "\n".join(lines) + "\n"


def next_text(root: Path) -> str:
    return render_next(summarize_next(root))
