"""Drivers decide what runs inside an attempt; the runner treats every kind the same way."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Protocol

WRITER = "import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(sys.argv[2])"


class Driver(Protocol):
    def environment(self, index: int) -> list[str]:
        """Docker exec environment entries, with credential names only (never values)."""
        ...

    def observe(self, item: dict, index: int, data: bytes, run_dir: Path) -> dict | None:
        """Validate a retained step before the next starts; return metering when available."""
        ...

    def retained(self) -> dict[str, object]:
        """Inputs a rerun needs, by name; each is written under the run's inputs."""
        ...

    def install(self, item: dict) -> list[list[str]]:
        """Commands of the install stage; skipped by the lifecycle in the baseline arm."""
        ...

    def steps(self, item: dict) -> list[list[str]]:
        """Commands of the planned attempt, one turn each."""
        ...


class Deterministic:
    """Fixed steps per arm from a script file. Exercises the runner; measures nothing."""

    def __init__(self, script_path: Path):
        self.base = script_path.parent
        self.script = json.loads(script_path.read_text())

    def retained(self) -> dict[str, object]:
        return {"script": self.script}

    def install(self, item: dict) -> list[list[str]]:
        del item
        return self._argv(self.script.get("install", []))

    def steps(self, item: dict) -> list[list[str]]:
        return self._argv(self.script.get(item["arm"], []))

    def environment(self, index: int) -> list[str]:
        return []

    def observe(self, item: dict, index: int, data: bytes, run_dir: Path) -> dict | None:
        return None

    def _argv(self, declared: list) -> list[list[str]]:
        """A step is an argv list, or {"write": path, "from": file} to place controller-held text."""
        steps = []
        for step in declared:
            if isinstance(step, dict):
                text = (self.base / step["from"]).read_text()
                steps.append(["python", "-c", WRITER, step["write"], text])
            else:
                steps.append([str(part) for part in step])
        return steps


def load_driver(profile: dict, profile_path: Path) -> Driver:
    kind = profile["driver"]["kind"]
    if kind == "deterministic":
        return Deterministic((profile_path.parent / profile["driver"]["script"]).resolve())
    if kind == "claude-code":
        return ClaudeCode()
    raise ValueError(f"Invalid evaluation profile: driver.kind: {kind} has no implementation yet")


TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_json_constant(value: str) -> None:
    raise ValueError("nonstandard JSON constant")


def parse_claude_stream(data: bytes, expected: dict) -> dict:
    """Meter the native final result, never assistant text or partial-message usage.

    Additional event kinds/fields are retained for forward compatibility. Core
    identity, ordering and final metering must be present and internally consistent.
    Errors deliberately never quote stream content (it can contain credentials).
    """
    try:
        events = [
            json.loads(
                line, object_pairs_hook=_unique_object, parse_constant=_invalid_json_constant
            )
            for line in data.decode("utf-8").splitlines()
            if line.strip()
        ]
        if not events or not all(
            isinstance(e, dict) and isinstance(e.get("type"), str) and e["type"] for e in events
        ):
            raise ValueError
        for event in events:
            if event["type"] == "stream_event" and (
                not isinstance(event.get("event"), dict)
                or not isinstance(event["event"].get("type"), str)
            ):
                raise ValueError
            if event["type"] in ("assistant", "user") and not isinstance(
                event.get("message"), dict
            ):
                raise ValueError
        inits = [e for e in events if e["type"] == "system" and e.get("subtype") == "init"]
        finals = [e for e in events if e["type"] == "result"]
        if len(inits) != 1 or len(finals) != 1 or events[-1] is not finals[0]:
            raise ValueError
        init, final = inits[0], finals[0]
        session = init.get("session_id")
        if not isinstance(session, str) or not session.strip():
            raise ValueError
        if (
            init.get("model") != expected["model"]
            or init.get("claude_code_version") != expected["version"]
        ):
            raise ValueError
        if final.get("session_id") != session or any(
            e.get("session_id", session) != session for e in events
        ):
            raise ValueError
        usage = final["usage"]
        tokens = {key: usage[key] for key in TOKEN_FIELDS}
        turns, cost = final["num_turns"], final["total_cost_usd"]
        # Native JavaScript counters must fit its exact integer range.
        if any(type(n) is not int or not 0 <= n <= 2**53 - 1 for n in [turns, *tokens.values()]):
            raise ValueError
        if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
            raise ValueError
        subtype = final["subtype"]
        if not isinstance(subtype, str) or (
            subtype != "success" and not subtype.startswith("error_")
        ):
            raise ValueError
        if type(final.get("is_error")) is not bool:
            raise ValueError
        if (subtype == "success") == final["is_error"]:
            raise ValueError
        return {
            **expected,
            "session_id": session,
            "turns": turns,
            "usage": {**tokens, "total_tokens": sum(tokens.values()), "cost_usd": cost},
            "complete": subtype == "success",
            "result_subtype": subtype,
            "limit": {"error_max_turns": "max_turns", "error_max_budget_usd": "max_spend_usd"}.get(
                subtype
            ),
        }
    except (ValueError, KeyError, TypeError, UnicodeError, OverflowError):
        raise ValueError(
            "Claude Code stream malformed, incomplete, or missing identity/usage"
        ) from None


def _check_version(data: bytes, expected: str) -> None:
    if data.strip() != f"{expected} (Claude Code)".encode():
        raise ValueError("Claude Code version does not match the pinned driver.version")


def retained_client(run_dir: Path, item: dict) -> dict:
    """Revalidate original client evidence when rebuilding reports without execution."""
    try:
        _check_version((run_dir / "client-version.txt").read_bytes(), item["client"]["version"])
        return parse_claude_stream((run_dir / "client-stream.jsonl").read_bytes(), item["client"])
    except OSError:
        raise ValueError("Claude Code version or structured stream unavailable") from None


class ClaudeCode:
    """One native print-mode session inside the isolated agent container."""

    def retained(self) -> dict[str, object]:
        return {}

    def install(self, item: dict) -> list[list[str]]:
        # Guidance selection/adoption belongs to task 7; this stage remains explicit.
        return []

    def steps(self, item: dict) -> list[list[str]]:
        return [
            ["claude", "--version"],
            [
                "claude",
                "-p",
                "--output-format",
                "stream-json",
                "--verbose",
                "--include-partial-messages",
                "--model",
                item["client"]["model"],
                "--max-turns",
                str(item["limits"]["max_turns"]),
                "--max-budget-usd",
                str(item["limits"]["max_spend_usd"]),
                "--permission-mode",
                "bypassPermissions",
                "--no-session-persistence",
                "--setting-sources",
                "project,local",
                "--",
                item["goal"],
            ],
        ]

    def environment(self, index: int) -> list[str]:
        if index == 1:
            return []
        return [
            "ANTHROPIC_API_KEY",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1",
            "DISABLE_AUTOUPDATER=1",
        ]

    def observe(self, item: dict, index: int, data: bytes, run_dir: Path) -> dict | None:
        if index == 1:
            (run_dir / "client-version.txt").write_bytes(data)
            _check_version(data, item["client"]["version"])
            return None
        (run_dir / "client-stream.jsonl").write_bytes(data)
        return parse_claude_stream(data, item["client"])
