"""Drivers decide what runs inside an attempt; the runner treats every kind the same way."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

WRITER = "import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(sys.argv[2])"


class Driver(Protocol):
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
    raise ValueError(f"Invalid evaluation profile: driver.kind: {kind} has no implementation yet")
