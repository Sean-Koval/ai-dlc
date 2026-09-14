"""Jira REST v3 transport fixtures; no tenant or live authentication evidence."""

import copy
import json

import httpx
import pytest
from fixtures.jira import CLOUD, PAYLOAD, Jira, field


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
        "optional_operations": ["link"],
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
