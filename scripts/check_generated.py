"""Check generated schemas and packaged bootstrap snapshots without writing files."""

import json
from pathlib import Path

from ai_dlc.contracts import PAYLOADS, RESPONSES, manifest

root = Path(__file__).resolve().parents[1]
actual = json.loads((root / "contracts/manifest.json").read_text())
if actual != manifest():
    raise SystemExit("Generated contract manifest is stale")

for operation in PAYLOADS:
    for suffix, model in [("request", PAYLOADS[operation]), ("response", RESPONSES[operation])]:
        path = root / "contracts" / f"{operation}.{suffix}.schema.json"
        if json.loads(path.read_text()) != model.model_json_schema():
            raise SystemExit(f"Generated schema is stale: {path.name}")
for relative in ["scripts/bootstrap.sh", "bootstrap/versions.sh", "bootstrap/download.sh"]:
    if (root / relative).read_bytes() != (
        root / "project-templates/project" / relative
    ).read_bytes():
        raise SystemExit(f"Packaged bootstrap is stale: {relative}")
