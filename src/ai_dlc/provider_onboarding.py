import json
import os
import re
import tempfile
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, NoReturn

import httpx

from ai_dlc.config import digest
from ai_dlc.providers.linear import LinearProvider

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


def _set_table_value(text: str, table: str, key: str, value: str) -> str:
    lines = text.splitlines(keepends=True)
    header_pattern = re.compile(rf"^\s*\[{re.escape(table)}\]\s*(?:#.*)?(?:\r?\n)?$")
    any_header = re.compile(r"^\s*\[\[?.*]\]?\s*(?:#.*)?(?:\r?\n)?$")
    start = next((index for index, line in enumerate(lines) if header_pattern.match(line)), None)
    encoded = json.dumps(value, ensure_ascii=False)

    if start is None:
        if text and not text.endswith(("\n", "\r")):
            text += "\n"
        separator = "" if not text or text.endswith("\n\n") else "\n"
        return f"{text}{separator}[{table}]\n{key} = {encoded}\n"

    end = next(
        (index for index in range(start + 1, len(lines)) if any_header.match(lines[index])),
        len(lines),
    )
    assignment = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*)(.*?)(\r?\n)?$")
    for index in range(start + 1, end):
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
    rendered = _render_patch(current_text, patch)
    # Parse the result before staging so a preservation bug can never replace the source.
    tomllib.loads(rendered)

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
