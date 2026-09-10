"""Explicit optional prose checks; no installation, sync or factual certification."""

import json
import shutil
import subprocess
from pathlib import Path

from ai_dlc.documentation.document_files import read_document
from ai_dlc.documentation.document_impact import _path
from ai_dlc.files import inside


def check_style(root: Path | str, *, paths: list[str]) -> dict:
    root = Path(root).absolute()
    if not isinstance(paths, list) or not 1 <= len(paths) <= 32:
        raise ValueError("Select 1 to 32 documentation paths")
    selected = []
    for relative in paths:
        relative = _path(relative)
        if Path(relative).parts[0] not in {"docs", "openspec"} or not relative.endswith(".md"):
            raise ValueError("Style checks require explicit repository Markdown documents")
        read_document(inside(root, relative))
        selected.append(relative)
    executable = shutil.which("vale")
    result = {
        "tool": "vale",
        "status": "unavailable",
        "alerts": {},
        "limitation": "Prose conventions only; no factual or semantic accuracy claim.",
    }
    if executable is None:
        result["reason"] = (
            "Configure Vale separately to use this optional check; no installation attempted."
        )
        return result
    try:
        run = subprocess.run(
            [executable, "--output=JSON", *selected],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        if run.returncode not in (0, 1):
            raise ValueError(run.stderr.strip() or "Vale could not complete the selected check")
        alerts = json.loads(run.stdout)
        if not isinstance(alerts, dict):
            raise ValueError("Invalid Vale JSON output")  # noqa: TRY004
        result["alerts"] = alerts
        result["status"] = "findings" if run.returncode or any(alerts.values()) else "passed"
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result["status"] = "error"
        result["reason"] = str(exc)
    return result
