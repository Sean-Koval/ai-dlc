"""Knowledge checks for ``ai-dlc doctor --knowledge`` and ``ai-dlc knowledge doctor``.

Each check is one line: ``pass``, ``fail`` or ``skip``, a name and a detail. A failing
line names the environment variable or the step to fix, never a value: provider
messages are not repeated, as one could carry a token or a page body. Any ``fail``
makes the command exit non-zero.

The checks follow the install (:mod:`ai_dlc.setup.knowledge_install`): the tools on
PATH, the recorded settings, the harness manifest and its drift, the tracker role
fetching one item, the wiki role finding one page, ``knowledge check`` on the clone,
one inbox item, and the pinned versions. Two installs of the same channel print the
same ``versions`` line.
"""

import json
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ai_dlc.documentation import knowledge_records
from ai_dlc.setup import knowledge_install as setup

Line = dict[str, str]
NO_PROJECT = "no ai-dlc.toml at --root; run it in the project that selects the role"


def _line(name: str, status: str, detail: str) -> Line:
    return {"check": name, "status": status, "detail": detail}


def _env_names(config: Mapping[str, Any], provider: str) -> list[str]:
    settings = (config.get("providers") or {}).get(provider) or {}
    names = [settings.get(key) for key in ("token_env", "email_env")]
    return [name for name in names if isinstance(name, str) and name]


def _unset(config: Mapping[str, Any], provider: str, environ: Mapping[str, str]) -> list[str]:
    return [name for name in _env_names(config, provider) if not environ.get(name)]


def check_prerequisites(environ: Mapping[str, str]) -> Line:
    missing = setup.missing_prerequisites(environ)
    if missing:
        return _line("prerequisites", "fail", "not on PATH: " + ", ".join(missing))
    return _line("prerequisites", "pass", ", ".join(setup.PREREQUISITES) + " found")


def check_harness(target: setup.Install, stored: Mapping[str, Any] | None, environ, runner):
    try:
        manifest = json.loads(target.manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _line("harness", "fail", "no harness manifest; run `ai-dlc knowledge install`"), None
    if stored:
        checkout = _harness_checkout(target, str(stored.get("TEAM_HARNESS_REPO", "")))
        if checkout is not None:
            command = setup.harness_command(
                checkout, str(manifest.get("harness", "")), "", target.home, "--check"
            )
            result = runner(
                command, cwd=checkout, env=dict(environ), text=True, capture_output=True
            )
            if result.returncode != 0:
                detail = "drifted or the channel moved; rerun `ai-dlc knowledge install`"
                return _line("harness", "fail", detail), manifest
    name = f"{manifest.get('harness')}@{manifest.get('channel')} r{manifest.get('revision')}"
    return _line("harness", "pass", name + " installed"), manifest


def _harness_checkout(target: setup.Install, source: str) -> Path | None:
    if not source:
        return None
    if not setup.is_url(source):
        path = Path(source).expanduser()
    else:
        path = target.cache_root / "team-harness" / setup.digest(source.strip().rstrip("/"))[:16]
    return path if (path / "scripts" / "install_local.py").is_file() else None


def check_tracker(root: Path, config: Mapping[str, Any] | None, environ: Mapping[str, str]) -> Line:
    if config is None:
        return _line("tracker", "skip", NO_PROJECT)
    provider = (config.get("roles") or {}).get("tracker")
    if not provider:
        return _line("tracker", "skip", "no provider selected for roles.tracker")
    unset = _unset(config, provider, environ)
    if unset:
        return _line("tracker", "fail", "set " + ", ".join(unset))
    from ai_dlc.work.tracker_items import TrackerItems

    try:
        found = TrackerItems(root, config, environ=environ).search(limit=1)
    except Exception:  # noqa: BLE001 - the message may carry a value; name the step
        found = {"status": "failed"}
    if found.get("status") == "ok" and found.get("items"):
        return _line("tracker", "pass", f"{provider} fetched one item")
    names = _env_names(config, provider)
    hint = f"check {', '.join(names)} and " if names else "check "
    return _line("tracker", "fail", f"{provider} fetched nothing; {hint}providers.{provider}")


def check_wiki(root: Path, config: Mapping[str, Any] | None, environ: Mapping[str, str]) -> Line:
    if config is None:
        return _line("wiki", "skip", NO_PROJECT)
    provider = (config.get("roles") or {}).get("wiki")
    if not provider:
        return _line("wiki", "skip", "no provider selected for roles.wiki")
    unset = _unset(config, provider, environ)
    if unset:
        return _line("wiki", "fail", "set " + ", ".join(unset))
    from ai_dlc.providers import Registry

    try:
        registry = Registry(dict(config), root=root, environ=environ)
        pages = registry.invoke(provider, "list_children", {"parent": None})["pages"]
    except Exception:  # noqa: BLE001 - the message may carry a value; name the step
        pages = []
    if pages:
        return _line("wiki", "pass", f"{provider} found one page")
    names = _env_names(config, provider)
    hint = f"check {', '.join(names)} and " if names else "check "
    return _line("wiki", "fail", f"{provider} found no page; {hint}providers.{provider}")


def check_records(checkout: Path | None) -> Line:
    if checkout is None or not (checkout / ".git").exists():
        return _line("knowledge check", "fail", "no knowledge clone; set KNOWLEDGE_CHECKOUT")
    from ai_dlc.documentation.knowledge_check import check_records as run_check

    try:
        result = run_check(checkout)
    except Exception:  # noqa: BLE001
        return _line("knowledge check", "fail", "could not read the clone; run it by hand")
    failures = result.get("failures") or []
    if failures:
        return _line(
            "knowledge check",
            "fail",
            f"{len(failures)} failures; run `ai-dlc knowledge check .` in KNOWLEDGE_CHECKOUT",
        )
    records = result.get("records") or 0
    count = records if isinstance(records, int) else len(records)
    return _line("knowledge check", "pass", f"{count} records pass")


def check_inbox(checkout: Path | None) -> Line:
    if checkout is None or not (checkout / "inbox").is_dir():
        return _line("inbox", "fail", "no inbox/ directory in KNOWLEDGE_CHECKOUT")
    items = sorted(path for path in (checkout / "inbox").rglob("*.md") if path.is_file())
    if not items:
        return _line("inbox", "pass", "empty (0 items)")
    first = items[0].relative_to(checkout).as_posix()
    return _line("inbox", "pass", f"{first} ({len(items)} items)")


def check_versions(checkout: Path | None, manifest: Mapping[str, Any] | None) -> Line:
    pinned = None
    if checkout is not None:
        try:
            parsed = tomllib.loads((checkout / "knowledge.toml").read_text(encoding="utf-8"))
            pinned = (parsed.get("format") or {}).get("version")
        except (OSError, ValueError):
            pinned = None
    manifest = manifest or {}
    digest = str(manifest.get("harness_digest") or "none")
    pin = pinned if pinned is not None else "unpinned"
    harness = f"{manifest.get('harness')}@{manifest.get('channel')} r{manifest.get('revision')}"
    parts = [
        f"format {pin} (ai-dlc reads {knowledge_records.FORMAT_VERSION})",
        f"harness {harness} {digest}",
        f"model {manifest.get('model') or 'unpinned'}",
        f"claude code {manifest.get('runtime_version') or 'unpinned'}",
    ]
    status = "pass" if pinned == knowledge_records.FORMAT_VERSION else "fail"
    if status == "fail":
        parts.append("knowledge.toml [format] version must match")
    return _line("versions", status, "; ".join(parts))


def doctor(
    root: Path,
    config: Mapping[str, Any] | None,
    home: Path,
    environ: Mapping[str, str],
    *,
    runner=None,
) -> dict:
    import subprocess

    runner = runner or subprocess.run
    target = setup.Install.for_home(home, environ)
    stored = setup.read_settings(target)
    lines = [check_prerequisites(environ)]
    if stored is None:
        lines.append(
            _line("settings", "fail", "no install recorded; run `ai-dlc knowledge install`")
        )
        checkout = None
    else:
        lines.append(_line("settings", "pass", f"recorded in {target.settings_path}"))
        location = str(stored.get("KNOWLEDGE_CHECKOUT") or "")
        checkout = Path(location) if location else None
    harness, manifest = check_harness(target, stored, environ, runner)
    lines += [
        harness,
        check_tracker(root, config, environ),
        check_wiki(root, config, environ),
        check_records(checkout),
        check_inbox(checkout),
        check_versions(checkout, manifest),
    ]
    failed = [line["check"] for line in lines if line["status"] == "fail"]
    return {"status": "failed" if failed else "ok", "failed": failed, "lines": lines}


def text(result: Mapping[str, Any]) -> str:
    return "".join(
        f"{line['status']:<4}  {line['check']}: {line['detail']}\n" for line in result["lines"]
    )
