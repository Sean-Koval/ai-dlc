"""Machine preflight: is this laptop ready before any repository is adopted (KAN-363)?

``ai-dlc doctor`` runs it where there is no ``ai-dlc.toml``. It reads PATH, a few
files and environment variables, and never contacts anything unless
``probe_versions`` is set: then it runs fixed ``--version`` probes and
``gh auth status``. Each item that fails names one next action.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ai_dlc.environment.bootstrap import bootstrap_bin

# The CLI each agent client is driven by. Antigravity is a desktop editor with no CLI.
CLIENT_COMMANDS = {"claude-code": "claude", "codex": "codex"}
CLIENT_INSTALL = {
    "claude-code": "Install Claude Code (https://docs.claude.com/en/docs/claude-code/setup), then open a new terminal.",
    "codex": "Install the Codex CLI (`npm install -g @openai/codex`), then open a new terminal.",
}
PROXY_VARIABLES = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")
TOKEN_VARIABLES = ("GITHUB_TOKEN", "MISE_GITHUB_TOKEN", "GH_TOKEN")

Runner = Callable[[list[str], Mapping[str, str]], int]


def _run(argv: list[str], environ: Mapping[str, str]) -> int:
    try:
        return subprocess.run(
            argv,
            env=dict(environ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        ).returncode
    except (OSError, subprocess.TimeoutExpired):
        return 1


def _item(
    item_id: str, status: str, detail: str, next_action: str = "", *, required: bool = True
) -> dict[str, Any]:
    return {
        "id": item_id,
        "status": status,
        "required": required,
        "detail": detail,
        "next_action": next_action or "No action required.",
    }


def _version(name: str, environ: Mapping[str, str], probe: bool) -> str:
    if not probe:
        return ""
    from ai_dlc.environment.version_probes import probe_version

    observed = probe_version(name, environ=environ).get("observed")
    return f" (version {observed})" if observed else " (version not observed)"


def _proxy(value: str) -> str:
    """The proxy's scheme, host and port; credentials in the URL are never shown."""
    parts = urlsplit(value if "://" in value else f"http://{value}")
    host = parts.hostname or "unparsed"
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{host}{port}"


def _python_check(
    which: Callable[[str], str | None], system: str, run: Runner, environ: Mapping[str, str]
) -> dict[str, Any]:
    python = which("python3")
    if python is None:
        return _item(
            "python3",
            "missing",
            "python3 is not on PATH; the workflow plugin's hooks need it",
            "Install Python 3 (on macOS: `xcode-select --install`, or Homebrew `brew install python`).",
        )
    # /usr/bin/python3 is a stub until the Command Line Tools are installed; running it
    # would open an installer dialog, so ask xcode-select instead.
    if (
        system == "Darwin"
        and python == "/usr/bin/python3"
        and run(["xcode-select", "-p"], environ) != 0
    ):
        return _item(
            "python3",
            "missing",
            "/usr/bin/python3 is the Xcode Command Line Tools stub, not a real Python",
            "Run `xcode-select --install`, or install Python with Homebrew, then rerun doctor.",
        )
    return _item("python3", "ready", f"python3 at {python}")


def _gh_checks(
    which: Callable[[str], str | None],
    run: Runner,
    environ: Mapping[str, str],
    probe: bool,
) -> tuple[list[dict[str, Any]], bool]:
    host = environ.get("GH_HOST") or "github.com"
    gh = which("gh")
    if gh is None:
        return [
            _item(
                "gh",
                "missing",
                "gh (GitHub CLI) is not on PATH",
                "Install the GitHub CLI (https://cli.github.com), then run `gh auth login`.",
            )
        ], False
    checks = [_item("gh", "ready", f"gh at {gh}{_version('gh', environ, probe)}")]
    # `gh auth token` reads the stored token locally; `gh auth status` asks the host.
    argv = ["gh", "auth", "status" if probe else "token", "--hostname", host]
    signed_in = run([gh, *argv[1:]], environ) == 0
    checks.append(
        _item(
            "gh-auth",
            "ready" if signed_in else "missing",
            f"gh is signed in to {host}"
            + (" (verified with the host)" if probe and signed_in else "")
            if signed_in
            else f"gh is not signed in to {host}",
            "" if signed_in else f"Run `gh auth login --hostname {host}`.",
        )
    )
    return checks, signed_in


def _client_checks(
    which: Callable[[str], str | None],
    environ: Mapping[str, str],
    clients: list[str] | None,
    probe: bool,
) -> list[dict[str, Any]]:
    selected = list(dict.fromkeys(clients or []))
    checks = []
    for client in selected or list(CLIENT_COMMANDS):
        command = CLIENT_COMMANDS.get(client)
        if command is None:
            checks.append(
                _item(
                    f"client:{client}",
                    "blocked",
                    f"{client} has no command-line client to check",
                    "Select codex or claude-code, or check the client by hand.",
                    required=False,
                )
            )
            continue
        found = which(command)
        checks.append(
            _item(
                f"client:{client}",
                "ready" if found else "missing",
                f"{command} at {found}{_version(command, environ, probe)}"
                if found
                else f"{command} ({client}) is not on PATH",
                "" if found else CLIENT_INSTALL[client],
                required=bool(selected),
            )
        )
    if not selected and not any(item["status"] == "ready" for item in checks):
        # Nothing selected: one installed client is enough, none is a failure.
        checks.append(
            _item(
                "client",
                "missing",
                "no agent client CLI (claude or codex) is on PATH",
                "Install Claude Code or the Codex CLI, or pass --agent-client to check one.",
            )
        )
    return checks


def _bootstrap_check(environ: Mapping[str, str], home: Path) -> dict[str, Any]:
    directory = bootstrap_bin(environ, home)
    entries = [Path(entry) for entry in environ.get("PATH", "").split(os.pathsep) if entry]
    if not directory.is_dir():
        return _item(
            "bootstrap-path",
            "info",
            f"no bootstrap directory at {directory}",
            "Nothing to do if ai-dlc came from `uv sync --locked`; otherwise run "
            "`sh scripts/bootstrap.sh --source` in an ai-dlc checkout.",
            required=False,
        )
    if directory in entries:
        return _item("bootstrap-path", "ready", f"{directory} is on PATH")
    return _item(
        "bootstrap-path",
        "missing",
        f"{directory} is not on PATH",
        "Run `ai-dlc project workspace-init --shell --apply`, then open a new terminal.",
    )


def _network_checks(environ: Mapping[str, str], gh_signed_in: bool) -> list[dict[str, Any]]:
    checks = []
    proxy = next((environ[name] for name in PROXY_VARIABLES if environ.get(name)), "")
    checks.append(
        _item(
            "https-proxy",
            "info",
            f"proxy {_proxy(proxy)}" if proxy else "no HTTPS_PROXY set",
            "" if proxy else "Behind a corporate proxy, set HTTPS_PROXY before bootstrap.",
            required=False,
        )
    )
    cert = environ.get("SSL_CERT_FILE", "")
    if cert and not Path(cert).expanduser().is_file():
        checks.append(
            _item(
                "custom-ca",
                "missing",
                f"SSL_CERT_FILE names {cert}, which does not exist",
                "Point SSL_CERT_FILE at your company's CA bundle, or unset it.",
            )
        )
    else:
        native = environ.get("UV_NATIVE_TLS", "")
        detail = ", ".join(
            part
            for part in (
                f"SSL_CERT_FILE={cert}" if cert else "",
                f"UV_NATIVE_TLS={native}" if native else "",
            )
            if part
        )
        checks.append(
            _item(
                "custom-ca",
                "info",
                detail or "no custom CA set",
                ""
                if detail
                else "If TLS fails behind a proxy, set SSL_CERT_FILE to the company CA bundle or UV_NATIVE_TLS=1.",
                required=False,
            )
        )
    token = next((name for name in TOKEN_VARIABLES if environ.get(name)), "")
    available = bool(token) or gh_signed_in
    checks.append(
        _item(
            "github-token",
            "ready" if available else "warning",
            f"{token} is set"
            if token
            else "gh can supply a token"
            if gh_signed_in
            else "no GitHub token",
            ""
            if available
            else "Set GITHUB_TOKEN or run `gh auth login`, so mise's GitHub downloads are not rate limited.",
            required=False,
        )
    )
    return checks


def machine_preflight(
    root: Path,
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    clients: list[str] | None = None,
    probe_versions: bool = False,
    system: str | None = None,
    run: Runner | None = None,
) -> dict[str, Any]:
    """Offline machine readiness for a directory that is not an ai-dlc project."""
    environment = os.environ if environ is None else environ
    home = home or Path(environment.get("HOME") or Path.home())
    system = system or platform.system()
    run = run or _run
    path = environment.get("PATH", "")

    def which(name: str) -> str | None:
        return shutil.which(name, path=path) if path else None

    git = which("git")
    checks = [
        _item("git", "ready", f"git at {git}{_version('git', environment, probe_versions)}")
        if git
        else _item("git", "missing", "git is not on PATH", "Install git, then rerun doctor.")
    ]
    gh, gh_signed_in = _gh_checks(which, run, environment, probe_versions)
    checks.extend(gh)
    checks.extend(_client_checks(which, environment, clients, probe_versions))
    checks.append(_python_check(which, system, run, environment))
    checks.append(_bootstrap_check(environment, home))
    mise = which("mise")
    checks.append(
        _item(
            "mise",
            "ready" if mise else "info",
            f"mise at {mise}" if mise else "mise is not on PATH",
            "" if mise else "Optional: without mise, setup and checks use the tools on PATH.",
            required=False,
        )
    )
    checks.extend(_network_checks(environment, gh_signed_in))
    blocking = [item for item in checks if item["required"] and item["status"] != "ready"]
    return {
        "schema": 1,
        "mode": "machine-preflight",
        "root": str(Path(root).resolve()),
        "project": False,
        "ready": not blocking,
        "probed": probe_versions,
        "checks": checks,
        "next": (
            blocking[0]["next_action"]
            if blocking
            else "This machine is ready. Adopt a repository with `ai-dlc project adopt --root PATH`."
        ),
    }
