"""Packaged deterministic fixtures and explicitly scoped read-only live health checks.

Isolation is provided by sandbox.test_provider, not by this process. Direct execution
is normal trusted-user execution and is never an isolation substitute.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import httpx

KIT_ROOT = Path("/kit")
FIXTURE_CONFIG = Path("/fixtures/provider.toml")
FIXTURE_TARGETS = {
    "linear": (["tests/test_providers.py"], "linear"),
    "github-issues": (["tests/test_providers.py"], "github_executable"),
    "openspec": (["tests/test_workflow.py"], "openspec or archived_spec or ignored_local_archive"),
    "github": (["tests/test_workflow.py"], "receipt or github_scm or finish_trusts"),
    "scm": (["tests/test_workflow.py"], "receipt or github_scm or finish_trusts"),
    "providers": (["tests/test_providers.py"], None),
    "workflow": (["tests/test_workflow.py"], None),
    "all": (["tests/test_providers.py", "tests/test_workflow.py"], None),
}
UNAVAILABLE_TARGETS = {"github-deployment", "cloudflare", "obsidian", "knowledge"}
LIVE_TARGETS = {"linear", "github-issues"}


def emit(result: dict, code: int) -> int:
    print(json.dumps(result, sort_keys=True))
    return code


def unavailable(name: str, live: bool, reason: str) -> int:
    return emit(
        {
            "provider": name,
            "live": live,
            "passed": False,
            "status": "unavailable",
            "scope": "read-only-health" if live else "offline-fixtures",
            "reason": reason,
            "mutation_conformance": "unavailable",
        },
        2,
    )


def fixture_suite(name: str) -> int:
    paths, expression = FIXTURE_TARGETS[name]
    if any(not (KIT_ROOT / path).is_file() for path in paths):
        return unavailable(
            name, False, "Packaged conformance fixtures are missing; use the built test image"
        )
    with tempfile.TemporaryDirectory(prefix="ai-dlc-conformance-") as temporary:
        scratch = Path(temporary)
        home = scratch / "home"
        home.mkdir()
        # Offline fixtures never inherit user provider credentials or proxy settings.
        env = {
            key: os.environ[key]
            for key in ("PATH", "LANG", "LC_ALL", "VIRTUAL_ENV", "SYSTEMROOT")
            if key in os.environ
        }
        env.update(
            {
                "HOME": str(home),
                "TMPDIR": str(scratch),
                "AI_DLC_TEST_TOKEN": "fake-credential",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                "GIT_CONFIG_NOSYSTEM": "1",
            }
        )
        command = [
            sys.executable,
            "-m",
            "pytest",
            *paths,
            "-q",
            "-p",
            "no:cacheprovider",
            "-o",
            "pythonpath=",
            "--import-mode=importlib",
            "--basetemp",
            str(scratch / "pytest"),
        ]
        if expression:
            command.extend(["-k", expression])
        try:
            result = subprocess.run(
                command,
                cwd=KIT_ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=240,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return unavailable(name, False, f"Fixture runner unavailable: {type(exc).__name__}")
    return emit(
        {
            "provider": name,
            "live": False,
            "scope": "offline-fixtures",
            "passed": result.returncode == 0,
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "mutation_conformance": "fixture-only",
        },
        0 if result.returncode == 0 else 1,
    )


def live_configuration(name: str) -> tuple[dict, str]:
    if not FIXTURE_CONFIG.is_file() or FIXTURE_CONFIG.is_symlink():
        raise ValueError("Live checks require the mounted /fixtures/provider.toml")
    data = tomllib.loads(FIXTURE_CONFIG.read_text())
    workspace = os.environ.get("AI_DLC_SANDBOX_WORKSPACE", "")
    if not workspace or data.get("sandbox_workspace") != workspace:
        raise ValueError("Live fixture must match AI_DLC_SANDBOX_WORKSPACE exactly")
    cfg = data.get("provider", {})
    if cfg.get("kind") != name:
        raise ValueError("Live fixture provider kind must match selected target")
    allowed = (
        {"kind", "token_env", "health_reference", "team_id"}
        if name == "linear"
        else {"kind", "token_env", "health_reference", "repository"}
    )
    if set(cfg) - allowed or set(data) - {"sandbox_workspace", "provider"}:
        raise ValueError("Live fixture contains unsupported configuration fields")
    reference = cfg.get("health_reference")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("An explicit existing health_reference is required")
    credential = cfg.get("token_env")
    if (
        not isinstance(credential, str)
        or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", credential)
        or not os.environ.get(credential)
    ):
        raise ValueError("Explicit live credential environment reference is unavailable")
    if name == "linear" and cfg.get("team_id") != workspace:
        raise ValueError("Linear team_id must be the designated sandbox workspace")
    if name == "github-issues":
        if cfg.get("repository") != workspace or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", workspace
        ):
            raise ValueError("GitHub repository must be the designated sandbox workspace")
        if credential not in {"GH_TOKEN", "GITHUB_TOKEN"}:
            raise ValueError("GitHub health requires GH_TOKEN or GITHUB_TOKEN")
        if not reference.isdigit():
            raise ValueError(
                "GitHub health_reference must be an issue number in the configured repository"
            )
        if not shutil.which("gh"):
            raise ValueError("GitHub CLI is unavailable in this image")
    return cfg, workspace


def live_health(name: str) -> int:
    if name not in LIVE_TARGETS:
        return unavailable(
            name, True, "No live conformance target is implemented for this subsystem"
        )
    try:
        cfg, workspace = live_configuration(name)
    except (ValueError, OSError) as exc:
        return unavailable(name, True, str(exc))
    try:
        if name == "linear":
            from ai_dlc.providers.linear import LinearProvider

            provider = LinearProvider(cfg)
            issue = provider.query(
                "query($id:String!) { issue(id:$id) { id url team { id } } }",
                {"id": cfg["health_reference"]},
            )["issue"]
            if issue["team"]["id"] != workspace or issue["id"] != cfg["health_reference"]:
                raise ValueError("Health issue does not belong to the designated sandbox team")
        else:
            from ai_dlc.providers.github_issues import GitHubIssuesProvider

            issue = GitHubIssuesProvider(cfg).invoke("read", {"reference": cfg["health_reference"]})
            if issue["id"] != cfg["health_reference"] or not issue["url"].startswith(
                f"https://github.com/{workspace}/issues/"
            ):
                raise ValueError(
                    "Health issue does not belong to the designated sandbox repository"
                )
    except (
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
        httpx.HTTPError,
        subprocess.SubprocessError,
    ) as exc:
        return emit(
            {
                "provider": name,
                "live": True,
                "passed": False,
                "status": "failed",
                "scope": "read-only-health",
                "reason": f"{type(exc).__name__}: read-only health verification failed",
                "mutation_conformance": "unavailable",
            },
            1,
        )
    return emit(
        {
            "provider": name,
            "live": True,
            "passed": True,
            "status": "passed",
            "scope": "read-only-health",
            "workspace": workspace,
            "health_reference": issue["id"],
            "mutation_conformance": "unavailable",
            "full_conformance": "unavailable",
        },
        0,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "provider", nargs="?", choices=sorted(set(FIXTURE_TARGETS) | UNAVAILABLE_TARGETS)
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Explicit read-only health check; never mutation conformance",
    )
    parser.add_argument(
        "--list", action="store_true", help="List implemented fixture and live scopes"
    )
    args = parser.parse_args(argv)
    if args.list:
        return emit(
            {
                "fixture_targets": sorted(FIXTURE_TARGETS),
                "live_read_only_targets": sorted(LIVE_TARGETS),
                "unavailable_targets": sorted(UNAVAILABLE_TARGETS),
                "live_mutation_conformance": "unavailable",
            },
            0,
        )
    if not args.provider:
        parser.error("a provider/subsystem target or --list is required")
    if args.live:
        return live_health(args.provider)
    if args.provider not in FIXTURE_TARGETS:
        return unavailable(
            args.provider,
            False,
            "No packaged conformance fixture suite is implemented for this target",
        )
    return fixture_suite(args.provider)


if __name__ == "__main__":
    raise SystemExit(main())
