"""Native package-manager preparation and owned workstation activation."""

import hashlib
import json
import shlex
import shutil
import subprocess
from pathlib import Path

import httpx
import tomli_w

from ai_dlc.agents import _section
from ai_dlc.config import read_toml
from ai_dlc.files import assets, atomic_write


def ensure_brew(root: Path, architecture: str) -> str:
    existing = shutil.which("brew")
    if existing:
        return existing
    prefix = Path("/opt/homebrew" if architecture in {"arm64", "aarch64"} else "/usr/local")
    binary = prefix / "bin/brew"
    if not binary.exists():
        source = read_toml(assets("modules") / "bootstrap.toml")["homebrew"]
        response = httpx.get(source["url"], timeout=60, follow_redirects=True)
        response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest() != source["sha256"]:
            raise ValueError("Homebrew installer digest mismatch; refusing execution")
        installer = root / "homebrew-install.sh"
        atomic_write(installer, response.text)
        # The native installer owns administrator access and interactive confirmation.
        subprocess.run(["/bin/bash", str(installer)], check=True)
    if not binary.is_file():
        raise RuntimeError("Homebrew installation incomplete; retry after native setup")
    return str(binary)


def activate_workstation(
    home: Path,
    tools: dict,
    mise: str,
    bootstrap_bin: Path,
    brew: str | None = None,
    shell: str = "zsh",
) -> dict:
    """Preserve authored values and reject changes to owned values before writing."""
    if shell not in {"bash", "zsh"}:
        return {
            "ready": False,
            "reason": "automatic activation supports bash/zsh; configure mise manually",
        }
    home = home.resolve()
    config_path = home / ".config/mise/config.toml"
    ownership_path = home / ".local/state/ai-dlc/workstation-ownership.json"
    previous = json.loads(ownership_path.read_text()) if ownership_path.exists() else {"tools": {}}
    config = read_toml(config_path) if config_path.exists() else {}
    current = config.setdefault("tools", {})
    for name, value in previous["tools"].items():
        if name in current and current[name] != value:
            raise ValueError(f"workstation runtime conflict: {name}")
    owned = dict(previous["tools"])
    drift = []
    for name, value in tools.items():
        if name in current and current[name] != value:
            # Ordinary setup preserves a working version. Updating the profile is
            # explicit, but replacing a user runtime still requires conflict resolution.
            drift.append({"tool": name, "installed_selection": current[name], "profile": value})
            continue
        if name not in current:
            current[name] = value
            owned[name] = value
    rc = home / (".zshrc" if shell == "zsh" else ".bashrc")
    path = shlex.quote(str(bootstrap_bin)) + ':"$PATH"'
    lines = [f"export PATH={path}"]
    if brew:
        lines.append('eval "$(' + shlex.quote(brew) + ' shellenv)"')
    lines.append('eval "$(' + shlex.quote(mise) + " activate " + shell + ')"')
    rendered_rc = _section(
        rc.read_text() if rc.exists() else "", "\n".join(lines) + "\n", toml=True
    )
    # Validate all conflicts first; each file has one declared owner.
    atomic_write(config_path, tomli_w.dumps(config))
    atomic_write(rc, rendered_rc)
    atomic_write(ownership_path, json.dumps({"tools": owned}, sort_keys=True, indent=2) + "\n")
    return {"ready": not drift, "shell": shell, "runtime_drift": drift, "restart_shell": True}
