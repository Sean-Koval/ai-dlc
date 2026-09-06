"""Deterministic project guidance and client-owned configuration sections."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import tomli_w

from ai_dlc import workflow_bundles as bundle_fs
from ai_dlc.components import load_component_catalog, resolve_components
from ai_dlc.config import load_project
from ai_dlc.files import assets, atomic_write, inside
from ai_dlc.locking import project_write_lock
from ai_dlc.workflow_bundles import MissingBundlePath, load_vendored_bundle

_BUNDLE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BUNDLE_PREFIXES = (".agents/skills/", ".claude/skills/", "docs/templates/")
_Snapshot = tuple[bytes, os.stat_result]


def _read_render_file(parent: int, name: str) -> _Snapshot | None:
    try:
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("render destination must be a regular file")
    descriptor = os.open(name, bundle_fs._FILE_FLAGS | os.O_NONBLOCK, dir_fd=parent)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not bundle_fs._same_object(before, opened):
            raise ValueError("render destination changed during planning")
        content = stream.read()
        after = os.fstat(stream.fileno())
    named = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if bundle_fs._identity(before) != bundle_fs._identity(after) or bundle_fs._identity(
        after
    ) != bundle_fs._identity(named):
        raise ValueError("render destination changed during planning")
    return content, after


def _matches_render_file(current: _Snapshot | None, expected: _Snapshot | None) -> bool:
    if current is None or expected is None:
        return current is expected
    content, metadata = current
    old_content, old_metadata = expected
    # Renaming an owned file changes ctime; inode, bytes, mode and mtime remain bound.
    return (
        content == old_content
        and bundle_fs._same_object(metadata, old_metadata)
        and metadata.st_mode == old_metadata.st_mode
        and metadata.st_mtime_ns == old_metadata.st_mtime_ns
    )


class _RenderState:
    """Keep the files and directory identities observed by the render planner."""

    def __init__(self, absolute: Path, project_parent: int, root: int) -> None:
        self.absolute = absolute
        self.project_parent = project_parent
        self.root = root
        self.directories: dict[str, int | None] = {"": root}
        self.snapshots: dict[str, _Snapshot | None] = {}
        self.created: list[str] = []

    def parent(self, name: str, *, create: bool = False) -> int | None:
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or name != relative.as_posix():
            raise ValueError("invalid render destination path")
        parent = self.root
        for index, part in enumerate(relative.parts[:-1]):
            key = PurePosixPath(*relative.parts[: index + 1]).as_posix()
            if key not in self.directories:
                try:
                    self.directories[key] = bundle_fs._open_named_directory(parent, part)
                except FileNotFoundError:
                    self.directories[key] = None
            child = self.directories[key]
            if child is None:
                if not create:
                    return None
                child, created = bundle_fs._ensure_named_directory(parent, part)
                if not created:
                    os.close(child)
                    raise ValueError("render destination ancestor changed after planning")
                self.directories[key] = child
                self.created.append(key)
            bundle_fs._verify_named_directory(parent, part, child)
            parent = child
        return parent

    def read(self, name: str) -> bytes | None:
        if name not in self.snapshots:
            parent = self.parent(name)
            self.snapshots[name] = (
                _read_render_file(parent, PurePosixPath(name).name) if parent is not None else None
            )
        snapshot = self.snapshots[name]
        return snapshot[0] if snapshot is not None else None

    def verify_directories(self) -> None:
        bundle_fs._verify_project_path(self.absolute, self.project_parent, self.root)
        for name, descriptor in self.directories.items():
            if not name:
                continue
            relative = PurePosixPath(name)
            parent_name = relative.parent.as_posix() if len(relative.parts) > 1 else ""
            parent = self.directories[parent_name]
            if parent is None:
                continue
            if descriptor is not None:
                bundle_fs._verify_named_directory(parent, relative.name, descriptor)
            else:
                try:
                    os.stat(relative.name, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                raise ValueError("render destination ancestor changed after planning")

    def verify_files(self) -> None:
        self.verify_directories()
        for name, expected in self.snapshots.items():
            parent = self.parent(name)
            current = (
                _read_render_file(parent, PurePosixPath(name).name) if parent is not None else None
            )
            if not _matches_render_file(current, expected):
                raise ValueError(f"render destination changed after planning: {name}")

    def close(self) -> None:
        for name, descriptor in reversed(list(self.directories.items())):
            if name and descriptor is not None:
                os.close(descriptor)


@dataclass
class _RenderChange:
    path: str
    parent: int
    before: _Snapshot | None
    backup: str | None = None
    stage: str | None = None
    published: _Snapshot | None = None
    mutated: bool = False

    @property
    def name(self) -> str:
        return PurePosixPath(self.path).name


def _stage_render_file(parent: int, content: bytes, mode: int) -> str:
    name = f".ai-dlc-{secrets.token_hex(12)}"
    descriptor = os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
        dir_fd=parent,
    )
    created = os.fstat(descriptor)
    try:
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not bundle_fs._same_object(named, created):
            raise OSError("render staging file changed")
    except BaseException:
        for _ in range(2):
            try:
                named = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if bundle_fs._same_object(named, created):
                    os.unlink(name, dir_fd=parent)
                break
            except OSError:
                continue
        raise
    finally:
        os.close(descriptor)
    return name


def _publish_render_change(
    state: _RenderState, change: _RenderChange, content: bytes | None
) -> None:
    state.verify_directories()
    if content is not None:
        mode = stat.S_IMODE(change.before[1].st_mode) if change.before is not None else 0o644
        change.stage = _stage_render_file(change.parent, content, mode)
    state.verify_directories()
    if not _matches_render_file(_read_render_file(change.parent, change.name), change.before):
        raise ValueError(f"render destination changed after planning: {change.path}")
    if change.before is not None:
        backup = f".ai-dlc-{secrets.token_hex(12)}"
        bundle_fs._rename_directory_noreplace(change.parent, change.name, backup)
        change.backup = backup
        change.mutated = True
        if not _matches_render_file(_read_render_file(change.parent, backup), change.before):
            raise ValueError(f"render destination changed during publication: {change.path}")
    state.verify_directories()
    if change.stage is not None:
        staged = _read_render_file(change.parent, change.stage)
        bundle_fs._rename_directory_noreplace(change.parent, change.stage, change.name)
        change.stage = None
        change.published = staged
        change.mutated = True
        if not _matches_render_file(_read_render_file(change.parent, change.name), staged):
            raise ValueError(f"render destination changed during publication: {change.path}")
    state.verify_directories()


def _restore_render_change(change: _RenderChange) -> None:
    if change.published is not None:
        current = _read_render_file(change.parent, change.name)
        if not _matches_render_file(current, change.published):
            raise OSError("render recovery preserved a late authored edit")
        displaced = f".ai-dlc-{secrets.token_hex(12)}"
        bundle_fs._rename_directory_noreplace(change.parent, change.name, displaced)
        captured = _read_render_file(change.parent, displaced)
        if not _matches_render_file(captured, change.published):
            bundle_fs._rename_directory_noreplace(change.parent, displaced, change.name)
            raise OSError("render recovery preserved a late authored edit")
        change.stage = displaced
        change.published = None
    if change.backup is not None:
        bundle_fs._rename_directory_noreplace(change.parent, change.backup, change.name)
        change.backup = None
    elif (
        change.mutated
        and change.before is not None
        and _read_render_file(change.parent, change.name) is None
    ):
        content, metadata = change.before
        recovery = _stage_render_file(change.parent, content, stat.S_IMODE(metadata.st_mode))
        change.backup = recovery
        bundle_fs._rename_directory_noreplace(change.parent, recovery, change.name)
        change.backup = None
    if change.stage is not None:
        os.unlink(change.stage, dir_fd=change.parent)
        change.stage = None


def _section(current: str, body: str, toml: bool = False) -> str:
    start = "# ai-dlc:begin " if toml else "<!-- ai-dlc:begin "
    end = "# ai-dlc:end" if toml else "<!-- ai-dlc:end -->"
    suffix = "" if toml else " -->"
    pattern = re.compile(
        re.escape(start) + r"([0-9a-f]{64})" + re.escape(suffix) + r"\n(.*?)" + re.escape(end),
        re.DOTALL,
    )
    matches = list(pattern.finditer(current))
    if len(matches) > 1 or (start in current and not matches):
        raise ValueError("managed section conflict: malformed markers")
    new = start + hashlib.sha256(body.encode()).hexdigest() + suffix + "\n" + body + end
    if matches:
        match = matches[0]
        if hashlib.sha256(match.group(2).encode()).hexdigest() != match.group(1):
            raise ValueError(
                "managed section conflict: preserve user edit and resolve before apply"
            )
        return current[: match.start()] + new + current[match.end() :]
    return current.rstrip() + ("\n\n" if current else "") + new + "\n"


def provider_index(resolved: dict) -> tuple[str, dict[str, str]]:
    """Build portable links and owned copies from validated component requirements."""
    base = assets("agents")
    builtins = {
        item["id"]
        for item in json.loads((assets("modules") / "components.json").read_text())["components"]
    }
    lines = [(base / "templates/provider-index.md").read_text().rstrip(), ""]
    copies = {}
    for component in resolved["components"]:
        links = []
        for guidance in component["guidance"]:
            if component["id"] in builtins:
                destination = ".ai-dlc/" + guidance
                copies[destination] = inside(base, guidance).read_text()
            else:
                destination = guidance
            links.append(f"[{guidance}](<{destination}>)")
        modules = ", ".join(component["modules"]) or "none"
        lines.append(
            f"- {component['role']}: {component['provider']} (modules: {modules}); "
            + (", ".join(links) or "no component instructions declared")
        )
    for item in resolved["unresolved"]:
        lines.append(f"- {item['role']}: {item['provider']}; unsupported: {item['reason']}")
    return "\n".join(lines) + "\n", copies


def provider_guidance_ready(root: Path, index: str, copies: dict[str, str], client: str) -> bool:
    """Check that the supported harness can reach intact configured instructions."""
    try:
        for filename, expected in [
            ("AGENTS.md", index),
            *([("CLAUDE.md", "@AGENTS.md\n")] if client == "claude-code" else []),
        ]:
            current = inside(root, filename).read_text()
            if (
                current.count("<!-- ai-dlc:begin ") != 1
                or current.count("<!-- ai-dlc:end -->") != 1
            ):
                return False
            match = re.search(
                r"<!-- ai-dlc:begin ([0-9a-f]{64}) -->\n(.*?)<!-- ai-dlc:end -->",
                current,
                re.DOTALL,
            )
            if not match or expected not in match.group(2):
                return False
            if hashlib.sha256(match.group(2).encode()).hexdigest() != match.group(1):
                return False
        for name, body in copies.items():
            if inside(root, name).read_text() != body:
                return False
    except (OSError, ValueError):
        return False
    return True


def _selected_bundle_ids(config: dict[str, Any]) -> list[str]:
    selected = config.get("agents", {}).get("bundles", [])
    if not isinstance(selected, list) or not all(
        isinstance(bundle_id, str) and _BUNDLE_ID.fullmatch(bundle_id) for bundle_id in selected
    ):
        raise ValueError("agents.bundles must be a list of bundle-ID slugs")
    if len(set(selected)) != len(selected):
        raise ValueError("agents.bundles must not contain duplicate IDs")
    return sorted(selected)


def _load_selected_bundles(root: Path, bundle_ids: list[str]) -> dict[str, dict[str, Any]]:
    bundles: dict[str, dict[str, Any]] = {}
    for bundle_id in bundle_ids:
        try:
            bundles[bundle_id] = load_vendored_bundle(root, bundle_id)
        except ValueError as exc:
            raise ValueError(f"selected bundle {bundle_id} is invalid: {exc}") from exc
    return bundles


def _shipped_skill_names() -> set[str]:
    lock = json.loads((assets("agents") / "skills.lock.json").read_text())
    return set(lock["skills"])


def _bundle_collision_details(bundles: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    details = {bundle_id: [] for bundle_id in bundles}
    claims: dict[str, list[tuple[str, str]]] = {}
    shipped = _shipped_skill_names()
    for bundle_id, bundle in bundles.items():
        manifest = bundle["manifest"]
        for kind in ("skills", "templates"):
            for name in manifest[kind]:
                claims.setdefault(name, []).append((bundle_id, kind[:-1]))
                if kind == "skills" and name in shipped:
                    details[bundle_id].append(
                        f"bundle skill export collision with shipped skill: {name}"
                    )
    for name, owners in claims.items():
        if len(owners) < 2:
            continue
        claimants = ", ".join(sorted(bundle_id for bundle_id, _ in owners))
        for bundle_id, _ in owners:
            details[bundle_id].append(
                f"bundle export collision for {name} among selected bundles: {claimants}"
            )
    return {bundle_id: sorted(set(items)) for bundle_id, items in details.items()}


def _raise_bundle_collisions(bundles: dict[str, dict[str, Any]]) -> None:
    collisions = _bundle_collision_details(bundles)
    messages = [
        f"{bundle_id}: {detail}"
        for bundle_id in sorted(collisions)
        for detail in collisions[bundle_id]
    ]
    if messages:
        raise ValueError("bundle collision: " + "; ".join(messages))


def _bundle_index(bundles: dict[str, dict[str, Any]]) -> str:
    if not bundles:
        return ""
    lines = ["## Workflow bundles", ""]
    for bundle_id, bundle in sorted(bundles.items()):
        manifest = bundle["manifest"]
        for kind in ("skills", "templates"):
            for name, payload_path in sorted(manifest[kind].items()):
                destination = (
                    f".ai-dlc/bundles/{bundle_id}/{payload_path}"
                    if kind == "skills"
                    else f"docs/templates/{name}.md"
                )
                lines.append(f"- {bundle_id} {kind[:-1]}: [{name}](<{destination}>)")
    return "\n".join(lines) + "\n"


def _bundle_outputs(
    bundles: dict[str, dict[str, Any]], clients: list[str]
) -> dict[str, tuple[str, str]]:
    outputs: dict[str, tuple[str, str]] = {}
    for bundle_id, bundle in sorted(bundles.items()):
        manifest = bundle["manifest"]
        payload = bundle["payload"]
        for name, relative in sorted(manifest["skills"].items()):
            for client in clients:
                directory = ".agents" if client == "codex" else ".claude"
                outputs[f"{directory}/skills/{name}/SKILL.md"] = (
                    bundle_id,
                    payload[relative],
                )
        for name, relative in sorted(manifest["templates"].items()):
            outputs[f"docs/templates/{name}.md"] = (bundle_id, payload[relative])
    return outputs


def _bundle_claims(
    bundles: dict[str, dict[str, Any]], clients: list[str]
) -> list[tuple[str, str, str]]:
    claims = []
    for bundle_id, bundle in sorted(bundles.items()):
        for name, relative in sorted(bundle["manifest"]["skills"].items()):
            for client in clients:
                directory = ".agents" if client == "codex" else ".claude"
                claims.append((f"{directory}/skills/{name}/SKILL.md", bundle_id, relative))
        for name, relative in sorted(bundle["manifest"]["templates"].items()):
            claims.append((f"docs/templates/{name}.md", bundle_id, relative))
    return claims


def _prior_bundle_files(previous: Any) -> dict[str, dict[str, str]]:
    if not isinstance(previous, dict):
        raise TypeError("bundle ownership document must be an object")
    if previous.get("schema") != 3:
        return {}
    files = previous.get("files")
    bundle_files = previous.get("bundle_files")
    if not isinstance(files, dict) or not isinstance(bundle_files, dict):
        raise TypeError("bundle ownership schema 3 is invalid")
    normalized: dict[str, dict[str, str]] = {}
    for path, entry in bundle_files.items():
        if (
            not isinstance(path, str)
            or not path.startswith(_BUNDLE_PREFIXES)
            or not isinstance(entry, dict)
            or set(entry) != {"owner", "sha256"}
            or not isinstance(entry["owner"], str)
            or _BUNDLE_ID.fullmatch(entry["owner"]) is None
            or not isinstance(entry["sha256"], str)
            or _SHA256.fullmatch(entry["sha256"]) is None
            or files.get(path) != entry["sha256"]
        ):
            raise ValueError("bundle ownership schema 3 is invalid")
        normalized[path] = dict(entry)
    return normalized


def _managed_bundle_path(path: str, clients: list[str], *, full_render: bool) -> bool:
    if path.startswith("docs/templates/") or full_render:
        return True
    return (path.startswith(".agents/skills/") and "codex" in clients) or (
        path.startswith(".claude/skills/") and "claude-code" in clients
    )


def _plan_bundle_files(
    read: Callable[[str], bytes | None],
    bundles: dict[str, dict[str, Any]],
    clients: list[str],
    *,
    full_render: bool,
    owned_files: dict[str, str],
    bundle_files: dict[str, dict[str, str]],
    planned: dict[str, str],
    removed: list[str],
) -> None:
    desired = _bundle_outputs(bundles, clients)
    for path, ownership in list(bundle_files.items()):
        if not _managed_bundle_path(path, clients, full_render=full_render):
            continue
        current = read(path)
        if current is not None and hashlib.sha256(current).hexdigest() != ownership["sha256"]:
            raise ValueError(f"managed bundle output conflict: {path}")
        if path not in desired:
            if current is not None:
                removed.append(path)
            bundle_files.pop(path)
            owned_files.pop(path, None)

    for path, (bundle_id, body) in desired.items():
        current = read(path)
        prior = bundle_files.get(path)
        if prior is None:
            if current is not None or path in owned_files:
                raise ValueError(f"bundle destination collision: {path}")
        elif prior["owner"] != bundle_id:
            raise ValueError(f"bundle destination collision: {path} is owned by {prior['owner']}")
        elif current is not None and hashlib.sha256(current).hexdigest() != prior["sha256"]:
            raise ValueError(f"managed bundle output conflict: {path}")
        digest = hashlib.sha256(body.encode()).hexdigest()
        planned[path] = body
        owned_files[path] = digest
        bundle_files[path] = {"owner": bundle_id, "sha256": digest}


def _apply_render_transaction(
    state: _RenderState,
    planned: dict[str, str],
    removed: list[str],
    changed: list[str],
) -> None:
    state.verify_files()
    changes: list[_RenderChange] = []
    try:
        # Planning already validated every existing ancestor. Open/create every
        # remaining parent before the first owned file is moved.
        for name in [*removed, *(name for name in changed if name not in removed)]:
            parent = state.parent(name, create=True)
            if parent is None:
                raise OSError("render destination parent is unavailable")
            changes.append(_RenderChange(name, parent, state.snapshots[name]))
        for change in changes:
            _publish_render_change(
                state, change, None if change.path in removed else planned[change.path].encode()
            )
        state.verify_directories()
        for change in changes:
            if not _matches_render_file(
                _read_render_file(change.parent, change.name), change.published
            ):
                raise ValueError(f"render destination changed during publication: {change.path}")
            if change.backup is not None and not _matches_render_file(
                _read_render_file(change.parent, change.backup), change.before
            ):
                raise ValueError(f"render destination changed during publication: {change.path}")
        for change in changes:
            if change.backup is not None:
                os.unlink(change.backup, dir_fd=change.parent)
                change.backup = None
        state.verify_directories()
    except BaseException as original:
        retry = []
        for change in reversed(changes):
            try:
                _restore_render_change(change)
            except BaseException:  # noqa: BLE001 - finish recovery before re-raising the original
                retry.append(change)
        for change in retry:
            try:
                _restore_render_change(change)
            except BaseException:  # noqa: BLE001 - preserve the original operational failure
                original.add_note(
                    "Render recovery preserved remaining .ai-dlc- backups for repair."
                )
        for name in reversed(state.created):
            relative = PurePosixPath(name)
            parent = state.directories[
                relative.parent.as_posix() if len(relative.parts) > 1 else ""
            ]
            descriptor = state.directories[name]
            if parent is not None and descriptor is not None:
                try:
                    bundle_fs._verify_named_directory(parent, relative.name, descriptor)
                    os.rmdir(relative.name, dir_fd=parent)
                except OSError:
                    pass
        raise


def _managed_section_state(path: Path, required: str) -> str:
    try:
        if path.is_symlink():
            return "blocked"
        if not path.exists():
            return "missing"
        if not path.is_file():
            return "blocked"
        current = path.read_text()
    except (OSError, UnicodeError):
        return "blocked"
    matches = list(
        re.finditer(
            r"<!-- ai-dlc:begin ([0-9a-f]{64}) -->\n(.*?)<!-- ai-dlc:end -->",
            current,
            re.DOTALL,
        )
    )
    if (
        len(matches) != 1
        or current.count("<!-- ai-dlc:begin ") != 1
        or current.count("<!-- ai-dlc:end -->") != 1
    ):
        return "blocked"
    match = matches[0]
    if hashlib.sha256(match.group(2).encode()).hexdigest() != match.group(1):
        return "blocked"
    return "ready" if required in match.group(2) else "missing"


def inspect_bundle_guidance(root: Path, config: dict, clients: list[str]) -> list[dict]:
    """Inspect selected vendored guidance and rendered outputs without source access."""
    bundle_ids = _selected_bundle_ids(config)
    if not bundle_ids:
        return []
    states: dict[str, dict[str, list[str]]] = {
        bundle_id: {"blocked": [], "missing": []} for bundle_id in bundle_ids
    }
    bundles: dict[str, dict[str, Any]] = {}
    for bundle_id in bundle_ids:
        path = root / ".ai-dlc" / "bundles" / bundle_id
        if not path.exists() and not path.is_symlink():
            states[bundle_id]["missing"].append("vendored bundle path is missing")
            continue
        try:
            bundles[bundle_id] = load_vendored_bundle(root, bundle_id)
        except MissingBundlePath as exc:
            states[bundle_id]["missing"].append(f"vendored bundle path is missing: {exc.path}")
            if exc.manifest is not None:
                bundles[bundle_id] = {"manifest": exc.manifest, "payload": {}}
        except ValueError as exc:
            states[bundle_id]["blocked"].append(str(exc))

    collisions = _bundle_collision_details(bundles)
    for bundle_id, details in collisions.items():
        states[bundle_id]["blocked"].extend(details)

    ownership_path = root / ".ai-dlc" / "agent-ownership.json"
    previous: dict[str, Any] = {}
    prior_bundle_files: dict[str, dict[str, str]] = {}
    if ownership_path.exists():
        try:
            previous = json.loads(ownership_path.read_text())
            prior_bundle_files = _prior_bundle_files(previous)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            for bundle_id in bundle_ids:
                states[bundle_id]["blocked"].append(f"bundle ownership is invalid: {exc}")

    claims = _bundle_claims(bundles, clients)
    for path, bundle_id, relative in claims:
        ownership = prior_bundle_files.get(path)
        if ownership is not None and ownership["owner"] != bundle_id:
            detail = (
                f"bundle destination collision between {bundle_id} and {ownership['owner']}: {path}"
            )
            states[bundle_id]["blocked"].append(detail)
            if ownership["owner"] in states:
                states[ownership["owner"]]["blocked"].append(detail)
            continue
        try:
            destination = inside(root, path)
        except ValueError:
            states[bundle_id]["blocked"].append(f"rendered bundle output is a symlink: {path}")
            continue
        if not destination.exists():
            states[bundle_id]["missing"].append(f"rendered bundle output is missing: {path}")
            continue
        if not destination.is_file():
            states[bundle_id]["blocked"].append(
                f"owned bundle output is not a regular file: {path}"
            )
            continue
        if ownership is None:
            states[bundle_id]["blocked"].append(
                f"bundle destination collision with unowned file: {path}"
            )
            continue
        try:
            current_digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        except OSError:
            states[bundle_id]["blocked"].append(f"owned bundle output cannot be read: {path}")
            continue
        if current_digest != ownership["sha256"]:
            states[bundle_id]["blocked"].append(f"owned bundle output has local edits: {path}")
        elif (
            body := bundles[bundle_id]["payload"].get(relative)
        ) is not None and current_digest != hashlib.sha256(body.encode()).hexdigest():
            states[bundle_id]["missing"].append(f"rendered bundle output is stale: {path}")

    desired_paths = {path for path, _, _ in claims}
    for path, ownership in prior_bundle_files.items():
        bundle_id = ownership["owner"]
        if bundle_id not in states or path in desired_paths:
            continue
        try:
            destination = inside(root, path)
        except ValueError:
            states[bundle_id]["blocked"].append(f"obsolete bundle output is a symlink: {path}")
            continue
        if destination.exists() and not destination.is_file():
            states[bundle_id]["blocked"].append(
                f"obsolete bundle output is not a regular file: {path}"
            )
            continue
        try:
            current_digest = (
                hashlib.sha256(destination.read_bytes()).hexdigest()
                if destination.exists()
                else None
            )
        except OSError:
            states[bundle_id]["blocked"].append(f"obsolete bundle output cannot be read: {path}")
            continue
        if current_digest is not None and current_digest != ownership["sha256"]:
            states[bundle_id]["blocked"].append(f"obsolete bundle output has local edits: {path}")
        else:
            states[bundle_id]["missing"].append(f"obsolete bundle output requires removal: {path}")

    index_state = _managed_section_state(root / "AGENTS.md", _bundle_index(bundles))
    if index_state != "ready":
        for bundle_id in bundle_ids:
            states[bundle_id][index_state].append("managed workflow-bundle index is unavailable")
    if "claude-code" in clients:
        claude_state = _managed_section_state(root / "CLAUDE.md", "@AGENTS.md\n")
        if claude_state != "ready":
            for bundle_id in bundle_ids:
                states[bundle_id][claude_state].append("CLAUDE.md does not reference AGENTS.md")

    results = []
    for bundle_id in bundle_ids:
        blocked = sorted(set(states[bundle_id]["blocked"]))
        missing = sorted(set(states[bundle_id]["missing"]))
        if blocked:
            status = "blocked"
            reason = blocked[0]
            action = (
                "Resolve bundle guidance conflicts or restore exact vendored and owned bytes, "
                "then run a full ai-dlc agents render --apply."
            )
        elif missing:
            status = "missing"
            reason = next(
                (detail for detail in missing if detail.startswith("vendored bundle path")),
                missing[0],
            )
            action = "Restore missing vendored content if needed, then run a full ai-dlc agents render --apply."
        else:
            status = "ready"
            reason = "bundle guidance is intact and rendered for configured clients"
            action = "No action required."
        results.append(
            {
                "bundle_id": bundle_id,
                "status": status,
                "reason": reason,
                "next_action": action,
            }
        )
    return results


def _render_agents(
    root: Path,
    apply: bool = False,
    client: str | None = None,
    target: str = "local",
    state: _RenderState | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()

    def read(name: str) -> bytes | None:
        if state is not None:
            return state.read(name)
        path = inside(root, name)
        return path.read_bytes() if path.exists() else None

    def text(name: str) -> str:
        return (read(name) or b"").decode().replace("\r\n", "\n").replace("\r", "\n")

    config = load_project(root)
    bundle_ids = _selected_bundle_ids(config)
    bundles = _load_selected_bundles(root, bundle_ids)
    _raise_bundle_collisions(bundles)
    clients = (
        [client]
        if client
        else config.get("roles", {}).get("agent-client", ["claude-code", "codex"])
    )
    if isinstance(clients, str):
        clients = [clients]
    if set(clients) - {"claude-code", "codex"}:
        raise ValueError("unsupported agent client; register a client adapter before rendering")
    for selected_client in clients:
        settings = config.get("agents", {}).get("clients", {}).get(selected_client, {})
        readiness = hook_readiness(
            selected_client,
            settings.get("version", ""),
            "local",
            settings.get("required_hooks", []),
        )
        if not readiness["ready"]:
            raise ValueError(
                f"unsupported required hooks for {selected_client}: {readiness['unavailable']}"
            )
    skill_sources = _skill_sources(config)
    try:
        components = resolve_components(config, load_component_catalog(root, config))
    except TypeError as exc:
        raise ValueError(f"invalid component metadata: {exc}") from exc
    index, provider_copies = provider_index(components)
    referenced_guidance = {
        guidance for component in components["components"] for guidance in component["guidance"]
    }
    checks = config.get("checks", {})
    lines = [
        "# Shared project guidance",
        "",
        "Read ai-dlc.toml and the active .ai-dlc/work record before work.",
        "Use specification artifacts for implementation tasks and the tracker for priority/status.",
        "Finalize required specifications before review. Complete work through ai-dlc work finish.",
        "Store architecture, design, decisions and runbooks in docs/. Keep personal notes in knowledge.",
        "",
        "## Verification",
        "",
    ]
    for name in checks.get("required", []):
        lines.append(f"- {name}: `{checks.get('commands', {}).get(name, 'MISSING COMMAND')}`")
    lines.extend(
        ["", "Run `ai-dlc project check --required` in the prepared project environment.", ""]
    )
    lines.append(index)
    bundle_index = _bundle_index(bundles)
    if bundle_index:
        lines.append(bundle_index)
    planned: dict[str, str] = {}
    for filename, body in [("AGENTS.md", "\n".join(lines)), ("CLAUDE.md", "@AGENTS.md\n")]:
        if filename == "CLAUDE.md" and "claude-code" not in clients:
            continue
        planned[filename] = _section(text(filename), body)
    servers = {}
    codex = {}
    for server in config.get("agents", {}).get("servers", []):
        sid = server["id"]
        if sid in servers:
            raise ValueError(f"duplicate MCP server: {sid}")
        definition = {k: server[k] for k in ["command", "args", "url"] if k in server}
        if "command" not in definition and "url" not in definition:
            raise ValueError(f"MCP server {sid} requires command or URL")
        if any(
            str(x).startswith(("/Users/", "/home/"))
            for x in [definition.get("command", ""), *definition.get("args", [])]
        ):
            raise ValueError("personal paths cannot appear in shared MCP configuration")
        env_names = server.get("env", [])
        if not isinstance(env_names, list) or not all(
            re.fullmatch(r"[A-Z_][A-Z0-9_]*", x) for x in env_names
        ):
            raise ValueError(
                "MCP env must list environment variable names, never credential values"
            )
        servers[sid] = {
            **definition,
            **({"env": {x: "${" + x + "}" for x in env_names}} if env_names else {}),
        }
        codex[sid] = {**definition, **({"env_vars": env_names} if env_names else {})}
    manifest_bytes = read(".ai-dlc/agent-ownership.json")
    previous = json.loads(manifest_bytes) if manifest_bytes is not None else {"mcp": {}}
    prior_bundle_files = _prior_bundle_files(previous)
    bundle_participates = bool(bundle_ids or prior_bundle_files or previous.get("schema") == 3)
    ownership: dict[str, Any] = dict(previous)
    ownership["schema"] = 3 if bundle_participates else 2
    owned_files = dict(previous.get("files", {}))
    bundle_files = dict(prior_bundle_files)
    removed = []
    for name, old_digest in list(owned_files.items()):
        if not name.startswith(".ai-dlc/providers/"):
            continue
        current = read(name)
        if current is not None and hashlib.sha256(current).hexdigest() != old_digest:
            raise ValueError(f"managed provider guidance conflict: {name}")
        if name not in provider_copies:
            if current is not None:
                removed.append(name)
            del owned_files[name]
    for name, body in provider_copies.items():
        current = read(name)
        if name not in owned_files and current is not None and current != body.encode():
            raise ValueError(f"authored provider guidance conflict: {name}")
        planned[name] = body
        owned_files[name] = hashlib.sha256(body.encode()).hexdigest()
    for selected_client in clients:
        directory = ".agents" if selected_client == "codex" else ".claude"
        prefix = directory + "/skills/"
        desired = {prefix + name + "/SKILL.md": body for name, body in skill_sources.items()}
        for name, old_digest in list(owned_files.items()):
            if not name.startswith(prefix):
                continue
            if name in prior_bundle_files:
                continue
            current = read(name)
            if current is not None and hashlib.sha256(current).hexdigest() != old_digest:
                raise ValueError(f"managed skill conflict: {name}")
            if name not in desired:
                if current is not None:
                    removed.append(name)
                del owned_files[name]
        for name, body in desired.items():
            current = read(name)
            if name not in owned_files and current is not None and current != body.encode():
                raise ValueError(f"authored skill conflict: {name}")
            planned[name] = body
            owned_files[name] = hashlib.sha256(body.encode()).hexdigest()
        _plan_hooks(read, config, selected_client, previous, ownership, planned)
    _plan_bundle_files(
        read,
        bundles,
        clients,
        full_render=client is None,
        owned_files=owned_files,
        bundle_files=bundle_files,
        planned=planned,
        removed=removed,
    )
    ownership["files"] = owned_files
    if bundle_participates:
        ownership["bundle_files"] = bundle_files
    if "claude-code" in clients:
        ownership["mcp"] = servers
        current = read(".mcp.json")
        document = json.loads(current) if current is not None else {}
        existing = document.setdefault("mcpServers", {})
        for sid, old in previous.get("mcp", {}).items():
            if sid in existing and existing[sid] != old:
                raise ValueError(f"MCP server conflict: {sid}")
            existing.pop(sid, None)
        for sid, definition in servers.items():
            if sid in existing and existing[sid] != definition:
                raise ValueError(f"MCP server conflict: {sid}")
            existing[sid] = definition
        planned[".mcp.json"] = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if "codex" in clients:
        current = text(".codex/config.toml")
        body = (
            tomli_w.dumps({"mcp_servers": codex})
            if codex
            else "# No project MCP servers configured.\n"
        )
        planned[".codex/config.toml"] = _section(current, body, toml=True)
        # Validate duplicate tables or invalid unmanaged text before writing any file.
        import tomllib

        tomllib.loads(planned[".codex/config.toml"])
    planned[".ai-dlc/agent-ownership.json"] = json.dumps(ownership, indent=2, sort_keys=True) + "\n"
    changed = [name for name, text in planned.items() if read(name) != text.encode()]
    changed.extend(removed)
    for name in removed:
        if name in referenced_guidance:
            raise ValueError(
                f"managed provider guidance conflict: {name} is still referenced; "
                "copy the instructions to a project-owned path and update the component manifest"
            )
    if apply:
        if bundle_participates:
            if state is None:
                raise ValueError("bundle render requires a bound project transaction")
            _apply_render_transaction(state, planned, removed, changed)
        else:
            for name in removed:
                inside(root, name).unlink()
            for name in changed:
                if name in removed:
                    continue
                atomic_write(inside(root, name), planned[name])
    return {"clean": not changed, "changed": changed, "applied": apply}


def render_agents(
    root: Path, apply: bool = False, client: str | None = None, target: str = "local"
) -> dict[str, Any]:
    """Render project guidance, transactionally when bundle outputs participate."""
    absolute = Path(root).resolve()
    if not apply:
        return _render_agents(absolute, apply=False, client=client, target=target)
    config = load_project(absolute)
    selected = bool(_selected_bundle_ids(config))
    ownership_path = absolute / ".ai-dlc" / "agent-ownership.json"
    previous: dict[str, Any] = {}
    if ownership_path.exists():
        previous = json.loads(ownership_path.read_text())
    participates = selected or previous.get("schema") == 3
    if participates:
        with (
            project_write_lock(absolute),
            bundle_fs._bound_project_root(absolute) as (bound, parent, descriptor),
        ):
            state = _RenderState(bound, parent, descriptor)
            try:
                return _render_agents(bound, apply=True, client=client, target=target, state=state)
            finally:
                state.close()
    return _render_agents(absolute, apply=True, client=client, target=target)


def _skill_sources(config: dict) -> dict[str, str]:
    base = assets("agents")
    lock = json.loads((base / "skills.lock.json").read_text())
    available = {p.parent.name: p for p in (base / "skills").glob("*/SKILL.md")}
    if set(available) != set(lock["skills"]):
        raise ValueError("skill digest lock does not match shipped collection")
    # Verify the whole package before planning any project writes.
    content = {}
    for name, path in sorted(available.items()):
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != lock["skills"][name]["sha256"]:
            raise ValueError(f"skill digest mismatch: {name}")
        content[name] = data.decode("utf-8")
    selected = config.get("agents", {}).get("skills", sorted(content))
    if not isinstance(selected, list) or not all(isinstance(name, str) for name in selected):
        raise ValueError("agents.skills must be a list of shipped skill names")
    if set(selected) - set(content):
        raise ValueError("unknown selected skill")
    return {name: content[name] for name in sorted(set(selected))}


def hook_readiness(client: str, version: str, target: str, required: list[str]) -> dict:
    import tomllib

    matrix = tomllib.loads((assets("agents") / "capabilities.toml").read_text())
    supported = set()
    for fixture in matrix["fixtures"]:
        if (fixture["client"], fixture["version"], fixture["target"]) == (client, version, target):
            supported.update(fixture["hooks"])
    unavailable = sorted(set(required) - supported)
    return {
        "ready": not unavailable,
        "unavailable": unavailable,
        "supported": sorted(supported),
        "coverage": matrix["coverage"],
    }


def target_hooks(config: dict, target: str) -> dict:
    clients = config.get("agents", {}).get("clients", {})
    results = {
        name: hook_readiness(
            name, settings.get("version", ""), target, settings.get("required_hooks", [])
        )
        for name, settings in clients.items()
    }
    return {
        "ready": all(result["ready"] for result in results.values()),
        "clients": results,
        "unavailable": [
            f"{name}:{hook}" for name, result in results.items() for hook in result["unavailable"]
        ],
    }


def _plan_hooks(
    read: Callable[[str], bytes | None],
    config: dict,
    client: str,
    previous: dict,
    ownership: dict,
    planned: dict,
) -> None:
    settings = config.get("agents", {}).get("clients", {}).get(client, {})
    required = settings.get("required_hooks", [])
    old = previous.get("hooks", {}).get(client, {})
    if not required and not old:
        return
    name = ".codex/hooks.json" if client == "codex" else ".claude/settings.json"
    current = read(name)
    document = json.loads(current) if current is not None else {}
    hooks = document.setdefault("hooks", {})
    for event, entries in old.items():
        current = hooks.get(event, [])
        for entry in entries:
            if entry not in current:
                raise ValueError(f"managed hook conflict: {client}/{event}")
            current.remove(entry)
        if not current:
            hooks.pop(event, None)
    rendered = {}
    events = {
        "bound-push": ("PreToolUse", "pre-tool"),
        "session-context": ("SessionStart", "session-start"),
        "stop-reminder": ("Stop", "stop"),
    }
    for feature in sorted(set(required)):
        event, action = events[feature]
        entry: dict[str, Any] = {
            "hooks": [
                {
                    "type": "command",
                    "command": f'ai-dlc hook {action} --root "$(git rev-parse --show-toplevel)"',
                    "timeout": 10,
                }
            ]
        }
        if event == "PreToolUse":
            entry["matcher"] = "Bash|exec_command"
        hooks.setdefault(event, []).append(entry)
        rendered.setdefault(event, []).append(entry)
    ownership["hooks"] = dict(ownership.get("hooks", {}))
    ownership["hooks"][client] = rendered
    planned[name] = json.dumps(document, indent=2, sort_keys=True) + "\n"
