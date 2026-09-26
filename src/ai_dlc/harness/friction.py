"""Session friction hints, retained only as ignored local counters and hashes."""

import hashlib
import json
import os
import shlex
from contextlib import contextmanager
from pathlib import Path

from ai_dlc.files import atomic_write, inside
from ai_dlc.locking import project_write_lock


@contextmanager
def _session_lock(root: Path, path: Path):
    if os.name == "nt":
        with project_write_lock(root):
            yield
        return
    import fcntl

    with (inside(root, str(path.with_suffix(".lock").relative_to(root)))).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _responses(value):
    """Unwrap the supported direct, shell stdout, and MCP text result shapes."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    if not isinstance(value, dict):
        return []
    results = [value]
    for key in ("stdout", "structuredContent"):
        if key in value:
            results.extend(_responses(value[key]))
    for item in value.get("content", []) if isinstance(value.get("content"), list) else []:
        if isinstance(item, dict) and item.get("type") == "text":
            results.extend(_responses(item.get("text")))
    return results


def _failed_result(payload, command):
    try:
        words = shlex.split(command)
    except ValueError:
        words = []
    tool = str(payload.get("tool_name", ""))
    is_work = words[:2] == ["ai-dlc", "work"] or tool.rsplit("__", 1)[-1].startswith("work_")
    return any(
        result.get("status") == "blocked"
        or (
            is_work
            and (
                result.get("status") in {"failed", "error"}
                or result.get("exit_code", 0) not in (0, None)
                or result.get("isError") is True
            )
        )
        for result in _responses(payload.get("tool_response"))
    )


def track_friction(root: Path, event: str, payload: dict, result: dict) -> dict:
    identity = payload.get("session_id")
    if event == "session-start" or not isinstance(identity, str) or not identity.strip():
        return result
    session = hashlib.sha256(identity.encode()).hexdigest()
    path = root / ".ai-dlc/local/session" / f"{session}.json"
    try:
        path = inside(root, str(path.relative_to(root)))
        if event == "stop" and not path.exists():
            return result
        path.parent.mkdir(parents=True, exist_ok=True)
        with _session_lock(root, path):
            state: dict = json.loads(path.read_text()) if path.exists() else {"count": 0}
            if event == "stop":
                if state["count"] >= 3 and not payload.get("stop_hook_active"):
                    result["friction"] = (
                        f"This session hit {state['count']} refusals; consider a learning note (`ai-dlc knowledge note learnings/...`)"
                    )
                return result
            data = payload.get("tool_input", {})
            command = data.get("command", data.get("cmd", ""))
            count = int(result.get("decision") == "deny") if event == "pre-tool" else 0
            if command and payload.get("tool_name") in {"Bash", "exec_command"}:
                digest = hashlib.sha256(command.encode()).hexdigest()
                if event == "pre-tool":
                    count += int(state.get("last_command") == digest)
                    state["last_command"] = digest
            count += int(_failed_result(payload, command))
            if count or command:
                state["count"] += count
                atomic_write(path, json.dumps(state))
    except (OSError, ValueError, TypeError, KeyError):
        pass  # Local guidance cannot prevent the actual tool operation.
    return result
