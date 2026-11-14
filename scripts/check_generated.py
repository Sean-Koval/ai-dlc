"""Check generated schemas and packaged bootstrap snapshots without writing files."""

import json
from pathlib import Path

from ai_dlc.contracts import PAYLOADS, RESPONSES, ServiceResult, manifest

root = Path(__file__).resolve().parents[1]
actual = json.loads((root / "contracts/manifest.json").read_text())
if actual != manifest():
    raise SystemExit("Generated contract manifest is stale; run scripts/build_contracts.py")

for operation in PAYLOADS:
    for suffix, model in [("request", PAYLOADS[operation]), ("response", RESPONSES[operation])]:
        path = root / "contracts" / f"{operation}.{suffix}.schema.json"
        if json.loads(path.read_text()) != model.model_json_schema():
            raise SystemExit(
                f"Generated schema is stale: {path.name}; run scripts/build_contracts.py"
            )
if json.loads((root / "contracts/service-result.schema.json").read_text()) != (
    ServiceResult.model_json_schema()
):
    raise SystemExit("Generated schema is stale: service-result.schema.json")
from ai_dlc.documentation.knowledge_notes import schema as knowledge_note_schema

if json.loads((root / "contracts/knowledge-note.schema.json").read_text()) != (
    knowledge_note_schema()
):
    raise SystemExit("Generated schema is stale: knowledge-note.schema.json")
from ai_dlc.documentation.knowledge_records import schema as knowledge_record_schema

if json.loads((root / "contracts/knowledge-record.schema.json").read_text()) != (
    knowledge_record_schema()
):
    raise SystemExit("Generated schema is stale: knowledge-record.schema.json")
import os
import subprocess
import tomllib

from ai_dlc.documentation.knowledge_records import append_errors, version_errors

VERSIONS = "contracts/knowledge-record.versions.toml"
head_versions = tomllib.loads((root / VERSIONS).read_text())
drift = version_errors(head_versions)
# Published versions are append-only against the base branch (verify.yml fetches history).
base_ref = f"origin/{os.environ.get('GITHUB_BASE_REF') or 'main'}"
base_copy = subprocess.run(
    ["git", "-C", str(root), "show", f"{base_ref}:{VERSIONS}"],
    capture_output=True,
    text=True,
    check=False,
)
if base_copy.returncode == 0:
    drift += append_errors(tomllib.loads(base_copy.stdout), head_versions)
else:
    print(f"note: {base_ref}:{VERSIONS} is unavailable; append-only check skipped")
if drift:
    raise SystemExit("Record format version drift: " + "; ".join(drift))
from ai_dlc.documentation.knowledge_stats import run_log_schema

if json.loads((root / "contracts/capture-run.schema.json").read_text()) != run_log_schema():
    raise SystemExit("Generated schema is stale: capture-run.schema.json")
for relative in ["scripts/bootstrap.sh", "bootstrap/versions.sh", "bootstrap/download.sh"]:
    if (root / relative).read_bytes() != (
        root / "project-templates/project" / relative
    ).read_bytes():
        raise SystemExit(f"Packaged bootstrap is stale: {relative}")
import runpy

stale_plugin = runpy.run_path(str(root / "scripts/build_workflow_plugin.py"))["drift"](root)
if stale_plugin:
    raise SystemExit(
        "Workflow plugin is stale; run scripts/build_workflow_plugin.py: " + ", ".join(stale_plugin)
    )
