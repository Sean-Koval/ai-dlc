"""Execution targets accepted by project setup and doctor."""

from __future__ import annotations

import tomllib
from typing import Any

from ai_dlc.files import assets

# Targets removed by the rendering freeze (ADR 0001). Cloud sandboxes are rendered by
# hangar at claim time; the dev container now bootstraps with the local target.
REMOVED_TARGETS = {
    "codex-cloud": "cloud sandboxes are rendered by hangar at claim time",
    "claude-cloud": "cloud sandboxes are rendered by hangar at claim time",
    "devcontainer": "use --target local inside the dev container",
}


def execution_targets() -> dict[str, dict[str, Any]]:
    """Return the packaged execution-target table."""
    return tomllib.loads((assets("targets") / "capabilities.toml").read_text())


def execution_target(target: str) -> dict[str, Any]:
    """Return one target's capabilities or refuse an unknown or removed target."""
    targets = execution_targets()
    if target in targets:
        return targets[target]
    supported = ", ".join(sorted(targets))
    reason = REMOVED_TARGETS.get(
        target, "cloud sandboxes are rendered by hangar; ai-dlc sets up local checkouts and CI"
    )
    raise ValueError(
        f"unsupported execution target: {target}; {reason} (supported targets: {supported})"
    )
