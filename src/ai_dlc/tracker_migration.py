"""Reviewed provider-neutral tracker moves with bounded local transaction recovery.

Writes use validated open file descriptors, never pathname replacement or stage
cleanup. This preserves concurrent pathname replacements but is not crash atomic;
partial or externally edited content requires explicit human recovery.
"""

import base64
import copy
import hashlib
import json
import os
import re
import stat
import tomllib
import uuid
from contextlib import contextmanager
from pathlib import Path

import tomli_w

from ai_dlc.config import digest, resolve_runtime
from ai_dlc.locking import project_write_lock
from ai_dlc.provider_onboarding import _set_table_value
from ai_dlc.providers import Registry
from ai_dlc.workflow import Work, resolve_work


def _sha(data):
    return hashlib.sha256(data).hexdigest()


@contextmanager
def _open(root, name, flags=os.O_RDONLY):
    """Anchor every path component; descriptor writes cannot follow replacements."""
    parts = Path(name).parts
    if not parts or Path(name).is_absolute() or any(p in {".", ".."} for p in parts):
        raise ValueError("Unsafe migration path")
    parent = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    descriptor = None
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        descriptor = os.open(parts[-1], flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=parent)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("Migration files must be regular files with no hard links")
        yield descriptor
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def _bytes(descriptor):
    size = os.fstat(descriptor).st_size
    return os.pread(descriptor, size + 1, 0)


def _identity(descriptor):
    info = os.fstat(descriptor)
    return {"device": info.st_dev, "inode": info.st_ino, "sha256": _sha(_bytes(descriptor))}


def _snapshot(root):
    names = ["ai-dlc.toml"] + [
        p.relative_to(root).as_posix() for p in sorted((root / ".ai-dlc/work").glob("*.toml"))
    ]
    snapshot, contents = {}, {}
    for name in names:
        with _open(root, name) as descriptor:
            snapshot[name] = _identity(descriptor)
            contents[name] = _bytes(descriptor)
            if _sha(contents[name]) != snapshot[name]["sha256"]:
                raise ValueError("Project files changed during migration snapshot")
    return snapshot, contents


def _runtime(root, *, environ, machine, machine_config):
    return resolve_runtime(
        root, machine=machine, machine_config=machine_config, environ=environ
    ).values


def _build(
    root,
    provider_id,
    *,
    mode,
    work_ids,
    mappings,
    environ,
    machine,
    machine_config,
    registry,
    schema=2,
):
    snapshot, contents = _snapshot(root)
    config = _runtime(root, environ=environ, machine=machine, machine_config=machine_config)
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise ValueError("Target provider ID is required")
    if provider_id not in config.get("providers", {}):
        raise ValueError("Target tracker must have an explicit configured provider alias")
    registry = registry or Registry(config, root=root, environ=environ)
    provider = registry.get(provider_id)
    if not callable(getattr(provider, "invoke", None)):
        raise TypeError("Target provider does not expose tracker operations")
    if mode not in {"default-only", "selected"}:
        raise ValueError("Migration mode must be default-only or selected")
    work_ids = list(work_ids or [])
    mappings = mappings or {}
    if mode == "default-only" and (work_ids or mappings):
        raise ValueError("Default-only migration does not accept selected work or mappings")
    if mode == "selected" and (
        not work_ids or len(set(work_ids)) != len(work_ids) or set(work_ids) != set(mappings)
    ):
        raise ValueError("Explicit mappings for exactly the selected work IDs are required")
    work_ids = sorted(work_ids)
    for work_id in work_ids:
        Work.safe_id(work_id)
        if f".ai-dlc/work/{work_id}.toml" not in contents:
            raise ValueError(f"Unknown selected work: {work_id}")
    proposed = copy.deepcopy(config)
    changes, verified, retained, observed = {}, {}, {}, {}
    if mode == "default-only":
        proposed.setdefault("roles", {})["tracker"] = provider_id
        source = contents["ai-dlc.toml"].decode()
        edited = _set_table_value(source, "roles", "tracker", provider_id)
        expected = tomllib.loads(source)
        expected.setdefault("roles", {})["tracker"] = provider_id
        if tomllib.loads(edited) != expected:
            raise ValueError("Project roles TOML representation cannot be safely updated")
        if edited.encode() != contents["ai-dlc.toml"]:
            changes["ai-dlc.toml"] = edited.encode()
    identities = set()
    for name, data in contents.items():
        if name == "ai-dlc.toml":
            continue
        raw = tomllib.loads(data.decode())
        work_id = Path(name).stem
        work = resolve_work(raw, config, work_id)
        retained[work_id] = copy.deepcopy(
            {"providers": work["providers"], "bindings": work["bindings"]}
        )
        if work_id in work_ids:
            if not work["reviewed"]:
                raise ValueError(f"Selected work must be reviewed: {work_id}")
            reference = mappings[work_id]
            if not isinstance(reference, str) or not reference.strip():
                raise ValueError("Target mapping must be a nonempty reference")
            target = registry.invoke(provider_id, "read", {"reference": reference})
            canonical = {"id": target["id"], "url": target["url"]}
            observed[work_id] = target["state"]
            if canonical["id"] in identities:
                raise ValueError("Duplicate canonical target identity across selected work")
            identities.add(canonical["id"])
            verified[work_id] = {
                "source": {
                    "provider": work["providers"].get("tracker"),
                    "binding": work["bindings"].get("tracker"),
                    "reference": work["artifacts"].get("tracker"),
                },
                "requested_reference": reference,
                "target": canonical,
            }
            work["providers"]["tracker"] = provider_id
            work["bindings"].pop("tracker", None)
            work["artifacts"]["tracker"] = reference
            updated = resolve_work(work, proposed, work_id)
            changes[name] = tomli_w.dumps(updated).encode()
        elif mode == "default-only" and not raw.get("providers"):
            # Freeze the full effective mapping, including the absence of a tracker.
            changes[name] = tomli_w.dumps(work).encode()
    planned = {
        "schema": schema,
        "root_digest": digest(str(root)),
        "mode": mode,
        "provider": provider_id,
        "work_ids": work_ids,
        "mappings": verified,
        "snapshot": snapshot,
        "runtime_digest": digest(config),
        "after_runtime_digest": digest(proposed),
        "retained": retained,
        "changes": {name: _sha(data) for name, data in changes.items()},
        "remote_mutations": False,
    }
    if schema == 2:
        capabilities = {"status": "not-inspected" if mode == "default-only" else "undeclared"}
        unsupported = []
        if mode == "selected" and getattr(registry, "declares", lambda *_: False)(
            provider_id, "capabilities"
        ):
            value = registry.invoke(provider_id, "capabilities", {})
            capabilities = {"status": "declared", "value": value}
            unsupported = sorted(
                key for key, supported in value["lifecycle"].items() if not supported
            )
        planned["evidence"] = {
            "source": local_source_evidence(),
            "capabilities": capabilities,
            "unsupported_transitions": unsupported,
            "targets": {
                key: {
                    "state": state,
                    "state_action": "preserve",
                    "completion_evidence": False,
                    "mapping": "not-attempted; source remote state unknown",
                }
                for key, state in observed.items()
            },
        }
    return planned, changes, contents


def local_source_evidence():
    return {
        "basis": "local-records-only",
        "remote_state": "unknown",
        "remote_history": "unknown",
        "omitted": ["remote-only issues", "comments", "attachments", "assignees", "remote edits"],
        "complete_import": False,
    }


def plan_tracker_migration(
    root,
    provider_id,
    *,
    mode,
    work_ids=None,
    mappings=None,
    environ=None,
    machine=None,
    machine_config=None,
    registry=None,
):
    """Read-only preview; target adapter reads establish configured canonical identity."""
    root = Path(root).resolve()
    planned, _, _ = _build(
        root,
        provider_id,
        mode=mode,
        work_ids=work_ids,
        mappings=mappings,
        environ=os.environ if environ is None else environ,
        machine=machine,
        machine_config=machine_config,
        registry=registry,
    )
    planned["operation_id"] = uuid.uuid4().hex
    planned["digest"] = digest(planned)
    return planned


def _validate(plan):
    fields = {
        "schema",
        "root_digest",
        "mode",
        "provider",
        "work_ids",
        "mappings",
        "snapshot",
        "runtime_digest",
        "after_runtime_digest",
        "retained",
        "changes",
        "remote_mutations",
        "operation_id",
        "digest",
    }
    if isinstance(plan, dict) and plan.get("schema") == 2:
        fields.add("evidence")
    if not isinstance(plan, dict) or set(plan) != fields:
        raise ValueError("Invalid migration plan fields")
    if (
        not isinstance(plan["provider"], str)
        or plan["mode"] not in {"default-only", "selected"}
        or not isinstance(plan["work_ids"], list)
        or not all(isinstance(work_id, str) for work_id in plan["work_ids"])
        or any(
            not isinstance(plan[field], dict)
            for field in ("mappings", "snapshot", "retained", "changes")
        )
        or plan["remote_mutations"] is not False
    ):
        raise ValueError("Invalid migration plan shape")
    for mapping in plan["mappings"].values():
        if not isinstance(mapping, dict) or not isinstance(mapping.get("requested_reference"), str):
            raise TypeError("Invalid migration plan mapping")
    for name, snapshot in plan["snapshot"].items():
        if (
            not isinstance(name, str)
            or not isinstance(snapshot, dict)
            or set(snapshot) != {"device", "inode", "sha256"}
            or type(snapshot["device"]) is not int
            or type(snapshot["inode"]) is not int
            or not isinstance(snapshot["sha256"], str)
        ):
            raise ValueError("Invalid migration plan snapshot")
    if plan["schema"] == 2:
        evidence = plan["evidence"]
        if not isinstance(evidence, dict):
            raise ValueError("Invalid migration evidence")
        creation = evidence.get("creation")
        if creation is not None:
            if (
                not isinstance(creation, dict)
                or set(creation) != {"operation_id", "intent_digest", "targets"}
                or not re.fullmatch(r"[a-f0-9]{32}", str(creation["operation_id"]))
                or not re.fullmatch(r"[a-f0-9]{64}", str(creation["intent_digest"]))
                or not isinstance(creation["targets"], dict)
                or not set(creation["targets"]) <= set(plan["work_ids"])
            ):
                raise ValueError("Invalid creation provenance")
            for row in creation["targets"].values():
                if (
                    not isinstance(row, dict)
                    or set(row) != {"operation_id", "correlation"}
                    or not re.fullmatch(r"[a-f0-9]{64}", str(row["operation_id"]))
                    or row["correlation"] != f"<!-- ai-dlc:{row['operation_id']} -->"
                ):
                    raise ValueError("Invalid creation provenance identity")
    value = copy.deepcopy(plan)
    expected = value.pop("digest", None)
    if expected != digest(value):
        raise ValueError("Migration plan digest changed")
    if (
        type(value.get("schema")) is not int
        or value["schema"] not in {1, 2}
        or not re.fullmatch(r"[a-f0-9]{32}", str(value.get("operation_id", "")))
    ):
        raise ValueError("Invalid migration plan schema or operation identity")
    return value


def _write_bytes(descriptor, data):
    offset = 0
    while offset < len(data):
        written = os.pwrite(descriptor, data[offset:], offset)
        if written <= 0:
            raise OSError("Incomplete migration write")
        offset += written
    os.ftruncate(descriptor, len(data))
    os.fsync(descriptor)


def _mkdir(root, name):
    # Never follow an existing symlink in evidence or plan directories.
    parent = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in Path(name).parts:
            try:
                os.mkdir(part, 0o700, dir_fd=parent)
                os.fsync(parent)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
    finally:
        os.close(parent)


def _new_json(root, name, value):
    _mkdir(root, str(Path(name).parent))
    with _open(root, name, os.O_WRONLY | os.O_CREAT | os.O_EXCL) as descriptor:
        _write_bytes(descriptor, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
    # Publish evidence before any target write, including the directory entry.
    parent = os.open(root / Path(name).parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def _read_json(root, name):
    with _open(root, name) as descriptor:
        return json.loads(_bytes(descriptor))


def _outcome(root, operation_id):
    result = {"status": "recovery-required"}
    for suffix in ("result", "recovered"):
        try:
            result = _read_json(root, f".ai-dlc/migrations/{operation_id}.{suffix}.json")
        except FileNotFoundError:
            continue
        except (OSError, ValueError):
            result = {"status": "recovery-required"}
        if (
            not isinstance(result, dict)
            or type(result.get("schema")) is not int
            or result.get("schema") != 1
            or result.get("operation_id") != operation_id
            or not isinstance(result.get("status"), str)
            or result.get("status") not in {"applied", "rolled-back", "recovery-required"}
        ):
            result = {"status": "recovery-required"}
    return result


def _pending(root):
    for path in sorted((root / ".ai-dlc/migrations").glob("*.json")):
        if path.name.endswith((".result.json", ".recovered.json")):
            continue
        if _outcome(root, path.stem)["status"] == "recovery-required":
            raise ValueError(f"Migration recovery required: {path.stem}")


def _matches(root, name, descriptor, expected):
    with _open(root, name) as current:
        return _identity(current) == expected and _identity(descriptor) == expected


def _transaction(root, plan, changes, contents, recheck):
    operation = plan["operation_id"]
    receipt_name = f".ai-dlc/migrations/{operation}.json"
    result_name = f".ai-dlc/migrations/{operation}.result.json"
    recovery = {
        name: {
            "before": base64.b64encode(contents[name]).decode(),
            "after": base64.b64encode(data).decode(),
        }
        for name, data in changes.items()
    }
    _new_json(
        root, receipt_name, {"schema": 1, "status": "prepared", "plan": plan, "recovery": recovery}
    )
    changed = []
    status, uncertain = "applied", []
    try:
        recheck()
        # Config last: changed records are already explicitly bound at default switch.
        for name in sorted(changes, key=lambda name: (name == "ai-dlc.toml", name)):
            recheck(changed)
            with _open(root, name, os.O_RDWR) as descriptor:
                expected = plan["snapshot"][name]
                if not _matches(root, name, descriptor, expected):
                    raise ValueError(f"Migration target changed: {name}")
                # Record attempted writes too; failures may occur after a partial write.
                changed.append(name)
                _write_bytes(descriptor, changes[name])
                after = {**expected, "sha256": _sha(changes[name])}
                if not _matches(root, name, descriptor, after):
                    raise ValueError(f"Migration write outcome uncertain: {name}")
        recheck(changed)
    except Exception:  # noqa: BLE001 -- failures require a durable bounded rollback outcome
        status = "rolled-back"
        for name in reversed(changed):
            try:
                with _open(root, name, os.O_RDWR) as descriptor:
                    before = plan["snapshot"][name]
                    after = {**before, "sha256": _sha(changes[name])}
                    if _matches(root, name, descriptor, before):
                        continue
                    if not _matches(root, name, descriptor, after):
                        uncertain.append(name)
                        continue
                    _write_bytes(descriptor, contents[name])
                    if not _matches(root, name, descriptor, before):
                        uncertain.append(name)
            except (OSError, ValueError):
                uncertain.append(name)
        if uncertain:
            status = "recovery-required"
    result = {
        "schema": 1,
        "operation_id": operation,
        "status": status,
        "receipt": receipt_name,
        "uncertain": uncertain,
    }
    _new_json(root, result_name, result)
    return result


def apply_tracker_migration(
    root, plan, *, environ=None, machine=None, machine_config=None, registry=None
):
    """Apply the exact preview after fresh identity and locked runtime/file checks."""
    root = Path(root).resolve()
    env = os.environ if environ is None else environ
    if isinstance(plan, (str, Path)):
        plan = load_tracker_migration_plan(root, Path(plan))
    saved = _validate(plan)
    with project_write_lock(root):
        _pending(root)

        def recheck(written=()):
            expected = copy.deepcopy(saved["snapshot"])
            for name in written:
                expected[name]["sha256"] = saved["changes"][name]
            if _snapshot(root)[0] != expected:
                raise ValueError("Migration project files changed since preview")
            runtime_digest = (
                saved["after_runtime_digest"]
                if "ai-dlc.toml" in written
                else saved["runtime_digest"]
            )
            if (
                digest(_runtime(root, environ=env, machine=machine, machine_config=machine_config))
                != runtime_digest
            ):
                raise ValueError("Migration effective runtime drift since preview")

        recheck()
        fresh, changes, contents = _build(
            root,
            saved["provider"],
            mode=saved["mode"],
            work_ids=saved["work_ids"],
            mappings={
                key: value["requested_reference"] for key, value in saved["mappings"].items()
            },
            environ=env,
            machine=machine,
            machine_config=machine_config,
            registry=registry,
            schema=saved["schema"],
        )
        # Creation provenance is historical reviewed metadata, not a live-state claim.
        if saved["schema"] == 2 and "creation" in saved["evidence"]:
            fresh["evidence"]["creation"] = saved["evidence"]["creation"]
        if {**fresh, "operation_id": saved["operation_id"]} != saved:
            raise ValueError("Migration plan or verified target identity drift")
        recheck()
        return _transaction(root, plan, changes, contents, recheck)


def _plan_name(root, path):
    path = Path(path)
    if path.is_absolute():
        path = path.relative_to(root)
    if path.parent != Path(".ai-dlc/local") or path.suffix != ".json":
        raise ValueError("Migration plans must be JSON files directly under .ai-dlc/local")
    return path.as_posix()


def save_tracker_migration_plan(root, plan, path):
    root = Path(root).resolve()
    _validate(plan)
    name = _plan_name(root, path)
    _new_json(root, name, plan)
    return name


def load_tracker_migration_plan(root, path):
    root = Path(root).resolve()
    plan = _read_json(root, _plan_name(root, path))
    _validate(plan)
    return plan


def inspect_tracker_migration(root, operation_id):
    """Read-only recovery inventory; never restore over an authored replacement."""
    root = Path(root).resolve()
    if not re.fullmatch(r"[a-f0-9]{32}", operation_id):
        raise ValueError("Invalid migration operation identity")
    receipt_name = f".ai-dlc/migrations/{operation_id}.json"
    receipt = _read_json(root, receipt_name)
    if (
        not isinstance(receipt, dict)
        or set(receipt) != {"schema", "status", "plan", "recovery"}
        or type(receipt.get("schema")) is not int
        or receipt["schema"] != 1
        or receipt["status"] != "prepared"
        or not isinstance(receipt["recovery"], dict)
    ):
        raise ValueError("Migration recovery receipt is invalid; preserve it for manual recovery")
    saved = _validate(receipt["plan"])
    if saved["operation_id"] != operation_id or saved["root_digest"] != digest(str(root)):
        raise ValueError("Migration recovery receipt identity mismatch")
    result = _outcome(root, operation_id)
    files = {}
    if set(receipt["recovery"]) != set(saved["changes"]):
        raise ValueError("Invalid recovery file set")
    for name, recovery in receipt["recovery"].items():
        if (
            not isinstance(recovery, dict)
            or set(recovery) != {"before", "after"}
            or not all(isinstance(value, str) for value in recovery.values())
        ):
            raise ValueError("Migration recovery receipt content is invalid")
        before = _sha(base64.b64decode(recovery["before"], validate=True))
        after = _sha(base64.b64decode(recovery["after"], validate=True))
        if before != saved["snapshot"][name]["sha256"] or after != saved["changes"][name]:
            raise ValueError("Migration recovery content digest mismatch")
        current = None
        try:
            with _open(root, name) as descriptor:
                current = _sha(_bytes(descriptor))
        except (OSError, ValueError):
            pass
        state = "before" if current == before else "after" if current == after else "changed"
        files[name] = {
            "state": state,
            "current_digest": current,
            "before_digest": before,
            "after_digest": after,
        }
    return {
        "operation_id": operation_id,
        "status": result["status"],
        "receipt": receipt_name,
        "files": files,
    }


def resolve_tracker_migration_recovery(root, operation_id):
    """Acknowledge a manually reconciled, uniformly before/after batch; no target writes."""
    root = Path(root).resolve()
    with project_write_lock(root):
        report = inspect_tracker_migration(root, operation_id)
        states = {row["state"] for row in report["files"].values()}
        if states and states not in ({"before"}, {"after"}):
            raise ValueError("Recovery files are mixed or changed; reconcile them manually first")
        status = "applied" if states == {"after"} else "rolled-back"
        result = {
            "schema": 1,
            "operation_id": operation_id,
            "status": status,
            "manual_reconciliation": True,
        }
        _new_json(root, f".ai-dlc/migrations/{operation_id}.recovered.json", result)
        return result
