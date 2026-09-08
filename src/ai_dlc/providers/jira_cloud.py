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

MAX_PAGES = 100
MAX_ROWS = 10000
MAX_BYTES = 8 * 1024 * 1024
MAX_REQUESTS = 300
MISSING_PROPERTY = object()
STATES = ("open", "in_progress", "closed", "cancelled")
RESERVED = {"project", "issuetype", "summary", "description", "properties", "ai-dlc"}


class JiraRefusal(ValueError):
    """Sanitized provider refusal safe for executable diagnostics."""


class JiraUncertain(RuntimeError):
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
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", str(config.get("project_key", ""))):
            raise JiraRefusal("Jira requires the reviewed project key")
        statuses = config.get("statuses", {})
        if not isinstance(statuses, dict) or set(statuses) != set(STATES):
            raise JiraRefusal("Jira requires explicit open/in_progress/closed/cancelled status IDs")
        for value in statuses.values():
            identity(value, "status ID", numeric=True)
        if len(set(statuses.values())) != len(STATES):
            raise JiraRefusal("Jira status mappings must be distinct")
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
        if not isinstance(transitions, dict) or set(transitions) - {"in_progress", "closed"}:
            raise JiraRefusal("Jira transition settings support in_progress and closed only")
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
        self.base = "https://api.atlassian.com/ex/jira/" + self.config["cloud_id"] + "/rest/api/3/"

    def close(self):
        if self.owned_client:
            self.client.close()

    def request(self, method, path, *, params=None, body=None, missing_property=False):
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
        if response.status_code == 204:
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

    def metadata(self):
        project = self.request("GET", "project/" + self.config["project_id"])
        if (
            not isinstance(project, dict)
            or project.get("id") != self.config["project_id"]
            or project.get("key") != self.config["project_key"]
        ):
            raise JiraRefusal("Jira project identity mismatch")
        path = "issue/createmeta/" + self.config["project_id"] + "/issuetypes"
        types = self.pages(path, "issueTypes")
        matches = [
            row
            for row in types
            if row["id"] == self.config["issue_type_id"] and row.get("subtask") is False
        ]
        if len(matches) != 1:
            raise JiraRefusal("Jira selected standard issue type is unavailable")
        rows = self.pages(path + "/" + self.config["issue_type_id"], "fields", id_key="fieldId")
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
                "fields": "project,issuetype,status,resolution,description",
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
            ("project", self.config["project_id"]),
            ("issuetype", self.config["issue_type_id"]),
        ]:
            if not isinstance(fields.get(key), dict) or fields[key].get("id") != expected:
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
        if status_id == states["cancelled"] or resolution_id in resolutions["cancelled"]:
            state = "cancelled"
        elif status_id == states["closed"] and resolution_id in resolutions["closed"]:
            state = "closed"
        elif (
            resolution_id is None
            and status_id in {states["open"], states["in_progress"]}
            and status.get("statusCategory", {}).get("key") != "done"
        ):
            state = "open" if status_id == states["open"] else "in_progress"
        else:
            state = "unknown"
        return {
            "id": issue_id,
            "url": self.config["site_url"] + "/browse/" + key,
            "state": state,
            "native_status_id": status_id,
            "native_resolution_id": resolution_id,
        }

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
                "fields": ["project", "issuetype", "status", "resolution", "description"],
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

    def create(self, payload):
        existing = self.find(payload["correlation"])["items"]
        if existing:
            return existing[0]
        fields = {
            **self.config.get("create_fields", {}),
            "project": {"id": self.config["project_id"]},
            "issuetype": {"id": self.config["issue_type_id"]},
            "summary": payload["title"],
            "description": adf([payload.get("body", ""), payload["correlation"]]),
        }
        validate_fields(self.metadata(), fields)
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

    def transition(self, payload):
        state = payload["state"]
        if state not in {"in_progress", "closed"}:
            raise JiraRefusal("Jira transition requires a supported normalized lifecycle state")
        current = self.read(payload["reference"])
        if current["state"] == state:
            return current
        if current["state"] not in {"open", "in_progress"}:
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
                row["to"].get("id") == self.config["statuses"][state]
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
                        "object": {"url": payload["url"], "title": "AI-DLC work evidence"},
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
                "optional_operations": ["link"],
            }
        else:
            if operation not in {"create", "find", "read", "transition", "link"}:
                raise JiraRefusal("Unsupported Jira operation")
            self.identity()
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
