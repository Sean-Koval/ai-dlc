"""Run the declared evaluation or print its complete, network-free dry run."""

import argparse
import json
import sys
from pathlib import Path

# Keep --dry-run usable with only Python, including an empty PATH.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_dlc.harness.skill_evaluation import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--declaration", type=Path, default=ROOT / "agents/evaluation.toml")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.declaration, dry_run=args.dry_run, output=args.out)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Evaluation refused: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result.get("stop_reason") else 0


if __name__ == "__main__":
    raise SystemExit(main())
