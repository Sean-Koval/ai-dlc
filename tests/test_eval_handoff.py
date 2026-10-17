"""The flightdeck handoff inventory names only paths that exist (#194).

Delete this test with the evaluation code in #195.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/verification/end-to-end-evaluation.md"


def inventory_paths() -> list[str]:
    text = DOC.read_text()
    section = text.split("### Inventory", 1)[1].split("### Port notes", 1)[0]
    paths = []
    for line in section.splitlines():
        match = re.match(r"- `([^`]+)`", line.strip())
        if match:
            paths.append(match.group(1))
    return paths


def test_every_handoff_path_exists():
    paths = inventory_paths()
    assert len(paths) >= 45
    missing = [path for path in paths if not (ROOT / path).exists()]
    assert missing == []


def test_inventory_covers_every_evaluation_module_and_test():
    listed = set(inventory_paths())
    modules = {
        str(path.relative_to(ROOT))
        for path in (ROOT / "src/ai_dlc/verification/evaluation").iterdir()
        if path.suffix in {".py", ".md"}
    }
    tests = {
        str(path.relative_to(ROOT))
        for pattern in ("test_evaluation_*.py", "test_*skill_evaluation.py", "test_design_pm_*.py")
        for path in (ROOT / "tests").glob(pattern)
    }
    schemas = {
        str(path.relative_to(ROOT)) for path in (ROOT / "contracts/evaluation").glob("*.json")
    }
    assert modules - listed == set()
    assert tests - listed == set()
    assert schemas - listed == set()


def test_frozen_notices_are_present():
    notice = "Frozen 2026-10; moving to Sean-Koval/flightdeck (Sean-Koval/flightdeck#17)."
    assert notice in (ROOT / "src/ai_dlc/verification/evaluation/FROZEN.md").read_text()
    assert notice in (ROOT / "src/ai_dlc/harness/skill_evaluation.py").read_text()
