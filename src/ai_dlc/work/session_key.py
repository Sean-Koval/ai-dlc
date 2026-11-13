"""Session join key: ties an agent session, and its trace, to a ticket and a work ID.

The key is ``aidlc1:<tracker>:<work>:<session>``. Each part is empty or matches
``[A-Za-z0-9._-]{1,100}``, so the key never needs quoting. A session without a
ticket keeps an empty tracker part; one on a branch no work record is bound to
keeps an empty work part. ``docs/design/session-join-key.md`` is the contract
flightdeck and hangar read.

Nothing here asks for input: the session-start hook derives the key from the
branch and the work record bound to it, writes it to the client's environment
file and the record, and ``work pr`` puts it in the PR body. Commits and PR bodies
carry it as a ``Work-Session:`` line, which :func:`read_session_keys` parses back.
"""

from __future__ import annotations

import os
import re
import shlex
import tomllib
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
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


def record_session(root: Path, key: SessionKey) -> bool:
    """Add the key to its work record's ``sessions`` list once; False when there is none."""
    from ai_dlc.files import inside
    from ai_dlc.locking import project_write_lock
    from ai_dlc.work.workflow import Work

    if not key.work_id:
        return False
    with project_write_lock(root):
        path = inside(root, f".ai-dlc/work/{key.work_id}.toml")
        raw = tomllib.loads(path.read_text())
        sessions = list(raw.get("sessions", []))
        if str(key) in sessions:
            return False
        raw["sessions"] = [*sessions, str(key)]
        Work.model_validate(raw)
        tmp = path.with_suffix(".toml.tmp")
        tmp.write_text(tomli_w.dumps(raw))
        tmp.replace(path)
    return True


def start_session(root: Path, branch: str, payload: Mapping, env: Mapping[str, str]) -> str:
    """Session-start step: derive, export and record the key; return the context line.

    A key already in the environment (set by hangar or a parent session) is kept.
    """
    key = current_session_key(env)
    if key is None:
        session_id = payload.get("session_id")
        key = derive(root, branch, session_id if isinstance(session_id, str) else None)
        export_to_client(key, env)
    try:
        record_session(root, key)
    except (OSError, ValueError, tomllib.TOMLDecodeError):
        pass  # an unreadable or invalid record keeps the key in the environment only
    return f"Session join key: {key}. End every commit message with the trailer `{key.trailer()}`."


def pull_request_session_keys(work: Mapping, env: Mapping[str, str] | None = None) -> list[str]:
    """The keys a work record's PR body carries: its sessions and the current one.

    A PR opened outside any session still gets one key, with an empty session part.
    """
    keys = [str(k) for k in map(SessionKey.parse, work.get("sessions", [])) if k]
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
    """Work records whose ID, ticket or recorded sessions match ``query``.

    ``query`` is a whole key, a session ID, a ticket key or a work ID. Each result
    lists the record's sessions as parsed keys, so a session ID resolves back to
    its ticket.
    """
    wanted = SessionKey.parse(query)
    query = query.strip()
    results = []
    for path in sorted((root / ".ai-dlc/work").glob("*.toml")):
        try:
            raw = tomllib.loads(path.read_text())
        except (OSError, tomllib.TOMLDecodeError):
            continue
        keys = [k for k in map(SessionKey.parse, raw.get("sessions", [])) if k]
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
                        {"key": str(k), "session_id": k.session_id, "tracker": k.tracker}
                        for k in keys
                    ],
                }
            )
    return results
