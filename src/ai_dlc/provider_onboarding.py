from collections.abc import Callable, Mapping
from typing import Any, NoReturn

import httpx

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
    except (KeyError, TypeError, ValueError):
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
