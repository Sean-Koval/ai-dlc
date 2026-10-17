"""Shape checks for decision records in ``docs/decisions/``.

A decision with knowledge-note frontmatter is validated against the shared schema;
its ``checks:`` entries are validated for shape only (flightdeck evaluates them).
An accepted decision's body is never edited: it is superseded by a new record.
"""

import re
from pathlib import Path

from ai_dlc.documentation import knowledge_notes
from ai_dlc.files import run_git

FILENAME = re.compile(r"^\d{4}-[a-z0-9][a-z0-9-]*\.md$")
EDITED = "accepted decisions are superseded, not edited"


def _finding(code: str, path: str, message: str, severity: str) -> dict:
    return {"code": code, "path": path, "message": message, "severity": severity}


def _committed(root: Path, relative: str) -> str | None:
    try:
        result = run_git(root, "show", f"HEAD:{relative}", check=False)
    except (OSError, RuntimeError, ValueError):
        return None
    return result.stdout if result.returncode == 0 else None


def _normalized(body: str) -> str:
    return "\n".join(line.rstrip() for line in body.strip().splitlines())


def decision_findings(root: Path | str) -> list[dict]:
    root = Path(root)
    folder = root / "docs/decisions"
    if not folder.is_dir():
        return []
    findings: list[dict] = []
    for path in sorted(folder.glob("*.md")):
        if path.name.lower() == "readme.md" or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        if not FILENAME.match(path.name):
            findings.append(
                _finding("decision-filename", relative, "Name decisions NNNN-slug.md.", "warning")
            )
        try:
            data, _raw, body = knowledge_notes.split(path.read_text(errors="replace"))
        except ValueError as exc:
            findings.append(_finding("decision-frontmatter", relative, str(exc), "error"))
            continue
        if data is None:
            findings.append(
                _finding(
                    "decision-frontmatter-missing",
                    relative,
                    "Decision has no knowledge-note frontmatter; it is not validated.",
                    "info",
                )
            )
            continue
        problems = knowledge_notes.errors(data)
        if not problems and data.get("kind") != "decision":
            problems = ["kind: a decision record needs kind: decision"]
        for problem in problems:
            findings.append(_finding("decision-schema", relative, problem, "error"))
        if not problems and data["id"] != f"decision/{path.stem}":
            findings.append(
                _finding("decision-id", relative, f"id should be decision/{path.stem}.", "warning")
            )
        committed = _committed(root, relative)
        if committed is None:
            continue
        try:
            before, _before_raw, before_body = knowledge_notes.split(committed)
        except ValueError:
            continue
        if (
            before
            and before.get("status") == "accepted"
            and data.get("status") != "superseded"
            and _normalized(before_body) != _normalized(body)
        ):
            findings.append(_finding("decision-edited", relative, EDITED, "error"))
    return findings
