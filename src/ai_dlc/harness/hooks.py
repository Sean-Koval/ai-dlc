"""Bounded hook guidance for explicitly supported tool payloads."""

import hashlib
import os
import shlex
import stat
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


SESSION_INSTRUCTION = "Read AGENTS.md and .ai-dlc/work; run ai-dlc next for the full summary."
SESSION_SUMMARY_LINES = 10


def session_context(root: Path) -> str:
    """The instruction plus the first lines of the offline summary; never blocks a session."""
    from ai_dlc.work.summary import next_text

    try:
        lines = next_text(root).splitlines()[:SESSION_SUMMARY_LINES]
    except (OSError, ValueError):
        # A missing project or unreadable configuration still gets the plain instruction.
        return SESSION_INSTRUCTION
    return "\n".join([SESSION_INSTRUCTION, *lines])


def handle_hook(root: Path, event: str, payload: dict) -> dict:
    from ai_dlc.harness.friction import track_friction

    return track_friction(root, event, payload, _handle_hook(root, event, payload))


def _session_recall(root: Path) -> list[dict]:
    from ai_dlc.config import resolve_runtime
    from ai_dlc.documentation.learnings import recall_work
    from ai_dlc.files import run_git
    from ai_dlc.providers import Registry

    try:
        branch = run_git(root, "branch", "--show-current", check=False).stdout.strip()
        config = resolve_runtime(root).values
        registry = Registry(config, root=root)
        for path in sorted((root / ".ai-dlc/work").glob("*.toml")):
            work = tomllib.loads(path.read_text())
            if branch and work.get("artifacts", {}).get("branch") == branch:
                return recall_work(work, config, registry)
    except Exception:  # noqa: BLE001 -- session context remains optional
        return []
    return []


def _bound_operation_decision(root: Path) -> dict[str, str]:
    """Apply the project push policy from a complete offline work inventory."""
    from ai_dlc.config import resolve_runtime
    from ai_dlc.files import inside, run_git
    from ai_dlc.work.workflow import resolve_work, validate_work

    try:
        branch_result = run_git(root, "branch", "--show-current", check=False)
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "decision": "deny",
            "reason": f"Cannot establish the current branch for this operation: {exc}",
        }
    branch = branch_result.stdout.strip()
    if branch_result.returncode or not branch:
        return {
            "decision": "deny",
            "reason": "Cannot establish the current branch for this operation. Check out a named branch and retry.",
        }

    try:
        config = resolve_runtime(root).values
    except (OSError, TypeError, ValueError) as exc:
        return {
            "decision": "deny",
            "reason": f"Cannot resolve the project bound-push policy: {exc}",
        }
    policy = config.get("agents", {}).get("bound_push_policy", "all-branches")
    if policy not in {"all-branches", "tracked-branches"}:
        return {
            "decision": "deny",
            "reason": (
                f"Invalid bound-push policy {policy!r}; choose 'all-branches' or "
                "'tracked-branches' in project configuration."
            ),
        }

    relative_inventory = ".ai-dlc/work"
    try:
        inventory = inside(root, relative_inventory)
        if inventory.is_symlink():
            raise ValueError("the work inventory directory is a symlink")
        if not inventory.exists():
            names: list[str] = []
        else:
            if not inventory.is_dir():
                raise ValueError("the work inventory path is not a directory")
            with os.scandir(inventory) as entries:
                names = sorted(entry.name for entry in entries if entry.name.endswith(".toml"))
    except (OSError, ValueError) as exc:
        return {
            "decision": "deny",
            "reason": f"Cannot read the complete work inventory at {relative_inventory}: {exc}",
        }

    matching: list[str] = []
    for name in names:
        work_id = Path(name).stem
        try:
            path = inside(root, f"{relative_inventory}/{name}")
            if not stat.S_ISREG(path.stat(follow_symlinks=False).st_mode):
                raise ValueError("entry is not a regular file")
            raw = tomllib.loads(path.read_text())
        except (OSError, TypeError, ValueError) as exc:
            return {
                "decision": "deny",
                "reason": f"Cannot read work inventory entry {name}: {exc}. Repair the inventory and retry.",
            }
        artifacts = raw.get("artifacts", {})
        if not isinstance(artifacts, dict):
            return {
                "decision": "deny",
                "reason": (
                    f"Work inventory entry {name} has malformed artifacts and its branch "
                    "association cannot be established."
                ),
            }
        if "branch" not in artifacts:
            continue
        record_branch = artifacts["branch"]
        if not isinstance(record_branch, str) or not record_branch.strip():
            return {
                "decision": "deny",
                "reason": (
                    f"Work inventory entry {name} has malformed artifacts.branch; repair the "
                    "record and retry."
                ),
            }
        if record_branch != branch:
            continue

        matching.append(work_id)
        try:
            work = resolve_work(raw, config, work_id)
        except AttributeError:
            return {
                "decision": "deny",
                "reason": (
                    f"Work {work_id} has malformed work data; providers must be a table. "
                    f"Repair .ai-dlc/work/{work_id}.toml and retry."
                ),
            }
        except (OSError, TypeError, ValueError) as exc:
            return {
                "decision": "deny",
                "reason": f"Work {work_id} is invalid for this branch: {exc}",
            }
        try:
            validation = validate_work(root, config, work_id)
        except AttributeError:
            return {
                "decision": "deny",
                "reason": (
                    f"Work {work_id} or its dependency closure has malformed work data; "
                    "providers must be a table. Repair the affected .ai-dlc/work record and retry."
                ),
            }
        except (OSError, TypeError, ValueError) as exc:
            return {
                "decision": "deny",
                "reason": f"Work {work_id} is invalid for this branch: {exc}",
            }
        if not validation["valid"]:
            detail = "; ".join(validation["errors"])
            return {
                "decision": "deny",
                "reason": f"Work {work_id} is invalid for this branch: {detail}",
            }
        if work["reviewed"] is not True:
            return {
                "decision": "deny",
                "reason": f"Work {work_id} must be reviewed before this bound operation.",
            }
        tracker = work["artifacts"].get("tracker")
        if not isinstance(tracker, str) or not tracker.strip():
            return {
                "decision": "deny",
                "reason": f"Work {work_id} must have a nonblank tracker reference before this bound operation.",
            }

    if matching:
        return {"decision": "allow", "coverage": "bound-operation"}
    if policy == "tracked-branches":
        return {
            "decision": "allow",
            "coverage": "bound-operation",
            "reason": (
                "The tracked-branches policy allows this covered nondestructive operation because "
                "the complete local inventory has no local work record for the current branch."
            ),
        }
    return {
        "decision": "deny",
        "reason": (
            "The all-branches bound-push policy requires a reviewed work record linked to a "
            "tracker. Run work start first."
        ),
    }


def _handle_hook(root: Path, event: str, payload: dict) -> dict:
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
        from ai_dlc.environment.team_sources import source_update_notices

        context = session_context(root)
        notices = source_update_notices()
        if notices:
            context += "\n" + "\n".join(notices)
        recalled = _session_recall(root)
        if recalled:
            context += "\nRelevant learnings (read these notes):\n" + "\n".join(
                f"{note['path']}: {note['first_line']}" for note in recalled
            )
        return {"context": context}
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
        return _bound_operation_decision(root)
    return {"decision": "allow", "coverage": category}
