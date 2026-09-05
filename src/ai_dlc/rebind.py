"""Explicit migration of pinned provider identities and their artifact references."""

import copy
import os
import tempfile
import tomllib
from pathlib import Path

import tomli_w

from ai_dlc.config import load_project, resolve_layers
from ai_dlc.templates import _apply, _files
from ai_dlc.workflow import Work, WorkService

ARTIFACTS = {
    "tracker": {"tracker"},
    "specs": {"spec"},
    "scm": {"pr", "branch"},
    "deploy": {"deployment"},
    "knowledge": {"knowledge"},
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
    root = Path(root).resolve()
    if role not in ARTIFACTS:
        raise ValueError("Unknown work provider role")
    if not provider_id.strip():
        raise ValueError("Provider ID is required")
    mappings = mappings or {}
    config = load_project(root)
    if connection_plan is not None and (role != "tracker" or provider_id != "linear"):
        raise ValueError("A Linear connection plan requires rebind tracker linear")
    if connection_plan is not None and config.get("roles", {}).get("tracker") != "linear":
        raise ValueError("A Linear connection migration requires the selected tracker to be linear")
    proposed = copy.deepcopy(config)
    proposed.setdefault("roles", {})[role] = provider_id
    before = _files(root)
    all_work_items = []
    for path in sorted((root / ".ai-dlc/work").glob("*.toml")):
        work = Work.model_validate(tomllib.loads(path.read_text())).model_dump(by_alias=True)
        if work["id"] != path.stem:
            raise ValueError("Work ID does not match filename")
        old = work["providers"].get(role, config.get("roles", {}).get(role))
        # A local status string is not evidence of completion: retain every work item.
        if old is not None:
            all_work_items.append((path.relative_to(root).as_posix(), work, old))
    saved_connection_plan = None
    if connection_plan is not None:
        from ai_dlc.provider_onboarding import _bound_linear_work, _load_connection_plan

        connection_path, saved_connection_plan = _load_connection_plan(root, connection_plan)
        affected_ids = set(_bound_linear_work(root, config))
        work_items = [item for item in all_work_items if item[1]["id"] in affected_ids]
    else:
        work_items = all_work_items
    active = [
        {
            "id": work["id"],
            "provider": old,
            "binding": work["bindings"].get(role),
            "artifacts": {k: v for k, v in work["artifacts"].items() if k in ARTIFACTS[role]},
        }
        for _, work, old in work_items
    ]
    plan = {
        "status": "planned",
        "role": role,
        "provider": provider_id,
        "active_work": active,
        "completion_policy": "Retained work requires mapping; local completion flags are not proof",
    }
    if connection_plan is not None:
        plan["connection_plan"] = connection_path.relative_to(root).as_posix()
    if not apply:
        return plan
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

    if connection_plan is not None:
        from ai_dlc.provider_onboarding import revalidate_saved_linear_connection

        config, saved_connection_plan = revalidate_saved_linear_connection(
            root,
            connection_plan,
            environ=os.environ if environ is None else environ,
            client=client,
        )
    after = dict(before)
    with tempfile.TemporaryDirectory(prefix="ai-dlc-rebind-") as temporary:
        stage = Path(temporary).resolve()
        staged_config = stage / "ai-dlc.toml"
        staged_config.write_bytes(before["ai-dlc.toml"])
        if saved_connection_plan is not None:
            from ai_dlc.provider_onboarding import apply_linear_connection

            apply_linear_connection(staged_config, saved_connection_plan)
            proposed = load_project(stage)
        else:
            staged_config.write_text(tomli_w.dumps(proposed))
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
            path.write_text(tomli_w.dumps(work))
            service = WorkService(stage, resolved, state_path=stage / "state")
            updated = service.load(work["id"], mutation=False)
            after[name] = tomli_w.dumps(updated).encode()
        after["ai-dlc.toml"] = staged_config.read_bytes()
        _apply(root, before, after)
    return {
        **plan,
        "status": "applied",
        **({"connection": "applied"} if saved_connection_plan is not None else {}),
    }
