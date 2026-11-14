"""Jira REST v3 transport fixtures; no tenant or live authentication evidence."""

import copy
import json

import httpx
import pytest
from fixtures.jira import CLOUD, PAYLOAD, Jira, field, labels_field


@pytest.fixture
def jira():
    return Jira()


def test_create_roundtrip_correlation_property_and_read_identity(jira):
    result = jira.provider().invoke("create", PAYLOAD)
    assert result["state"] == "open" and result["id"] == "101"
    row = jira.issues[0]
    assert (
        row["fields"]["description"]["content"][-1]["content"][0]["text"] == PAYLOAD["correlation"]
    )
    assert row["properties"]["ai-dlc"]["correlation"] == PAYLOAD["correlation"]
    assert row["properties"]["ai-dlc"]["cloud_id"] == CLOUD
    assert (
        jira.provider().invoke("find", {"correlation": PAYLOAD["correlation"]})["items"][0]["id"]
        == "101"
    )
    assert len(jira.writes()) == 1


@pytest.mark.parametrize(
    "mode, header", [("oauth_bearer", "Bearer "), ("personal_scoped_token_basic", "Basic ")]
)
def test_explicit_auth_methods(jira, mode, header):
    jira.config.update(auth_mode=mode, email_env="JIRA_EMAIL")
    jira.provider().invoke("find", {"correlation": "absent"})
    assert all(r.headers["Authorization"].startswith(header) for r in jira.requests)


@pytest.mark.parametrize("damage", ["account", "site", "edition", "mode", "overlap"])
def test_identity_and_mapping_refusals_precede_writes(jira, damage):
    if damage == "account":
        jira.account = "other"
    elif damage == "site":
        jira.site = "https://foreign.atlassian.net"
    elif damage == "edition":
        jira.deployment = "Server"
    elif damage == "mode":
        jira.config["auth_mode"] = "guess"
    else:
        jira.config["resolutions"]["cancelled"] = ["1000"]
    with pytest.raises(ValueError):
        jira.provider().invoke("create", PAYLOAD)
    assert jira.writes() == []


@pytest.mark.parametrize("damage", ["marker", "property", "duplicate", "warning", "token", "page"])
def test_search_conflicts_and_incomplete_pages_refuse(jira, damage):
    jira.provider().invoke("create", PAYLOAD)
    if damage == "marker":
        jira.issues[0]["fields"]["description"]["content"].pop()
    elif damage == "property":
        jira.issues[0]["properties"]["ai-dlc"]["project_id"] = "foreign"
    elif damage == "duplicate":
        jira.issues.append({**copy.deepcopy(jira.issues[0]), "id": "102", "key": "WORK-2"})
    elif damage == "warning":
        jira.search_override = lambda r: {
            "issues": [],
            "isLast": True,
            "warnings": [{"message": "truncated"}],
        }
    elif damage == "token":
        jira.search_override = lambda r: {"issues": [], "isLast": False, "nextPageToken": "same"}
    else:
        jira.search_override = lambda r: {"issues": []}
    with pytest.raises((ValueError, RuntimeError)):
        jira.provider().invoke("find", {"correlation": PAYLOAD["correlation"]})
    assert len(jira.writes()) == 1


def test_complete_search_traverses_continuations(jira):
    jira.provider().invoke("create", PAYLOAD)
    jira.search_override = lambda r: (
        {"issues": copy.deepcopy(jira.issues), "isLast": True}
        if json.loads(r.content).get("nextPageToken")
        else {"issues": [], "isLast": False, "nextPageToken": "next"}
    )
    assert (
        len(jira.provider().invoke("find", {"correlation": PAYLOAD["correlation"]})["items"]) == 1
    )


@pytest.mark.parametrize("damage", ["missing", "unsupported", "reserved", "allowed"])
def test_create_field_validation_before_mutation(jira, damage):
    jira.fields.append(field("customfield_1", "string", True))
    if damage == "unsupported":
        jira.fields[-1]["schema"]["type"] = "mystery"
        jira.config["create_fields"] = {"customfield_1": "x"}
    elif damage == "reserved":
        jira.config["create_fields"] = {"summary": "override"}
    elif damage == "allowed":
        jira.fields[-1]["allowedValues"] = ["allowed"]
        jira.config["create_fields"] = {"customfield_1": "other"}
    with pytest.raises(ValueError):
        jira.provider().invoke("create", PAYLOAD)
    assert jira.writes() == []


@pytest.mark.parametrize("damage", ["ambiguous", "required", "cancelled", "unknown"])
def test_transition_refuses_ambiguity_fields_or_false_completion(jira, damage):
    jira.provider().invoke("create", PAYLOAD)
    if damage == "ambiguous":
        jira.transitions.append({**jira.transitions[-1], "id": "32"})
    elif damage == "required":
        jira.transitions[-1]["fields"] = {"customfield_1": field("customfield_1", required=True)}
    elif damage == "cancelled":
        jira.transition_resolution = "2000"
    else:
        jira.transition_resolution = "9999"
    with pytest.raises((ValueError, RuntimeError)):
        jira.provider().invoke(
            "transition", {"reference": "101", "state": "closed", "operation_id": "finish"}
        )
    assert len(jira.writes("/transitions")) == (0 if damage in ["ambiguous", "required"] else 1)


def test_explicit_transition_and_fields_and_idempotent_link(jira):
    jira.provider().invoke("create", PAYLOAD)
    jira.transitions.append({**jira.transitions[-1], "id": "32"})
    jira.transitions[-1]["fields"] = {"customfield_1": field("customfield_1", required=True)}
    jira.config["transitions"] = {"closed": {"id": "32", "fields": {"customfield_1": "reviewed"}}}
    assert (
        jira.provider().invoke(
            "transition", {"reference": "101", "state": "closed", "operation_id": "finish"}
        )["state"]
        == "closed"
    )
    description = copy.deepcopy(jira.issues[0]["fields"]["description"])
    payload = {
        "reference": "101",
        "url": "https://github.com/acme/app/pull/1",
        "operation_id": "link",
    }
    jira.provider().invoke("link", payload)
    jira.provider().invoke("link", payload)
    assert len(jira.writes("/remotelink")) == 1
    assert jira.issues[0]["fields"]["description"] == description


@pytest.mark.parametrize(
    "reference",
    [
        "https://foreign.atlassian.net/browse/WORK-1",
        "OTHER-1",
        "https://work.atlassian.net/browse/WORK-1?extra=1",
        "../101",
    ],
)
def test_foreign_references_refuse_before_mutation(jira, reference):
    with pytest.raises(ValueError):
        jira.provider().invoke(
            "link",
            {"reference": reference, "url": "https://example.test/pr", "operation_id": "link"},
        )
    assert jira.writes() == []


@pytest.mark.parametrize("operation", ["transition", "link"])
def test_lost_mutation_response_is_read_back_without_repeating(jira, operation):
    jira.provider().invoke("create", PAYLOAD)
    handle = jira.handle

    def lost(request):
        result = handle(request)
        if request.method == "POST" and request.url.path.endswith(
            "/transitions" if operation == "transition" else "/remotelink"
        ):
            raise httpx.ReadTimeout("credential-sentinel", request=request)
        return result

    jira.client = httpx.Client(transport=httpx.MockTransport(lost))
    payload = {
        "reference": "101",
        "operation_id": "mutate",
        **(
            {"state": "closed"} if operation == "transition" else {"url": "https://example.test/pr"}
        ),
    }
    result = jira.provider().invoke(operation, payload)
    assert result["id"] == "101"
    assert len(jira.writes()) == 2


def test_search_missing_optional_property_fetches_exact_property_before_absence(jira):
    jira.provider().invoke("create", PAYLOAD)
    row = copy.deepcopy(jira.issues[0])
    row.pop("properties")
    row["fields"]["description"] = None
    jira.search_override = lambda r: {"issues": [copy.deepcopy(row)], "isLast": True}
    handle = jira.handle

    def property_response(request):
        if request.url.path.endswith("/properties/ai-dlc"):
            return httpx.Response(
                200, json={"key": "ai-dlc", "value": jira.issues[0]["properties"]["ai-dlc"]}
            )
        return handle(request)

    jira.client = httpx.Client(transport=httpx.MockTransport(property_response))
    with pytest.raises(ValueError, match="scope conflict"):
        jira.provider().invoke("find", {"correlation": PAYLOAD["correlation"]})


def test_search_tolerates_authored_unowned_issue_only_after_property_not_found(jira):
    jira.provider().invoke("create", PAYLOAD)
    row = copy.deepcopy(jira.issues[0])
    row.update(id="500", key="WORK-500")
    row.pop("properties")
    row["fields"]["description"] = None
    jira.search_override = lambda r: {
        "issues": [row, copy.deepcopy(jira.issues[0])],
        "isLast": True,
    }
    handle = jira.handle
    jira.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda r: (
                httpx.Response(404) if r.url.path.endswith("/500/properties/ai-dlc") else handle(r)
            )
        )
    )
    assert (
        len(jira.provider().invoke("find", {"correlation": PAYLOAD["correlation"]})["items"]) == 1
    )


def test_redirect_does_not_forward_credentials(jira):
    seen = []

    def redirect(request):
        seen.append(request.url.host)
        return httpx.Response(302, headers={"Location": "https://foreign.test/steal"})

    jira.client = httpx.Client(transport=httpx.MockTransport(redirect), follow_redirects=True)
    with pytest.raises(RuntimeError) as caught:
        jira.provider().invoke("create", PAYLOAD)
    assert seen == ["api.atlassian.com"]
    assert "credential-sentinel" not in str(caught.value)


@pytest.mark.parametrize("shape", ["repeat", "truncated", "changed-total", "page-budget"])
def test_discovery_pagination_refuses_incomplete_metadata(jira, monkeypatch, shape):
    import ai_dlc.providers.jira_cloud as module

    handle = jira.handle
    calls = []

    def pages(request):
        if request.url.path.endswith("/issuetypes"):
            calls.append(request)
            start = int(request.url.params["startAt"])
            if shape == "truncated":
                return httpx.Response(
                    200, json={"issueTypes": [], "startAt": 0, "maxResults": 100, "total": 1}
                )
            row_id = "10" if shape == "repeat" else str(start + 10)
            return httpx.Response(
                200,
                json={
                    "issueTypes": [{"id": row_id, "name": "Task", "subtask": False}],
                    "startAt": start,
                    "maxResults": 1,
                    "total": 100 if shape != "changed-total" else 100 + start,
                },
            )
        return handle(request)

    monkeypatch.setattr(module, "MAX_PAGES", 2)
    jira.client = httpx.Client(transport=httpx.MockTransport(pages))
    with pytest.raises(RuntimeError):
        jira.provider().invoke("create", PAYLOAD)
    assert jira.writes() == [] and len(calls) <= 2


@pytest.mark.parametrize(
    "schema, value",
    [
        ({"type": "string"}, "reviewed"),
        ({"type": "integer"}, 2),
        ({"type": "number"}, 2.5),
        ({"type": "boolean"}, True),
        ({"type": "option"}, {"id": "5"}),
        ({"type": "array", "items": "string"}, ["reviewed"]),
        (
            {
                "type": "string",
                "custom": "com.atlassian.jira.plugin.system.customfieldtypes:textarea",
            },
            {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "reviewed"}]}
                ],
            },
        ),
    ],
)
def test_explicit_supported_create_field_types_roundtrip(jira, schema, value):
    jira.fields.append({**field("customfield_1", required=True), "schema": schema})
    jira.config["create_fields"] = {"customfield_1": value}
    jira.provider().invoke("create", PAYLOAD)
    assert jira.issues[0]["fields"]["customfield_1"] == value


def test_declared_builtin_capabilities_cross_executable_boundary_without_network(jira):
    import os

    from ai_dlc.providers import ExecutableProvider, Registry

    registry = Registry(
        {"providers": {"tickets": jira.config}},
        environ={**os.environ, "JIRA_TOKEN": "credential-sentinel"},
    )
    assert registry.declares("tickets", "capabilities")
    assert isinstance(registry.get("tickets"), ExecutableProvider)
    assert registry.invoke("tickets", "capabilities", {}) == {
        "schema": 1,
        "lifecycle": {"in_progress": True, "closed": True},
        "optional_operations": ["comment", "create_typed", "link", "query", "update"],
    }


def test_completion_refuses_explicit_cancelled_resolution_before_request(jira):
    jira.config["transitions"] = {"closed": {"fields": {"resolution": {"id": "2000"}}}}
    with pytest.raises(ValueError, match="cancellation"):
        jira.provider()
    assert jira.requests == []


@pytest.mark.parametrize("damage", ["missing-resolution", "boolean-schema"])
def test_read_refuses_incomplete_terminal_or_property_evidence(jira, damage):
    jira.provider().invoke("create", PAYLOAD)
    if damage == "missing-resolution":
        jira.issues[0]["fields"].pop("resolution")
    else:
        jira.issues[0]["properties"]["ai-dlc"]["schema"] = True
    with pytest.raises((ValueError, TypeError)):
        jira.provider().invoke("read", {"reference": "101"})


@pytest.mark.parametrize("operation", ["create", "transition"])
@pytest.mark.parametrize("has_default", [False, True])
@pytest.mark.parametrize("has_allowed_values", [False, True])
def test_empty_required_multiselect_refuses_before_mutation(
    jira, operation, has_default, has_allowed_values
):
    from ai_dlc.providers.jira_cloud import JiraFieldError

    metadata = field("customfield_1", "array", required=True, hasDefaultValue=has_default)
    metadata["schema"]["items"] = "option"
    if has_allowed_values:
        metadata["allowedValues"] = [{"id": "5", "value": "Reviewed"}]
    if operation == "create":
        jira.fields.append(metadata)
        jira.config["create_fields"] = {"customfield_1": []}
        payload = PAYLOAD
        endpoint = "/issue"
    else:
        jira.provider().invoke("create", PAYLOAD)
        jira.transitions[-1]["fields"] = {"customfield_1": metadata}
        jira.config["transitions"] = {"closed": {"fields": {"customfield_1": []}}}
        payload = {"reference": "101", "state": "closed", "operation_id": "finish"}
        endpoint = "/transitions"
    with pytest.raises(JiraFieldError, match="required field.*customfield_1"):
        jira.provider().invoke(operation, payload)
    assert jira.writes(endpoint) == []


def test_optional_empty_multiselect_keeps_explicit_clear_semantics(jira):
    metadata = field("customfield_1", "array", required=False)
    metadata["schema"]["items"] = "option"
    metadata["allowedValues"] = [{"id": "5", "value": "Reviewed"}]
    jira.fields.append(metadata)
    jira.config["create_fields"] = {"customfield_1": []}
    jira.provider().invoke("create", PAYLOAD)
    assert jira.issues[0]["fields"]["customfield_1"] == []


def test_registry_discovery_includes_executable_jira_without_network():
    from ai_dlc.providers import Registry

    assert "jira-cloud" in Registry(environ={}).discover()["builtins"]


@pytest.mark.parametrize("operation", ["create", "transition"])
@pytest.mark.parametrize(
    "value",
    [
        None,
        {"type": "doc", "version": 1, "content": []},
        {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "   "}]}],
        },
    ],
)
def test_required_adf_needs_nonempty_write_content(jira, operation, value):
    from ai_dlc.providers.jira_cloud import JiraFieldError

    metadata = field("customfield_1", required=True)
    metadata["schema"]["custom"] = "com.atlassian.jira.plugin.system.customfieldtypes:textarea"
    if operation == "create":
        jira.fields.append(metadata)
        jira.config["create_fields"] = {"customfield_1": value}
        payload = PAYLOAD
        endpoint = "/issue"
    else:
        jira.provider().invoke("create", PAYLOAD)
        jira.transitions[-1]["fields"] = {"customfield_1": metadata}
        jira.config["transitions"] = {"closed": {"fields": {"customfield_1": value}}}
        payload = {"reference": "101", "state": "closed", "operation_id": "finish"}
        endpoint = "/transitions"
    with pytest.raises(JiraFieldError, match="required field.*customfield_1"):
        jira.provider().invoke(operation, payload)
    assert jira.writes(endpoint) == []


@pytest.mark.parametrize(
    "schema,value",
    [({"type": "boolean"}, False), ({"type": "integer"}, 0), ({"type": "number"}, 0.0)],
)
def test_required_false_and_zero_are_valid_values(jira, schema, value):
    jira.fields.append({**field("customfield_1", required=True), "schema": schema})
    jira.config["create_fields"] = {"customfield_1": value}
    jira.provider().invoke("create", PAYLOAD)
    assert jira.issues[0]["fields"]["customfield_1"] == value


def test_optional_null_adf_keeps_clear_semantics(jira):
    metadata = field("customfield_1", required=False)
    metadata["schema"]["custom"] = "com.atlassian.jira.plugin.system.customfieldtypes:textarea"
    jira.fields.append(metadata)
    jira.config["create_fields"] = {"customfield_1": None}
    jira.provider().invoke("create", PAYLOAD)
    assert jira.issues[0]["fields"]["customfield_1"] is None


# KAN-317: a project's real tickets, statuses and types (Jira project KAN's shape).


def filed_by_person(jira, *, status="1", category="new", issue_type="10", key="WORK-7"):
    """An issue ai-dlc did not create: no ai-dlc property and no correlation marker."""
    jira.issues.append(
        {
            "id": "501",
            "key": key,
            "fields": {
                "project": {"id": "100"},
                "issuetype": {"id": issue_type},
                "summary": "Filed by a person",
                "description": None,
                "status": {"id": status, "statusCategory": {"key": category}},
                "resolution": None,
            },
            "properties": {},
        }
    )


KAN_STATUSES = {
    "open": ["1", "5"],
    "in_progress": ["2", "6", "7"],
    "closed": ["3"],
    "cancelled": ["4"],
}


def test_read_transition_and_link_accept_an_issue_without_the_ai_dlc_property(jira):
    filed_by_person(jira)
    provider = jira.provider()
    assert provider.invoke("read", {"reference": "WORK-7"})["state"] == "open"
    started = provider.invoke(
        "transition", {"reference": "WORK-7", "state": "in_progress", "operation_id": "start"}
    )
    assert started["state"] == "in_progress"
    linked = provider.invoke(
        "link",
        {"reference": "WORK-7", "url": "https://example.test/pr/1", "operation_id": "link"},
    )
    assert linked["id"] == "501"
    # find still matches only issues that carry the property, so it never adopts this one.
    assert provider.invoke("find", {"correlation": PAYLOAD["correlation"]})["items"] == []


def test_read_still_refuses_a_present_but_foreign_property(jira):
    filed_by_person(jira)
    jira.issues[0]["properties"] = {"ai-dlc": {"schema": 1, "project_id": "foreign"}}
    with pytest.raises(ValueError, match="scope conflict"):
        jira.provider().invoke("read", {"reference": "WORK-7"})


def test_issue_type_ids_widen_the_types_read_but_not_the_type_created(jira):
    filed_by_person(jira, issue_type="11")
    with pytest.raises(ValueError, match="project/type identity mismatch"):
        jira.provider().invoke("read", {"reference": "WORK-7"})
    jira.config["issue_type_ids"] = ["11", "12"]
    assert jira.provider().invoke("read", {"reference": "WORK-7"})["state"] == "open"
    jira.issues.clear()
    jira.provider().invoke("create", PAYLOAD)
    assert jira.issues[0]["fields"]["issuetype"] == {"id": "10"}


@pytest.mark.parametrize(
    "status, category, state",
    [
        ("1", "new", "open"),
        ("5", "new", "open"),
        ("2", "indeterminate", "in_progress"),
        ("6", "indeterminate", "in_progress"),
        ("7", "indeterminate", "in_progress"),
    ],
)
def test_several_statuses_share_one_normalized_state(jira, status, category, state):
    jira.config["statuses"] = KAN_STATUSES
    filed_by_person(jira, status=status, category=category)
    assert jira.provider().invoke("read", {"reference": "WORK-7"})["state"] == state


def test_completion_moves_from_a_folded_review_status_to_the_first_closed_id(jira):
    jira.config["statuses"] = KAN_STATUSES
    filed_by_person(jira, status="7", category="indeterminate")
    closed = jira.provider().invoke(
        "transition", {"reference": "WORK-7", "state": "closed", "operation_id": "finish"}
    )
    assert closed["state"] == "closed"
    # Starting an issue already in a status that reads as in_progress writes nothing.
    jira.issues[0]["fields"].update(
        status={"id": "7", "statusCategory": {"key": "indeterminate"}}, resolution=None
    )
    before = len(jira.writes("/transitions"))
    jira.provider().invoke(
        "transition", {"reference": "WORK-7", "state": "in_progress", "operation_id": "start"}
    )
    assert len(jira.writes("/transitions")) == before


def test_in_review_and_needs_decision_are_states_and_transition_targets(jira):
    jira.config["statuses"] = {
        "open": ["1", "5"],
        "in_progress": ["2"],
        "in_review": ["7"],
        "needs_decision": ["6"],
        "closed": ["3"],
        "cancelled": ["4"],
    }
    jira.transitions += [
        {"id": "41", "name": "Review", "to": {"id": "7"}, "fields": {}},
        {"id": "51", "name": "Wait", "to": {"id": "6"}, "fields": {}},
    ]
    filed_by_person(jira, status="5")
    provider = jira.provider()
    for state, status in [("needs_decision", "6"), ("in_progress", "2"), ("in_review", "7")]:
        result = provider.invoke(
            "transition", {"reference": "WORK-7", "state": state, "operation_id": state}
        )
        assert result["state"] == state
        assert jira.issues[0]["fields"]["status"]["id"] == status
    assert (
        provider.invoke(
            "transition", {"reference": "WORK-7", "state": "closed", "operation_id": "finish"}
        )["state"]
        == "closed"
    )


def test_unmapped_optional_state_refuses_before_any_request(jira):
    filed_by_person(jira)
    provider = jira.provider()
    with pytest.raises(ValueError, match="supported normalized lifecycle state"):
        provider.invoke(
            "transition", {"reference": "WORK-7", "state": "in_review", "operation_id": "review"}
        )
    assert jira.writes() == []


@pytest.mark.parametrize(
    "statuses",
    [
        {**KAN_STATUSES, "closed": ["3", "5"]},
        {**KAN_STATUSES, "open": []},
        {**KAN_STATUSES, "open": ["To Do"]},
        {**KAN_STATUSES, "in_review": ["2"]},
        {**KAN_STATUSES, "ready_for_agent": ["8"]},
        {key: value for key, value in KAN_STATUSES.items() if key != "cancelled"},
    ],
)
def test_status_list_mappings_refuse_ambiguity_before_requests(jira, statuses):
    jira.config["statuses"] = statuses
    with pytest.raises(ValueError):
        jira.provider()
    assert jira.requests == []


def test_transition_settings_for_an_unmapped_optional_state_refuse(jira):
    jira.config["transitions"] = {"in_review": {"id": "41"}}
    with pytest.raises(ValueError, match="no status mapping"):
        jira.provider()


def test_public_invocation_refuses_every_mapped_terminal_status():
    from ai_dlc.providers import Registry

    config = {"providers": {"jira-cloud": {"kind": "jira-cloud", "statuses": KAN_STATUSES}}}
    registry = Registry(config, environ={})
    for state in ["3", "4", "closed"]:
        with pytest.raises(ValueError, match="Terminal transitions"):
            registry.invoke(
                "jira-cloud",
                "transition",
                {"reference": "WORK-7", "state": state, "operation_id": "x"},
            )


# Labels and update (KAN-441): the tracker tools of the MCP surface write through these.


def test_create_sets_labels_and_reads_them_back(jira):
    jira.fields.append(labels_field())

    result = jira.provider().invoke("create", {**PAYLOAD, "labels": ["exec:pair", "repo:x"]})

    assert result["labels"] == ["exec:pair", "repo:x"]
    assert jira.issues[0]["fields"]["labels"] == ["exec:pair", "repo:x"]
    assert "update" in jira.provider().invoke("capabilities", {})["optional_operations"]


def test_create_with_labels_refuses_when_the_project_has_no_labels_field(jira):
    with pytest.raises(ValueError, match="not available"):
        jira.provider().invoke("create", {**PAYLOAD, "labels": ["exec:pair"]})
    assert jira.writes() == []


def test_update_sets_fields_keeps_the_correlation_marker_and_reads_back(jira):
    jira.fields.append(labels_field())
    jira.provider().invoke("create", PAYLOAD)
    payload = {
        "reference": "WORK-1",
        "operation_id": "edit",
        "title": "Renamed",
        "body": "New body",
        "labels": ["exec:human"],
    }

    result = jira.provider().invoke("update", payload)

    assert result["labels"] == ["exec:human"]
    fields = jira.issues[0]["fields"]
    assert fields["summary"] == "Renamed"
    texts = [part["content"][0]["text"] for part in fields["description"]["content"]]
    assert texts == ["New body", PAYLOAD["correlation"]]
    assert jira.provider().invoke("find", {"correlation": PAYLOAD["correlation"]})["items"]
    assert [r.method for r in jira.requests if r.url.path.endswith("/issue/101")][-2:] == [
        "PUT",
        "GET",
    ]


@pytest.mark.parametrize("damage", ["closed", "empty", "not-editable", "lost"])
def test_update_refuses_or_reports_uncertain(jira, damage):
    jira.provider().invoke("create", PAYLOAD)
    payload = {"reference": "101", "operation_id": "edit", "labels": ["x"]}
    if damage == "closed":
        jira.fields.append(labels_field())
        jira.provider().invoke(
            "transition", {"reference": "101", "state": "closed", "operation_id": "finish"}
        )
    elif damage == "empty":
        payload = {"reference": "101", "operation_id": "edit"}
    elif damage == "lost":
        jira.fields.append(labels_field())
        original = jira.handle

        def drop_put(request):
            if request.method == "PUT":
                jira.requests.append(request)
                return httpx.Response(204)
            return original(request)

        jira.client = httpx.Client(transport=httpx.MockTransport(drop_put))
    with pytest.raises((ValueError, RuntimeError)):
        jira.provider().invoke("update", payload)
    assert "labels" not in jira.issues[0]["fields"]


def test_query_builds_quoted_jql_and_filters_state_without_writing(jira):
    jira.fields.append(labels_field())
    jira.provider().invoke("create", {**PAYLOAD, "labels": ["exec:pair"]})
    writes = len(jira.writes())

    found = jira.provider().invoke(
        "query", {"text": 'say "hi"', "labels": ["exec:pair"], "state": "open", "limit": 5}
    )

    assert [(i["id"], i["title"], i["labels"]) for i in found["items"]] == [
        ("101", "New work", ["exec:pair"])
    ]
    jql = json.loads(jira.requests[-1].content)["jql"]
    assert jql == (
        'project = 100 AND text ~ "say \\"hi\\"" AND labels = "exec:pair" ORDER BY updated DESC'
    )
    assert len(jira.writes()) == writes
    closed = jira.provider().invoke("query", {"state": "closed", "limit": 5})
    assert closed["items"] == []
    with pytest.raises(ValueError):
        jira.provider().invoke("query", {"text": "a\nb", "limit": 5})


def test_comment_posts_plain_paragraphs_once(jira):
    jira.provider().invoke("create", PAYLOAD)
    payload = {"reference": "WORK-1", "body": "First line\n\nSecond", "operation_id": "c"}

    first = jira.provider().invoke("comment", payload)
    again = jira.provider().invoke("comment", payload)

    assert first == again
    assert first["url"].endswith("/browse/WORK-1?focusedCommentId=9000")
    comments = jira.issues[0]["comments"]
    assert len(comments) == 1
    texts = [part["content"][0]["text"] for part in comments[0]["body"]["content"]]
    assert texts == ["First line", "Second"]


# Decisions (KAN-518): file one with its fields and link it as blocking the work.


def decision_site(jira):
    from fixtures.jira import DECISION_SETTINGS, decision_fields

    jira.fields.append(labels_field())
    jira.decision_fields = decision_fields()
    jira.config["decision"] = copy.deepcopy(DECISION_SETTINGS)
    jira.provider().invoke("create", PAYLOAD)  # the work item, WORK-1 (id 101)
    return jira


DECIDE = {
    "title": "Which store holds the index?",
    "body": "Context",
    "correlation": "<!-- ai-dlc:decision:x -->",
    "operation_id": "decide-1",
    "labels": ["decision", "exec:human"],
    "blocks": "WORK-1",
    "options": ["Git", "SQLite"],
    "recommendation": "Git, reviewed with the records.",
    "default": "Git.",
    "scope": "project",
    "due": "2026-11-20",
}


def test_decide_files_a_decision_with_its_fields_and_one_blocking_link(jira):
    decision_site(jira)

    first = jira.provider().invoke("decide", DECIDE)
    second = jira.provider().invoke("decide", DECIDE)

    assert first["id"] == second["id"] == "102"
    assert first["blocks"] == "https://work.atlassian.net/browse/WORK-1"
    fields = jira.issues[1]["fields"]
    assert fields["issuetype"] == {"id": "45"}
    assert fields["customfield_10104"] == {"id": "10201"}
    assert fields["customfield_10106"] == "2026-11-20"
    options = fields["customfield_10100"]["content"]
    assert [p["content"][0]["text"] for p in options] == ["1. Git", "2. SQLite"]
    assert fields["issuelinks"] == [{"type": {"name": "Blocks"}, "outwardIssue": {"id": "101"}}]
    work = jira.issues[0]["fields"]["issuelinks"]
    assert work == [{"type": {"name": "Blocks"}, "inwardIssue": {"id": "102"}}]  # "is blocked by"
    (link,) = jira.writes("/issueLink")
    assert json.loads(link.content)["inwardIssue"] == {"id": "102"}  # the blocker
    assert "decide" in jira.provider().invoke("capabilities", {})["optional_operations"]


def test_decide_is_unavailable_without_decision_settings(jira):
    jira.provider().invoke("create", PAYLOAD)

    assert "decide" not in jira.provider().invoke("capabilities", {})["optional_operations"]
    with pytest.raises(ValueError, match="decision settings"):
        jira.provider().invoke("decide", DECIDE)
    assert len(jira.writes()) == 1


def test_decide_refuses_a_scope_the_field_does_not_allow(jira):
    decision_site(jira)

    with pytest.raises(ValueError, match="allowed values"):
        jira.provider().invoke("decide", {**DECIDE, "scope": "Galaxy"})
    assert len(jira.issues) == 1


def test_decide_refuses_work_that_is_already_closed(jira):
    decision_site(jira)
    jira.issues[0]["fields"].update(
        status={"id": "3", "statusCategory": {"key": "done"}}, resolution={"id": "1000"}
    )

    with pytest.raises(ValueError, match="open work"):
        jira.provider().invoke("decide", DECIDE)
    assert len(jira.issues) == 1


def test_decide_reports_uncertain_when_the_link_does_not_read_back(jira):
    decision_site(jira)
    jira.drop_links = True

    with pytest.raises(RuntimeError, match="issue link"):
        jira.provider().invoke("decide", DECIDE)


@pytest.mark.parametrize(
    "settings",
    [
        {"issue_type_id": "45", "fields": {"options": "customfield_1"}},
        {"issue_type_id": "Decision", "fields": {}},
        {"issue_type_id": "45", "fields": {}, "extra": 1},
    ],
)
def test_decision_settings_are_checked(jira, settings):
    jira.config["decision"] = settings

    with pytest.raises(ValueError):
        jira.provider()


def test_create_with_a_type_fields_parent_and_a_link(jira):
    decision_site(jira)
    jira.config["issue_type_ids"] = ["46"]
    jira.decision_fields.append(field("parent", "issuelink"))
    jira.extra_types = {"46": jira.decision_fields}
    payload = {
        **PAYLOAD,
        "correlation": "<!-- typed -->",
        "issue_type": "46",
        "fields": {
            "customfield_10100": ["A", "B"],
            "customfield_10101": "A",
            "customfield_10102": "A",
            "customfield_10104": "Suite",
            "customfield_10106": "2026-12-01",
        },
        "parent": "WORK-1",
        "links": [{"type": "Blocks", "target": "WORK-1"}],
    }

    result = jira.provider().invoke("create", payload)

    fields = jira.issues[1]["fields"]
    assert result["id"] == "102" and fields["parent"] == {"id": "101"}
    assert fields["customfield_10104"] == {"id": "10202"}
    assert fields["issuelinks"] == [{"type": {"name": "Blocks"}, "outwardIssue": {"id": "101"}}]
    assert "create_typed" in jira.provider().invoke("capabilities", {})["optional_operations"]


def test_create_refuses_an_unconfigured_type_or_a_system_field(jira):
    decision_site(jira)

    with pytest.raises(ValueError, match="issue_type_ids"):
        jira.provider().invoke("create", {**PAYLOAD, "issue_type": "99"})
    with pytest.raises(ValueError, match="custom field"):
        jira.provider().invoke(
            "create", {**PAYLOAD, "correlation": "c2", "fields": {"summary": "x"}}
        )
    assert len(jira.issues) == 1


def test_a_reversed_link_payload_reads_back_as_the_decision_being_blocked(jira):
    """The fake keeps Jira's POST semantics, so the payload's sides cannot silently swap."""
    decision_site(jira)
    jira.provider().invoke("create", {**PAYLOAD, "correlation": "second"})  # WORK-2, id 102
    jira.client.post(
        f"https://api.atlassian.com/ex/jira/{CLOUD}/rest/api/3/issueLink",
        json={
            "type": {"name": "Blocks"},
            "outwardIssue": {"id": "102"},
            "inwardIssue": {"id": "101"},
        },
    )

    assert jira.issues[1]["fields"]["issuelinks"] == [
        {"type": {"name": "Blocks"}, "inwardIssue": {"id": "101"}}
    ]


def test_create_refuses_the_decision_type(jira):
    decision_site(jira)

    with pytest.raises(ValueError, match="tracker_create_decision"):
        jira.provider().invoke(
            "create",
            {
                **PAYLOAD,
                "correlation": "d",
                "issue_type": "45",
                "fields": {"customfield_10105": "1"},
            },
        )
    assert len(jira.issues) == 1
