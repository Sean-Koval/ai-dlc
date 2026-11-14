"""Session join key: ties an agent session, and its trace, to a ticket and a work ID.

The key is ``aidlc1:<tracker>:<work>:<session>``. Each part is empty or matches
``[A-Za-z0-9._-]{1,100}``, so the key never needs quoting. A session without a
ticket keeps an empty tracker part; one on a branch no work record is bound to
keeps an empty work part. ``docs/design/session-join-key.md`` is the contract
flightdeck and hangar read.

Nothing here asks for input. The session-start hook derives the key from the
branch and the work record bound to it. It writes the key to the client's
environment file and the ignored log ``.ai-dlc/local/sessions/<work>.jsonl``, never
to the tracked record. ``work pr`` puts the logged keys in the PR body and ``work
finish`` copies them into the record once. Commits and PR bodies carry the key as a
``Work-Session:`` line, which :func:`read_session_keys` parses back.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import tomllib
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import tomli_w

VERSION = "aidlc1"
TRAILER = "Work-Session"
ENV_KEY = "AI_DLC_SESSION_KEY"
ENV_TRACKER = "AI_DLC_TRACKER_KEY"
ENV_WORK = "AI_DLC_WORK_ID"
ENV_SESSION = "AI_DLC_SESSION_ID"
# Claude Code reads exported variables from this file into every later Bash call.
CLIENT_ENV_FILE = "CLAUDE_ENV_FILE"

_PART = r"[A-Za-z0-9._-]{0,100}"
_KEY = re.compile(rf"{VERSION}:({_PART}):({_PART}):({_PART})")
_LINE = re.compile(rf"^\s*{TRAILER}:\s*({VERSION}:\S*)\s*$", re.MULTILINE)
_SAFE = re.compile(r"[A-Za-z0-9._-]{1,100}")
# KAN convention: a branch starts with its ticket key (KAN-35-apply-atomic).
_BRANCH_TICKET = re.compile(r"^([A-Z][A-Z0-9]+-\d+)(?:$|[-_/])")


@dataclass(frozen=True)
class SessionKey:
    tracker: str
    work_id: str
    session_id: str

    def __str__(self) -> str:
        return f"{VERSION}:{self.tracker}:{self.work_id}:{self.session_id}"

    @classmethod
    def parse(cls, text: str) -> SessionKey | None:
        """The key in ``text``, or None when it is not exactly one key."""
        match = _KEY.fullmatch(text.strip())
        return cls(*match.groups()) if match else None

    def trailer(self) -> str:
        return f"{TRAILER}: {self}"

    def environment(self) -> dict[str, str]:
        return {
            ENV_KEY: str(self),
            ENV_TRACKER: self.tracker,
            ENV_WORK: self.work_id,
            ENV_SESSION: self.session_id,
        }


def read_session_keys(text: str) -> list[SessionKey]:
    """Every ``Work-Session:`` key in a commit message, PR body or trace note, in order.

    This is the read side for trace review: give it the text and get the ticket,
    work ID and session back. Malformed lines are skipped, duplicates kept once.
    """
    keys: list[SessionKey] = []
    for candidate in _LINE.findall(text or ""):
        key = SessionKey.parse(candidate)
        if key and key not in keys:
            keys.append(key)
    return keys


def current_session_key(env: Mapping[str, str] | None = None) -> SessionKey | None:
    """The key the session-start hook exported, read from the environment."""
    return SessionKey.parse((os.environ if env is None else env).get(ENV_KEY, ""))


def tracker_key(reference: str) -> str:
    """The bare ticket key of a tracker reference: KAN-463 from its browse URL, 15 from an issue URL."""
    reference = (reference or "").strip()
    parsed = urlsplit(reference)
    if parsed.scheme and parsed.netloc:
        segments = [segment for segment in parsed.path.split("/") if segment]
        reference = segments[-1] if segments else ""
    return reference if _SAFE.fullmatch(reference) else ""


def bound_record(root: Path, branch: str) -> tuple[str, dict] | None:
    """The work ID and raw record bound to ``branch``, or None."""
    if not branch:
        return None
    for path in sorted((root / ".ai-dlc/work").glob("*.toml")):
        try:
            raw = tomllib.loads(path.read_text())
        except (OSError, tomllib.TOMLDecodeError):
            continue
        artifacts = raw.get("artifacts", {})
        if isinstance(artifacts, dict) and artifacts.get("branch") == branch:
            return path.stem, raw
    return None


def derive(root: Path, branch: str, session_id: str | None) -> SessionKey:
    """Build the key from the branch and its work record; never raises, never asks.

    The tracker part comes from the record's tracker artifact, else from a ticket
    key that starts the branch name. A missing or unsafe session ID is replaced
    by a fresh one.
    """
    work_id, tracker = "", ""
    found = bound_record(root, branch)
    if found:
        work_id, raw = found
        artifacts = raw.get("artifacts", {})
        tracker = tracker_key(str(artifacts.get("tracker", "")))
    if not tracker:
        match = _BRANCH_TICKET.match(branch or "")
        tracker = match.group(1) if match else ""
    session = (session_id or "").strip()
    if not _SAFE.fullmatch(session):
        session = uuid.uuid4().hex
    return SessionKey(tracker, work_id if _SAFE.fullmatch(work_id) else "", session)


def export_to_client(key: SessionKey, env: Mapping[str, str]) -> bool:
    """Append ``export`` lines to the client's environment file, if it gave one."""
    target = env.get(CLIENT_ENV_FILE)
    if not target:
        return False
    lines = "".join(
        f"export {name}={shlex.quote(value)}\n" for name, value in key.environment().items()
    )
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(lines)
    return True


def local_sessions_path(root: Path, work_id: str) -> Path:
    """The ignored per-work session log the session-start hook appends to."""
    return root / ".ai-dlc/local/sessions" / f"{work_id}.jsonl"


def local_session_keys(root: Path, work_id: str) -> list[str]:
    """Keys logged locally for ``work_id``, oldest first; unreadable lines are skipped."""
    path = local_sessions_path(root, work_id)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    keys: list[str] = []
    for line in lines:
        try:
            value = json.loads(line).get("key", "")
        except (ValueError, AttributeError):
            continue
        key = SessionKey.parse(value) if isinstance(value, str) else None
        if key and key.work_id == work_id and str(key) not in keys:
            keys.append(str(key))
    return keys


def log_session(root: Path, key: SessionKey) -> bool:
    """Append the key to the ignored local log once; the tracked record is never touched."""
    if not key.work_id or str(key) in local_session_keys(root, key.work_id):
        return False
    path = local_sessions_path(root, key.work_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "key": str(key),
        "tracker": key.tracker,
        "work_id": key.work_id,
        "session_id": key.session_id,
        "started_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return True


def collect_into_record(root: Path, work_id: str) -> list[str]:
    """Copy locally logged keys into the record's ``sessions`` list; return those added.

    ``work finish`` calls this once the work completes. Running it again adds nothing.
    """
    from ai_dlc.files import inside
    from ai_dlc.locking import project_write_lock
    from ai_dlc.work.workflow import Work

    logged = local_session_keys(root, work_id)
    if not logged:
        return []
    with project_write_lock(root):
        path = inside(root, f".ai-dlc/work/{work_id}.toml")
        raw = tomllib.loads(path.read_text())
        sessions = list(raw.get("sessions", []))
        added = [key for key in logged if key not in sessions]
        if not added:
            return []
        raw["sessions"] = [*sessions, *added]
        Work.model_validate(raw)
        tmp = path.with_suffix(".toml.tmp")
        tmp.write_text(tomli_w.dumps(raw))
        tmp.replace(path)
    return added


ENV_NAMES = (ENV_KEY, ENV_TRACKER, ENV_WORK, ENV_SESSION)


def start_session(root: Path, branch: str, payload: Mapping, env: Mapping[str, str]) -> str:
    """Session-start step: derive, export and log the key; return the context text.

    When the key or any component variable is already set (by hangar, a parent
    session or anything else), nothing is exported and every value is kept, in
    whatever format it has. The text carries the key on its own
    ``Work-Session:`` line so :func:`read_session_keys` finds it in transcripts.
    """
    if any(name in env for name in ENV_NAMES):
        existing = env.get(ENV_KEY, "")
        key = SessionKey.parse(existing)
        if key is not None:
            _log_quietly(root, key)
            return _context(str(key))
        kept = ", ".join(name for name in ENV_NAMES if name in env)
        text = f"Session join variables already set ({kept}); kept as they are."
        if existing.strip() and existing.isprintable() and not any(c.isspace() for c in existing):
            text += f"\n{TRAILER}: {existing}"
        return text
    session_id = payload.get("session_id")
    key = derive(root, branch, session_id if isinstance(session_id, str) else None)
    export_to_client(key, env)
    _log_quietly(root, key)
    return _context(str(key))


def _context(key: str) -> str:
    return (
        f"Session join key: {key}. End every commit message with this trailer line:\n"
        f"{TRAILER}: {key}"
    )


def _log_quietly(root: Path, key: SessionKey) -> None:
    try:
        log_session(root, key)
    except OSError:
        pass  # an unwritable log keeps the key in the environment only


def pull_request_session_keys(
    work: Mapping, env: Mapping[str, str] | None = None, root: Path | None = None
) -> list[str]:
    """The keys a PR body carries: recorded, locally logged under ``root``, and current.

    A PR opened outside any session still gets one key, with an empty session part.
    """
    keys = [str(k) for k in map(SessionKey.parse, work.get("sessions", [])) if k]
    if root is not None:
        keys += [key for key in local_session_keys(root, work["id"]) if key not in keys]
    current = current_session_key(env)
    if current and current.work_id == work["id"] and str(current) not in keys:
        keys.append(str(current))
    if not keys:
        artifacts = work.get("artifacts", {})
        tracker = tracker_key(str(artifacts.get("tracker", "")))
        if not tracker:
            match = _BRANCH_TICKET.match(str(artifacts.get("branch", "")))
            tracker = match.group(1) if match else ""
        keys.append(str(SessionKey(tracker, work["id"], "")))
    return keys


def find_sessions(root: Path, query: str) -> list[dict]:
    """Work records whose ID, ticket or sessions (recorded or logged) match ``query``.

    ``query`` is a whole key, a session ID, a ticket key or a work ID. Each result
    lists the record's sessions as parsed keys, so a session ID resolves back to
    its ticket.
    """
    wanted = SessionKey.parse(query)
    query = query.strip()
    if not query:
        return []  # a blank query would match every record without a ticket
    results = []
    for path in sorted((root / ".ai-dlc/work").glob("*.toml")):
        try:
            raw = tomllib.loads(path.read_text())
        except (OSError, tomllib.TOMLDecodeError):
            continue
        recorded = [str(k) for k in map(SessionKey.parse, raw.get("sessions", [])) if k]
        logged = [key for key in local_session_keys(root, path.stem) if key not in recorded]
        keys = [k for k in map(SessionKey.parse, [*recorded, *logged]) if k]
        ticket = tracker_key(str(raw.get("artifacts", {}).get("tracker", "")))
        if wanted is not None:
            hit = wanted in keys
        else:
            hit = query in {path.stem, ticket} or any(k.session_id == query for k in keys)
        if hit:
            results.append(
                {
                    "work_id": path.stem,
                    "tracker": ticket,
                    "pr": raw.get("artifacts", {}).get("pr", ""),
                    "sessions": [
                        {
                            "key": str(k),
                            "session_id": k.session_id,
                            "tracker": k.tracker,
                            "recorded": str(k) in recorded,
                        }
                        for k in keys
                    ],
                }
            )
    return results
