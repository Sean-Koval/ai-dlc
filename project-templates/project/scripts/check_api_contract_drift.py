"""Compare one optional src/<pkg>/app.py FastAPI contract without rewriting it."""

import ast
import difflib
import importlib
import json
import sys
from pathlib import Path


def fastapi_module(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    return any(
        isinstance(node, ast.ImportFrom)
        and (node.module or "").split(".")[0] == "fastapi"
        or isinstance(node, ast.Import)
        and any(alias.name.split(".")[0] == "fastapi" for alias in node.names)
        for node in ast.walk(tree)
    )


def main():
    root = Path(__file__).resolve().parent.parent
    candidates = [path for path in sorted((root / "src").glob("*/app.py")) if fastapi_module(path)]
    if not candidates:
        print("api-contract-drift: skipped (no FastAPI app in src/<pkg>/app.py)")
        return 0
    if len(candidates) != 1:
        print(
            "api-contract-drift: multiple FastAPI app candidates; select a project-specific check",
            file=sys.stderr,
        )
        return 1
    sys.path.insert(0, str(root / "src"))
    from fastapi import FastAPI
    import yaml

    module = importlib.import_module(candidates[0].parent.name + ".app")
    app = getattr(module, "app", None)
    if not isinstance(app, FastAPI):
        print("api-contract-drift: skipped (module exposes no FastAPI app)")
        return 0
    committed = yaml.safe_load((root / "docs/api/openapi.yaml").read_text())
    actual = app.openapi()
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
