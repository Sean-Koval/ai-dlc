"""Optional personal learning continuity through the existing knowledge role."""

import re
from datetime import UTC, datetime
from pathlib import Path

from ai_dlc.documentation.knowledge import Knowledge


def configured_knowledge(config):
    vault = config.get("paths", {}).get("vault")
    if not vault:
        raise ValueError("knowledge unavailable: configure paths.vault")
    return Knowledge(vault)


def recall_work(work, config, registry):
    """Knowledge failures never prevent starting work; recall performs no mutations."""
    try:
        provider = work.get("providers", {}).get("knowledge")
        knowledge = registry.get(provider) if provider else configured_knowledge(config)
        terms = re.findall(r"[\w-]+", work.get("title", ""))
        spec = work.get("artifacts", {}).get("spec", "")
        if spec:
            terms.extend(re.findall(r"[\w-]+", Path(spec).name))
        return knowledge.recall(terms, limit=5)
    except Exception:  # noqa: BLE001 -- optional knowledge must not block work
        return []


def store_learning(service, work, body, result):
    """Persist a retry-stable path before asking the knowledge provider to write."""
    operation_id = service.op_id(work, "learning")
    begun = False
    try:
        record = service.journal.begin(operation_id, {"body": body})
        begun = True
        if record["status"] == "succeeded":
            result["learning"] = record["result"]
            return
        path_id = operation_id + ":path"
        path_record = service.journal.begin(path_id, {})
        if path_record["status"] == "succeeded":
            path = path_record["result"]["path"]
        else:
            day = datetime.now(UTC).date().isoformat()
            path = f"learnings/{day}-{work['id']}.md"
            service.journal.succeed(path_id, {"path": path})
        note = service.role(work, "knowledge", lambda: configured_knowledge(service.config)).note(
            path, body, operation_id
        )
        service.journal.succeed(operation_id, note)
        result["learning"] = note
    except Exception as exc:  # noqa: BLE001 -- completion survives optional provider failures
        if begun:
            service.journal.uncertain(operation_id)
        result["status"] += ",learning_pending"
        result["learning_error"] = str(exc)
