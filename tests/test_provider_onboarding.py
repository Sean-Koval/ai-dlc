import json
import shlex
import stat
import tomllib
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
import tomli_w
from typer.testing import CliRunner

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


@pytest.mark.parametrize(
    "source",
    [
        'schema = 4\n[providers.linear]\ntoken_env = "TOKEN"',
        (
            'schema = 4\n[providers.linear]\ntoken_env = "TOKEN"\n'
            '[providers.linear.statuses]\nin_progress = "old-started"\n'
            '[[setup.steps]]\nid = "keep"\ncommand = "true"\n'
        ),
    ],
)
def test_apply_inserts_missing_mappings_at_real_toml_boundaries(tmp_path, source):
    """EOF and array-table boundaries must not redirect an otherwise safe insertion."""
    from ai_dlc.provider_onboarding import apply_linear_connection, plan_linear_connection

    path = tmp_path / "ai-dlc.toml"
    path.write_text(source)
    before = tomllib.loads(source)
    plan = plan_linear_connection(before, _selection_discovery(), _selection())

    apply_linear_connection(path, plan)

    rendered = path.read_text()
    after = tomllib.loads(rendered)
    assert after == {
        **before,
        "providers": {
            "linear": {
                **before["providers"]["linear"],
                "team_id": "team-a",
                "statuses": {"in_progress": "doing-a", "closed": "done-a"},
            }
        },
    }
    if "setup" in before:
        assert after["setup"] == before["setup"]
        assert '[[setup.steps]]\nid = "keep"\ncommand = "true"' in rendered


def _write_connect_project(root: Path, *, bound: bool = False) -> Path:
    root.mkdir()
    config_path = root / "ai-dlc.toml"
    config_path.write_text(
        'schema = 4\n[roles]\ntracker = "linear"\n\n'
        '[providers.linear]\ntoken_env = "LINEAR_TEST_TOKEN"\nteam_id = "old-team"\n\n'
        '[providers.linear.statuses]\nin_progress = "old-started"\nclosed = "old-closed"\n'
    )
    if bound:
        work = {
            "schema": 1,
            "id": "bound-work",
            "title": "Bound work",
            "scope": "Keep the tracker binding stable",
            "requires_spec": False,
            "spec_reason": "Regression fixture",
            "acceptance": ["No silent rebinding"],
            "reviewed": True,
            "providers": {"tracker": "linear"},
            "artifacts": {"tracker": "SAN-1"},
            "bindings": {"tracker": "a" * 64},
        }
        work_path = root / ".ai-dlc/work/bound-work.toml"
        work_path.parent.mkdir(parents=True)
        work_path.write_text(tomli_w.dumps(work))
    return config_path


def _stub_cli_discovery(monkeypatch, discovery=None):
    import ai_dlc.provider_onboarding as onboarding

    calls = []
    result = _selection_discovery() if discovery is None else discovery

    def discover(settings, *, environ, client):
        calls.append((deepcopy(settings), environ, client))
        return deepcopy(result)

    monkeypatch.setattr(onboarding, "discover_linear", discover)
    return calls


def _connect_args(root: Path) -> list[str]:
    return [
        "provider",
        "connect",
        "linear",
        "--root",
        str(root),
        "--organization",
        "org-1",
        "--team",
        "team-a",
        "--in-progress",
        "doing-a",
        "--closed",
        "done-a",
    ]


def test_provider_connect_without_selections_prints_complete_discovery_and_writes_nothing(
    tmp_path, monkeypatch
):
    """Inferring a state or entering preview mode would violate read-only discovery."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    _write_connect_project(root)
    calls = _stub_cli_discovery(monkeypatch)
    monkeypatch.setenv("LINEAR_TEST_TOKEN", "credential-sentinel")
    before = {
        path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }

    result = CliRunner().invoke(app, ["provider", "connect", "linear", "--root", str(root)])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == _selection_discovery()
    assert len(calls) == 1
    assert "credential-sentinel" not in result.output
    assert before == {
        path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize(
    "arguments",
    [
        ["--organization", "org-1"],
        ["--team", "team-a", "--in-progress", "doing-a", "--closed", "done-a"],
        ["--apply"],
        ["--plan-file", ".ai-dlc/local/linear-plan.json"],
        ["--apply", "--plan-file", ".ai-dlc/local/linear-plan.json", "--team", "team-a"],
    ],
)
def test_provider_connect_refuses_incomplete_or_conflicting_modes_before_discovery(
    tmp_path, monkeypatch, arguments
):
    """Mixing discovery, preview, and apply inputs could approve a different operation."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    calls = _stub_cli_discovery(monkeypatch)
    before = config_path.read_bytes()

    result = CliRunner().invoke(
        app, ["provider", "connect", "linear", "--root", str(root), *arguments]
    )

    assert result.exit_code != 0
    assert "selection" in result.output.lower() or "plan" in result.output.lower()
    assert calls == []
    assert config_path.read_bytes() == before


def test_provider_connect_validates_provider_before_read_or_write(tmp_path, monkeypatch):
    """An unknown provider must not fall through to Linear or mutate project state."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    calls = _stub_cli_discovery(monkeypatch)
    before = config_path.read_bytes()

    result = CliRunner().invoke(app, ["provider", "connect", "not-linear", "--root", str(root)])

    assert result.exit_code != 0
    assert "not supported" in result.output
    assert calls == []
    assert config_path.read_bytes() == before


@pytest.mark.parametrize("field", ["kind", "type"])
def test_provider_connect_refuses_non_linear_effective_kind_before_client_or_credential_use(
    tmp_path, monkeypatch, field
):
    """A provider alias must never send another adapter's credential to Linear."""
    import ai_dlc.provider_onboarding as onboarding
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    config_path.write_text(
        config_path.read_text().replace(
            "[providers.linear]\n", f'[providers.linear]\n{field} = "github-issues"\n'
        )
    )
    monkeypatch.setenv("LINEAR_TEST_TOKEN", "credential-sentinel")
    clients = []

    def client_factory():
        clients.append("constructed")
        raise AssertionError("Linear client must not be constructed")

    monkeypatch.setattr(onboarding.httpx, "Client", client_factory)
    before = config_path.read_bytes()

    result = CliRunner().invoke(app, ["provider", "connect", "linear", "--root", str(root)])

    assert result.exit_code != 0
    assert "does not use the Linear adapter" in result.output
    assert "credential-sentinel" not in result.output
    assert clients == []
    assert config_path.read_bytes() == before


def test_provider_connect_preview_can_save_only_the_non_secret_reviewed_plan(tmp_path, monkeypatch):
    """Saving the resolved provider settings could persist the environment credential."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    _stub_cli_discovery(monkeypatch)
    monkeypatch.setenv("LINEAR_TEST_TOKEN", "credential-sentinel")
    before = config_path.read_bytes()
    plan_path = root / ".ai-dlc/local/linear-plan.json"

    result = CliRunner().invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    saved = json.loads(plan_path.read_text())
    assert payload["status"] == "planned"
    assert payload["plan"] == saved
    assert payload["plan_file"] == ".ai-dlc/local/linear-plan.json"
    assert saved["selected"] == _selection()
    assert saved["patch"] == {
        "team_id": "team-a",
        "statuses": {"in_progress": "doing-a", "closed": "done-a"},
    }
    assert "token_env" not in json.dumps(saved)
    assert "credential-sentinel" not in plan_path.read_text() + result.output
    assert config_path.read_bytes() == before


@pytest.mark.parametrize("escape", ["outside", "symlink"])
def test_provider_connect_refuses_plan_paths_outside_local_control_state(
    tmp_path, monkeypatch, escape
):
    """Path traversal or a symlink could save reviewed metadata outside project-local state."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    _stub_cli_discovery(monkeypatch)
    outside = tmp_path / "outside.json"
    if escape == "outside":
        plan_path = outside
    else:
        local = root / ".ai-dlc/local"
        local.mkdir(parents=True)
        plan_path = local / "plan.json"
        plan_path.symlink_to(outside)
    before = config_path.read_bytes()

    result = CliRunner().invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)])

    assert result.exit_code != 0
    assert ".ai-dlc/local" in result.output
    assert not outside.exists()
    assert config_path.read_bytes() == before


@pytest.mark.parametrize("redirect", ["root", "docs"])
def test_provider_connect_refuses_a_symlinked_local_confinement_anchor(
    tmp_path, monkeypatch, redirect
):
    """The local anchor itself must never redefine shared project content as local state."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    docs = root / "docs"
    docs.mkdir()
    authored = docs / "plan.json"
    authored.write_text("authored documentation\n")
    local = root / ".ai-dlc/local"
    local.parent.mkdir()
    local.symlink_to(root if redirect == "root" else docs, target_is_directory=True)
    _stub_cli_discovery(monkeypatch)
    before = {config_path: config_path.read_bytes(), authored: authored.read_bytes()}
    plan_path = local / ("ai-dlc.toml" if redirect == "root" else "plan.json")

    result = CliRunner().invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)])

    assert result.exit_code != 0
    assert ".ai-dlc/local" in result.output
    assert all(path.read_bytes() == contents for path, contents in before.items())


def test_connection_plan_load_refuses_a_symlinked_local_anchor(tmp_path):
    """Apply must not read a shared file through a redirected local-state anchor."""
    from ai_dlc.provider_onboarding import _load_connection_plan

    root = tmp_path / "project"
    root.mkdir()
    shared = root / "reviewed.json"
    shared.write_text('{"shared": true}\n')
    local = root / ".ai-dlc/local"
    local.parent.mkdir()
    local.symlink_to(root, target_is_directory=True)

    with pytest.raises(ValueError, match=".ai-dlc/local"):
        _load_connection_plan(root, local / shared.name)

    assert shared.read_text() == '{"shared": true}\n'


@pytest.mark.parametrize("component", ["ai-dlc", "intermediate", "leaf"])
def test_provider_connect_refuses_every_symlinked_local_path_component(
    tmp_path, monkeypatch, component
):
    """Neither an anchor parent, nested directory, nor existing leaf may redirect plan I/O."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    docs = root / "docs"
    docs.mkdir()
    authored = docs / "plan.json"
    authored.write_text("authored documentation\n")
    if component == "ai-dlc":
        redirected = tmp_path / "redirected-control"
        (redirected / "local").mkdir(parents=True)
        (root / ".ai-dlc").symlink_to(redirected, target_is_directory=True)
        plan_path = root / ".ai-dlc/local/plan.json"
    else:
        local = root / ".ai-dlc/local"
        local.mkdir(parents=True)
        if component == "intermediate":
            (local / "review").symlink_to(docs, target_is_directory=True)
            plan_path = local / "review/plan.json"
        else:
            plan_path = local / "plan.json"
            plan_path.symlink_to(authored)
    _stub_cli_discovery(monkeypatch)
    before = {config_path: config_path.read_bytes(), authored: authored.read_bytes()}

    result = CliRunner().invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)])

    assert result.exit_code != 0
    assert ".ai-dlc/local" in result.output
    assert all(path.read_bytes() == contents for path, contents in before.items())


def test_provider_connect_apply_revalidates_saved_selection_then_applies_exact_plan(
    tmp_path, monkeypatch
):
    """Applying without a fresh read could accept membership that changed after review."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    calls = _stub_cli_discovery(monkeypatch)
    monkeypatch.setenv("LINEAR_TEST_TOKEN", "credential-sentinel")
    plan_path = root / ".ai-dlc/local/linear-plan.json"
    runner = CliRunner()
    preview = runner.invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)])
    assert preview.exit_code == 0, preview.output

    result = runner.invoke(
        app,
        [
            "provider",
            "connect",
            "linear",
            "--root",
            str(root),
            "--plan-file",
            str(plan_path),
            "--apply",
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "provider": "linear",
        "status": "applied",
        "selected": _selection(),
    }
    assert len(calls) == 2
    applied = tomllib.loads(config_path.read_text())
    assert applied["providers"]["linear"] == {
        "token_env": "LINEAR_TEST_TOKEN",
        "team_id": "team-a",
        "statuses": {"in_progress": "doing-a", "closed": "done-a"},
    }
    assert "credential-sentinel" not in result.output + plan_path.read_text()


def test_provider_connect_preview_and_apply_hash_raw_collection_operations(tmp_path, monkeypatch):
    """A supported collection operation must survive unchanged-source preview and apply."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    config_path.write_text(
        config_path.read_text().replace(
            'tracker = "linear"',
            'tracker = "linear"\nagent-client = { add = ["codex"] }',
        )
    )
    _stub_cli_discovery(monkeypatch)
    plan_path = root / ".ai-dlc/local/linear-plan.json"
    runner = CliRunner()

    preview = runner.invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)])
    assert preview.exit_code == 0, preview.output
    result = runner.invoke(
        app,
        [
            "provider",
            "connect",
            "linear",
            "--root",
            str(root),
            "--plan-file",
            str(plan_path),
            "--apply",
        ],
    )

    assert result.exit_code == 0, result.output
    assert tomllib.loads(config_path.read_text())["roles"]["agent-client"] == {"add": ["codex"]}


def test_connection_rebind_hashes_raw_collection_operations(tmp_path, monkeypatch):
    """Connection rebind must use the same raw source authority as provider preview."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root, bound=True)
    config_path.write_text(
        config_path.read_text().replace(
            'tracker = "linear"',
            'tracker = "linear"\nagent-client = { add = ["codex"] }',
        )
    )
    _stub_cli_discovery(monkeypatch)
    plan_path = root / ".ai-dlc/local/linear-plan.json"
    mappings_path = root / ".ai-dlc/local/linear-rebind.toml"
    runner = CliRunner()
    preview = runner.invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)])
    assert preview.exit_code != 0 and plan_path.is_file()
    mappings_path.write_text(tomli_w.dumps({"bound-work": {"tracker": "SAN-101"}}))

    result = runner.invoke(app, _rebind_connection_args(root, plan_path, mappings_path))

    assert result.exit_code == 0, result.output
    assert tomllib.loads(config_path.read_text())["roles"]["agent-client"] == {"add": ["codex"]}


@pytest.mark.parametrize("race", ["bind-existing", "create-bound"])
def test_provider_connect_apply_refuses_work_that_becomes_bound_during_staging(
    tmp_path, monkeypatch, race
):
    """The final coordinated boundary must see bindings created after initial validation."""
    import ai_dlc.provider_onboarding as onboarding
    from ai_dlc.cli import app
    from ai_dlc.config import load_project
    from ai_dlc.workflow import WorkService

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    if race == "bind-existing":
        work_path = _add_bound_work(
            root,
            "racing-work",
            "SAN-9",
            branch="keep/racing",
            binding=None,
        )
    else:
        work_path = root / ".ai-dlc/work/racing-work.toml"
    _stub_cli_discovery(monkeypatch)
    plan_path = root / ".ai-dlc/local/linear-plan.json"
    runner = CliRunner()
    assert runner.invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)]).exit_code == 0
    config_before = config_path.read_bytes()
    real_chmod = onboarding.os.chmod
    raced_bytes = None

    def bind_during_staging(staged_name, mode):
        nonlocal raced_bytes
        real_chmod(staged_name, mode)
        if race == "create-bound":
            _add_bound_work(
                root,
                "racing-work",
                "SAN-9",
                branch="keep/racing",
                binding=None,
            )
        service = WorkService(root, load_project(root), state_path=tmp_path / "state")
        service.load("racing-work", mutation=True)
        raced_bytes = work_path.read_bytes()

    monkeypatch.setattr(onboarding.os, "chmod", bind_during_staging)
    result = runner.invoke(
        app,
        [
            "provider",
            "connect",
            "linear",
            "--root",
            str(root),
            "--plan-file",
            str(plan_path),
            "--apply",
        ],
    )

    assert result.exit_code != 0
    assert "racing-work" in result.output
    assert config_path.read_bytes() == config_before
    assert raced_bytes is not None and work_path.read_bytes() == raced_bytes


def test_provider_connect_serializes_and_rejects_a_pending_stale_work_writer(tmp_path, monkeypatch):
    """A writer waiting on apply must not save a binding calculated from the old config."""
    import threading

    import ai_dlc.provider_onboarding as onboarding
    from ai_dlc.cli import app
    from ai_dlc.config import load_project
    from ai_dlc.workflow import WorkService

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    work_path = _add_bound_work(
        root,
        "pending-work",
        "SAN-9",
        branch="keep/pending",
        binding=None,
    )
    work_before = work_path.read_bytes()
    _stub_cli_discovery(monkeypatch)
    plan_path = root / ".ai-dlc/local/linear-plan.json"
    runner = CliRunner()
    assert runner.invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)]).exit_code == 0
    service = WorkService(root, load_project(root), state_path=tmp_path / "state")
    started = threading.Event()
    threads = []
    errors = []
    real_chmod = onboarding.os.chmod

    def start_pending_writer(staged_name, mode):
        real_chmod(staged_name, mode)

        def mutate():
            started.set()
            try:
                service.load("pending-work", mutation=True)
            except ValueError as exc:
                errors.append(str(exc))

        thread = threading.Thread(target=mutate)
        threads.append(thread)
        thread.start()
        assert started.wait(timeout=2)

    monkeypatch.setattr(onboarding.os, "chmod", start_pending_writer)
    result = runner.invoke(
        app,
        [
            "provider",
            "connect",
            "linear",
            "--root",
            str(root),
            "--plan-file",
            str(plan_path),
            "--apply",
        ],
    )
    for thread in threads:
        thread.join(timeout=2)

    assert result.exit_code == 0, result.output
    assert errors == ["Project configuration changed; retry the work mutation"]
    assert work_path.read_bytes() == work_before
    assert tomllib.loads(config_path.read_text())["providers"]["linear"]["team_id"] == "team-a"


def test_provider_connect_apply_refuses_remote_membership_drift_without_recomputing_plan(
    tmp_path, monkeypatch
):
    """A removed state must invalidate the saved choice instead of selecting a replacement."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    discovery = _selection_discovery()
    calls = _stub_cli_discovery(monkeypatch, discovery)
    plan_path = root / ".ai-dlc/local/linear-plan.json"
    runner = CliRunner()
    assert runner.invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)]).exit_code == 0
    saved = plan_path.read_bytes()
    discovery["teams"][0]["states"] = [
        state for state in discovery["teams"][0]["states"] if state["id"] != "doing-a"
    ]
    monkeypatch.setattr(
        __import__("ai_dlc.provider_onboarding", fromlist=["discover_linear"]),
        "discover_linear",
        lambda settings, *, environ, client: deepcopy(discovery),
    )
    before = config_path.read_bytes()

    result = runner.invoke(
        app,
        [
            "provider",
            "connect",
            "linear",
            "--root",
            str(root),
            "--plan-file",
            str(plan_path),
            "--apply",
        ],
    )

    assert result.exit_code != 0
    assert "in_progress" in result.output
    assert config_path.read_bytes() == before
    assert plan_path.read_bytes() == saved
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["stale", "tampered"])
def test_provider_connect_apply_refuses_stale_or_tampered_plan_without_writing(
    tmp_path, monkeypatch, failure
):
    """Only the exact reviewed plan for the unchanged source can reach atomic apply."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    _stub_cli_discovery(monkeypatch)
    plan_path = root / ".ai-dlc/local/linear-plan.json"
    runner = CliRunner()
    assert runner.invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)]).exit_code == 0
    if failure == "stale":
        config_path.write_text(config_path.read_text() + '\n[project]\nname = "Changed"\n')
    else:
        plan = json.loads(plan_path.read_text())
        plan["patch"]["token_env"] = "credential-sentinel"
        plan_path.write_text(json.dumps(plan))
    before = config_path.read_bytes()

    result = runner.invoke(
        app,
        [
            "provider",
            "connect",
            "linear",
            "--root",
            str(root),
            "--plan-file",
            str(plan_path),
            "--apply",
        ],
    )

    assert result.exit_code != 0
    assert "credential-sentinel" not in result.output
    assert config_path.read_bytes() == before


def test_provider_connect_refuses_changed_mapping_for_bound_linear_work(tmp_path, monkeypatch):
    """A new team or status mapping must not silently invalidate pinned tracker identity."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root, bound=True)
    _stub_cli_discovery(monkeypatch)
    before = config_path.read_bytes()

    result = CliRunner().invoke(app, _connect_args(root))

    assert result.exit_code != 0
    assert "bound-work" in result.output
    normalized = " ".join(result.output.replace("│", " ").split())
    assert (
        f"ai-dlc provider connect linear --root {root} --organization org-1 --team team-a "
        "--in-progress doing-a --closed done-a --plan-file .ai-dlc/local/linear-plan.json"
        in normalized
    )
    assert (
        f"ai-dlc project rebind tracker linear --root {root} --connection-plan "
        ".ai-dlc/local/linear-plan.json --mappings .ai-dlc/local/linear-rebind.toml --no-plan"
        in normalized
    )
    assert "automatic" not in result.output.lower()
    assert config_path.read_bytes() == before


def _add_bound_work(
    root: Path,
    work_id: str,
    tracker: str,
    *,
    branch: str,
    provider: str = "linear",
    binding: str | None = "b" * 64,
) -> Path:
    work = {
        "schema": 1,
        "id": work_id,
        "title": f"Bound {work_id}",
        "scope": "Keep every explicitly mapped tracker artifact",
        "requires_spec": False,
        "spec_reason": "Migration regression fixture",
        "acceptance": ["Binding follows reviewed configuration"],
        "reviewed": True,
        "providers": {"tracker": provider},
        "artifacts": {"tracker": tracker, "branch": branch},
        "bindings": {} if binding is None else {"tracker": binding},
    }
    path = root / ".ai-dlc/work" / f"{work_id}.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(work))
    return path


def _rebind_connection_args(root: Path, plan_path: Path, mappings_path: Path) -> list[str]:
    return [
        "project",
        "rebind",
        "tracker",
        "linear",
        "--root",
        str(root),
        "--connection-plan",
        str(plan_path),
        "--mappings",
        str(mappings_path),
        "--no-plan",
    ]


def test_bound_mapping_refusal_guides_atomic_explicit_connection_rebind(tmp_path, monkeypatch):
    """Recovery must migrate only listed bound Linear work in a mixed tracker history."""
    from ai_dlc.cli import app
    from ai_dlc.config import load_project
    from ai_dlc.workflow import WorkService

    root = tmp_path / "project"
    config_path = _write_connect_project(root, bound=True)
    second_path = _add_bound_work(root, "second-work", "SAN-2", branch="keep/second")
    alternate_path = _add_bound_work(
        root,
        "github-work",
        "GH-9",
        branch="keep/github",
        provider="github-issues",
        binding="c" * 64,
    )
    unbound_path = _add_bound_work(
        root,
        "unbound-linear",
        "SAN-3",
        branch="keep/unbound",
        binding=None,
    )
    preserved = {
        alternate_path: alternate_path.read_bytes(),
        unbound_path: unbound_path.read_bytes(),
    }
    calls = _stub_cli_discovery(monkeypatch)
    monkeypatch.setenv("LINEAR_TEST_TOKEN", "credential-sentinel")
    plan_path = root / ".ai-dlc/local/linear-plan.json"
    mappings_path = root / ".ai-dlc/local/linear-rebind.toml"
    runner = CliRunner()

    refused = runner.invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)])
    assert refused.exit_code != 0
    assert plan_path.is_file()
    assert "already bound: bound-work, second-work." in refused.output
    assert "github-work" not in refused.output
    assert "unbound-linear" not in refused.output
    normalized = " ".join(refused.output.replace("│", " ").split())
    assert (
        f"ai-dlc project rebind tracker linear --root {root} --connection-plan "
        ".ai-dlc/local/linear-plan.json --mappings .ai-dlc/local/linear-rebind.toml --no-plan"
        in normalized
    )
    mappings_path.write_text(
        tomli_w.dumps(
            {
                "bound-work": {"tracker": "SAN-101"},
                "second-work": {"tracker": "SAN-202"},
            }
        )
    )

    result = runner.invoke(app, _rebind_connection_args(root, plan_path, mappings_path))

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["status"] == "applied"
    assert payload["connection"] == "applied"
    assert [work["id"] for work in payload["active_work"]] == ["bound-work", "second-work"]
    assert len(calls) == 2
    config = load_project(root)
    assert config["providers"]["linear"] == {
        "token_env": "LINEAR_TEST_TOKEN",
        "team_id": "team-a",
        "statuses": {"in_progress": "doing-a", "closed": "done-a"},
    }
    expected_trackers = {"bound-work": "SAN-101", "second-work": "SAN-202"}
    for work_id, tracker in expected_trackers.items():
        path = root / ".ai-dlc/work" / f"{work_id}.toml"
        work = tomllib.loads(path.read_text())
        assert work["artifacts"]["tracker"] == tracker
        assert work["artifacts"].get("branch") == (
            "keep/second" if work_id == "second-work" else None
        )
        assert work["bindings"]["tracker"] not in {"a" * 64, "b" * 64}
        WorkService(root, config, state_path=tmp_path / "state").load(work_id)
    assert "credential-sentinel" not in result.output + plan_path.read_text()
    assert second_path.exists() and config_path.exists()
    assert all(path.read_bytes() == contents for path, contents in preserved.items())


def test_bound_mapping_recovery_quotes_caller_selected_connection_plan_path(tmp_path, monkeypatch):
    """A copied recovery command must retain a plan path containing shell syntax as one token."""
    from ai_dlc.cli import app

    root = tmp_path / "project"
    _write_connect_project(root, bound=True)
    _stub_cli_discovery(monkeypatch)
    relative_plan = Path(".ai-dlc/local/reviewed plan;$(not-a-command).json")
    plan_path = root / relative_plan

    result = CliRunner().invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)])

    assert result.exit_code != 0
    assert plan_path.is_file()
    marker = "Complete the reviewed migration with `"
    command = result.output.split(marker, 1)[1].split("`", 1)[0]
    assert shlex.split(command) == [
        "ai-dlc",
        "project",
        "rebind",
        "tracker",
        "linear",
        "--root",
        str(root),
        "--connection-plan",
        relative_plan.as_posix(),
        "--mappings",
        ".ai-dlc/local/linear-rebind.toml",
        "--no-plan",
    ]


@pytest.mark.parametrize("failure", ["stale", "tampered", "remote", "incomplete-mappings"])
def test_explicit_connection_rebind_failures_leave_every_project_file_unchanged(
    tmp_path, monkeypatch, failure
):
    """No validation or discovery failure may partially update config or work records."""
    import ai_dlc.provider_onboarding as onboarding
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root, bound=True)
    _add_bound_work(root, "second-work", "SAN-2", branch="keep/second")
    _add_bound_work(
        root,
        "github-work",
        "GH-9",
        branch="keep/github",
        provider="github-issues",
        binding="c" * 64,
    )
    discovery = _selection_discovery()
    _stub_cli_discovery(monkeypatch, discovery)
    plan_path = root / ".ai-dlc/local/linear-plan.json"
    mappings_path = root / ".ai-dlc/local/linear-rebind.toml"
    runner = CliRunner()
    refused = runner.invoke(app, [*_connect_args(root), "--plan-file", str(plan_path)])
    assert refused.exit_code != 0 and plan_path.is_file()
    mappings = {
        "bound-work": {"tracker": "SAN-101"},
        "second-work": {"tracker": "SAN-202"},
    }
    if failure == "stale":
        config_path.write_text(config_path.read_text() + '\n[project]\nname = "Changed"\n')
    elif failure == "tampered":
        saved = json.loads(plan_path.read_text())
        saved["patch"]["token_env"] = "credential-sentinel"
        plan_path.write_text(json.dumps(saved))
    elif failure == "remote":
        discovery["teams"][0]["states"] = [
            state for state in discovery["teams"][0]["states"] if state["id"] != "doing-a"
        ]
        monkeypatch.setattr(
            onboarding,
            "discover_linear",
            lambda settings, *, environ, client: deepcopy(discovery),
        )
    else:
        mappings.pop("second-work")
    mappings_path.write_text(tomli_w.dumps(mappings))
    before = {
        path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }

    result = runner.invoke(app, _rebind_connection_args(root, plan_path, mappings_path))

    assert result.exit_code != 0
    expected_error = {
        "stale": "source digest changed",
        "tampered": "Invalid Linear connection plan patch",
        "remote": "not in the selected team",
        "incomplete-mappings": "second-work",
    }[failure]
    assert expected_error in result.output
    assert "github-work" not in result.output
    assert "credential-sentinel" not in result.output
    assert before == {
        path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


def test_provider_connect_redacts_remote_credential_sentinel_from_stable_cli_error(
    tmp_path, monkeypatch
):
    """Provider failures must not echo an authorization value into terminal output."""
    import ai_dlc.provider_onboarding as onboarding
    from ai_dlc.cli import app

    root = tmp_path / "project"
    config_path = _write_connect_project(root)
    monkeypatch.setenv("LINEAR_TEST_TOKEN", "credential-sentinel")

    def fail(settings, *, environ, client):
        raise RuntimeError("Linear discovery failed because GraphQL returned errors")

    monkeypatch.setattr(onboarding, "discover_linear", fail)
    before = config_path.read_bytes()

    result = CliRunner().invoke(app, ["provider", "connect", "linear", "--root", str(root)])

    assert result.exit_code != 0
    assert "Linear discovery failed" in result.output
    assert "credential-sentinel" not in result.output
    assert config_path.read_bytes() == before
