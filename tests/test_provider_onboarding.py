import json

import httpx
import pytest


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _response(data):
    return httpx.Response(200, json={"data": data})


def _complete_page(nodes):
    return {
        "nodes": nodes,
        "pageInfo": {"hasNextPage": False, "endCursor": None},
    }


def test_discovery_returns_all_teams_and_states_without_guessing_duplicate_names():
    """Dropping duplicate labels or one of two started states would hide valid ID choices."""
    from ai_dlc.provider_onboarding import discover_linear

    requests = []

    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        query = body["query"]
        if "LinearDiscoveryOrganization" in query:
            return _response(
                {"organization": {"id": "org-1", "name": "Sandbox", "urlKey": "sandbox"}}
            )
        if "LinearDiscoveryTeams" in query:
            return _response(
                {
                    "teams": _complete_page(
                        [
                            {"id": "team-a", "name": "AI-DLC", "key": "AID"},
                            {"id": "team-b", "name": "AI-DLC", "key": "LAB"},
                        ]
                    )
                }
            )
        team_id = body["variables"]["teamId"]
        states = {
            "team-a": [
                {"id": "todo-a", "name": "Todo", "type": "unstarted"},
                {"id": "doing-a", "name": "In Progress", "type": "started"},
                {"id": "review-a", "name": "In Review", "type": "started"},
                {"id": "done-a", "name": "Done", "type": "completed"},
            ],
            "team-b": [
                {"id": "todo-b", "name": "Todo", "type": "unstarted"},
                {"id": "done-b", "name": "Done", "type": "completed"},
            ],
        }
        return _response({"team": {"id": team_id, "states": _complete_page(states[team_id])}})

    result = discover_linear(
        {"token_env": "LINEAR_TEST_TOKEN"},
        environ={"LINEAR_TEST_TOKEN": "credential-value"},
        client=_client(handle),
    )

    assert result == {
        "organization": {"id": "org-1", "name": "Sandbox", "urlKey": "sandbox"},
        "teams": [
            {
                "id": "team-a",
                "name": "AI-DLC",
                "key": "AID",
                "states": [
                    {"id": "todo-a", "name": "Todo", "type": "unstarted"},
                    {"id": "doing-a", "name": "In Progress", "type": "started"},
                    {"id": "review-a", "name": "In Review", "type": "started"},
                    {"id": "done-a", "name": "Done", "type": "completed"},
                ],
            },
            {
                "id": "team-b",
                "name": "AI-DLC",
                "key": "LAB",
                "states": [
                    {"id": "todo-b", "name": "Todo", "type": "unstarted"},
                    {"id": "done-b", "name": "Done", "type": "completed"},
                ],
            },
        ],
    }
    assert all("mutation" not in request["query"].lower() for request in requests)
    assert "credential-value" not in json.dumps(result)


def test_discovery_consumes_independent_team_and_state_pages():
    """Stopping at either connection's first page would return an incomplete choice set."""
    from ai_dlc.provider_onboarding import discover_linear

    seen = []

    def handle(request):
        body = json.loads(request.content)
        query = body["query"]
        variables = body["variables"]
        seen.append((query, variables))
        if "LinearDiscoveryOrganization" in query:
            return _response(
                {"organization": {"id": "org-1", "name": "Sandbox", "urlKey": "sandbox"}}
            )
        if "LinearDiscoveryTeams" in query:
            if variables["after"] is None:
                return _response(
                    {
                        "teams": {
                            "nodes": [{"id": "team-a", "name": "One", "key": "ONE"}],
                            "pageInfo": {"hasNextPage": True, "endCursor": "teams-next"},
                        }
                    }
                )
            assert variables["after"] == "teams-next"
            return _response(
                {"teams": _complete_page([{"id": "team-b", "name": "Two", "key": "TWO"}])}
            )
        team_id = variables["teamId"]
        if team_id == "team-a" and variables["after"] is None:
            return _response(
                {
                    "team": {
                        "id": "team-a",
                        "states": {
                            "nodes": [{"id": "doing", "name": "In Progress", "type": "started"}],
                            "pageInfo": {"hasNextPage": True, "endCursor": "states-next"},
                        },
                    }
                }
            )
        if team_id == "team-a":
            assert variables["after"] == "states-next"
            states = [{"id": "done", "name": "Done", "type": "completed"}]
        else:
            states = [{"id": "backlog", "name": "Backlog", "type": "backlog"}]
        return _response({"team": {"id": team_id, "states": _complete_page(states)}})

    result = discover_linear(
        {"token_env": "TOKEN"}, environ={"TOKEN": "secret"}, client=_client(handle)
    )

    assert [team["id"] for team in result["teams"]] == ["team-a", "team-b"]
    assert [state["id"] for state in result["teams"][0]["states"]] == ["doing", "done"]
    team_cursors = [
        variables["after"] for query, variables in seen if "LinearDiscoveryTeams" in query
    ]
    state_cursors = [
        variables["after"]
        for query, variables in seen
        if "LinearDiscoveryStates" in query and variables["teamId"] == "team-a"
    ]
    assert team_cursors == [None, "teams-next"]
    assert state_cursors == [None, "states-next"]


@pytest.mark.parametrize(
    ("connection", "payload"),
    [
        (
            "teams",
            {
                "nodes": [{"id": "team-a", "name": "One", "key": "ONE"}],
                "pageInfo": {"hasNextPage": True, "endCursor": None},
            },
        ),
        (
            "states",
            {
                "nodes": [{"id": "doing", "name": "In Progress", "type": "started"}],
                "pageInfo": {"hasNextPage": True, "endCursor": ""},
            },
        ),
    ],
)
def test_discovery_refuses_connections_that_claim_an_unpageable_remainder(connection, payload):
    """Treating a missing next cursor as completion would silently truncate discovery."""
    from ai_dlc.provider_onboarding import discover_linear

    def handle(request):
        body = json.loads(request.content)
        query = body["query"]
        if "LinearDiscoveryOrganization" in query:
            return _response(
                {"organization": {"id": "org-1", "name": "Sandbox", "urlKey": "sandbox"}}
            )
        if "LinearDiscoveryTeams" in query:
            teams = (
                payload
                if connection == "teams"
                else _complete_page([{"id": "team-a", "name": "One", "key": "ONE"}])
            )
            return _response({"teams": teams})
        return _response({"team": {"id": "team-a", "states": payload}})

    with pytest.raises(RuntimeError, match="incomplete"):
        discover_linear({"token_env": "TOKEN"}, environ={"TOKEN": "secret"}, client=_client(handle))


def test_discovery_refuses_partial_graphql_data_and_redacts_echoed_credential():
    """GraphQL errors must not yield partial discovery or expose the configured secret."""
    from ai_dlc.provider_onboarding import discover_linear

    secret = "linear-secret-sentinel"

    def handle(_request):
        return httpx.Response(
            200,
            json={
                "data": {"organization": {"id": "org-1", "name": "Sandbox", "urlKey": "sandbox"}},
                "errors": [{"message": f"request rejected for {secret}"}],
            },
        )

    with pytest.raises(RuntimeError, match="discovery") as caught:
        discover_linear({"token_env": "TOKEN"}, environ={"TOKEN": secret}, client=_client(handle))
    assert secret not in str(caught.value)


def test_discovery_refuses_non_object_json_without_exposing_credential():
    """A valid JSON value with the wrong shape must become a safe discovery failure."""
    from ai_dlc.provider_onboarding import discover_linear

    secret = "linear-secret-sentinel"

    def handle(_request):
        return httpx.Response(200, json=[secret])

    with pytest.raises(RuntimeError, match="incomplete") as caught:
        discover_linear({"token_env": "TOKEN"}, environ={"TOKEN": secret}, client=_client(handle))
    assert secret not in str(caught.value)


def test_discovery_refuses_a_repeated_non_empty_pagination_cursor():
    """A server repeating its cursor must fail instead of looping forever."""
    from ai_dlc.provider_onboarding import discover_linear

    calls = 0

    def handle(request):
        nonlocal calls
        body = json.loads(request.content)
        if "LinearDiscoveryOrganization" in body["query"]:
            return _response(
                {"organization": {"id": "org-1", "name": "Sandbox", "urlKey": "sandbox"}}
            )
        calls += 1
        return _response(
            {
                "teams": {
                    "nodes": [{"id": f"team-{calls}", "name": "One", "key": "ONE"}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "repeated-cursor"},
                }
            }
        )

    with pytest.raises(RuntimeError, match="incomplete"):
        discover_linear({"token_env": "TOKEN"}, environ={"TOKEN": "secret"}, client=_client(handle))
    assert calls == 2


def test_discovery_refuses_workflow_states_returned_for_another_team():
    """Associating states with the wrong team would permit an invalid later selection."""
    from ai_dlc.provider_onboarding import discover_linear

    def handle(request):
        body = json.loads(request.content)
        if "LinearDiscoveryOrganization" in body["query"]:
            return _response(
                {"organization": {"id": "org-1", "name": "Sandbox", "urlKey": "sandbox"}}
            )
        if "LinearDiscoveryTeams" in body["query"]:
            return _response(
                {"teams": _complete_page([{"id": "team-a", "name": "One", "key": "ONE"}])}
            )
        return _response(
            {
                "team": {
                    "id": "team-b",
                    "states": _complete_page(
                        [{"id": "doing", "name": "In Progress", "type": "started"}]
                    ),
                }
            }
        )

    with pytest.raises(RuntimeError, match="incomplete"):
        discover_linear({"token_env": "TOKEN"}, environ={"TOKEN": "secret"}, client=_client(handle))


@pytest.mark.parametrize("status_code", [401, 403])
def test_discovery_reports_authorization_failure_without_exposing_credential(status_code):
    """Authorization responses must become actionable, credential-safe failures."""
    from ai_dlc.provider_onboarding import discover_linear

    secret = "linear-secret-sentinel"

    def handle(request):
        assert request.headers["Authorization"] == secret
        return httpx.Response(status_code, text=f"denied {secret}")

    with pytest.raises(RuntimeError, match="authorization") as caught:
        discover_linear({"token_env": "TOKEN"}, environ={"TOKEN": secret}, client=_client(handle))
    assert secret not in str(caught.value)


def test_discovery_requires_configured_credential_without_contacting_linear():
    """Missing local authorization must fail before any remote request is attempted."""
    from ai_dlc.provider_onboarding import discover_linear

    def handle(_request):
        raise AssertionError("request should not be attempted")

    with pytest.raises(ValueError, match="MISSING_LINEAR_TOKEN"):
        discover_linear({"token_env": "MISSING_LINEAR_TOKEN"}, environ={}, client=_client(handle))
