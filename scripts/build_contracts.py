"""Write the generated contract files from their sources (KAN-486).

``contracts/manifest.json`` and the operation schemas are built from ``ai_dlc.contracts``
and the knowledge models; ``scripts/check_generated.py`` checks them. Two pull requests
that each add an operation can still touch the same lines of the manifest. Resolve such
a conflict by keeping either side and running this script on the merged sources; never
merge the JSON by hand.

    uv run --locked --no-sync python scripts/build_contracts.py
"""

import json
from pathlib import Path

from ai_dlc.contracts import PAYLOADS, RESPONSES, ServiceResult, manifest
from ai_dlc.documentation.knowledge_notes import schema as knowledge_note_schema
from ai_dlc.documentation.knowledge_records import schema as knowledge_record_schema

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"


def generated() -> dict[str, object]:
    """Each generated file under ``contracts/`` and its content."""
    files: dict[str, object] = {"manifest.json": manifest()}
    for operation in sorted(PAYLOADS):
        files[f"{operation}.request.schema.json"] = PAYLOADS[operation].model_json_schema()
        files[f"{operation}.response.schema.json"] = RESPONSES[operation].model_json_schema()
    files["service-result.schema.json"] = ServiceResult.model_json_schema()
    files["knowledge-note.schema.json"] = knowledge_note_schema()
    files["knowledge-record.schema.json"] = knowledge_record_schema()
    return files


def main() -> int:
    for name, content in generated().items():
        path = CONTRACTS / name
        if path.is_file() and json.loads(path.read_text(encoding="utf-8")) == content:
            continue  # unchanged; keep the file's own layout
        path.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote contracts/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
