"""Optional personal learning continuity through the existing knowledge role."""

import os
import re
import subprocess
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from ai_dlc.documentation import knowledge_notes
from ai_dlc.documentation.knowledge import Knowledge

REVIEW_AFTER = timedelta(days=90)


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


def resolve_author(interactive: bool) -> str:
    """Name the learning's author from explicit sources only.

    ``AI_DLC_AUTHOR`` (set by agents to ``agent:<client>@<plugin digest>``) wins. A person
    running the CLI is ``human:<gh login>``. Nothing is inferred from another session.
    """
    explicit = os.environ.get("AI_DLC_AUTHOR", "").strip()
    if explicit:
        return explicit if re.match(r"^(human|agent):\S+$", explicit) else f"agent:{explicit}"
    if not interactive:
        return "agent:unknown"
    try:
        login = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "human:unknown"
    return f"human:{login}" if re.fullmatch(r"[A-Za-z0-9-]{1,39}", login) else "human:unknown"


def _sources(work, config, evidence) -> list[dict]:
    repository = config.get("scm", {}).get("repository", "")
    merged = evidence.get("pr-merged") or {}
    pr = merged.get("pr")
    url = (pr.get("html_url") if isinstance(pr, dict) else None) or ""
    reference = str(work.get("artifacts", {}).get("pr", ""))
    if not url and reference.startswith("https://"):
        url = reference
    if not url and reference.isdigit() and repository:
        url = f"https://github.com/{repository}/pull/{reference}"
    sha = merged.get("sha")
    if not url or not sha:
        raise ValueError("learning provenance needs the merged PR URL and merge commit")
    sources = [{"uri": url, "hash": f"git:{sha}"}]
    run_id = (evidence.get("ci-green") or {}).get("run_id")
    if run_id and repository:
        sources.append(
            {"uri": f"https://github.com/{repository}/actions/runs/{run_id}", "hash": f"git:{sha}"}
        )
    return sources


def learning_note(body, work, config, evidence, day, author) -> str:
    """Return the note with knowledge-note frontmatter; supplied fields are never overwritten."""
    start = date.fromisoformat(day)
    supplied, _raw, _body = knowledge_notes.split(body)
    supplied = supplied or {}
    repository = config.get("scm", {}).get("repository")
    defaults = {
        "id": f"learning/{day}-{work['id']}",
        "kind": "learning",
        "scope": "personal",
        "label": "internal",
        # Only computed when needed, so a learning citing its own sources needs no PR URL.
        "sources": supplied.get("sources") or _sources(work, config, evidence),
        "author": author,
        "confidence": "medium",
        "valid_from": start,
        "valid_to": None,
        "review_by": start + REVIEW_AFTER,
        "supersedes": [],
        "work": work["id"],
        **({"repository": repository} if repository else {}),
    }
    note = knowledge_notes.with_missing(body, defaults)
    data, _raw, _body = knowledge_notes.split(note)
    problems = knowledge_notes.errors(data or {})
    if problems:
        raise ValueError("learning frontmatter is invalid: " + "; ".join(problems))
    return note


def store_learning(service, work, body, result, author="agent:unknown"):
    """Persist a retry-stable path and final note before asking the provider to write.

    The input body identifies the operation (a different body conflicts); the generated
    note is journaled with the path, so a retry writes byte-identical content.
    """
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
        saved = path_record["result"] if path_record["status"] == "succeeded" else {}
        if "note" in saved:
            path, note = saved["path"], saved["note"]
        else:
            path = saved.get("path")
            if path is None:
                day = datetime.now(UTC).date().isoformat()
                path = f"learnings/{day}-{work['id']}.md"
            day = Path(path).name[:10]
            note = learning_note(body, work, service.config, result["evidence"], day, author)
            service.journal.succeed(path_id, {"path": path, "note": note})
        note_result = service.role(
            work, "knowledge", lambda: configured_knowledge(service.config)
        ).note(path, note, operation_id)
        service.journal.succeed(operation_id, note_result)
        result["learning"] = note_result
    except Exception as exc:  # noqa: BLE001 -- completion survives optional provider failures
        if begun:
            service.journal.uncertain(operation_id)
        result["status"] += ",learning_pending"
        result["learning_error"] = str(exc)
