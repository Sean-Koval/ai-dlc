"""Bounded hook guidance for explicitly supported tool payloads."""

import hashlib
import shlex
import tomllib
from pathlib import Path


def classify_command(command: str) -> str:
    try:
        words = shlex.split(command)
    except ValueError:
        return "unsupported"
    if any(x in command for x in [";", "&&", "||", "|", "\n", "$(", "`"]):
        return "unsupported"
    if words[:1] == ["rm"]:
        return "destructive"
    if words[:2] == ["git", "reset"] and "--hard" in words[2:]:
        return "destructive"
    if words[:2] == ["git", "clean"] and any(
        flag == "--force" or (flag.startswith("-") and not flag.startswith("--") and "f" in flag)
        for flag in words[2:]
    ):
        return "destructive"
    if words[:2] == ["git", "push"] and any(
        flag in {"-f", "--force", "--delete", "-d", "--mirror"}
        or flag.startswith(("--force-with-lease", ":"))
        for flag in words[2:]
    ):
        return "destructive"
    if words[:2] == ["git", "push"] or words[:3] == ["gh", "pr", "create"]:
        return "bound-operation"
    if words[:1] == ["git"] and "push" in words:
        return "unsupported"
    if words[:1] == ["rm"] or words[:3] in [["git", "reset", "--hard"], ["git", "clean", "-fd"]]:
        return "destructive"
    return "ordinary"


def handle_hook(root: Path, event: str, payload: dict) -> dict:
    if event == "stop":
        if payload.get("stop_hook_active"):
            return {"reminder": False}
        session = str(payload.get("session_id", "unknown"))
        marker = root / ".ai-dlc/local/reminders" / hashlib.sha256(session.encode()).hexdigest()
        if marker.exists():
            return {"reminder": False}
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.touch(exist_ok=False)
        except OSError:
            return {"reminder": False}
        return {
            "reminder": True,
            "message": "Record outcomes and next steps when convenient; unavailable knowledge can remain pending.",
        }
    if event == "session-start":
        return {"context": "Read AGENTS.md and .ai-dlc/work; use ai-dlc context --brief."}
    tool = payload.get("tool_name")
    if tool in {"Edit", "Write"}:
        file_path = payload.get("tool_input", {}).get("file_path", "")
        try:
            relative = Path(file_path).resolve().relative_to(root.resolve())
        except ValueError:
            relative = Path()
        if relative.parts[:2] == ("docs", "specs"):
            return {
                "decision": "allow",
                "warning": "Specification edit: reconcile implementation and reviewed work record before review.",
            }
    if tool not in {"Bash", "exec_command"}:
        return {"decision": "allow", "coverage": "unsupported tool payload"}
    data = payload.get("tool_input", {})
    category = classify_command(data.get("command", data.get("cmd", "")))
    if category == "destructive":
        return {
            "decision": "deny",
            "reason": "Destructive operation denied: this hook cannot request native approval. Review and authorize it through the client's native controls.",
        }
    if category == "bound-operation":
        import subprocess

        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        bound = False
        for record in (root / ".ai-dlc/work").glob("*.toml"):
            value = tomllib.loads(record.read_text())
            artifacts = value.get("artifacts", {})
            if (
                branch
                and artifacts.get("branch") == branch
                and artifacts.get("tracker")
                and value.get("reviewed") is True
            ):
                bound = True
                break
        if not bound:
            return {
                "decision": "deny",
                "reason": "This branch has no reviewed work record linked to a tracker. Run work start first.",
            }
    return {"decision": "allow", "coverage": category}
