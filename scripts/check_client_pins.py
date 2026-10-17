"""Compare the module catalog's agent client pins with hangar's harness lock.

Local, optional and offline: pass the path of a hangar checkout's
`src/hangar/harnesses.lock.yaml`. Exit status 1 lists every client whose pin differs.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
# Module id -> (mise package key, hangar harness name).
CLIENTS = {
    "claude-code": ("npm:@anthropic-ai/claude-code", "claude-code"),
    "codex": ("npm:@openai/codex", "codex"),
}


def compare(catalog: dict, lock: dict) -> list[str]:
    """Return one line per client whose catalog pin differs from the lock."""
    drift = []
    for module, (package, harness) in CLIENTS.items():
        pinned = catalog.get(module, {}).get("mise", {}).get(package)
        locked = lock.get(harness, {}).get("version")
        if str(pinned) != str(locked):
            drift.append(f"{module}: catalog {pinned} != hangar {locked}")
    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hangar-lock", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=ROOT / "modules" / "catalog.toml")
    args = parser.parse_args(argv)
    catalog = tomllib.loads(args.catalog.read_text())
    lock = yaml.safe_load(args.hangar_lock.read_text()) or {}
    drift = compare(catalog, lock)
    for line in drift:
        print(line, file=sys.stderr)
    if not drift:
        print("client pins match hangar's harness lock")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
