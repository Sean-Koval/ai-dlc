"""Select verified native launchers with the installed engine's owned transaction."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from ai_dlc._windows_storage import guarded_path, opened, safe_read
from ai_dlc.harness.windows_render import WindowsRenderState
from ai_dlc.locking import project_write_lock


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def select(home: Path, environment: Path, mode: str, publish: bool) -> dict:
    directory = home / "bin"
    executable = environment / "Scripts/ai-dlc.exe"
    with guarded_path(executable.parent) as parent, opened(executable, parent=parent):
        launcher = safe_read(executable)
        subprocess.run([str(executable), "--version"], check=True)
    with project_write_lock(directory), WindowsRenderState(directory) as state:
        raw = state.read("ai-dlc-selection.json")
        previous = json.loads(raw) if raw else None
        current = state.read("ai-dlc.exe")
        companion = state.read("ai-dlc-cli.exe")
        if previous:
            for name, value in (("ai-dlc.exe", current), ("ai-dlc-cli.exe", companion)):
                if value is not None and digest(value) != previous.get("launcher_sha256"):
                    raise ValueError(
                        f"Selected {name} has authored changes or stale ownership metadata"
                    )
        elif current is not None or companion is not None:
            raise ValueError(
                "Existing launcher has no owned selection metadata; preserve it and choose another bootstrap home"
            )
        working = False
        if current is not None and previous is not None:
            selected_executable = directory / "ai-dlc.exe"
            with guarded_path(directory) as parent, opened(selected_executable, parent=parent):
                if digest(safe_read(selected_executable)) != previous["launcher_sha256"]:
                    raise ValueError("Selected launcher changed before execution")
                working = (
                    subprocess.run(
                        [str(selected_executable), "--version"], capture_output=True, check=False
                    ).returncode
                    == 0
                )
        if mode == "source" and not publish and working:
            repaired = []
            if companion is None and current is not None:
                state.apply({"ai-dlc-cli.exe": current}, [], ["ai-dlc-cli.exe"])
                repaired = ["ai-dlc-cli.exe"]
            else:
                state.verify_files()
            return {
                "published": False,
                "selected": previous,
                "prepared": str(executable),
                "repaired": repaired,
            }
        source_root = environment / "ai-dlc-source-root"
        source_revision = environment / "ai-dlc-source-revision"
        selected = {
            "schema": 1,
            "environment": str(environment),
            "cli": str(executable),
            "mode": mode,
            "source_root": safe_read(source_root).decode().strip() if mode == "source" else None,
            "source_revision": safe_read(source_revision).decode().strip()
            if mode == "source"
            else None,
            "launcher_sha256": digest(launcher),
        }
        planned = {
            "ai-dlc-cli.exe": launcher,
            "ai-dlc.exe": launcher,
            "ai-dlc-selection.json": (json.dumps(selected, indent=2) + "\n").encode(),
        }
        retained = state.apply(planned, [], list(planned))
        return {
            "published": True,
            "selected": selected,
            "prepared": str(executable),
            "retained": retained,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--mode", choices=("source", "release"), required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    print(json.dumps(select(args.home, args.environment, args.mode, args.publish)))
