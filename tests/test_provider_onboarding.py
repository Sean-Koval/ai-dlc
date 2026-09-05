import json
import stat
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


@pytest.mark.parametrize("delimiter", ['"""', "'''"])
def test_apply_ignores_table_like_lines_inside_unrelated_multiline_strings(tmp_path, delimiter):
    """Physical lines inside TOML strings must never be mistaken for provider syntax."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text(
        "schema = 4\n"
        "[project]\n"
        f"description = {delimiter}\n"
        "[providers.linear]\n"
        'team_id = "decoy-team"\n'
        "[providers.linear.statuses]\n"
        'in_progress = "decoy-started"\n'
        'closed = "decoy-completed"\n'
        f"{delimiter}\n"
    )
    before = tomllib.loads(path.read_text())
    plan = plan_linear_connection(before, _selection_discovery(), _selection())

    apply_linear_connection(path, plan)

    after = tomllib.loads(path.read_text())
    assert after["project"]["description"] == before["project"]["description"]
    assert after["providers"]["linear"] == {
        "team_id": "team-a",
        "statuses": {"in_progress": "doing-a", "closed": "done-a"},
    }


def test_apply_updates_real_tables_after_a_multiline_string_decoy(tmp_path):
    """A decoy header must not hide or redirect edits away from the real provider tables."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text(
        'schema = 4\n[project]\ndescription = """\n'
        "[providers.linear]\n"
        'team_id = "decoy-team"\n'
        '"""\n\n[providers.linear]\nteam_id = "old-team" # real\n\n'
        '[providers.linear.statuses]\nin_progress = "old-started"\nclosed = "old-closed"\n'
    )
    before = tomllib.loads(path.read_text())
    plan = plan_linear_connection(before, _selection_discovery(), _selection())

    apply_linear_connection(path, plan)

    rendered = path.read_text()
    after = tomllib.loads(rendered)
    assert after["project"]["description"] == before["project"]["description"]
    assert after["providers"]["linear"]["team_id"] == "team-a"
    assert rendered.count('team_id = "decoy-team"') == 1
    assert 'team_id = "team-a" # real' in rendered


def test_apply_supports_quoted_provider_table_segments(tmp_path):
    """Quoted table path segments are equivalent TOML and can be preserved safely."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text(
        'schema = 4\n[providers."linear"] # quoted provider\n'
        'token_env = "TOKEN"\nteam_id = "old-team"\n\n'
        '["providers".linear.statuses] # quoted root\n'
        'in_progress = "old-started"\nclosed = "old-closed"\n'
    )
    plan = plan_linear_connection(
        tomllib.loads(path.read_text()), _selection_discovery(), _selection()
    )

    apply_linear_connection(path, plan)

    rendered = path.read_text()
    parsed = tomllib.loads(rendered)
    assert parsed["providers"]["linear"] == {
        "token_env": "TOKEN",
        "team_id": "team-a",
        "statuses": {"in_progress": "doing-a", "closed": "done-a"},
    }
    assert '[providers."linear"] # quoted provider' in rendered
    assert '["providers".linear.statuses] # quoted root' in rendered


@pytest.mark.parametrize(
    "source",
    [
        (
            'schema = 4\nproviders.linear.team_id = "old-team"\n'
            'providers.linear.statuses.in_progress = "old-started"\n'
            'providers.linear.statuses.closed = "old-closed"\n'
        ),
        (
            'schema = 4\n[providers.linear]\nteam_id = "old-team"\n'
            'statuses = { in_progress = "old-started", closed = "old-closed" }\n'
        ),
        (
            "schema = 4\n[providers]\n"
            'linear = { team_id = "old-team", statuses = { in_progress = "old-started", '
            'closed = "old-closed" } }\n'
        ),
    ],
)
def test_apply_deliberately_refuses_valid_toml_representations_it_cannot_preserve(tmp_path, source):
    """Unsupported equivalent layouts need an actionable domain refusal, not parser leakage."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text(source)
    plan = plan_linear_connection(
        tomllib.loads(path.read_text()), _selection_discovery(), _selection()
    )
    before = path.read_bytes()

    with pytest.raises(ValueError, match="TOML representation"):
        apply_linear_connection(path, plan)

    assert path.read_bytes() == before
    assert list(tmp_path.glob(".ai-dlc-linear-*")) == []


def test_apply_semantic_verification_rejects_any_unrelated_rendered_change(tmp_path, monkeypatch):
    """Parseable output is unsafe unless its complete semantic delta is exactly the patch."""
    import ai_dlc.provider_onboarding as onboarding

    path = tmp_path / "ai-dlc.toml"
    path.write_text('schema = 4\n[project]\nname = "Keep"\n')
    plan = onboarding.plan_linear_connection(
        tomllib.loads(path.read_text()), _selection_discovery(), _selection()
    )
    before = path.read_bytes()
    real_render = onboarding._render_patch

    def corrupt_unrelated_value(text, patch):
        return real_render(text, patch).replace('name = "Keep"', 'name = "Changed"')

    monkeypatch.setattr(onboarding, "_render_patch", corrupt_unrelated_value)
    with pytest.raises(ValueError, match="TOML representation"):
        onboarding.apply_linear_connection(path, plan)

    assert path.read_bytes() == before
    assert list(tmp_path.glob(".ai-dlc-linear-*")) == []


@pytest.mark.parametrize("delimiter", ['"""', "'''"])
@pytest.mark.parametrize("target_table", ["provider", "statuses"])
@pytest.mark.parametrize("real_assignment", [True, False])
def test_apply_ignores_assignment_decoys_inside_target_table_multiline_values(
    tmp_path, delimiter, target_table, real_assignment
):
    """Assignments embedded in provider notes must not receive or prevent the mapping update."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    if target_table == "provider":
        provider_body = f'notes = {delimiter}\nteam_id = "decoy-team"\n{delimiter}\n' + (
            'team_id = "old-team" # real team\n' if real_assignment else ""
        )
        statuses_body = 'in_progress = "old-started"\nclosed = "old-closed"\n'
    else:
        provider_body = 'team_id = "old-team"\n'
        statuses_body = (
            f"notes = {delimiter}\n"
            'in_progress = "decoy-started"\nclosed = "decoy-closed"\n'
            f"{delimiter}\n"
            + (
                'in_progress = "old-started" # real started\nclosed = "old-closed" # real closed\n'
                if real_assignment
                else ""
            )
        )
    path = tmp_path / "ai-dlc.toml"
    path.write_text(
        f"schema = 4\n[providers.linear]\n{provider_body}\n"
        f"[providers.linear.statuses]\n{statuses_body}"
    )
    before = tomllib.loads(path.read_text())
    plan = plan_linear_connection(before, _selection_discovery(), _selection())

    apply_linear_connection(path, plan)

    rendered = path.read_text()
    after = tomllib.loads(rendered)
    assert after["providers"]["linear"]["team_id"] == "team-a"
    assert after["providers"]["linear"]["statuses"]["in_progress"] == "doing-a"
    assert after["providers"]["linear"]["statuses"]["closed"] == "done-a"
    notes_owner = after["providers"]["linear"]
    before_notes_owner = before["providers"]["linear"]
    if target_table == "statuses":
        notes_owner = notes_owner["statuses"]
        before_notes_owner = before_notes_owner["statuses"]
        assert 'in_progress = "decoy-started"' in rendered
        assert 'closed = "decoy-closed"' in rendered
    else:
        assert 'team_id = "decoy-team"' in rendered
    assert notes_owner["notes"] == before_notes_owner["notes"]


def test_apply_semantic_verification_is_type_sensitive(tmp_path, monkeypatch):
    """Python equality must not let an unrelated integer-to-boolean change pass as exact."""
    import ai_dlc.provider_onboarding as onboarding

    path = tmp_path / "ai-dlc.toml"
    path.write_text("schema = 4\n[project]\nretries = 1\n")
    plan = onboarding.plan_linear_connection(
        tomllib.loads(path.read_text()), _selection_discovery(), _selection()
    )
    before = path.read_bytes()
    real_render = onboarding._render_patch

    def change_value_type(text, patch):
        return real_render(text, patch).replace("retries = 1", "retries = true")

    monkeypatch.setattr(onboarding, "_render_patch", change_value_type)
    with pytest.raises(ValueError, match="TOML representation"):
        onboarding.apply_linear_connection(path, plan)

    assert path.read_bytes() == before
    assert list(tmp_path.glob(".ai-dlc-linear-*")) == []


def test_apply_preserves_restrictive_source_mode(tmp_path):
    """Atomic replacement must not broaden access to project configuration metadata."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text('schema = 4\n[providers.linear]\ntoken_env = "TOKEN"\n')
    path.chmod(0o600)
    plan = plan_linear_connection(
        tomllib.loads(path.read_text()), _selection_discovery(), _selection()
    )

    apply_linear_connection(path, plan)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
