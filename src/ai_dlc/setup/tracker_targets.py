"""Explicit reviewed target creation; reconciliation never writes work bindings."""

import copy
import os
import re
import tomllib
import uuid
from pathlib import Path

from ai_dlc.config import digest, read_toml
from ai_dlc.contracts import validate_request
from ai_dlc.locking import project_write_lock
from ai_dlc.providers import Registry
from ai_dlc.work.journal import Journal
from ai_dlc.work.traceability import render_ticket_body
from ai_dlc.work.tracker_migration import (
    _new_json,
    _pending,
    _plan_name,
    _read_json,
    _runtime,
    _snapshot,
    local_source_evidence,
    plan_tracker_migration,
)
from ai_dlc.work.workflow import Work, resolve_work


def _operation(plan, work_id):
    return digest(
        {
            "root": plan["root_digest"],
            "intent": plan["operation_id"],
            "provider": plan["provider"],
            "binding": plan["runtime_digest"],
            "work": work_id,
        }
    )


def _validate(plan):
    fields = {
        "schema",
        "kind",
        "operation_id",
        "root_digest",
        "runtime_digest",
        "snapshot",
        "provider",
        "work_ids",
        "creates",
        "mappings",
        "sources",
        "source",
        "digest",
    }
    if not isinstance(plan, dict) or set(plan) != fields:
        raise ValueError("Invalid target creation plan fields")
    value = copy.deepcopy(plan)
    expected = value.pop("digest")
    if (
        type(plan["schema"]) is not int
        or plan["schema"] != 1
        or plan["kind"] != "tracker-target-creation"
        or digest(value) != expected
    ):
        raise ValueError("Invalid target creation plan schema/digest")
    if not isinstance(plan["operation_id"], str) or not re.fullmatch(
        r"[a-f0-9]{32}", plan["operation_id"]
    ):
        raise ValueError("Invalid target creation operation identity")
    if any(
        not isinstance(plan[key], str) or not plan[key]
        for key in ("root_digest", "runtime_digest", "provider")
    ):
        raise ValueError("Invalid target creation identity")
    if digest(plan["source"]) != digest(local_source_evidence()):
        raise ValueError("Target creation requires the explicit local-records source")
    if not isinstance(plan["work_ids"], list) or not all(
        isinstance(key, str) for key in plan["work_ids"]
    ):
        raise ValueError("Invalid selected work IDs")
    if any(
        not isinstance(plan[key], dict) for key in ("creates", "mappings", "sources", "snapshot")
    ):
        raise ValueError("Invalid target creation mappings")
    ids = plan["work_ids"]
    if (
        ids != sorted(set(ids))
        or not plan["creates"]
        or set(ids) != set(plan["creates"]) | set(plan["mappings"])
        or set(plan["creates"]) & set(plan["mappings"])
        or set(plan["sources"]) != set(ids)
    ):
        raise ValueError(
            "Exactly one create intent or existing mapping is required per selected work"
        )
    for key in ids:
        Work.safe_id(key)
        if f".ai-dlc/work/{key}.toml" not in plan["snapshot"]:
            raise ValueError("Selected source snapshot is missing")
        source = plan["sources"][key]
        if (
            not isinstance(source, dict)
            or set(source) != {"provider", "binding", "reference"}
            or any(v is not None and not isinstance(v, str) for v in source.values())
        ):
            raise ValueError("Invalid source provenance")
    for name, snapshot in plan["snapshot"].items():
        if (
            not isinstance(name, str)
            or not isinstance(snapshot, dict)
            or set(snapshot) != {"device", "inode", "sha256"}
            or any(type(snapshot[key]) is not int for key in ("device", "inode"))
            or not isinstance(snapshot["sha256"], str)
        ):
            raise ValueError("Invalid source snapshot")
    for reference in plan["mappings"].values():
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("Existing target reference is required")
    for key, intent in plan["creates"].items():
        if not isinstance(intent, dict) or set(intent) != {"payload"}:
            raise ValueError("Invalid create intent")
        payload = validate_request("create", intent["payload"]).payload
        if (
            payload != intent["payload"]
            or payload["operation_id"] != _operation(plan, key)
            or payload["correlation"] != f"<!-- ai-dlc:{_operation(plan, key)} -->"
        ):
            raise ValueError("Creation payload or correlation identity changed")
    return plan


def read_tracker_mappings(path) -> dict[str, str]:
    """Read a reviewed mapping table: one ``[work-id]`` table with exactly ``tracker``."""
    raw = read_toml(Path(path)) if path else {}
    if any(not isinstance(row, dict) or set(row) != {"tracker"} for row in raw.values()):
        raise ValueError("Mappings must have exactly tracker = REFERENCE per work table")
    return {key: row["tracker"] for key, row in raw.items()}


def plan_tracker_targets(
    root,
    provider_id,
    *,
    work_ids,
    create_work_ids,
    source,
    mappings=None,
    environ=None,
    machine=None,
    machine_config=None,
    registry=None,
):
    """Preview exact local-record-derived content; no source/target service requests."""
    if source != "local-records":
        raise ValueError("Explicit source=local-records is required; remote history is unknown")
    root = Path(root).resolve()
    env = os.environ if environ is None else environ
    with project_write_lock(root):
        snapshot, contents = _snapshot(root)
        config = _runtime(root, environ=env, machine=machine, machine_config=machine_config)
        if provider_id not in config.get("providers", {}):
            raise ValueError("Target tracker requires an explicit configured provider alias")
        registry = registry or Registry(config, root=root, environ=env)
        if not callable(getattr(registry.get(provider_id), "invoke", None)):
            raise TypeError("Target provider does not expose tracker operations")
        if (
            not isinstance(work_ids, list)
            or not isinstance(create_work_ids, list)
            or not all(isinstance(key, str) for key in work_ids + create_work_ids)
            or len(set(work_ids)) != len(work_ids)
            or len(set(create_work_ids)) != len(create_work_ids)
        ):
            raise ValueError("Explicit unique selected/create work IDs are required")
        planned = {
            "schema": 1,
            "kind": "tracker-target-creation",
            "operation_id": uuid.uuid4().hex,
            "root_digest": digest(str(root)),
            "runtime_digest": digest(config),
            "snapshot": snapshot,
            "provider": provider_id,
            "work_ids": sorted(work_ids),
            "creates": {},
            "mappings": copy.deepcopy(mappings or {}),
            "sources": {},
            "source": local_source_evidence(),
        }
        for work_id in work_ids:
            Work.safe_id(work_id)
            name = f".ai-dlc/work/{work_id}.toml"
            if name not in contents:
                raise ValueError(f"Unknown selected work: {work_id}")
            work = resolve_work(tomllib.loads(contents[name].decode()), config, work_id)
            if not work["reviewed"]:
                raise ValueError("Selected work must be reviewed before creating a target")
            planned["sources"][work_id] = {
                "provider": work["providers"].get("tracker"),
                "binding": work["bindings"].get("tracker"),
                "reference": work["artifacts"].get("tracker"),
            }
            if work_id in create_work_ids:
                operation = _operation(planned, work_id)
                planned["creates"][work_id] = {
                    "payload": {
                        "title": work["title"],
                        "body": render_ticket_body(work),
                        "correlation": f"<!-- ai-dlc:{operation} -->",
                        "operation_id": operation,
                    }
                }
        for intent in planned["creates"].values():
            intent["payload"] = validate_request("create", intent["payload"]).payload
        if set(create_work_ids) != set(planned["creates"]):
            raise ValueError("Create work IDs must be explicitly selected")
        planned["digest"] = digest(planned)
        _validate(planned)
        return planned


def save_tracker_targets_plan(root, plan, path):
    root = Path(root).resolve()
    _validate(plan)
    if plan["root_digest"] != digest(str(root)):
        raise ValueError("Target creation root changed")
    name = _plan_name(root, path)
    _new_json(root, name, plan)
    return name


def _fresh(root, plan):
    try:
        return _snapshot(root)[0] == plan["snapshot"]
    except (OSError, ValueError):
        return False


def _canonical(item):
    return {key: item[key] for key in ("id", "url", "state")}


def _remember_target(root, journal, operation_id, item, retained, work_id, *, refresh=False):
    """Keep the first durable identity; serialize comparison with result publication."""
    candidate = _canonical(item)
    with project_write_lock(root):
        record = journal.lookup(operation_id)
        if record is None:
            raise ValueError("Creation journal intent is missing; preserve local state")
        known = record["result"]
        if known is not None:
            retained[work_id] = _canonical(known)
            if (candidate["id"], candidate["url"]) != (known["id"], known["url"]):
                raise ValueError("Known target identity changed; retain the original reference")
        if known is None or refresh:
            journal.succeed(operation_id, candidate)
            retained[work_id] = candidate


def _begin_creation_records(journal, plan):
    """Validate every full immutable fingerprint before any remote result reuse."""
    return {
        key: journal.begin(
            intent["payload"]["operation_id"], {"creation_plan": plan, "work_id": key}
        )
        for key, intent in plan["creates"].items()
    }


def _create_target(root, plan, registry, payload, *, env, machine, machine_config):
    """Create under the project lock only while the local snapshot is unchanged."""
    with project_write_lock(root):
        _pending(root)
        if (
            not _fresh(root, plan)
            or digest(_runtime(root, environ=env, machine=machine, machine_config=machine_config))
            != plan["runtime_digest"]
        ):
            raise ValueError("Local creation snapshot changed; only reconcile existing targets")
        return registry.invoke(plan["provider"], "create", payload)


def _locate_target(root, plan, registry, record, payload, *, env, machine, machine_config):
    """Find, reread or create one target; absence never authorizes a retry."""
    found = registry.invoke(plan["provider"], "find", {"correlation": payload["correlation"]})[
        "items"
    ]
    if len(found) > 1:
        raise ValueError("Duplicate target correlation; inspect retained targets")
    if found:
        return found[0]
    if record["status"] == "succeeded":
        known = record["result"]
        if not isinstance(known, dict):
            raise ValueError("Successful creation journal lacks target identity")
        return registry.invoke(plan["provider"], "read", {"reference": known["id"]})
    if not record["created"]:
        raise RuntimeError("Creation remains uncertain; absence never authorizes retry")
    return _create_target(
        root, plan, registry, payload, env=env, machine=machine, machine_config=machine_config
    )


def _resolve_created_target(
    root, plan, registry, journal, record, work_id, retained, *, env, machine, machine_config
):
    """Resolve one create intent and journal its verified identity."""
    payload = plan["creates"][work_id]["payload"]
    if record["result"] is not None:
        retained[work_id] = _canonical(record["result"])
    item = _locate_target(
        root,
        plan,
        registry,
        record,
        payload,
        env=env,
        machine=machine,
        machine_config=machine_config,
    )
    _remember_target(root, journal, payload["operation_id"], item, retained, work_id)
    # Independent read establishes current identity before accepting a mapping.
    checked = registry.invoke(plan["provider"], "read", {"reference": item["id"]})
    if (checked["id"], checked["url"]) != (item["id"], item["url"]):
        raise ValueError("Created target identity changed")
    _remember_target(
        root, journal, payload["operation_id"], checked, retained, work_id, refresh=True
    )
    return checked


def _resolve_targets(root, plan, registry, journal, records, *, env, machine, machine_config):
    """Resolve every selected work item, retaining targets across transport failures."""
    results, unresolved, retained = {}, {}, {}
    for work_id in plan["work_ids"]:
        try:
            if work_id in plan["mappings"]:
                item = registry.invoke(
                    plan["provider"], "read", {"reference": plan["mappings"][work_id]}
                )
            else:
                item = _resolve_created_target(
                    root,
                    plan,
                    registry,
                    journal,
                    records[work_id],
                    work_id,
                    retained,
                    env=env,
                    machine=machine,
                    machine_config=machine_config,
                )
            results[work_id] = _canonical(item)
            retained[work_id] = results[work_id]
        except Exception as exc:  # noqa: BLE001 -- preserve targets after arbitrary transport failures
            if work_id in plan["creates"] and work_id not in retained:
                journal.uncertain(plan["creates"][work_id]["payload"]["operation_id"])
            unresolved[work_id] = str(exc)
    return results, unresolved, retained


def _verify_migration_targets(migration_plan, results):
    """Every planned mapping must still name the reconciled target identity."""
    for key, mapped in migration_plan["mappings"].items():
        target = mapped["target"]
        if (target["id"], target["url"]) != (results[key]["id"], results[key]["url"]):
            raise ValueError("Known target identity changed during final verification")


def _creation_evidence(plan):
    """Evidence tying the migration plan back to the reviewed creation intent."""
    return {
        "operation_id": plan["operation_id"],
        "intent_digest": plan["digest"],
        "targets": {
            key: {
                "operation_id": intent["payload"]["operation_id"],
                "correlation": intent["payload"]["correlation"],
            }
            for key, intent in plan["creates"].items()
        },
    }


def _bind_creation_evidence(migration_plan, plan):
    """Attach creation evidence and recompute the plan digest last."""
    migration_plan["evidence"]["creation"] = _creation_evidence(plan)
    migration_plan.pop("digest")
    migration_plan["digest"] = digest(migration_plan)
    return migration_plan


def _plan_selected_migration(root, plan, results, registry, *, env, machine, machine_config):
    """Plan the separate local apply and verify it against the reconciled targets."""
    migration_plan = plan_tracker_migration(
        root,
        plan["provider"],
        mode="selected",
        work_ids=plan["work_ids"],
        mappings={key: row["id"] for key, row in results.items()},
        environ=env,
        machine=machine,
        machine_config=machine_config,
        registry=registry,
    )
    _verify_migration_targets(migration_plan, results)
    if (
        migration_plan["snapshot"] != plan["snapshot"]
        or migration_plan["runtime_digest"] != plan["runtime_digest"]
    ):
        return "local-conflict", None
    return "resolved", _bind_creation_evidence(migration_plan, plan)


def _summarize_reconciliation(
    root, plan, results, unresolved, registry, *, env, machine, machine_config
):
    """Derive the final status and, when resolved, the local migration plan."""
    status = "unresolved" if unresolved else "resolved"
    migration_plan = None
    if not _fresh(root, plan):
        status = "local-conflict"
    elif not unresolved:
        if len({item["id"] for item in results.values()}) != len(results):
            status = "unresolved"
            unresolved["mappings"] = "Duplicate target identity across selected work"
        else:
            try:
                status, migration_plan = _plan_selected_migration(
                    root,
                    plan,
                    results,
                    registry,
                    env=env,
                    machine=machine,
                    machine_config=machine_config,
                )
            except Exception as exc:  # noqa: BLE001 -- preserve targets after arbitrary transport failures
                status, migration_plan = "unresolved", None
                unresolved["mappings"] = str(exc)
    return status, migration_plan


def _reconciliation_result(plan, status, results, retained, unresolved, migration_plan):
    """Shape the reconciliation report."""
    return {
        "status": status,
        "operation_id": plan["operation_id"],
        "targets": results,
        "retained_targets": retained,
        "unresolved": unresolved,
        "migration_plan": migration_plan,
        "next_action": "Review/save the local migration plan, then apply separately."
        if migration_plan
        else "Retain the saved intent and local state; rerun only reconciles. Reuse retained targets in fresh existing mappings after local conflicts.",
    }


def reconcile_tracker_targets(
    root, plan, *, environ=None, machine=None, machine_config=None, registry=None
):
    """Reconcile an exact reviewed intent, then preview a separate local apply."""
    root = Path(root).resolve()
    env = os.environ if environ is None else environ
    if isinstance(plan, (str, Path)):
        plan = _read_json(root, _plan_name(root, plan))
    plan = copy.deepcopy(_validate(plan))
    if plan["root_digest"] != digest(str(root)):
        raise ValueError("Target creation root changed")
    config = _runtime(root, environ=env, machine=machine, machine_config=machine_config)
    if digest(config) != plan["runtime_digest"]:
        raise ValueError("Target creation effective destination/configuration changed")
    registry = registry or Registry(config, root=root, environ=env)
    state = Path(env.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "ai-dlc"
    with project_write_lock(root):
        journal = Journal(state / "tracker-migrations" / plan["root_digest"] / "operations.sqlite3")
    try:
        records = _begin_creation_records(journal, plan)
        results, unresolved, retained = _resolve_targets(
            root,
            plan,
            registry,
            journal,
            records,
            env=env,
            machine=machine,
            machine_config=machine_config,
        )
        status, migration_plan = _summarize_reconciliation(
            root,
            plan,
            results,
            unresolved,
            registry,
            env=env,
            machine=machine,
            machine_config=machine_config,
        )
        return _reconciliation_result(plan, status, results, retained, unresolved, migration_plan)
    finally:
        journal.db.close()
