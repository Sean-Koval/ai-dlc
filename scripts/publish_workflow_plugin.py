"""Publish the workflow plugin into a team harness directory; offline, never pushes.

    python scripts/publish_workflow_plugin.py --harness-repo PATH --dry-run
    python scripts/publish_workflow_plugin.py --harness-repo PATH --apply

PATH is the harness directory, the one that holds (or will hold) ``harness.lock``,
for example ``examples/team-harness/harnesses/team-default`` in agent-factory. The
script copies ``plugins/ai-dlc-workflow/`` without ``native/`` to
``PATH/plugins/<marketplace>/ai-dlc-workflow/`` with ``--marketplace`` (hangar's
directory-marketplace layout, hangar#221) or ``PATH/plugins/ai-dlc-workflow/`` without it, and ``plugins/ai-dlc-workflow/native/codex/`` to
``PATH/native/codex/ai-dlc-workflow/``, then prints the component ids and digests to
pin. It never edits ``harness.lock``, ``marketplace.json`` or any file it did not
publish: a target directory must be empty or exactly an earlier publication (its
files match the digests that publication's ``plugin.lock.json`` recorded), or the
script refuses. The change reaches the harness repository by pull request; re-pin
with the harness repository's own tooling (``hangar harness freeze`` or its relock
script), which also owns the ``Harness-Digest:`` trailer.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "ai-dlc-workflow"
SOURCE = Path("plugins") / PLUGIN
NATIVE = "native/codex"
PLUGIN_TARGET = Path("plugins") / PLUGIN  # without --marketplace (layout before hangar#221)
NATIVE_TARGET = Path("native/codex") / PLUGIN
LOCK = "plugin.lock.json"
REPOSITORY = "https://github.com/Sean-Koval/ai-dlc"


class Refused(Exception):
    pass


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_workflow_plugin", Path(__file__).with_name("build_workflow_plugin.py")
    )
    if spec is None or spec.loader is None:
        raise Refused("cannot load scripts/build_workflow_plugin.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def files_digest(files: dict[str, bytes]) -> str:
    """hangar's ``harness_lock.files_digest`` (a plugin or skill directory's digest).

    For each file in path-component order: the path, a NUL and the raw SHA-256 of its
    content. Kept byte-compatible so the printed value equals what `hangar harness check`
    recomputes.
    """
    digest = hashlib.sha256()
    for rel in sorted(files, key=lambda r: tuple(r.split("/"))):
        digest.update(rel.encode() + b"\0")
        digest.update(hashlib.sha256(files[rel]).digest())
    return "sha256:" + digest.hexdigest()


def read_tree(directory: Path) -> dict[str, bytes]:
    if not directory.is_dir():
        return {}
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts
    }


def source_files(root: Path) -> tuple[dict[str, bytes], dict[str, bytes]]:
    """(Claude plugin files without native/, Codex files) from a current build."""
    builder = _builder()
    stale = builder.drift(root)
    if stale:
        raise Refused(
            "the plugin build is stale; run scripts/build_workflow_plugin.py first: "
            + ", ".join(stale)
        )
    tree = read_tree(root / SOURCE)
    plugin = {path: data for path, data in tree.items() if not path.startswith("native/")}
    native = {
        path.removeprefix(NATIVE + "/"): data
        for path, data in tree.items()
        if path.startswith(NATIVE + "/")
    }
    return plugin, native


def _previous_lock(plugin_target: dict[str, bytes], where: Path) -> dict:
    try:
        lock = json.loads(plugin_target[LOCK])
    except (KeyError, ValueError) as exc:
        raise Refused(f"{where}/{LOCK} is missing or unreadable") from exc
    if not isinstance(lock, dict) or lock.get("plugin") != PLUGIN:
        raise Refused(f"{where}/{LOCK} does not describe {PLUGIN}")
    return lock


def _legacy_publication(target: dict[str, bytes], lock: dict, where: Path) -> set[str]:
    """Paths of a publication whose lock predates per-file digests (proved by components)."""
    builder = _builder()
    try:
        parts = builder.components(target)
    except KeyError as exc:
        raise Refused(f"{where} lacks a published file: {exc}") from exc
    manifest = json.loads(target.get(".claude-plugin/plugin.json", b"{}"))
    if (
        parts != lock.get("components")
        or builder.sha256(builder.canonical(parts)) != lock.get("content_digest")
        or manifest.get("metadata", {}).get("content_digest") != lock.get("content_digest")
    ):
        raise Refused(f"{where} was edited after publication; refusing to overwrite")
    owned = {f"skills/{name}/SKILL.md" for name in builder.TEAM_SKILLS}
    owned |= {f"skills/{builder.GUIDE}/SKILL.md", "hooks/hooks.json", "hooks/aidlc_hook.py"}
    owned |= {".claude-plugin/plugin.json", "README.md", LOCK}
    unknown = sorted(set(target) - owned)
    if unknown:
        raise Refused(f"{where} holds files it did not publish: {', '.join(unknown)}")
    return owned


def _verify(name: Path, target: dict[str, bytes], recorded: dict[str, str]) -> None:
    unknown = sorted(set(target) - set(recorded))
    if unknown:
        raise Refused(f"{name} holds files it did not publish: {', '.join(unknown)}")
    edited = sorted(path for path, data in target.items() if sha256(data) != recorded[path])
    if edited:
        raise Refused(f"{name} was edited after publication: {', '.join(edited)}")


def target_for(marketplace: str | None) -> Path:
    """Where the Claude plugin goes: ``plugins/<marketplace>/ai-dlc-workflow`` (hangar#221's directory
    marketplace) or, without a marketplace, ``plugins/ai-dlc-workflow``."""
    if marketplace is None:
        return PLUGIN_TARGET
    if not marketplace or "/" in marketplace or marketplace.startswith("."):
        raise Refused(f"invalid marketplace name: {marketplace!r}")
    return Path("plugins") / marketplace / PLUGIN


def marketplace_entry(harness: Path, marketplace: str | None) -> dict:
    """The entry to list the plugin under; the harness's own entry when it already has one."""
    suggested = {
        "name": PLUGIN,
        "source": f"./{PLUGIN}" if marketplace else f"./{PLUGIN_TARGET.as_posix()}",
        "defaultEnabled": False,
    }
    if marketplace is None:
        return suggested
    try:
        data = json.loads(
            (harness / "plugins" / marketplace / ".claude-plugin/marketplace.json").read_text()
        )
        entries = [e for e in data.get("plugins", []) if isinstance(e, dict)]
    except (OSError, ValueError, AttributeError):
        return suggested
    return next((e for e in entries if e.get("name") == PLUGIN), suggested)


def plugin_digest(entry: dict, files: dict[str, bytes]) -> str:
    """hangar's plugin digest (``plugins.content_digest``): the entry as canonical JSON, a newline,
    and the directory's ``files_digest``."""
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    return sha256(f"{canonical}\n{files_digest(files)}".encode())


def owned_paths(harness: Path, target: Path = PLUGIN_TARGET) -> tuple[set[str], set[str]]:
    """Files an earlier publication created (and may replace), or refuse."""
    plugin_target = read_tree(harness / target)
    native_target = read_tree(harness / NATIVE_TARGET)
    if not plugin_target:
        if native_target:
            raise Refused(f"{NATIVE_TARGET} exists without {target}; refusing")
        return set(), set()
    lock = _previous_lock(plugin_target, target)
    if "files" not in lock:
        if native_target:
            raise Refused(f"{NATIVE_TARGET} predates per-file digests; refusing")
        return _legacy_publication(plugin_target, lock, target), set()
    published = {path: data for path, data in plugin_target.items() if path != LOCK}
    _verify(target, published, lock["files"])
    native_recorded = lock.get("native", {}).get("codex", {}).get("files", {})
    _verify(NATIVE_TARGET, native_target, native_recorded)
    return set(plugin_target), set(native_target)


def plan(root: Path, harness: Path, marketplace: str | None = None) -> dict:
    plugin, native = source_files(root)
    target = target_for(marketplace)
    plugin_owned, native_owned = owned_paths(harness, target)
    entry = marketplace_entry(harness, marketplace)
    changes = []
    for base, files, owned in [
        (target, plugin, plugin_owned),
        (NATIVE_TARGET, native, native_owned),
    ]:
        current = read_tree(harness / base)
        for path, data in files.items():
            if current.get(path) != data:
                changes.append({"action": "write", "path": (base / path).as_posix(), "data": data})
        for path in sorted(owned - set(files)):
            changes.append({"action": "remove", "path": (base / path).as_posix()})
    lock = json.loads(plugin[LOCK])
    skills = {
        path.split("/")[1]: data
        for path, data in plugin.items()
        if path.startswith("skills/") and path.endswith("/SKILL.md")
    }
    components = [
        {
            "id": f"plugin:{PLUGIN}@{lock['content_digest']}",
            "path": target.as_posix(),
            "content_digest": lock["content_digest"],
            "hangar_files_digest": files_digest(plugin),
            **(
                {
                    "lock_id": f"plugin:{PLUGIN}@{marketplace}",
                    "hangar_plugin_digest": plugin_digest(entry, plugin),
                }
                if marketplace
                else {}
            ),
        },
        *(
            {
                "id": f"skill:{name}@{sha256(data)}",
                "hangar_files_digest": files_digest({"SKILL.md": data}),
            }
            for name, data in sorted(skills.items())
        ),
        *(
            {
                "id": f"native:codex/{PLUGIN}/{path}",
                "path": (NATIVE_TARGET / path).as_posix(),
                "digest": sha256(data),
            }
            for path, data in sorted(native.items())
        ),
    ]
    return {
        "harness": str(harness),
        "revision": lock["revision"],
        "source": source_reference(root),
        "changes": changes,
        "components": components,
        "plugin_path": target.as_posix(),
        "marketplace_entry": entry,
        "notes": [
            "plugin.json `version` overrides a marketplace entry's version.",
            "Keep `plugins.autoUpdate: false` in the harness lock for experiment sandboxes.",
            (
                "Re-pin with the harness repository's tooling (hangar harness freeze or its "
                "relock script); it computes the lock's digests and the Harness-Digest trailer."
            ),
        ],
    }


def source_reference(root: Path) -> str:
    """``git:<repository>#plugins/ai-dlc-workflow@<commit>`` for the harness lock's ``source``."""
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--", SOURCE.as_posix()],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    suffix = "+dirty" if dirty else ""
    return f"git:{REPOSITORY}#{SOURCE.as_posix()}@{commit}{suffix}"


def apply(harness: Path, changes: list[dict], target: Path = PLUGIN_TARGET) -> None:
    for change in changes:
        target = harness / change["path"]
        if change["action"] == "remove":
            target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(change["data"])
    for base in (target, NATIVE_TARGET):
        directory = harness / base
        for folder in sorted(directory.rglob("*"), reverse=True) if directory.is_dir() else []:
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()


def report(result: dict, applied: bool) -> dict:
    changes = [{"action": c["action"], "path": c["path"]} for c in result["changes"]]
    return {
        **result,
        "changes": changes,
        "status": ("applied" if applied else "planned") if changes else "unchanged",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--harness-repo", type=Path, required=True, help="harness directory")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--marketplace",
        help="publish into plugins/<marketplace>/ai-dlc-workflow (hangar#221's directory marketplace)",
    )
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    harness = args.harness_repo.resolve()
    if harness.exists() and not harness.is_dir():
        print(f"Publish refused: {harness} is not a directory", file=sys.stderr)
        return 1
    try:
        result = plan(args.root, harness, args.marketplace)
        if args.apply:
            apply(harness, result["changes"], target_for(args.marketplace))
    except (Refused, OSError, ValueError) as exc:
        print(f"Publish refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report(result, args.apply), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
