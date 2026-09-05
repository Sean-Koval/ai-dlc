import copy
import json
import os
import re
import shlex
import tempfile
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, NoReturn

import httpx

from ai_dlc.config import digest
from ai_dlc.providers.linear import LinearProvider
from ai_dlc.workflow import Work

_ORGANIZATION_QUERY = """
query LinearDiscoveryOrganization {
  organization { id name urlKey }
}
"""

_TEAMS_QUERY = """
query LinearDiscoveryTeams($after: String) {
  teams(first: 50, after: $after) {
    nodes { id name key }
    pageInfo { hasNextPage endCursor }
  }
}
"""

_STATES_QUERY = """
query LinearDiscoveryStates($teamId: String!, $after: String) {
  team(id: $teamId) {
    id
    states(first: 50, after: $after) {
      nodes { id name type }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""


def _incomplete(detail: str) -> NoReturn:
    raise RuntimeError(f"Linear discovery returned incomplete {detail}")


def _query(provider: LinearProvider, query: str, variables: dict[str, Any]) -> Mapping[str, Any]:
    try:
        data = provider.query(query, variables)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            raise RuntimeError("Linear authorization failed") from None
        raise RuntimeError(
            f"Linear discovery request failed with HTTP status {exc.response.status_code}"
        ) from None
    except httpx.HTTPError:
        raise RuntimeError("Linear discovery request failed") from None
    except RuntimeError:
        # Provider errors can contain upstream GraphQL messages. Those messages are
        # intentionally not forwarded because an upstream response may echo a secret.
        raise RuntimeError("Linear discovery failed because GraphQL returned errors") from None
    except (AttributeError, KeyError, TypeError, ValueError):
        raise RuntimeError("Linear discovery returned an incomplete response") from None
    if not isinstance(data, Mapping):
        _incomplete("response")
    return data


def _connection_nodes(fetch: Callable[[str | None], Any], *, label: str) -> list[Mapping[str, Any]]:
    nodes: list[Mapping[str, Any]] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    while True:
        connection = fetch(cursor)
        if not isinstance(connection, Mapping):
            _incomplete(f"{label} pagination")
        page_nodes = connection.get("nodes")
        page_info = connection.get("pageInfo")
        if not isinstance(page_nodes, list) or not isinstance(page_info, Mapping):
            _incomplete(f"{label} pagination")
        if not all(isinstance(node, Mapping) for node in page_nodes):
            _incomplete(f"{label} data")
        has_next_page = page_info.get("hasNextPage")
        if not isinstance(has_next_page, bool):
            _incomplete(f"{label} pagination")
        nodes.extend(page_nodes)
        if not has_next_page:
            return nodes
        next_cursor = page_info.get("endCursor")
        if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
            raise RuntimeError(f"Linear discovery returned incomplete {label} pagination")
        seen_cursors.add(next_cursor)
        cursor = next_cursor


def _selected_fields(node: Mapping[str, Any], fields: tuple[str, ...], *, label: str) -> dict:
    selected = {field: node.get(field) for field in fields}
    if any(not isinstance(value, str) or not value for value in selected.values()):
        raise RuntimeError(f"Linear discovery returned incomplete {label} data")
    return selected


def discover_linear(
    settings: dict,
    *,
    environ: Mapping[str, str],
    client,
) -> dict:
    """Discover the organization, teams, and workflow states visible to one credential."""
    _validate_linear_settings(settings)
    token_env = settings.get("token_env", "LINEAR_API_KEY")
    if not isinstance(token_env, str) or not token_env:
        raise ValueError("Linear token_env must name an environment variable")
    if not environ.get(token_env):
        raise ValueError(f"Set the configured Linear credential environment variable: {token_env}")

    provider = LinearProvider(settings, client=client, environ=environ)
    organization_data = _query(provider, _ORGANIZATION_QUERY, {}).get("organization")
    if not isinstance(organization_data, Mapping):
        _incomplete("organization data")
    organization = _selected_fields(
        organization_data, ("id", "name", "urlKey"), label="organization"
    )

    team_nodes = _connection_nodes(
        lambda after: _query(provider, _TEAMS_QUERY, {"after": after}).get("teams"),
        label="team",
    )
    teams = []
    for team_node in team_nodes:
        team = _selected_fields(team_node, ("id", "name", "key"), label="team")
        team_id = team["id"]

        def fetch_states(after: str | None, *, team_id: str = team_id) -> Any:
            team_data = _query(
                provider,
                _STATES_QUERY,
                {"teamId": team_id, "after": after},
            ).get("team")
            if not isinstance(team_data, Mapping) or team_data.get("id") != team_id:
                _incomplete("team state data")
            return team_data.get("states")

        state_nodes = _connection_nodes(fetch_states, label=f"workflow state for team {team_id}")
        team["states"] = [
            _selected_fields(state, ("id", "name", "type"), label="workflow state")
            for state in state_nodes
        ]
        teams.append(team)

    return {"organization": organization, "teams": teams}


_SELECTION_FIELDS = {"organization_id", "team_id", "in_progress", "closed"}
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _validate_linear_settings(settings: Any) -> dict:
    if not isinstance(settings, dict):
        raise TypeError("Configure providers.linear before connecting Linear")
    effective_kind = settings.get("kind", settings.get("type", "linear"))
    if effective_kind != "linear":
        raise ValueError("Configured provider linear does not use the Linear adapter")
    return settings


def _selection_value(selection: Mapping[str, Any], field: str) -> str:
    value = selection.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Linear {field} selection is required")
    return value


def plan_linear_connection(config: dict, discovery: dict, selection: dict) -> dict:
    """Validate explicit Linear IDs and return a non-secret configuration patch."""
    if not isinstance(config, dict):
        raise TypeError("Linear connection config must be a dictionary")
    if not isinstance(discovery, Mapping):
        raise TypeError("Linear discovery result must be a mapping")
    if not isinstance(selection, Mapping) or set(selection) != _SELECTION_FIELDS:
        raise ValueError("Linear selection must contain organization, team, and status IDs")

    selected = {field: _selection_value(selection, field) for field in _SELECTION_FIELDS}
    organization = discovery.get("organization")
    if (
        not isinstance(organization, Mapping)
        or organization.get("id") != selected["organization_id"]
    ):
        raise ValueError("Selected Linear organization is not in discovery")

    teams = discovery.get("teams")
    if not isinstance(teams, list):
        raise TypeError("Linear discovery teams must be a list")
    matching_teams = [
        team
        for team in teams
        if isinstance(team, Mapping) and team.get("id") == selected["team_id"]
    ]
    if len(matching_teams) != 1:
        raise ValueError("Selected Linear team is not in the selected organization")
    states = matching_teams[0].get("states")
    if not isinstance(states, list):
        raise TypeError("Selected Linear team workflow states must be a list")

    def require_state(field: str, expected_type: str) -> None:
        matching_states = [
            state
            for state in states
            if isinstance(state, Mapping) and state.get("id") == selected[field]
        ]
        if len(matching_states) != 1:
            raise ValueError(f"Selected Linear {field} state is not in the selected team")
        if matching_states[0].get("type") != expected_type:
            raise ValueError(f"Selected Linear {field} state must have type {expected_type}")

    require_state("in_progress", "started")
    require_state("closed", "completed")

    normalized = {
        "organization_id": selected["organization_id"],
        "team_id": selected["team_id"],
        "in_progress": selected["in_progress"],
        "closed": selected["closed"],
    }
    return {
        "provider": "linear",
        "before_digest": digest(config),
        "selected": normalized,
        "patch": {
            "team_id": normalized["team_id"],
            "statuses": {
                "in_progress": normalized["in_progress"],
                "closed": normalized["closed"],
            },
        },
    }


def _validated_plan(plan: dict) -> tuple[str, dict[str, Any]]:
    if not isinstance(plan, dict) or set(plan) != {
        "provider",
        "before_digest",
        "selected",
        "patch",
    }:
        raise ValueError("Invalid Linear connection plan")
    before_digest = plan.get("before_digest")
    selected = plan.get("selected")
    if (
        plan.get("provider") != "linear"
        or not isinstance(before_digest, str)
        or not _DIGEST.fullmatch(before_digest)
        or not isinstance(selected, Mapping)
        or set(selected) != _SELECTION_FIELDS
    ):
        raise ValueError("Invalid Linear connection plan")
    normalized = {field: _selection_value(selected, field) for field in _SELECTION_FIELDS}
    expected_patch = {
        "team_id": normalized["team_id"],
        "statuses": {
            "in_progress": normalized["in_progress"],
            "closed": normalized["closed"],
        },
    }
    if plan.get("patch") != expected_patch:
        raise ValueError("Invalid Linear connection plan patch")
    return before_digest, expected_patch


def _comment_suffix(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
        elif quote == '"' and character == "\\":
            escaped = True
        elif quote is not None and character == quote:
            quote = None
        elif quote is None and character in {'"', "'"}:
            quote = character
        elif quote is None and character == "#":
            start = index
            while start and value[start - 1] in {" ", "\t"}:
                start -= 1
            return value[start:]
    return ""


def _is_escaped(value: str, index: int) -> bool:
    backslashes = 0
    index -= 1
    while index >= 0 and value[index] == "\\":
        backslashes += 1
        index -= 1
    return bool(backslashes % 2)


def _structural_lines(lines: list[str]) -> list[bool]:
    """Mark lines that begin outside a TOML multiline string."""
    multiline: str | None = None
    structural = []
    for line in lines:
        structural.append(multiline is None)
        index = 0
        single: str | None = None
        while index < len(line):
            if multiline == "basic":
                if line.startswith('"""', index) and not _is_escaped(line, index):
                    multiline = None
                    index += 3
                else:
                    index += 1
            elif multiline == "literal":
                if line.startswith("'''", index):
                    multiline = None
                    index += 3
                else:
                    index += 1
            elif single == "basic":
                if line[index] == '"' and not _is_escaped(line, index):
                    single = None
                index += 1
            elif single == "literal":
                if line[index] == "'":
                    single = None
                index += 1
            elif line[index] == "#":
                break
            elif line.startswith('"""', index):
                multiline = "basic"
                index += 3
            elif line.startswith("'''", index):
                multiline = "literal"
                index += 3
            elif line[index] == '"':
                single = "basic"
                index += 1
            elif line[index] == "'":
                single = "literal"
                index += 1
            else:
                index += 1
    return structural


def _marker_path(value: Any, path: tuple[str, ...] = ()) -> tuple[str, ...] | None:
    if not isinstance(value, dict):
        return None
    if value.get("__ai_dlc_table_marker__") is True:
        return path
    for key, child in value.items():
        found = _marker_path(child, (*path, key))
        if found is not None:
            return found
    return None


def _table_path(line: str) -> tuple[str, ...] | None:
    if not line.lstrip().startswith("["):
        return None
    try:
        parsed = tomllib.loads(f"{line.rstrip()}\n__ai_dlc_table_marker__ = true\n")
    except tomllib.TOMLDecodeError:
        return None
    return _marker_path(parsed)


def _table_paths(text: str) -> list[tuple[str, ...] | None]:
    lines = text.splitlines(keepends=True)
    structural = _structural_lines(lines)
    return [_table_path(line) if structural[index] else None for index, line in enumerate(lines)]


def _unsupported_representation() -> NoReturn:
    raise ValueError(
        "Linear TOML representation cannot be updated safely; use "
        "[providers.linear] and [providers.linear.statuses] tables"
    )


def _validate_editable_representation(
    config: dict[str, Any], table_paths: list[tuple[str, ...] | None]
) -> None:
    providers = config.get("providers")
    if providers is None:
        return
    if not isinstance(providers, dict):
        _unsupported_representation()
    linear = providers.get("linear")
    if linear is None:
        return
    if not isinstance(linear, dict):
        _unsupported_representation()

    provider_path = ("providers", "linear")
    status_path = (*provider_path, "statuses")
    paths = {path for path in table_paths if path is not None}
    if provider_path not in paths and not any(
        path[: len(provider_path)] == provider_path and len(path) > len(provider_path)
        for path in paths
    ):
        _unsupported_representation()

    statuses = linear.get("statuses")
    if statuses is None:
        return
    if not isinstance(statuses, dict):
        _unsupported_representation()
    if status_path not in paths and not any(
        path[: len(status_path)] == status_path and len(path) > len(status_path) for path in paths
    ):
        _unsupported_representation()


def _set_table_value(text: str, table: str, key: str, value: str) -> str:
    lines = text.splitlines(keepends=True)
    structural = _structural_lines(lines)
    paths = _table_paths(text)
    target_path = tuple(table.split("."))
    start = next((index for index, path in enumerate(paths) if path == target_path), None)
    encoded = json.dumps(value, ensure_ascii=False)

    if start is None:
        if text and not text.endswith(("\n", "\r")):
            text += "\n"
        separator = "" if not text or text.endswith("\n\n") else "\n"
        return f"{text}{separator}[{table}]\n{key} = {encoded}\n"

    end = next((index for index in range(start + 1, len(lines)) if paths[index]), len(lines))
    key_pattern = rf'(?:{re.escape(key)}|"{re.escape(key)}"|\'{re.escape(key)}\')'
    assignment = re.compile(rf"^(\s*{key_pattern}\s*=\s*)(.*?)(\r?\n)?$")
    for index in range(start + 1, end):
        if not structural[index]:
            continue
        match = assignment.match(lines[index])
        if match:
            newline = match.group(3) or ""
            lines[index] = f"{match.group(1)}{encoded}{_comment_suffix(match.group(2))}{newline}"
            return "".join(lines)
    lines.insert(end, f"{key} = {encoded}\n")
    return "".join(lines)


def _render_patch(text: str, patch: dict[str, Any]) -> str:
    rendered = _set_table_value(text, "providers.linear", "team_id", patch["team_id"])
    rendered = _set_table_value(
        rendered,
        "providers.linear.statuses",
        "in_progress",
        patch["statuses"]["in_progress"],
    )
    return _set_table_value(
        rendered,
        "providers.linear.statuses",
        "closed",
        patch["statuses"]["closed"],
    )


def _expected_config(config: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    expected = copy.deepcopy(config)
    providers = expected.setdefault("providers", {})
    if not isinstance(providers, dict):
        _unsupported_representation()
    linear = providers.setdefault("linear", {})
    if not isinstance(linear, dict):
        _unsupported_representation()
    statuses = linear.setdefault("statuses", {})
    if not isinstance(statuses, dict):
        _unsupported_representation()
    linear["team_id"] = patch["team_id"]
    statuses["in_progress"] = patch["statuses"]["in_progress"]
    statuses["closed"] = patch["statuses"]["closed"]
    return expected


def apply_linear_connection(path: Path, plan: dict) -> None:
    """Atomically apply an unchanged, reviewed Linear mapping plan."""
    path = Path(path)
    before_digest, patch = _validated_plan(plan)
    try:
        current_text = path.read_bytes().decode()
        current_config = tomllib.loads(current_text)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        raise ValueError("Current Linear configuration is invalid") from None
    if digest(current_config) != before_digest:
        raise ValueError("Linear connection plan source digest changed")
    _validate_editable_representation(current_config, _table_paths(current_text))
    rendered = _render_patch(current_text, patch)
    # Parse and compare semantics before staging so a preservation bug can never
    # replace the source merely because the rewritten text remains valid TOML.
    try:
        rendered_config = tomllib.loads(rendered)
    except tomllib.TOMLDecodeError:
        _unsupported_representation()
    if digest(rendered_config) != digest(_expected_config(current_config, patch)):
        _unsupported_representation()

    mode = path.stat().st_mode & 0o777
    descriptor, staged_name = tempfile.mkstemp(dir=path.parent, prefix=".ai-dlc-linear-")
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged_name, mode)
        # Re-read immediately before the atomic replace. This is deliberately the
        # same canonical digest used at preview time, so comment-only edits survive.
        try:
            latest_text = path.read_bytes().decode()
            latest_config = tomllib.loads(latest_text)
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            raise ValueError("Current Linear configuration is invalid") from None
        if digest(latest_config) != before_digest:
            raise ValueError("Linear connection plan source digest changed")
        if latest_text != current_text:
            raise ValueError("Linear connection source changed during apply")
        os.replace(staged_name, path)
    finally:
        if os.path.exists(staged_name):
            os.unlink(staged_name)


def _connection_plan_path(root: Path, requested: Path) -> Path:
    root = Path(root).resolve()
    local = root / ".ai-dlc/local"
    resolved_local = local.resolve(strict=False)
    if not resolved_local.is_relative_to(root):
        raise ValueError("Linear connection plan must stay under .ai-dlc/local")
    candidate = requested if requested.is_absolute() else root / requested
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(resolved_local):
        raise ValueError("Linear connection plan must stay under .ai-dlc/local")
    return resolved


def _save_connection_plan(root: Path, requested: Path, plan: dict) -> Path:
    _validated_plan(plan)
    path = _connection_plan_path(root, requested)
    if path.exists() and not path.is_file():
        raise ValueError("Linear connection plan path must be a file")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, staged_name = tempfile.mkstemp(dir=path.parent, prefix=".ai-dlc-linear-plan-")
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(plan, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged_name, 0o600)
        os.replace(staged_name, path)
    finally:
        if os.path.exists(staged_name):
            os.unlink(staged_name)
    return path


def _load_connection_plan(root: Path, requested: Path) -> tuple[Path, dict]:
    path = _connection_plan_path(root, requested)
    try:
        plan = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Linear connection plan file is invalid or unavailable") from None
    _validated_plan(plan)
    return path, plan


def _bound_linear_work(root: Path, config: dict) -> list[str]:
    work_root = root / ".ai-dlc/work"
    bound = []
    for path in sorted(work_root.glob("*.toml")):
        try:
            raw = tomllib.loads(path.read_text())
            work = Work.model_validate(raw)
        except (OSError, tomllib.TOMLDecodeError, ValueError, TypeError):
            raise ValueError(
                f"Cannot verify Linear work bindings in {path.name}; repair the work record"
            ) from None
        provider = work.providers.get("tracker", config.get("roles", {}).get("tracker"))
        if provider == "linear" and work.bindings.get("tracker"):
            bound.append(work.id)
    return bound


def _guard_mapping_change(
    root: Path,
    config: dict,
    plan: dict,
    *,
    plan_file: Path | None = None,
) -> None:
    linear = config.get("providers", {}).get("linear", {})
    statuses = linear.get("statuses", {}) if isinstance(linear, Mapping) else {}
    current = {
        "team_id": linear.get("team_id") if isinstance(linear, Mapping) else None,
        "statuses": {
            "in_progress": statuses.get("in_progress") if isinstance(statuses, Mapping) else None,
            "closed": statuses.get("closed") if isinstance(statuses, Mapping) else None,
        },
    }
    if current == plan["patch"]:
        return
    bound = _bound_linear_work(root, config)
    if bound:
        root_argument = shlex.quote(str(root))
        mappings = ".ai-dlc/local/linear-rebind.toml"
        if plan_file is not None:
            connection_plan = _connection_plan_path(root, plan_file).relative_to(root).as_posix()
            prerequisite = ""
        else:
            connection_plan = ".ai-dlc/local/linear-plan.json"
            selected = plan["selected"]
            prerequisite = (
                " First save this reviewed selection with `ai-dlc provider connect linear "
                f"--root {root_argument} "
                f"--organization {shlex.quote(selected['organization_id'])} "
                f"--team {shlex.quote(selected['team_id'])} "
                f"--in-progress {shlex.quote(selected['in_progress'])} "
                f"--closed {shlex.quote(selected['closed'])} "
                f"--plan-file {connection_plan}`."
            )
        command = (
            "ai-dlc project rebind tracker linear "
            f"--root {root_argument} --connection-plan {connection_plan} "
            f"--mappings {mappings} --no-plan"
        )
        raise ValueError(
            "Linear mapping change refused because tracker work is already bound: "
            + ", ".join(bound)
            + "."
            + prerequisite
            + f" Complete the reviewed migration with `{command}`; "
            "the mappings file must replace every affected tracker artifact"
        )


def revalidate_saved_linear_connection(
    root: Path,
    plan_file: Path,
    *,
    environ: Mapping[str, str],
    client=None,
) -> tuple[dict, dict]:
    """Load one saved plan and revalidate its exact selection against fresh Linear reads."""
    from ai_dlc.config import load_project

    root = Path(root).resolve()
    config = load_project(root)
    settings = _validate_linear_settings(config.get("providers", {}).get("linear"))
    _, saved_plan = _load_connection_plan(root, plan_file)
    owned_client = client is None
    active_client = httpx.Client() if owned_client else client
    try:
        discovery = discover_linear(settings, environ=environ, client=active_client)
    finally:
        if owned_client:
            active_client.close()
    fresh = plan_linear_connection(config, discovery, saved_plan["selected"])
    if fresh["patch"] != saved_plan["patch"]:
        raise ValueError("Linear connection plan no longer matches fresh discovery")
    if fresh["before_digest"] != saved_plan["before_digest"]:
        raise ValueError("Linear connection plan source digest changed")
    return config, saved_plan


def connect_linear_provider(
    root: Path,
    *,
    organization: str | None = None,
    team: str | None = None,
    in_progress: str | None = None,
    closed: str | None = None,
    plan_file: Path | None = None,
    apply: bool = False,
    environ: Mapping[str, str],
    client=None,
) -> dict:
    """Discover, preview, or apply one explicitly reviewed Linear connection."""
    selections = {
        "organization_id": organization,
        "team_id": team,
        "in_progress": in_progress,
        "closed": closed,
    }
    supplied = [value is not None for value in selections.values()]
    if apply:
        if plan_file is None:
            raise ValueError("Linear connection apply requires --plan-file")
        if any(supplied):
            raise ValueError("Linear connection apply consumes a saved plan; omit selection flags")
    elif any(supplied) and not all(supplied):
        raise ValueError("Linear connection preview requires every selection flag")
    elif plan_file is not None and not all(supplied):
        raise ValueError("Saving a Linear connection plan requires every selection flag")

    root = Path(root).resolve()
    from ai_dlc.config import load_project

    if apply:
        if plan_file is None:  # Retain type narrowing at the orchestration boundary.
            raise ValueError("Linear connection apply requires --plan-file")
        config, saved_plan = revalidate_saved_linear_connection(
            root,
            plan_file,
            environ=environ,
            client=client,
        )
        _guard_mapping_change(root, config, saved_plan, plan_file=plan_file)
        apply_linear_connection(root / "ai-dlc.toml", saved_plan)
        return {
            "provider": "linear",
            "status": "applied",
            "selected": saved_plan["selected"],
        }

    config = load_project(root)
    settings = _validate_linear_settings(config.get("providers", {}).get("linear"))

    owned_client = client is None
    active_client = httpx.Client() if owned_client else client
    try:
        discovery = discover_linear(settings, environ=environ, client=active_client)
        if not any(supplied):
            return discovery
        selection = {key: value for key, value in selections.items() if value is not None}
        plan = plan_linear_connection(config, discovery, selection)
        result = {"provider": "linear", "status": "planned", "plan": plan}
        if plan_file is not None:
            saved_path = _save_connection_plan(root, plan_file, plan)
            result["plan_file"] = saved_path.relative_to(root).as_posix()
        _guard_mapping_change(root, config, plan, plan_file=plan_file)
        return result
    finally:
        if owned_client:
            active_client.close()
