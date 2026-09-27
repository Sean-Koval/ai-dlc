"""Explicit migration of pinned provider identities and their artifact references."""

import copy
import os
import tempfile
import tomllib
from pathlib import Path

import tomli_w

from ai_dlc.config import load_project, resolve_layers
from ai_dlc.locking import project_write_lock
from ai_dlc.setup.templates import apply_files, checkout_files
from ai_dlc.work.workflow import Work, WorkService, project_source_digest

ARTIFACTS = {
    "tracker": {"tracker"},
    "specs": {"spec"},
    "scm": {"pr", "branch"},
    "deploy": {"deployment"},
    "knowledge": {"knowledge"},
}


def _validate_connection_plan_request(
    role: str, provider_id: str, config: dict, connection_plan: Path | None
) -> None:
    """A Linear connection plan only accompanies a tracker rebind to the selected linear."""
    if connection_plan is not None and (role != "tracker" or provider_id != "linear"):
        raise ValueError("A Linear connection plan requires rebind tracker linear")
    if connection_plan is not None and config.get("roles", {}).get("tracker") != "linear":
        raise ValueError("A Linear connection migration requires the selected tracker to be linear")


def _collect_work_items(root: Path, role: str, config: dict) -> list[tuple[str, dict, str]]:
    """Every work record bound to the role as (relative path, record, current provider)."""
    all_work_items = []
    for path in sorted((root / ".ai-dlc/work").glob("*.toml")):
        work = Work.model_validate(tomllib.loads(path.read_text(encoding="utf-8"))).model_dump(
            by_alias=True
        )
        if work["id"] != path.stem:
            raise ValueError("Work ID does not match filename")
        old = work["providers"].get(role, config.get("roles", {}).get(role))
        # A local status string is not evidence of completion: retain every work item.
        if old is not None:
            all_work_items.append((path.relative_to(root).as_posix(), work, old))
    return all_work_items


def _plan_rebind(role: str, provider_id: str, work_items: list) -> dict:
    """Describe the retained work and the mapping policy without changing anything."""
    active = [
        {
            "id": work["id"],
            "provider": old,
            "binding": work["bindings"].get(role),
            "artifacts": {k: v for k, v in work["artifacts"].items() if k in ARTIFACTS[role]},
        }
        for _, work, old in work_items
    ]
    return {
        "status": "planned",
        "role": role,
        "provider": provider_id,
        "active_work": active,
        "completion_policy": "Retained work requires mapping; local completion flags are not proof",
    }


def _validate_mappings(role: str, mappings: dict, work_items: list) -> dict:
    """Require one explicit, non-empty replacement per expected artifact of each work item."""
    unknown = set(mappings) - {work["id"] for _, work, _ in work_items}
    if unknown:
        raise ValueError(f"Unknown work mapping: {sorted(unknown)}")
    validated_mappings = {}
    for _, work, _ in work_items:
        replacements = mappings.get(work["id"])
        expected = ARTIFACTS[role] & work["artifacts"].keys()
        if not expected:
            expected = {next(iter(sorted(ARTIFACTS[role])))}
        if (
            not isinstance(replacements, dict)
            or set(replacements) != expected
            or any(
                not isinstance(value, str) or not value.strip() for value in replacements.values()
            )
        ):
            raise ValueError(
                f"Explicit replacement artifact mapping required for {work['id']}: {sorted(expected)}"
            )
        validated_mappings[work["id"]] = replacements
    return validated_mappings


def _stage_and_apply(
    root: Path,
    role: str,
    provider_id: str,
    proposed: dict,
    before: dict,
    work_items: list,
    validated_mappings: dict,
    machine_config: dict | None,
    saved_connection_plan,
) -> None:
    """Rewrite configuration and work records in a staging directory, then apply atomically."""
    after = dict(before)
    with tempfile.TemporaryDirectory(prefix="ai-dlc-rebind-") as temporary:
        stage = Path(temporary).resolve()
        staged_config = stage / "ai-dlc.toml"
        staged_config.write_bytes(before["ai-dlc.toml"])
        if saved_connection_plan is not None:
            from ai_dlc.setup.provider_onboarding import apply_linear_connection

            apply_linear_connection(staged_config, saved_connection_plan)
            proposed = load_project(stage)
        else:
            staged_config.write_text(tomli_w.dumps(proposed), encoding="utf-8", newline="\n")
        resolved = resolve_layers(
            [("project", proposed)] + ([("machine", machine_config)] if machine_config else [])
        ).values
        for name, work, _ in work_items:
            replacements = validated_mappings[work["id"]]
            work["providers"][role] = provider_id
            work["bindings"].pop(role, None)
            work["artifacts"].update(replacements)
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(tomli_w.dumps(work), encoding="utf-8", newline="\n")
            service = WorkService(
                stage,
                resolved,
                state_path=stage / "state",
                _source_digest=project_source_digest(stage),
            )
            updated = service.load(work["id"], mutation=False)
            after[name] = tomli_w.dumps(updated).encode()
        after["ai-dlc.toml"] = staged_config.read_bytes()
        apply_files(root, before, after)


def _rebind(
    root: Path,
    role: str,
    provider_id: str,
    apply: bool = False,
    mappings: dict | None = None,
    *,
    machine_config: dict | None = None,
    connection_plan: Path | None = None,
    environ=None,
    client=None,
) -> dict:
    root = Path(root).resolve()
    if role not in ARTIFACTS:
        raise ValueError("Unknown work provider role")
    if not provider_id.strip():
        raise ValueError("Provider ID is required")
    mappings = mappings or {}
    config = load_project(root)
    _validate_connection_plan_request(role, provider_id, config, connection_plan)
    proposed = copy.deepcopy(config)
    proposed.setdefault("roles", {})[role] = provider_id
    before = checkout_files(root)
    all_work_items = _collect_work_items(root, role, config)
    saved_connection_plan = None
    if connection_plan is not None:
        from ai_dlc.setup.provider_onboarding import _bound_linear_work, _load_connection_plan

        connection_path, saved_connection_plan = _load_connection_plan(root, connection_plan)
        affected_ids = set(_bound_linear_work(root, config))
        work_items = [item for item in all_work_items if item[1]["id"] in affected_ids]
    else:
        work_items = all_work_items
    plan = _plan_rebind(role, provider_id, work_items)
    if connection_plan is not None:
        plan["connection_plan"] = connection_path.relative_to(root).as_posix()
    if not apply:
        return plan
    validated_mappings = _validate_mappings(role, mappings, work_items)

    if connection_plan is not None:
        from ai_dlc.setup.provider_onboarding import revalidate_saved_linear_connection

        config, saved_connection_plan = revalidate_saved_linear_connection(
            root,
            connection_plan,
            environ=os.environ if environ is None else environ,
            client=client,
        )
    _stage_and_apply(
        root,
        role,
        provider_id,
        proposed,
        before,
        work_items,
        validated_mappings,
        machine_config,
        saved_connection_plan,
    )
    return {
        **plan,
        "status": "applied",
        **({"connection": "applied"} if saved_connection_plan is not None else {}),
    }


def rebind(
    root: Path,
    role: str,
    provider_id: str,
    apply: bool = False,
    mappings: dict | None = None,
    *,
    machine_config: dict | None = None,
    connection_plan: Path | None = None,
    environ=None,
    client=None,
) -> dict:
    """Plan or apply an explicit provider rebind under the project write lock."""
    if not apply:
        return _rebind(
            root,
            role,
            provider_id,
            apply,
            mappings,
            machine_config=machine_config,
            connection_plan=connection_plan,
            environ=environ,
            client=client,
        )
    with project_write_lock(root):
        return _rebind(
            root,
            role,
            provider_id,
            apply,
            mappings,
            machine_config=machine_config,
            connection_plan=connection_plan,
            environ=environ,
            client=client,
        )
