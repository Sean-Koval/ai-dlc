"""Controlled messy-project baseline for repeatable document organization qualification.

Build a disposable copy for the manual walkthrough in
docs/runbooks/document-workspace-qualification.md:

    uv run --locked --no-sync python tests/fixtures/messy_project.py DESTINATION

The baseline is input to a harness exercise, not an organization mapping. The
review points describe what a reviewer checks in the outcome.
"""

import subprocess
import sys
from pathlib import Path

FILES = {
    "README.md": "# Parcel service\n\nStart with [architecture](docs/architecture.md) and [deployment](docs/deployment.md). Historical notes are in [the experiment](legacy/retry-experiment.md).\n",
    "docs/architecture.md": "# Parcel architecture\n\nThe API accepts parcels and enqueues delivery jobs. A worker dispatches jobs through the carrier adapter.\n\nSee [adapter decision](adr/001-adapter.md), [configuration](configuration.md), and [retry specification](../openspec/specs/delivery/spec.md).\n",
    "docs/architecture-notes.md": "# Carrier adapter explanation\n\nThe API accepts parcels and enqueues delivery jobs. A worker dispatches jobs through the carrier adapter.\n\nThe adapter exists because carriers have different rate limits. This boundary allows a future carrier without changing the queue protocol.\n",
    "docs/deployment.md": "# Deploy Parcel\n\nRun `python -m parcel.check_config` before starting workers. Set `RETRY_LIMIT=3`. Restart the worker after configuration changes.\n\nConsult [configuration](configuration.md) and the [architecture](architecture.md).\n",
    "docs/configuration.md": "# Configuration reference\n\n`RETRY_LIMIT` defaults to 3 attempts. The worker reads it on startup. Values must be positive integers.\n\nSee [deployment](deployment.md).\n",
    "docs/adr/001-adapter.md": "# ADR 001: Carrier adapter\n\nStatus: accepted.\n\nWe use a carrier adapter to isolate authentication and carrier-specific retry errors. A direct HTTP call from each queue handler was rejected because it repeated credential handling.\n\nSee [architecture](../architecture.md).\n",
    "legacy/retry-experiment.md": "# Retry experiment\n\nStatus: historical, superseded by the [delivery specification](../openspec/specs/delivery/spec.md).\n\nWe tried ten attempts during a 2024 spike. It increased carrier throttling, so we chose three attempts. The experiment remains useful rationale.\n",
    "SETUP_OLD.md": "# Old setup instructions\n\nStatus: superseded. This document describes the removed shell worker, not the current Python worker. Use [deployment](docs/deployment.md).\n\nHistorical command: `./worker.sh --retries 10`. Do not use it for current deployment.\n",
    "openspec/specs/delivery/spec.md": "# Delivery behavior\n\n## Purpose\nBound attempts to avoid carrier throttling.\n\n## Requirements\n### Requirement: Retry limit\nThe worker SHALL make at most three attempts by default.\n\n#### Scenario: Repeated carrier failure\n- **WHEN** the carrier repeatedly fails\n- **THEN** processing stops after three attempts\n",
    "src/parcel/config.py": "RETRY_LIMIT = 3\n",
    ".gitignore": "ignored/\n.obsidian/\n.ai-dlc/local/\n",
    "ignored/scratch.md": "Private excluded scratch content.\n",
    "ai-dlc.toml": 'schema = 4\n[project]\nname = "Parcel qualification"\n[roles]\nspecs = "openspec"\nknowledge = "obsidian"\n',
}

EXPECTED_REVIEW_POINTS = (
    (
        "docs/architecture.md and docs/architecture-notes.md overlap; a consolidation keeps "
        "the carrier rate-limit rationale."
    ),
    "docs/adr/001-adapter.md is an existing decision record whose convention is retained.",
    "SETUP_OLD.md is superseded history that points to docs/deployment.md.",
    "legacy/retry-experiment.md is labelled historical rationale for three attempts.",
    "docs/deployment.md is an operational procedure; docs/configuration.md is reference.",
    "openspec/specs/delivery/spec.md keeps the retry requirement byte-identical under OpenSpec.",
    "ignored/scratch.md stays Git-ignored and outside review.",
    (
        "src/parcel/config.py is the only code evidence; unsupported operational claims keep "
        "explicit uncertainty."
    ),
)


def build_messy_project(destination: Path) -> Path:
    """Write the baseline into an empty directory and commit it as a stable checkout."""
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"Destination must be empty: {destination}")
    for relative, body in FILES.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    git = ["git", "-C", str(destination), "-c", "user.name=AI-DLC qualification"]
    git += ["-c", "user.email=qualification@example.invalid"]
    subprocess.run(["git", "init", "-q", str(destination)], check=True)
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "-qm", "fixture: establish messy project baseline"], check=True)
    return destination


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: messy_project.py DESTINATION")
    print(build_messy_project(Path(sys.argv[1])))
