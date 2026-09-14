"""Compare one optional src/<pkg>/app.py FastAPI contract without rewriting it."""

import difflib
import importlib
import json
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "src"))
    apps = []
    for path in sorted((root / "src").glob("*/app.py")):
        # Inspect the exported instance, including re-exports and factory-created apps.
        module = importlib.import_module(path.parent.name + ".app")
        app = getattr(module, "app", None)
        if app is None:
            continue
        try:
            from fastapi import FastAPI
        except ModuleNotFoundError as exc:
            if exc.name == "fastapi":
                continue
            raise
        if isinstance(app, FastAPI):
            apps.append(app)
    if not apps:
        print("api-contract-drift: skipped (no FastAPI app in src/<pkg>/app.py)")
        return 0
    if len(apps) != 1:
        print(
            "api-contract-drift: multiple FastAPI app candidates; select a project-specific check",
            file=sys.stderr,
        )
        return 1
    import yaml

    committed = yaml.safe_load((root / "docs/api/openapi.yaml").read_text())
    actual = apps[0].openapi()
    before = json.dumps(committed, indent=2, sort_keys=True).splitlines(keepends=True)
    after = json.dumps(actual, indent=2, sort_keys=True).splitlines(keepends=True)
    if before != after:
        print(
            "".join(
                difflib.unified_diff(
                    before, after, fromfile="docs/api/openapi.yaml", tofile="app.openapi()"
                )
            )
        )
        return 1
    print("api-contract-drift: contract matches app.openapi()")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
