import json
import tomllib

import httpx
import pytest

from ai_dlc.config import digest


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


def _selection_discovery():
    return {
        "organization": {"id": "org-1", "name": "Sandbox", "urlKey": "sandbox"},
        "teams": [
            {
                "id": "team-a",
                "name": "AI-DLC",
                "key": "AID",
                "states": [
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
                    {"id": "doing-b", "name": "In Progress", "type": "started"},
                    {"id": "done-b", "name": "Done", "type": "completed"},
                ],
            },
        ],
    }


def _selection(**overrides):
    selected = {
        "organization_id": "org-1",
        "team_id": "team-a",
        "in_progress": "doing-a",
        "closed": "done-a",
    }
    selected.update(overrides)
    return selected


def _linear_config(secret="credential-sentinel"):
    return {
        "schema": 4,
        "project": {"name": "Example"},
        "providers": {
            "linear": {
                "token_env": "LINEAR_SANDBOX_TOKEN",
                "credential_fixture": secret,
                "team_id": "old-team",
                "statuses": {"in_progress": "old-started", "closed": "old-completed"},
            }
        },
    }


def test_plan_validates_ids_and_returns_only_the_reviewed_non_secret_mapping():
    """Copying provider settings into a plan could persist a credential value."""
    from ai_dlc.provider_onboarding import plan_linear_connection

    config = _linear_config()
    result = plan_linear_connection(config, _selection_discovery(), _selection())

    assert result == {
        "provider": "linear",
        "before_digest": digest(config),
        "selected": _selection(),
        "patch": {
            "team_id": "team-a",
            "statuses": {"in_progress": "doing-a", "closed": "done-a"},
        },
    }
    assert "credential-sentinel" not in json.dumps(result)
    assert "token_env" not in json.dumps(result)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"organization_id": "org-other"}, "organization"),
        ({"team_id": "team-other"}, "team"),
        ({"in_progress": "doing-b"}, "in_progress"),
        ({"closed": "done-b"}, "closed"),
        ({"in_progress": "done-a"}, "started"),
        ({"closed": "doing-a"}, "completed"),
    ],
)
def test_plan_refuses_foreign_or_wrong_type_selections_without_writing(
    tmp_path, overrides, message
):
    """Accepting an ID by existence alone could bind a team to another team's state."""
    from ai_dlc.provider_onboarding import plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text('schema = 4\n# retained\n[providers.linear]\ntoken_env = "TOKEN"\n')
    before = path.read_bytes()

    with pytest.raises(ValueError, match=message):
        plan_linear_connection(
            tomllib.loads(path.read_text()), _selection_discovery(), _selection(**overrides)
        )

    assert path.read_bytes() == before


def test_apply_updates_only_selected_mappings_and_preserves_comments_and_token_env(tmp_path):
    """Reserializing the config would erase comments and can disturb unrelated values."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text(
        "schema = 4\n"
        "# project comment\n"
        "[project]\n"
        'name = "Keep Me" # inline project comment\n\n'
        "[providers.linear]\n"
        'token_env = "LINEAR_SANDBOX_TOKEN" # credential reference stays\n'
        'team_id = "old-team" # selected team\n'
        'health_reference = "keep-health"\n\n'
        "[providers.linear.statuses]\n"
        'in_progress = "old-started" # selected started state\n'
        'closed = "old-completed" # selected completed state\n\n'
        "[checks]\n"
        'required = ["test"] # unrelated section\n'
    )
    config = tomllib.loads(path.read_text())
    plan = plan_linear_connection(config, _selection_discovery(), _selection())

    apply_linear_connection(path, plan)

    rendered = path.read_text()
    parsed = tomllib.loads(rendered)
    assert parsed["providers"]["linear"] == {
        "token_env": "LINEAR_SANDBOX_TOKEN",
        "team_id": "team-a",
        "health_reference": "keep-health",
        "statuses": {"in_progress": "doing-a", "closed": "done-a"},
    }
    assert parsed["project"] == {"name": "Keep Me"}
    assert parsed["checks"] == {"required": ["test"]}
    assert "# project comment" in rendered
    assert "# inline project comment" in rendered
    assert "# credential reference stays" in rendered
    assert "# selected team" in rendered
    assert "# selected started state" in rendered
    assert "# selected completed state" in rendered
    assert "# unrelated section" in rendered


def test_apply_adds_missing_linear_mapping_tables_without_reserializing_existing_content(tmp_path):
    """A project without mapping tables still needs a focused additive patch."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text('schema = 4\n# keep this\n[project]\nname = "Example"\n')
    plan = plan_linear_connection(
        tomllib.loads(path.read_text()), _selection_discovery(), _selection()
    )

    apply_linear_connection(path, plan)

    rendered = path.read_text()
    parsed = tomllib.loads(rendered)
    assert parsed["providers"]["linear"] == {
        "team_id": "team-a",
        "statuses": {"in_progress": "doing-a", "closed": "done-a"},
    }
    assert "# keep this" in rendered


def test_apply_refuses_a_stale_digest_without_modifying_the_changed_file(tmp_path):
    """Applying after semantic config drift would overwrite a plan the user did not review."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text('schema = 4\n[project]\nname = "Before"\n')
    plan = plan_linear_connection(
        tomllib.loads(path.read_text()), _selection_discovery(), _selection()
    )
    path.write_text('schema = 4\n[project]\nname = "After"\n')
    changed = path.read_bytes()

    with pytest.raises(ValueError, match="digest"):
        apply_linear_connection(path, plan)

    assert path.read_bytes() == changed


def test_apply_preserves_comment_only_changes_made_after_preview(tmp_path):
    """Canonical digest approval must not discard newer comments from the current text."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text('schema = 4\n[project]\nname = "Example"\n')
    plan = plan_linear_connection(
        tomllib.loads(path.read_text()), _selection_discovery(), _selection()
    )
    path.write_text('# added after preview\nschema = 4\n[project]\nname = "Example"\n')

    apply_linear_connection(path, plan)

    assert path.read_text().startswith("# added after preview\n")


def test_apply_rejects_a_tampered_patch_without_modifying_the_file(tmp_path):
    """Allowing patch fields beyond the selection could overwrite credentials or other settings."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text('schema = 4\n[providers.linear]\ntoken_env = "TOKEN"\n')
    plan = plan_linear_connection(
        tomllib.loads(path.read_text()), _selection_discovery(), _selection()
    )
    plan["patch"]["token_env"] = "credential-sentinel"
    before = path.read_bytes()

    with pytest.raises(ValueError, match="plan"):
        apply_linear_connection(path, plan)

    assert path.read_bytes() == before
    assert "credential-sentinel" not in path.read_text()


def test_apply_atomic_replace_failure_preserves_original_bytes(tmp_path, monkeypatch):
    """A failed final replacement must leave the approved source file recoverable."""
    import ai_dlc.provider_onboarding as onboarding

    path = tmp_path / "ai-dlc.toml"
    path.write_text('schema = 4\n[project]\nname = "Example"\n')
    plan = onboarding.plan_linear_connection(
        tomllib.loads(path.read_text()), _selection_discovery(), _selection()
    )
    before = path.read_bytes()

    def fail_replace(_source, _destination):
        raise OSError("injected atomic replace failure")

    monkeypatch.setattr(onboarding.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected"):
        onboarding.apply_linear_connection(path, plan)

    assert path.read_bytes() == before
    assert list(tmp_path.glob(".ai-dlc-linear-*")) == []


def test_apply_refuses_a_concurrent_comment_change_before_atomic_replace(tmp_path, monkeypatch):
    """A write racing apply must not erase newer authored comments with the same config digest."""
    import ai_dlc.provider_onboarding as onboarding

    path = tmp_path / "ai-dlc.toml"
    path.write_text('schema = 4\n[project]\nname = "Example"\n')
    plan = onboarding.plan_linear_connection(
        tomllib.loads(path.read_text()), _selection_discovery(), _selection()
    )
    real_chmod = onboarding.os.chmod

    def add_concurrent_comment(staged_name, mode):
        real_chmod(staged_name, mode)
        path.write_text(path.read_text() + "# concurrent authored comment\n")

    monkeypatch.setattr(onboarding.os, "chmod", add_concurrent_comment)
    with pytest.raises(ValueError, match="changed during apply"):
        onboarding.apply_linear_connection(path, plan)

    assert path.read_text().endswith("# concurrent authored comment\n")
    assert list(tmp_path.glob(".ai-dlc-linear-*")) == []
