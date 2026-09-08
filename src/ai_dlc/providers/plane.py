"""Bounded Plane work-items REST contract with local durable mutation intents."""

import copy
import html
import ipaddress
import json
import os
import re
import sys
import uuid
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from ai_dlc.contracts import validate_request, validate_response
from ai_dlc.providers.plane_attempts import PlaneAttemptStore, digest

MAX_PAGES, MAX_ROWS, MAX_REQUESTS, MAX_BYTES = 100, 10000, 300, 8 * 1024 * 1024
STATES = ("open", "in_progress", "closed", "cancelled")
GROUPS = {
    "open": {"backlog", "unstarted"},
    "in_progress": {"started"},
    "closed": {"completed"},
    "cancelled": {"cancelled"},
}


class PlaneUncertain(RuntimeError):
    pass


def uid(value):
    try:
        if not isinstance(value, str) or str(uuid.UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError("Plane requires canonical UUID identity") from None
    return value


def origin(value, deployment):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        raise ValueError("Plane requires an explicit origin")
    parsed = urlsplit(value)
    try:
        host, port = parsed.hostname, parsed.port
        loopback = host == "localhost" or (
            host is not None and ipaddress.ip_address(host).is_loopback
        )
    except ValueError:
        host, port = parsed.hostname, parsed.port
        loopback = False
    if (
        not host
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or "?" in value
        or "#" in value
        or "%" in value
        or parsed.netloc.endswith(":")
        or port == 0
        or "\\" in value
        or not re.fullmatch(r"[a-z0-9.-]+|[0-9a-f:]+", host)
        or parsed.scheme not in {"http", "https"}
        or (parsed.scheme == "http" and (deployment != "self_hosted" or not loopback))
    ):
        raise ValueError("Plane requires HTTPS or explicit self_hosted HTTP loopback origin")
    authority = f"[{host}]" if ":" in host else host
    if port is not None:
        authority += ":" + str(port)
    if parsed.netloc != authority:
        raise ValueError("Plane origin authority must be canonical")
    return parsed.scheme + "://" + authority


def settings(config, *, selected=True):
    config = copy.deepcopy(config)
    if set(config) & {"root", "state_home", "attempt_store", "ledger", "command"}:
        raise ValueError("Plane invocation context cannot come from provider configuration")
    if config.get("deployment") not in {"cloud", "self_hosted"}:
        raise ValueError("Plane deployment must be selected explicitly")
    for key in ("api_url", "web_url"):
        config[key] = origin(config.get(key), config["deployment"])
    if config["deployment"] == "cloud" and (
        config["api_url"] != "https://api.plane.so" or config["web_url"] != "https://app.plane.so"
    ):
        raise ValueError("Plane Cloud origins must match the documented service")
    if config.get("auth_mode") not in {"api_key", "oauth_bearer"}:
        raise ValueError("Plane auth_mode must be selected explicitly")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(config.get("token_env", ""))):
        raise ValueError("Plane requires a named token_env")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(config.get("workspace_slug", ""))):
        raise ValueError("Plane requires an explicit workspace slug")
    if selected:
        for key in ("account_id", "workspace_id", "project_id"):
            uid(config.get(key))
        if not re.fullmatch(r"[A-Z][A-Z0-9_-]*", str(config.get("project_key", ""))):
            raise ValueError("Plane requires reviewed project identifier")
        states = config.get("statuses")
        if (
            not isinstance(states, dict)
            or set(states) != set(STATES)
            or len(set(states.values())) != 4
        ):
            raise ValueError("Plane requires distinct lifecycle state mappings")
        for value in states.values():
            uid(value)
    return config


class Text(HTMLParser):
    def __init__(self, value):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.feed(value)

    def handle_data(self, data):
        self.parts.append(data)


class PlaneProvider:
    def __init__(
        self, config, *, root=None, state_home=None, environ=None, transport=None, selected=True
    ):
        self.config = settings(config, selected=selected)
        self.environ = os.environ if environ is None else environ
        self.root = Path(root).resolve() if root is not None else None
        self.state_home = (
            Path(state_home)
            if state_home is not None
            else Path(self.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        )
        token = self.environ.get(self.config["token_env"])
        if not isinstance(token, str) or not token or any(c in token for c in "\r\n"):
            raise ValueError("Plane token environment reference is unavailable")
        headers = (
            {"X-API-Key": token}
            if self.config["auth_mode"] == "api_key"
            else {"Authorization": "Bearer " + token}
        )
        self.client = httpx.Client(
            headers=headers, transport=transport, follow_redirects=False, timeout=20
        )
        self.requests = 0
        self.workspace_path = "/api/v1/workspaces/" + self.config["workspace_slug"] + "/projects/"

    def close(self):
        self.client.close()

    def request(self, method, path, *, body=None, params=None):
        self.requests += 1
        if self.requests > MAX_REQUESTS:
            raise PlaneUncertain("Plane request budget incomplete; inspect the operation")
        try:
            response = self.client.request(
                method, self.config["api_url"] + path, json=body, params=params
            )
            if response.status_code not in {200, 201} or len(response.content) > MAX_BYTES:
                raise PlaneUncertain(
                    "Plane response unavailable or incomplete; inspect the operation"
                )
            data = response.json()
            if not isinstance(data, dict):
                raise PlaneUncertain("Plane response schema incomplete; inspect the operation")
            return data
        except (httpx.HTTPError, ValueError):
            raise PlaneUncertain("Plane request outcome unknown; inspect the operation") from None

    def pages(self, path):
        rows, ids, cursors = [], set(), set()
        cursor = None
        total = None
        for _ in range(MAX_PAGES):
            data = self.request(
                "GET", path, params={"per_page": 100, **({"cursor": cursor} if cursor else {})}
            )
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("results"), list)
                or type(data.get("next_page_results")) is not bool
                or type(data.get("count")) is not int
                or type(data.get("total_results")) is not int
                or data["count"] != len(data["results"])
                or data["total_results"] < 0
                or (total is not None and total != data["total_results"])
            ):
                raise ValueError("Plane pagination incomplete or inconsistent")
            total = data["total_results"]
            for row in data["results"]:
                if not isinstance(row, dict) or uid(row.get("id")) in ids:
                    raise ValueError("Plane pagination contains duplicate resource IDs")
                ids.add(row["id"])
                rows.append(row)
            if len(rows) > MAX_ROWS or len(rows) > total:
                raise ValueError("Plane pagination exceeds complete resource budget")
            if not data["next_page_results"]:
                if len(rows) != total:
                    raise ValueError("Plane pagination truncated")
                return rows
            cursor = data.get("next_cursor")
            if (
                not isinstance(cursor, str)
                or not cursor
                or len(cursor) > 512
                or cursor in cursors
                or not data["results"]
            ):
                raise ValueError("Plane pagination cursor incomplete or repeated")
            cursors.add(cursor)
        raise ValueError("Plane pagination budget incomplete")

    def identity(self):
        account = self.request("GET", "/api/v1/users/me/")
        account_id = uid(account.get("id"))
        if self.config.get("account_id", account_id) != account_id:
            raise ValueError("Plane authenticated account differs from reviewed account")
        return account_id

    def project(self):
        project = self.request("GET", self.workspace_path + self.config["project_id"] + "/")
        if (
            project.get("id") != self.config["project_id"]
            or project.get("workspace") != self.config["workspace_id"]
            or project.get("identifier") != self.config["project_key"]
            or project.get("archived_at")
        ):
            raise ValueError("Plane project/workspace identity differs or project is archived")
        return project

    @property
    def items_path(self):
        return self.workspace_path + self.config["project_id"] + "/work-items/"

    def state_catalog(self):
        rows = self.pages(self.workspace_path + self.config["project_id"] + "/states/")
        for row in rows:
            if (
                row.get("project") != self.config["project_id"]
                or row.get("workspace") != self.config["workspace_id"]
            ):
                raise ValueError("Plane states cross project/workspace identity")
        for logical in STATES:
            matches = [row for row in rows if row["id"] == self.config["statuses"][logical]]
            if len(matches) != 1 or matches[0].get("group") not in GROUPS[logical]:
                raise ValueError("Plane lifecycle state mapping changed or is ambiguous")
        return rows

    def external_id(self, correlation):
        return digest(
            {
                "api": self.config["api_url"],
                "workspace": self.config["workspace_id"],
                "project": self.config["project_id"],
                "correlation": correlation,
            }
        )

    def item(self, data, correlation=None):
        if (
            not isinstance(data, dict)
            or data.get("workspace") != self.config["workspace_id"]
            or data.get("project") != self.config["project_id"]
            or data.get("archived_at")
        ):
            raise ValueError("Plane work item has foreign or archived identity")
        item_id = uid(data.get("id"))
        value = data.get("description_html")
        if not isinstance(value, str):
            raise TypeError("Plane correlation description is unavailable")
        markers = [
            part
            for part in Text(value).parts
            if part.startswith("<!-- ai-dlc:") and part.endswith("-->")
        ]
        if (
            len(markers) != 1
            or data.get("external_source") != "ai-dlc"
            or data.get("external_id") != self.external_id(markers[0])
            or (correlation is not None and markers[0] != correlation)
        ):
            raise ValueError("Plane exact correlation and external identity disagree")
        state = data.get("state")
        if isinstance(state, dict):
            state = state.get("id")
        logical = next(
            (key for key, value in self.config["statuses"].items() if value == state), "unknown"
        )
        return {
            "id": self.config["api_url"] + self.items_path + item_id + "/",
            "url": self.config["web_url"]
            + "/"
            + self.config["workspace_slug"]
            + "/projects/"
            + self.config["project_id"]
            + "/issues/"
            + item_id,
            "state": logical,
            "title": data.get("name", ""),
            "correlation": markers[0],
        }

    def find(self, correlation):
        expected = self.external_id(correlation)
        found = []
        for row in self.pages(self.items_path):
            value = row.get("description_html", "")
            if (
                row.get("external_source") == "ai-dlc"
                and row.get("external_id") == expected
                or isinstance(value, str)
                and correlation in Text(value).parts
            ):
                found.append(self.item(row, correlation))
        if len(found) > 1:
            raise ValueError("Plane correlation is duplicated; inspect the operation")
        return found[0] if found else None

    def reference(self, reference):
        api_prefix = self.config["api_url"] + self.items_path
        if (
            isinstance(reference, str)
            and reference.startswith(api_prefix)
            and reference.endswith("/")
        ):
            return uid(reference[len(api_prefix) : -1])
        prefix = (
            self.config["web_url"]
            + "/"
            + self.config["workspace_slug"]
            + "/projects/"
            + self.config["project_id"]
            + "/issues/"
        )
        if not isinstance(reference, str) or not reference.startswith(prefix):
            raise ValueError("Plane reference crosses reviewed tenant/project")
        return uid(reference[len(prefix) :])

    def read(self, reference):
        item_id = self.reference(reference)
        result = self.item(self.request("GET", self.items_path + item_id + "/"))
        if result["id"] != self.config["api_url"] + self.items_path + item_id + "/":
            raise ValueError("Plane returned a different work item")
        return result

    def invoke(self, operation, payload):
        payload = validate_request(operation, payload).payload
        self.requests = 0
        if operation == "capabilities":
            return {
                "schema": 1,
                "lifecycle": {"in_progress": True, "closed": True},
                "optional_operations": ["link"],
            }
        mutation = operation in {"create", "link", "transition"}
        if mutation and self.root is None:
            raise ValueError(
                "Plane mutations require trusted local root and durable intent storage"
            )
        self.identity()
        self.project()
        self.state_catalog()
        if operation == "find":
            found = self.find(payload["correlation"])
            return {"items": [found] if found else []}
        if operation == "read":
            return self.read(payload["reference"])
        if not mutation:
            raise ValueError("Unsupported Plane operation")
        if operation == "create" and (
            "<!-- ai-dlc:" in payload["body"]
            or not re.fullmatch(r"<!-- ai-dlc:[^<>\r\n]+ -->", payload["correlation"])
        ):
            raise ValueError("Plane requires one unambiguous exact correlation marker")
        scope = {
            key: self.config[key]
            for key in (
                "deployment",
                "api_url",
                "web_url",
                "account_id",
                "workspace_slug",
                "workspace_id",
                "project_id",
                "project_key",
                "statuses",
            )
        }
        store = PlaneAttemptStore(self.root, self.state_home)
        fresh = store.begin(
            payload["operation_id"], {"scope": scope, "operation": operation, "payload": payload}
        )
        if operation == "create":
            reconcile = lambda: self.find(payload["correlation"])
            path, method = self.items_path, "POST"
            body = {
                "name": payload["title"],
                "description_html": "<p>"
                + html.escape(payload["body"])
                + "</p><p>"
                + html.escape(payload["correlation"])
                + "</p>",
                "state": self.config["statuses"]["open"],
                "external_source": "ai-dlc",
                "external_id": self.external_id(payload["correlation"]),
            }
        else:
            current = self.read(payload["reference"])
            item_id = self.reference(current["id"])
            path = self.items_path + item_id + "/"
            if operation == "transition":
                state = payload["state"]
                if (
                    state not in {"in_progress", "closed"}
                    or current["state"] in {"cancelled", "unknown"}
                    or current["state"] == "closed"
                    and state != "closed"
                ):
                    raise ValueError("Plane refuses unknown or terminal state reversal")

                def reconcile():
                    result = self.read(payload["reference"])
                    return result if result["state"] == state else None

                method, body = "PATCH", {"state": self.config["statuses"][state]}
            else:
                parsed = urlsplit(payload["url"])
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                ):
                    raise ValueError("Plane artifact URL must be an HTTPS reference")
                path += "links/"

                def reconcile():
                    matches = []
                    for row in self.pages(path):
                        if (
                            row.get("project") != self.config["project_id"]
                            or row.get("workspace") != self.config["workspace_id"]
                            or row.get("issue") != item_id
                        ):
                            raise ValueError("Plane link has foreign identity")
                        if row.get("url") == payload["url"]:
                            matches.append(row)
                    if len(matches) > 1:
                        raise ValueError("Plane exact URL is duplicated; inspect the operation")
                    return current if matches else None

                method, body = "POST", {"url": payload["url"], "title": "AI-DLC work evidence"}
        result = reconcile()
        if result is not None:
            store.verify()
            return result
        if not fresh:
            raise PlaneUncertain(
                "Plane intent remains unresolved; inspect "
                + payload["operation_id"]
                + "; retain local state, rerun only reconciles"
            )
        store.verify()
        try:
            self.request(method, path, body=body)
        except PlaneUncertain:
            pass
        result = reconcile()
        if result is None:
            raise PlaneUncertain(
                "Plane outcome remains unresolved; inspect "
                + payload["operation_id"]
                + "; retain local state"
            )
        store.verify()
        return result


def main():
    try:
        config = json.loads(sys.argv[1])
        context = json.loads(sys.argv[2]) if len(sys.argv) == 3 else {}
        provider = PlaneProvider(
            config, root=context.get("root"), state_home=context.get("state_home")
        )
        try:
            request = json.load(sys.stdin)
            result = provider.invoke(request["operation"], request.get("payload", {}))
            print(json.dumps(validate_response(request["operation"], result)))
        finally:
            provider.close()
    except (ValueError, PlaneUncertain) as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:  # noqa: BLE001 -- keep unexpected transport/config errors out of diagnostics
        print("Plane provider failed; inspect operation without retrying mutation", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
