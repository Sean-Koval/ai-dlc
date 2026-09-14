"""Jira REST v3 transport fixture: settings, field schemas and an in-memory Cloud site."""

import copy
import json

import httpx

CLOUD = "11111111-2222-3333-4444-555555555555"
SETTINGS = {
    "kind": "jira-cloud",
    "site_url": "https://work.atlassian.net",
    "cloud_id": CLOUD,
    "account_id": "account-1",
    "project_id": "100",
    "project_key": "WORK",
    "issue_type_id": "10",
    "auth_mode": "oauth_bearer",
    "token_env": "JIRA_TOKEN",
    "statuses": {"open": "1", "in_progress": "2", "closed": "3", "cancelled": "4"},
    "resolutions": {"closed": ["1000"], "cancelled": ["2000"]},
}
PAYLOAD = {
    "title": "New work",
    "body": "Reviewed acceptance",
    "correlation": "<!-- ai-dlc:exact -->",
    "operation_id": "op-1",
}


def field(key, type="string", required=False, **extra):
    return {
        "fieldId": key,
        "key": key,
        "name": key,
        "schema": {"type": type},
        "required": required,
        "operations": ["set"],
        **extra,
    }


class Jira:
    def __init__(self):
        self.config = copy.deepcopy(SETTINGS)
        self.requests = []
        self.issues = []
        self.links = []
        self.account = "account-1"
        self.site = "https://work.atlassian.net"
        self.deployment = "Cloud"
        self.lost_create = False
        self.hidden = False
        self.search_override = None
        self.fields = [
            field("project", "project", True),
            field("issuetype", "issuetype", True),
            field("summary", required=True),
            field("description"),
        ]
        self.transitions = [
            {"id": "21", "name": "Start", "to": {"id": "2"}, "fields": {}},
            {"id": "31", "name": "Complete", "to": {"id": "3"}, "fields": {}},
        ]
        self.transition_resolution = "1000"
        self.client = httpx.Client(transport=httpx.MockTransport(self.handle))

    def page(self, rows, key="values"):
        return {key: copy.deepcopy(rows), "startAt": 0, "maxResults": 100, "total": len(rows)}

    def handle(self, request):
        assert request.url.host == "api.atlassian.com"
        assert request.url.path.startswith(f"/ex/jira/{CLOUD}/rest/api/3/")
        self.requests.append(request)
        path = request.url.path.split("/rest/api/3/", 1)[1]
        body = json.loads(request.content) if request.content else None
        if path == "serverInfo":
            data = {"deploymentType": self.deployment, "baseUrl": self.site}
        elif path == "myself":
            data = {"accountId": self.account, "active": True}
        elif path == "project/search":
            data = self.page([{"id": "100", "key": "WORK", "name": "Work"}])
        elif path == "project/100":
            data = {"id": "100", "key": "WORK", "name": "Work"}
        elif path == "project/100/statuses":
            data = [
                {
                    "id": "10",
                    "name": "Task",
                    "statuses": [
                        {"id": str(i), "name": n}
                        for i, n in enumerate(["Open", "In Progress", "Done", "Cancelled"], 1)
                    ],
                }
            ]
        elif path == "resolution":
            data = [{"id": "1000", "name": "Done"}, {"id": "2000", "name": "Won't do"}]
        elif path == "issue/createmeta/100/issuetypes":
            data = self.page([{"id": "10", "name": "Task", "subtask": False}], "issueTypes")
        elif path == "issue/createmeta/100/issuetypes/10":
            data = self.page(self.fields, "fields")
        elif path == "search/jql":
            data = (
                self.search_override(request)
                if self.search_override
                else {"issues": [] if self.hidden else copy.deepcopy(self.issues), "isLast": True}
            )
        elif path == "issue" and request.method == "POST":
            row = {
                "id": str(101 + len(self.issues)),
                "key": f"WORK-{1 + len(self.issues)}",
                "fields": body["fields"],
                "properties": {p["key"]: p["value"] for p in body["properties"]},
            }
            row["fields"].update(
                {"status": {"id": "1", "statusCategory": {"key": "new"}}, "resolution": None}
            )
            self.issues.append(row)
            if self.lost_create:
                raise httpx.ReadTimeout("credential-sentinel", request=request)
            return httpx.Response(201, json={"id": row["id"], "key": row["key"]})
        elif path.endswith("/transitions"):
            if request.method == "POST":
                target = next(
                    t["to"]["id"] for t in self.transitions if t["id"] == body["transition"]["id"]
                )
                self.issues[0]["fields"].update(
                    status={
                        "id": target,
                        "statusCategory": {"key": "done" if target == "3" else "indeterminate"},
                    },
                    resolution={"id": self.transition_resolution} if target == "3" else None,
                )
                return httpx.Response(204)
            data = {"transitions": copy.deepcopy(self.transitions)}
        elif path.endswith("/remotelink"):
            if request.method == "POST":
                self.links.append({"id": len(self.links) + 1, **body})
                return httpx.Response(201, json={"id": len(self.links)})
            data = copy.deepcopy(self.links)
        elif path.startswith("issue/"):
            ref = path.split("/")[1]
            data = next((copy.deepcopy(i) for i in self.issues if ref in [i["id"], i["key"]]), None)
            if data is None:
                return httpx.Response(404, json={"errorMessages": ["credential-sentinel"]})
        else:
            raise AssertionError((request.method, path))
        return httpx.Response(200, json=data)

    def provider(self):
        from ai_dlc.providers.jira_cloud import JiraCloudProvider

        return JiraCloudProvider(
            self.config,
            client=self.client,
            environ={"JIRA_TOKEN": "credential-sentinel", "JIRA_EMAIL": "person@example.test"},
        )

    def writes(self, suffix=None):
        return [
            r
            for r in self.requests
            if r.method == "POST"
            and not r.url.path.endswith("/search/jql")
            and (suffix is None or r.url.path.endswith(suffix))
        ]
