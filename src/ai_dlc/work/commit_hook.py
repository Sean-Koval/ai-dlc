"""Opt-in Git commit-msg hook that appends the session join key as a trailer.

``ai-dlc work hooks install`` is the only way it is installed; nothing installs it
silently. It refuses to replace a commit-msg hook it did not write.
"""

from __future__ import annotations

import stat
from pathlib import Path

from ai_dlc.errors import RefusedError
from ai_dlc.files import run_git

MARKER = "# ai-dlc: session join key trailer (KAN-463)"
SCRIPT = f"""#!/bin/sh
{MARKER}
# Appends `Work-Session: $AI_DLC_SESSION_KEY` once; does nothing without the key.
[ -n "$AI_DLC_SESSION_KEY" ] || exit 0
git interpret-trailers --in-place --if-exists addIfDifferent \\
  --trailer "Work-Session: $AI_DLC_SESSION_KEY" "$1"
"""


def hook_path(root: Path) -> Path:
    """Where Git runs commit-msg for this checkout, honouring core.hooksPath."""
    path = Path(run_git(root, "rev-parse", "--git-path", "hooks/commit-msg").stdout.strip())
    return path if path.is_absolute() else root / path


def install_commit_msg_hook(root: Path) -> dict:
    """Install the hook once; refuse to overwrite a hook another tool owns."""
    path = hook_path(root)
    if path.exists():
        current = path.read_text(encoding="utf-8", errors="replace")
        if MARKER not in current:
            raise RefusedError(
                f"{path} already exists and was not written by ai-dlc; add the "
                "Work-Session trailer to it by hand or remove it first"
            )
        if current == SCRIPT:
            return {"status": "unchanged", "path": str(path)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SCRIPT, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return {"status": "installed", "path": str(path)}
