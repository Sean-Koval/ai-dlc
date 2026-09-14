"""Contained viewport evidence from an explicitly installed Playwright browser."""

import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from ai_dlc.errors import RefusedError, UncertainError
from ai_dlc.files import inside


def _viewports(values):
    result = []
    for value in values:
        match = re.fullmatch(r"([1-9]\d{0,3})x([1-9]\d{0,3})", value)
        if not match or value in result:
            raise RefusedError("Viewports must be unique WIDTHxHEIGHT dimensions (1–9999)")
        result.append(value)
    return result


def _states(values):
    result = []
    seen = set()
    for value in values:
        name, separator, selector = value.partition("=")
        if (
            not separator
            or not selector.strip()
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", name)
            or name in seen
        ):
            raise RefusedError("States must have unique safe NAME=SELECTOR values")
        seen.add(name)
        result.append({"name": name, "selector": selector})
    return result or [{"name": "default", "selector": None}]


def capture_design(root: Path, *, url: str, out: Path | None = None, viewports=None, states=None):
    """Wait for each named visible selector and capture its viewport, without inventing interactions."""
    root = Path(root).resolve()
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise RefusedError("Capture URL must be HTTP(S) without embedded credentials")
    sizes = _viewports(viewports or ["1280x800", "390x844"])
    selected = _states(states or [])
    now = datetime.now(UTC)
    output = (
        Path(out)
        if out is not None
        else Path(".ai-dlc/local/design") / now.strftime("%Y%m%dT%H%M%S%fZ")
    )
    if output.is_absolute():
        try:
            output = output.relative_to(root)
        except ValueError as exc:
            raise RefusedError("Capture output must be inside the project") from exc
    destination = inside(root, str(output))
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise RefusedError(
            "Capture output must be a new or empty directory; preserve prior evidence"
        )
    destination.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD="1", npm_config_offline="true")
    files = []
    for viewport in sizes:
        for state in selected:
            filename = f"{viewport}-{state['name']}.png"
            target = inside(root, str(output / filename))
            args = [
                "npx",
                "--no-install",
                "playwright",
                "screenshot",
                "--browser",
                "chromium",
                "--viewport-size",
                viewport.replace("x", ","),
                "--timeout",
                "30000",
            ]
            if state["selector"]:
                args.extend(["--wait-for-selector", state["selector"]])
            args.extend([url, str(target)])
            try:
                result = subprocess.run(
                    args,
                    cwd=root,
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=60,
                    check=False,
                )
                if result.returncode:
                    raise ValueError(result.stderr.strip() or result.stdout.strip())
                if not target.is_file() or target.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                    raise ValueError("Playwright did not produce a PNG screenshot")
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                raise UncertainError(
                    f"Capture incomplete in {destination}; install Playwright and its browser during setup or resolve the page/selector error: {exc}"
                ) from exc
            files.append(filename)
    manifest = {
        "url": url,
        "captured_at": now.isoformat(),
        "viewports": sizes,
        "states": selected,
        "files": files,
    }
    path = inside(root, str(output / "manifest.json"))
    with path.open("x") as handle:
        handle.write(json.dumps(manifest, indent=2) + "\n")
    return {"status": "captured", "manifest": str(path), "files": files}
