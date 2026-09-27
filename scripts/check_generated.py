"""Check generated schemas and packaged bootstrap snapshots without writing files."""

import json
from pathlib import Path

from ai_dlc.contracts import PAYLOADS, RESPONSES, ServiceResult, manifest
from ai_dlc.harness.agents import render_agents

root = Path(__file__).resolve().parents[1]
if not render_agents(root)["clean"]:
    raise SystemExit("Generated agent guidance is stale; run ai-dlc agents render --apply")
actual = json.loads((root / "contracts/manifest.json").read_text(encoding="utf-8"))
if actual != manifest():
    raise SystemExit("Generated contract manifest is stale")

for operation in PAYLOADS:
    for suffix, model in [("request", PAYLOADS[operation]), ("response", RESPONSES[operation])]:
        path = root / "contracts" / f"{operation}.{suffix}.schema.json"
        if json.loads(path.read_text(encoding="utf-8")) != model.model_json_schema():
            raise SystemExit(f"Generated schema is stale: {path.name}")
if json.loads((root / "contracts/service-result.schema.json").read_text(encoding="utf-8")) != (
    ServiceResult.model_json_schema()
):
    raise SystemExit("Generated schema is stale: service-result.schema.json")
from ai_dlc.verification.evaluation.contracts import SCHEMAS

for name, model in SCHEMAS.items():
    path = root / "contracts/evaluation" / f"{name}.schema.json"
    if (
        not path.is_file()
        or json.loads(path.read_text(encoding="utf-8")) != model.model_json_schema()
    ):
        raise SystemExit(f"Generated schema is stale: evaluation/{path.name}")
for relative in [
    "scripts/bootstrap.sh",
    "bootstrap/versions.sh",
    "bootstrap/download.sh",
    "scripts/bootstrap.ps1",
    "bootstrap/windows.json",
    "bootstrap/windows.ps1",
    "bootstrap/windows-native.cs",
    "bootstrap/windows-select.py",
]:
    if (root / relative).read_bytes() != (
        root / "project-templates/project" / relative
    ).read_bytes():
        raise SystemExit(f"Packaged bootstrap is stale: {relative}")
