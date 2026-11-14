"""Bounded Jira Cloud REST v3 lifecycle; credentials stay in the process environment."""

import base64
import copy
import hashlib
import json
import math
import os
import re
import sys
import uuid
from urllib.parse import urlsplit

import httpx

from ai_dlc.contracts import validate_request, validate_response
from ai_dlc.errors import RefusedError, UncertainError

MAX_PAGES = 100
MAX_ROWS = 10000
MAX_BYTES = 8 * 1024 * 1024
MAX_REQUESTS = 300
MISSING_PROPERTY = object()
STATES = ("open", "in_progress", "closed", "cancelled")
# Optional normalized states for workflows with a review or decision-wait status (KAN's
# In Review and Needs Decision). Unmapped, those statuses read as unknown.
OPTIONAL_STATES = ("in_review", "needs_decision")
# Normalized states a transition may target; the first status ID mapped to the state is
# where the transition lands.
TRANSITION_STATES = ("in_progress", "in_review", "needs_decision", "closed")
# Normalized states a transition may start from; terminal and unknown states never move.
MOVABLE_STATES = ("open", "in_progress", "in_review", "needs_decision")
RESERVED = {"project", "issuetype", "summary", "description", "properties", "ai-dlc"}
# The fields a Decision carries (KAN-518): each names the custom field ID that holds it.
DECISION_FIELDS = ("options", "recommendation", "default", "scope", "due")
# The keys of a decide payload that are a create payload's too.
CREATE_KEYS = ("title", "body", "labels", "correlation", "operation_id", "parent")


class JiraRefusal(RefusedError):
    """Sanitized provider refusal safe for executable diagnostics."""


class JiraUncertain(UncertainError):
    """Sanitized remote failure; no transport payload is retained in the message."""


class JiraFieldError(JiraRefusal):
    """Safe field-ID-only guidance that can cross the executable boundary."""


def identity(value, label, *, numeric=False):
    if not isinstance(value, str) or not value or (numeric and not re.fullmatch(r"[0-9]+", value)):
        raise JiraRefusal(f"Jira requires an explicit {label}")
    return value


def cloud_settings(config, *, selected=True):
    config = copy.deepcopy(config)
    site = urlsplit(identity(config.get("site_url"), "Cloud site URL"))
    if (
        site.scheme != "https"
        or not site.hostname
        or not re.fullmatch(r"[a-z0-9-]+\.atlassian\.net", site.hostname)
        or site.netloc != site.hostname
        or site.path not in {"", "/"}
        or site.query
        or site.fragment
    ):
        raise JiraRefusal("Jira site must be a bare HTTPS atlassian.net Cloud site")
    config["site_url"] = f"https://{site.hostname}"
    cloud = identity(config.get("cloud_id"), "Cloud UUID")
    try:
        if str(uuid.UUID(cloud)) != cloud:
            raise ValueError
    except ValueError:
        raise JiraRefusal("Jira requires an explicit canonical Cloud UUID") from None
    if config.get("auth_mode") not in {"oauth_bearer", "personal_scoped_token_basic"}:
        raise JiraRefusal(
            "Select supported Jira auth_mode explicitly; credentials are never guessed"
        )
    for key in ["token_env"] + (
        ["email_env"] if config["auth_mode"] == "personal_scoped_token_basic" else []
    ):
        if not isinstance(config.get(key), str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", config[key]
        ):
            raise JiraRefusal(f"Jira requires a named {key} environment reference")
    if selected:
        identity(config.get("account_id"), "account ID")
        for key in ("project_id", "issue_type_id"):
            identity(config.get(key), key, numeric=True)
        # issue_type_id is the type ai-dlc creates; issue_type_ids widens what it reads,
        # transitions and links (a project's stories, tasks and bugs).
        extra_types = config.get("issue_type_ids", [])
        if not isinstance(extra_types, list):
            raise JiraRefusal("Jira issue_type_ids must be a list of issue type IDs")
        for value in extra_types:
            identity(value, "issue type ID", numeric=True)
        config["issue_type_ids"] = list(dict.fromkeys([config["issue_type_id"], *extra_types]))
        decision = config.get("decision")
        if decision is not None:
            # Optional: the work type, fields and link a Decision is filed with (decide).
            if not isinstance(decision, dict) or set(decision) - {
                "issue_type_id",
                "link_type",
                "fields",
            }:
                raise JiraRefusal("Jira decision settings support issue_type_id, link_type, fields")
            identity(decision.get("issue_type_id"), "decision issue type ID", numeric=True)
            decision.setdefault("link_type", "Blocks")
            identity(decision["link_type"], "decision link type")
            names = decision.get("fields")
            if (
                not isinstance(names, dict)
                or set(names) != set(DECISION_FIELDS)
                or not all(
                    isinstance(value, str) and re.fullmatch(r"customfield_[0-9]+", value)
                    for value in names.values()
                )
                or len(set(names.values())) != len(names)
            ):
                raise JiraRefusal(
                    "Jira decision fields map options, recommendation, default, scope and due "
                    "to distinct custom field IDs"
                )
            config["issue_type_ids"].append(decision["issue_type_id"])
            config["issue_type_ids"] = list(dict.fromkeys(config["issue_type_ids"]))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", str(config.get("project_key", ""))):
            raise JiraRefusal("Jira requires the reviewed project key")
        statuses = config.get("statuses", {})
        if (
            not isinstance(statuses, dict)
            or not set(STATES) <= set(statuses)
            or set(statuses) - set(STATES) - set(OPTIONAL_STATES)
        ):
            raise JiraRefusal(
                "Jira requires explicit open/in_progress/closed/cancelled status IDs; "
                "in_review and needs_decision are optional"
            )
        # A state maps to one status ID or to a nonempty list of them, so several native
        # statuses can share one normalized state (To Do and Ready for Agent are both open).
        normalized = {}
        for state, value in statuses.items():
            values = value if isinstance(value, list) else [value]
            if not values:
                raise JiraRefusal(f"Jira status mapping for {state} requires a status ID")
            for item in values:
                identity(item, "status ID", numeric=True)
            normalized[state] = values
        mapped = [item for values in normalized.values() for item in values]
        if len(set(mapped)) != len(mapped):
            raise JiraRefusal("Jira status mappings must be distinct")
        config["statuses"] = normalized
        resolutions = config.get("resolutions", {})
        if not isinstance(resolutions, dict) or set(resolutions) != {"closed", "cancelled"}:
            raise JiraRefusal("Jira requires successful and cancelled resolution IDs")
        for values in resolutions.values():
            if not isinstance(values, list) or not values:
                raise JiraRefusal("Jira resolution mapping requires nonempty ID lists")
            for value in values:
                identity(value, "resolution ID", numeric=True)
            if len(set(values)) != len(values):
                raise JiraRefusal("Jira resolution IDs must be unique")
        if set(resolutions["closed"]) & set(resolutions["cancelled"]):
            raise JiraRefusal("Jira successful/cancelled resolution mappings must be disjoint")
        if (
            not isinstance(config.get("create_fields", {}), dict)
            or RESERVED & config.get("create_fields", {}).keys()
        ):
            raise JiraRefusal("Jira create_fields cannot override reserved generated fields")
        transitions = config.get("transitions", {})
        if not isinstance(transitions, dict) or set(transitions) - set(TRANSITION_STATES):
            raise JiraRefusal(
                "Jira transition settings support in_progress, in_review, needs_decision "
                "and closed only"
            )
        if set(transitions) & set(OPTIONAL_STATES) - set(normalized):
            raise JiraRefusal("Jira transition settings name a state with no status mapping")
        for entry in transitions.values():
            if (
                not isinstance(entry, dict)
                or set(entry) - {"id", "fields"}
                or not isinstance(entry.get("fields", {}), dict)
            ):
                raise JiraRefusal("Jira transition settings require reviewed ID/fields")
            if "id" in entry:
                identity(entry["id"], "transition ID", numeric=True)
        resolution = transitions.get("closed", {}).get("fields", {}).get("resolution")
        if resolution is not None and (
            not isinstance(resolution, dict) or resolution.get("id") not in resolutions["closed"]
        ):
            raise JiraRefusal(
                "Jira completion fields cannot select a cancellation or unknown resolution"
            )
    return config


def adf(texts):
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": text}]}
            for text in texts
            if text
        ],
    }


def adf_text(value):
    if value is None:
        return []
    if (
        not isinstance(value, dict)
        or value.get("type") != "doc"
        or value.get("version") != 1
        or not isinstance(value.get("content"), list)
    ):
        raise JiraRefusal("Jira description is not complete ADF")
    result = []

    def walk(node):
        if not isinstance(node, dict) or not isinstance(node.get("type"), str):
            raise TypeError("Jira ADF content is incomplete")
        if node["type"] == "text":
            result.append(identity(node.get("text"), "ADF text"))
        children = node.get("content", [])
        if not isinstance(children, list):
            raise TypeError("Jira ADF content is incomplete")
        for child in children:
            walk(child)

    walk(value)
    return result


def validate_fields(metadata, values):
    """Validate a deliberately bounded field subset without guessing custom values."""
    if not isinstance(metadata, dict) or not isinstance(values, dict):
        raise TypeError("Jira field metadata is incomplete")
    if set(values) - set(metadata):
        raise JiraRefusal("Jira reviewed field is not available in current metadata")
    for key, meta in metadata.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key):
            raise JiraRefusal("Jira field identity is unsupported")
        if (
            not isinstance(meta, dict)
            or type(meta.get("required")) is not bool
            or not isinstance(meta.get("operations"), list)
        ):
            raise JiraRefusal(f"Jira field metadata is incomplete: {key}")
        if key not in values:
            if meta["required"] and meta.get("hasDefaultValue") is not True:
                raise JiraFieldError(f"Jira required field needs a reviewed value: {key}")
            continue
        if "set" not in meta["operations"]:
            raise JiraRefusal(f"Jira field cannot be set: {key}")
        value = values[key]
        if meta["required"] and (value is None or isinstance(value, list) and not value):
            raise JiraFieldError(f"Jira required field needs a reviewed value: {key}")
        schema = meta.get("schema", {})
        type_name = schema.get("type")

        def valid(item, kind):
            if kind == "string":
                return isinstance(item, str) and bool(item)
            if kind == "number":
                return type(item) in {int, float} and math.isfinite(item)
            if kind == "integer":
                return type(item) is int
            if kind == "boolean":
                return type(item) is bool
            if kind == "date":
                return isinstance(item, str) and bool(
                    re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", item)
                )
            if kind in {
                "project",
                "issuetype",
                "option",
                "priority",
                "resolution",
                "version",
                "component",
                "securitylevel",
            }:
                return (
                    isinstance(item, dict)
                    and set(item) == {"id"}
                    and isinstance(item["id"], str)
                    and bool(item["id"])
                )
            return False

        if key == "description" or str(schema.get("custom", "")).endswith(":textarea"):
            texts = adf_text(value)
            if meta["required"] and not any(text.strip() for text in texts):
                raise JiraFieldError(f"Jira required field needs a reviewed value: {key}")
        elif type_name == "array":
            if not isinstance(value, list) or not all(
                valid(item, schema.get("items")) for item in value
            ):
                raise JiraRefusal(f"Jira unsupported or invalid field value: {key}")
        elif not valid(value, type_name):
            raise JiraRefusal(f"Jira unsupported or invalid field value: {key}")
        if "allowedValues" in meta:
            allowed = meta["allowedValues"]
            if not isinstance(allowed, list):
                raise JiraRefusal(f"Jira allowed values are incomplete: {key}")

            def matches(item, allowed=allowed):
                return any(
                    item == other
                    or isinstance(item, dict)
                    and isinstance(other, dict)
                    and item.get("id") == other.get("id")
                    for other in allowed
                )

            if not all(matches(item) for item in (value if type_name == "array" else [value])):
                raise JiraRefusal(f"Jira field value is outside current allowed values: {key}")


class JiraCloudProvider:
    def __init__(self, config, *, client=None, environ=None, selected=True):
        self.config = cloud_settings(config, selected=selected)
        env = os.environ if environ is None else environ
        token = env.get(self.config["token_env"])
        if not token:
            raise JiraRefusal("Jira credential environment reference is not populated")
        if self.config["auth_mode"] == "oauth_bearer":
            self.authorization = "Bearer " + token
        else:
            email = env.get(self.config["email_env"])
            if not email or ":" in email or "\n" in email or "\r" in email:
                raise JiraRefusal("Jira email environment reference is not populated or invalid")
            self.authorization = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
        self.client = client or httpx.Client(timeout=30, follow_redirects=False)
        self.owned_client = client is None
        self.requests_used = 0
        self.account = None
        self.base = "https://api.atlassian.com/ex/jira/" + self.config["cloud_id"] + "/rest/api/3/"

    def close(self):
        if self.owned_client:
            self.client.close()

    def request(self, method, path, *, params=None, body=None, missing_property=False, empty=False):
        self.requests_used += 1
        if self.requests_used > MAX_REQUESTS:
            raise JiraUncertain("Jira complete operation request budget exhausted")
        try:
            response = self.client.request(
                method,
                self.base + path,
                params=params,
                json=body,
                headers={"Authorization": self.authorization, "Accept": "application/json"},
                timeout=30,
                follow_redirects=False,
            )
        except (httpx.HTTPError, ValueError, UnicodeError):
            raise JiraUncertain(
                "Jira request outcome is uncertain; inspect retained work journal"
            ) from None
        if response.status_code == 404 and missing_property:
            return MISSING_PROPERTY
        if not 200 <= response.status_code < 300:
            raise JiraUncertain(
                f"Jira request refused (HTTP {response.status_code}); verify permissions and reviewed fields"
            )
        if response.status_code == 204 or empty and not response.content:
            return None
        if len(response.content) > MAX_BYTES:
            raise JiraUncertain("Jira response exceeds complete-response budget")
        try:
            return response.json()
        except ValueError:
            raise JiraUncertain("Jira response is not complete JSON") from None

    def identity(self):
        site = self.request("GET", "serverInfo")
        if (
            not isinstance(site, dict)
            or site.get("deploymentType") != "Cloud"
            or site.get("baseUrl", "").rstrip("/") != self.config["site_url"]
        ):
            raise JiraRefusal("Jira Cloud site identity mismatch or unsupported edition")
        account = self.request("GET", "myself")
        if not isinstance(account, dict) or account.get("active") is not True:
            raise JiraRefusal("Jira authenticated account is inactive or incomplete")
        account_id = identity(account.get("accountId"), "authenticated account ID")
        if self.config.get("account_id") and account_id != self.config["account_id"]:
            raise JiraRefusal("Jira account identity mismatch")
        return account_id

    def pages(self, path, key, *, id_key="id", params=None):
        rows, seen, total, start = [], set(), None, 0
        for _ in range(MAX_PAGES):
            page = self.request(
                "GET", path, params={**(params or {}), "startAt": start, "maxResults": 100}
            )
            if (
                not isinstance(page, dict)
                or not isinstance(page.get(key), list)
                or type(page.get("total")) is not int
                or page["total"] < 0
                or type(page.get("startAt")) is not int
                or page.get("startAt") != start
                or type(page.get("maxResults")) is not int
                or page["maxResults"] < 1
                or page.get("warningMessages")
                or page.get("warnings")
            ):
                raise JiraUncertain("Jira discovery pagination is incomplete")
            if total is not None and total != page["total"]:
                raise JiraUncertain("Jira discovery changed during pagination")
            total = page["total"]
            batch = page[key]
            if (
                total > MAX_ROWS
                or len(rows) + len(batch) > total
                or len(batch) > page["maxResults"]
            ):
                raise JiraUncertain("Jira discovery exceeds complete resource budget")
            for row in batch:
                if not isinstance(row, dict):
                    raise TypeError("Jira discovery row is incomplete")
                row_id = identity(row.get(id_key), "discovery resource ID")
                if row_id in seen:
                    raise JiraUncertain("Jira discovery repeats resource identity")
                seen.add(row_id)
            rows.extend(batch)
            start += len(batch)
            if start == total:
                if page.get("isLast") is False:
                    raise JiraUncertain("Jira discovery pagination contradicts total")
                return rows
            if not batch or page.get("isLast") is True:
                raise JiraUncertain("Jira discovery pagination is incomplete")
        raise JiraUncertain("Jira discovery pagination budget exhausted; results incomplete")

    def metadata(self, issue_type_id=None):
        project = self.request("GET", "project/" + self.config["project_id"])
        if (
            not isinstance(project, dict)
            or project.get("id") != self.config["project_id"]
            or project.get("key") != self.config["project_key"]
        ):
            raise JiraRefusal("Jira project identity mismatch")
        path = "issue/createmeta/" + self.config["project_id"] + "/issuetypes"
        selected = issue_type_id or self.config["issue_type_id"]
        types = self.pages(path, "issueTypes")
        matches = [row for row in types if row["id"] == selected and row.get("subtask") is False]
        if len(matches) != 1:
            raise JiraRefusal("Jira selected standard issue type is unavailable")
        rows = self.pages(path + "/" + selected, "fields", id_key="fieldId")
        return {row["fieldId"]: row for row in rows}

    def reference(self, reference):
        if reference.startswith("https://"):
            parsed = urlsplit(reference)
            if (
                f"{parsed.scheme}://{parsed.netloc}" != self.config["site_url"]
                or parsed.query
                or parsed.fragment
                or not parsed.path.startswith("/browse/")
            ):
                raise JiraRefusal("Jira reference belongs to another site or is unsupported")
            reference = parsed.path.removeprefix("/browse/")
        if re.fullmatch(r"[0-9]+", reference):
            return reference
        if not re.fullmatch(re.escape(self.config["project_key"]) + r"-[1-9][0-9]*", reference):
            raise JiraRefusal("Jira reference belongs to another project or is unsupported")
        return reference

    def raw_read(self, reference):
        selected = self.reference(reference)
        row = self.request(
            "GET",
            "issue/" + selected,
            params={
                "fields": "project,issuetype,status,resolution,description,summary,labels",
                "properties": "ai-dlc",
            },
        )
        if not isinstance(row, dict) or row.get("id" if selected.isdigit() else "key") != selected:
            raise JiraRefusal("Jira read-back reference identity mismatch")
        return row

    def scope(self):
        return {
            key: self.config[key]
            for key in ("cloud_id", "account_id", "project_id", "issue_type_id")
        }

    def evidence(self, row, *, correlation=None):
        if not isinstance(row, dict) or not isinstance(row.get("fields"), dict):
            raise TypeError("Jira issue identity/correlation evidence is incomplete")
        if "properties" not in row:
            issue_id = identity(row.get("id"), "issue ID", numeric=True)
            prop = self.request(
                "GET", "issue/" + issue_id + "/properties/ai-dlc", missing_property=True
            )
            if prop is MISSING_PROPERTY:
                row["properties"] = {}
            elif isinstance(prop, dict) and prop.get("key") == "ai-dlc" and "value" in prop:
                row["properties"] = {"ai-dlc": prop["value"]}
            else:
                raise JiraRefusal("Jira issue property response is incomplete")
        if not isinstance(row["properties"], dict):
            raise TypeError("Jira issue property evidence is incomplete")
        if correlation is None and "ai-dlc" not in row["properties"]:
            # An issue ai-dlc did not create (filed by a person, an agent through another
            # tool, or hangar) has no property to check. Read, transition and link still
            # apply to it; find and create match only issues that carry the property.
            return True
        fields = row["fields"]
        prop = row["properties"].get("ai-dlc")
        texts = adf_text(fields.get("description"))
        if (
            correlation is not None
            and correlation not in texts
            and (not isinstance(prop, dict) or prop.get("correlation") != correlation)
        ):
            return False
        if (
            not isinstance(prop, dict)
            or type(prop.get("schema")) is not int
            or prop.get("schema") != 1
            or any(prop.get(key) != value for key, value in self.scope().items())
            or not isinstance(prop.get("operation_id"), str)
            or not prop["operation_id"]
            or not isinstance(prop.get("correlation"), str)
            or prop["correlation"] not in texts
            or correlation is not None
            and prop["correlation"] != correlation
        ):
            raise JiraRefusal(
                "Jira correlation property/ADF scope conflict; inspect existing issue"
            )
        return True

    def item(self, row):
        if not isinstance(row, dict) or not isinstance(row.get("fields"), dict):
            raise TypeError("Jira issue identity is incomplete")
        fields = row["fields"]
        if "resolution" not in fields:
            raise JiraRefusal("Jira resolution evidence is incomplete")
        for key, expected in [
            ("project", [self.config["project_id"]]),
            ("issuetype", self.config["issue_type_ids"]),
        ]:
            if not isinstance(fields.get(key), dict) or fields[key].get("id") not in expected:
                raise JiraRefusal("Jira issue project/type identity mismatch")
        issue_id = identity(row.get("id"), "numeric issue ID", numeric=True)
        key = self.reference(identity(row.get("key"), "issue key"))
        if key.isdigit():
            raise JiraRefusal("Jira issue key is incomplete")
        status = fields.get("status")
        if not isinstance(status, dict):
            raise TypeError("Jira status identity is incomplete")
        status_id = identity(status.get("id"), "status ID", numeric=True)
        resolution = fields.get("resolution")
        resolution_id = (
            identity(resolution.get("id"), "resolution ID", numeric=True)
            if isinstance(resolution, dict)
            else None
        )
        if resolution is not None and not isinstance(resolution, dict):
            raise JiraRefusal("Jira resolution identity is incomplete")
        states, resolutions = self.config["statuses"], self.config["resolutions"]
        active = next((name for name in MOVABLE_STATES if status_id in states.get(name, [])), None)
        if status_id in states["cancelled"] or resolution_id in resolutions["cancelled"]:
            state = "cancelled"
        elif status_id in states["closed"] and resolution_id in resolutions["closed"]:
            state = "closed"
        elif (
            active is not None
            and resolution_id is None
            and status.get("statusCategory", {}).get("key") != "done"
        ):
            state = active
        else:
            state = "unknown"
        result = {
            "id": issue_id,
            "url": self.config["site_url"] + "/browse/" + key,
            "state": state,
            "native_status_id": status_id,
            "native_resolution_id": resolution_id,
        }
        labels = fields.get("labels")
        if isinstance(labels, list) and all(isinstance(label, str) for label in labels):
            result["labels"] = labels
        return result

    def read(self, reference):
        row = self.raw_read(reference)
        self.evidence(row)
        return self.item(row)

    def find(self, correlation):
        rows, tokens, ids = [], set(), set()
        token = None
        for _ in range(MAX_PAGES):
            body = {
                "jql": "project = " + self.config["project_id"] + " ORDER BY id",
                "maxResults": 100,
                "fields": ["project", "issuetype", "status", "resolution", "description", "labels"],
                "properties": ["ai-dlc"],
            }
            if token:
                body["nextPageToken"] = token
            page = self.request("POST", "search/jql", body=body)
            if (
                not isinstance(page, dict)
                or not isinstance(page.get("issues"), list)
                or type(page.get("isLast")) is not bool
                or page.get("warnings")
                or page.get("warningMessages")
            ):
                raise JiraUncertain("Jira correlation search is incomplete")
            for row in page["issues"]:
                issue_id = identity(
                    row.get("id") if isinstance(row, dict) else None,
                    "search issue ID",
                    numeric=True,
                )
                if issue_id in ids:
                    raise JiraUncertain("Jira correlation search repeats issue identity")
                ids.add(issue_id)
                if len(ids) > MAX_ROWS:
                    raise JiraUncertain("Jira correlation search budget exceeded; incomplete")
                if self.evidence(row, correlation=correlation):
                    rows.append(self.item(row))
            token = page.get("nextPageToken")
            if page["isLast"]:
                if token:
                    raise JiraUncertain("Jira correlation pagination is contradictory")
                if len(rows) > 1:
                    raise JiraRefusal("Duplicate Jira correlation conflict")
                return {"items": rows}
            if not isinstance(token, str) or not token or token in tokens:
                raise JiraUncertain("Jira correlation search pagination is incomplete")
            tokens.add(token)
        raise JiraUncertain("Jira correlation search page budget exhausted; incomplete")

    def plain_fields(self, metadata, values):
        """Jira values for plain custom field values: ADF text, option IDs, dates."""
        result = {}
        for key, value in values.items():
            if not re.fullmatch(r"customfield_[0-9]+", key) or key not in metadata:
                raise JiraRefusal(f"Jira field is not a custom field of this work type: {key}")
            meta = metadata[key]
            if str(meta.get("schema", {}).get("custom", "")).endswith(":textarea"):
                lines = value if isinstance(value, list) else [str(value)]
                result[key] = adf([str(line) for line in lines])
            elif "allowedValues" in meta and isinstance(value, str):
                allowed = meta["allowedValues"] if isinstance(meta["allowedValues"], list) else []
                chosen = [
                    row
                    for row in allowed
                    if isinstance(row, dict)
                    and str(row.get("value", "")).casefold() == value.casefold()
                ]
                if len(chosen) != 1:
                    raise JiraRefusal(f"Jira field value is not one of its allowed values: {key}")
                result[key] = {"id": identity(chosen[0].get("id"), "option ID")}
            else:
                result[key] = value
        return result

    def create(self, payload, *, decision=False):
        issue_type_id = payload.get("issue_type") or self.config["issue_type_id"]
        if issue_type_id not in self.config["issue_type_ids"]:
            raise JiraRefusal("Jira work type is not one of the configured issue_type_ids")
        settings = self.config.get("decision") or {}
        if issue_type_id == settings.get("issue_type_id") and not decision:
            # A Decision is filed only by decide, which sets just its question fields.
            raise JiraRefusal("File a Decision with decide (tracker_create_decision), not create")
        links = [(link["type"], self.read(link["target"])) for link in payload.get("links") or []]
        parent = self.read(payload["parent"]) if payload.get("parent") else None
        existing = self.find(payload["correlation"])["items"]
        if existing:
            item = existing[0]
        else:
            item = self.file(payload, issue_type_id, parent)
        for link_type, target in links:
            self.issue_link(item["id"], target["id"], link_type)
        return item

    def file(self, payload, issue_type_id, parent):
        # create_fields are reviewed for the configured type only.
        typed = issue_type_id != self.config["issue_type_id"]
        defaults = {} if typed else self.config.get("create_fields", {})
        fields = {
            **defaults,
            "project": {"id": self.config["project_id"]},
            "issuetype": {"id": issue_type_id},
            "summary": payload["title"],
            "description": adf([payload.get("body", ""), payload["correlation"]]),
        }
        if payload.get("labels"):
            fields["labels"] = list(dict.fromkeys([*fields.get("labels", []), *payload["labels"]]))
        metadata = self.metadata(issue_type_id)
        fields.update(self.plain_fields(metadata, payload.get("fields") or {}))
        validate_fields(metadata, fields)
        if parent is not None:
            # The parent field's schema is not a plain value; it is checked for presence only.
            if "parent" not in metadata:
                raise JiraRefusal("Jira work type has no parent field")
            fields["parent"] = {"id": parent["id"]}
        prop = {
            "schema": 1,
            **self.scope(),
            "correlation": payload["correlation"],
            "operation_id": payload["operation_id"],
        }
        result = self.request(
            "POST",
            "issue",
            body={"fields": fields, "properties": [{"key": "ai-dlc", "value": prop}]},
        )
        issue_id = identity(
            result.get("id") if isinstance(result, dict) else None, "created issue ID", numeric=True
        )
        row = self.raw_read(issue_id)
        self.evidence(row, correlation=payload["correlation"])
        if row["properties"]["ai-dlc"] != prop or row.get("id") != issue_id:
            raise JiraRefusal("Jira create read-back identity mismatch; outcome uncertain")
        return self.item(row)

    def decide(self, payload):
        """File a Decision with its fields and a link blocking the work item (``create``)."""
        settings = self.config.get("decision")
        if not settings:
            raise JiraRefusal("Jira decision settings are not configured; decide is unavailable")
        work = self.read(payload["blocks"])
        if work["state"] not in MOVABLE_STATES:
            raise JiraRefusal("A Decision blocks open work only")
        names = settings["fields"]
        options = [f"{number}. {option}" for number, option in enumerate(payload["options"], 1)]
        typed = {
            **{key: payload[key] for key in CREATE_KEYS if key in payload},
            "issue_type": settings["issue_type_id"],
            "fields": {
                names["options"]: options,
                names["recommendation"]: payload["recommendation"],
                names["default"]: payload["default"],
                names["scope"]: payload["scope"],
                names["due"]: payload["due"],
            },
            "links": [{"type": settings["link_type"], "target": payload["blocks"]}],
        }
        return {**self.create(typed, decision=True), "blocks": work["url"]}

    def issue_link(self, source_id, target_id, link_type):
        def linked():
            row = self.request("GET", "issue/" + source_id, params={"fields": "issuelinks"})
            rows = row.get("fields", {}).get("issuelinks") if isinstance(row, dict) else None
            if not isinstance(rows, list) or len(rows) > MAX_ROWS:
                raise JiraUncertain("Jira issue link read-back is incomplete")
            return any(
                isinstance(link, dict)
                and isinstance(link.get("type"), dict)
                and link["type"].get("name") == link_type
                and isinstance(link.get("outwardIssue"), dict)
                and link["outwardIssue"].get("id") == target_id
                for link in rows
            )

        if linked():
            return
        try:
            # On POST, inwardIssue takes the type's outward description: inwardIssue
            # "blocks" outwardIssue. Read from the source, the target shows as outwardIssue.
            self.request(
                "POST",
                "issueLink",
                body={
                    "type": {"name": link_type},
                    "inwardIssue": {"id": source_id},
                    "outwardIssue": {"id": target_id},
                },
                empty=True,  # Jira answers 201 with no body
            )
        except RuntimeError:
            if linked():
                return
            raise
        if not linked():
            raise JiraUncertain(
                "Jira did not confirm the issue link; inspect the work item's links"
            )

    def update(self, payload):
        """Set the summary, description or labels of an open issue, then read it back."""
        row = self.raw_read(payload["reference"])
        self.evidence(row)
        current = self.item(row)
        if current["state"] not in MOVABLE_STATES:
            raise JiraRefusal("Jira update applies only to an open issue")
        fields = {}
        if payload.get("title") is not None:
            fields["summary"] = payload["title"]
        if payload.get("body") is not None:
            # Keep the correlation marker, so find still matches an issue ai-dlc created.
            marker = row["properties"].get("ai-dlc", {}).get("correlation")
            fields["description"] = adf([payload["body"], marker])
        if payload.get("labels") is not None:
            fields["labels"] = list(dict.fromkeys(payload["labels"]))
        if not fields:
            raise JiraRefusal("Jira update needs a title, body or labels")
        meta = self.request("GET", "issue/" + current["id"] + "/editmeta")
        if not isinstance(meta, dict) or not isinstance(meta.get("fields"), dict):
            raise JiraRefusal("Jira edit metadata is incomplete")
        if set(fields) - set(meta["fields"]):
            raise JiraRefusal("Jira field is not editable on this issue")
        validate_fields({key: meta["fields"][key] for key in fields}, fields)
        failure = None
        try:
            self.request("PUT", "issue/" + current["id"], body={"fields": fields})
        except RuntimeError as exc:
            # Known identity allows one read-back; never repeat the mutation here.
            failure = exc
        after = self.raw_read(current["id"])
        self.evidence(after)
        stored = after["fields"]
        expected = {
            "summary": lambda value: stored.get("summary") == value,
            "description": lambda value: adf_text(stored.get("description")) == adf_text(value),
            "labels": lambda value: sorted(stored.get("labels") or []) == sorted(value),
        }
        if not all(expected[key](value) for key, value in fields.items()):
            if failure is not None:
                raise failure
            raise JiraUncertain("Jira update read-back does not match; inspect the issue")
        return self.item(after)

    def query(self, payload):
        """One bounded page of this project's issues matching text and labels; read-only."""

        def quoted(value):
            if any(ord(char) < 32 for char in value):
                raise JiraRefusal("Jira search values cannot hold control characters")
            return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

        jql = "project = " + self.config["project_id"]
        if payload.get("text"):
            jql += " AND text ~ " + quoted(payload["text"])
        for label in payload.get("labels", []):
            jql += " AND labels = " + quoted(label)
        page = self.request(
            "POST",
            "search/jql",
            body={
                "jql": jql + " ORDER BY updated DESC",
                "maxResults": payload["limit"],
                "fields": ["project", "issuetype", "status", "resolution", "summary", "labels"],
            },
        )
        if (
            not isinstance(page, dict)
            or not isinstance(page.get("issues"), list)
            or len(page["issues"]) > payload["limit"]
            or page.get("warnings")
            or page.get("warningMessages")
        ):
            raise JiraUncertain("Jira search is incomplete")
        items = []
        for row in page["issues"]:
            item = self.item(row)
            if isinstance(row["fields"].get("summary"), str):
                item["title"] = row["fields"]["summary"]
            if payload.get("state") in (None, item["state"]):
                items.append(item)
        return {"items": items, "complete": page.get("isLast") is True}

    def comment(self, payload):
        """Add one plain-text comment once; a repeat by this account returns the first."""
        current = self.read(payload["reference"])
        texts = [line.strip() for line in payload["body"].splitlines() if line.strip()]
        path = "issue/" + current["id"] + "/comment"

        def url(comment_id):
            return current["url"] + "?focusedCommentId=" + comment_id

        for row in self.pages(path, "comments"):
            author = row.get("author")
            if (
                isinstance(author, dict)
                and author.get("accountId") == self.account
                and adf_text(row.get("body")) == texts
            ):
                return {"id": str(row["id"]), "url": url(str(row["id"]))}
        created = self.request("POST", path, body={"body": adf(texts)})
        comment_id = identity(
            created.get("id") if isinstance(created, dict) else None, "comment ID", numeric=True
        )
        return {"id": comment_id, "url": url(comment_id)}

    def transition(self, payload):
        state = payload["state"]
        if state not in TRANSITION_STATES or state not in self.config["statuses"]:
            raise JiraRefusal("Jira transition requires a supported normalized lifecycle state")
        # The first status ID mapped to a state is where a transition to it lands.
        target = self.config["statuses"][state][0]
        current = self.read(payload["reference"])
        if current["state"] == state:
            return current
        if current["state"] not in MOVABLE_STATES:
            raise JiraRefusal("Jira terminal or unknown state requires explicit reconciliation")
        response = self.request(
            "GET",
            "issue/" + current["id"] + "/transitions",
            params={"expand": "transitions.fields"},
        )
        rows = response.get("transitions") if isinstance(response, dict) else None
        if not isinstance(rows, list) or len(rows) > MAX_ROWS:
            raise JiraRefusal("Jira current transition discovery is incomplete")
        selected = self.config.get("transitions", {}).get(state, {})
        matches, ids = [], set()
        for row in rows:
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("to"), dict)
                or not isinstance(row.get("fields"), dict)
            ):
                raise TypeError("Jira current transition metadata is incomplete")
            transition_id = identity(row.get("id"), "transition ID", numeric=True)
            if transition_id in ids:
                raise JiraRefusal("Jira transition identity is duplicated")
            ids.add(transition_id)
            if (
                row["to"].get("id") == target
                and row.get("isAvailable") is not False
                and ("id" not in selected or transition_id == selected["id"])
            ):
                matches.append(row)
        if len(matches) != 1:
            raise JiraRefusal("Select one unambiguous currently available Jira transition ID")
        fields = selected.get("fields", {})
        validate_fields(matches[0]["fields"], fields)
        try:
            self.request(
                "POST",
                "issue/" + current["id"] + "/transitions",
                body={"transition": {"id": matches[0]["id"]}, "fields": fields},
            )
        except RuntimeError:
            # Known identity allows one read-back; never repeat the mutation here.
            result = self.read(current["id"])
            if result["state"] == state:
                return result
            raise
        result = self.read(current["id"])
        if result["state"] != state:
            raise JiraUncertain("Jira transition did not confirm requested state; inspect outcome")
        return result

    def link(self, payload):
        current = self.read(payload["reference"])
        parsed = urlsplit(payload["url"])
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise JiraRefusal("Jira evidence link requires an HTTPS URL without credentials")
        global_id = (
            "ai-dlc:"
            + hashlib.sha256(
                json.dumps(
                    {**self.scope(), "issue_id": current["id"], "url": payload["url"]},
                    sort_keys=True,
                ).encode()
            ).hexdigest()
        )
        path = "issue/" + current["id"] + "/remotelink"

        def existing():
            rows = self.request("GET", path)
            if (
                not isinstance(rows, list)
                or len(rows) > MAX_ROWS
                or any(
                    not isinstance(row, dict) or not isinstance(row.get("object"), dict)
                    for row in rows
                )
            ):
                raise JiraRefusal("Jira remote link discovery is incomplete")
            matches = [row for row in rows if row.get("globalId") == global_id]
            if len(matches) > 1 or matches and matches[0]["object"].get("url") != payload["url"]:
                raise JiraRefusal("Jira scoped remote link identity conflict")
            return bool(matches)

        if not existing():
            try:
                self.request(
                    "POST",
                    path,
                    body={
                        "globalId": global_id,
                        "object": {"url": payload["url"], "title": "ai-dlc work evidence"},
                    },
                )
            except RuntimeError:
                if existing():
                    return self.read(current["id"])
                raise
            if not existing():
                raise JiraUncertain("Jira remote link read-back is incomplete; outcome uncertain")
        return self.read(current["id"])

    def invoke(self, operation, payload):
        self.requests_used = 0
        payload = validate_request(operation, payload).payload
        if operation == "capabilities":
            result = {
                "schema": 1,
                "lifecycle": {"in_progress": True, "closed": True},
                "optional_operations": ["comment", "create_typed", "link", "query", "update"]
                + (["decide"] if self.config.get("decision") else []),
            }
        else:
            if operation not in {
                "create",
                "decide",
                "find",
                "read",
                "transition",
                "link",
                "update",
                "query",
                "comment",
            }:
                raise JiraRefusal("Unsupported Jira operation")
            self.account = self.identity()
            if operation == "find":
                result = self.find(payload["correlation"])
            elif operation == "read":
                result = self.read(payload["reference"])
            else:
                result = getattr(self, operation)(payload)
        return validate_response(operation, result)


def main():
    provider = None
    try:
        provider = JiraCloudProvider(json.loads(sys.argv[1]))
        request = json.load(sys.stdin)
        print(json.dumps(provider.invoke(request["operation"], request["payload"])))
    except (JiraRefusal, JiraUncertain) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
    except Exception:  # noqa: BLE001 -- never emit transport credentials across the executable boundary
        print(
            "Jira provider refused or outcome uncertain; inspect identity, permissions and work journal",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    finally:
        if provider is not None:
            provider.close()


if __name__ == "__main__":
    main()
