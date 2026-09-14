"""Plane transport fixture: configuration, payloads and an in-memory HTTP API."""

import json

import httpx

U = [f"00000000-0000-4000-8000-{i:012d}" for i in range(1, 12)]
CFG = {
    "kind": "plane",
    "deployment": "self_hosted",
    "api_url": "http://localhost:3000",
    "web_url": "http://localhost:3000",
    "auth_mode": "api_key",
    "token_env": "PLANE_TEST_TOKEN",
    "account_id": U[0],
    "workspace_slug": "test-team",
    "workspace_id": U[1],
    "project_id": U[2],
    "project_key": "TEST",
    "statuses": dict(zip(("open", "in_progress", "closed", "cancelled"), U[3:7])),
}
CORRELATION = "<!-- ai-dlc:project=fixture;work=one -->"
CREATE = {
    "title": "Authored <title>",
    "body": "Human <body>",
    "correlation": CORRELATION,
    "operation_id": "fixture-create",
}


def page(rows):
    return {
        "results": rows,
        "count": len(rows),
        "total_results": len(rows),
        "next_page_results": False,
        "next_cursor": "",
    }


class PlaneHTTP:
    def __init__(self):
        self.items, self.links, self.writes = [], [], []
        self.hide_items = self.hide_links = False
        self.lose = None
        self.user = U[0]
        self.states = [
            {"id": i, "name": name, "group": group, "project": U[2], "workspace": U[1]}
            for i, name, group in zip(
                U[3:7],
                ("Todo", "Doing", "Done", "Cancelled"),
                ("unstarted", "started", "completed", "cancelled"),
            )
        ]
        self.project = {
            "id": U[2],
            "identifier": "TEST",
            "name": "Fixture",
            "workspace": U[1],
            "archived_at": None,
        }

    def __call__(self, request):
        p = request.url.path
        if request.method == "GET":
            if p.endswith("/users/me/"):
                return httpx.Response(200, json={"id": self.user})
            if p.endswith("/projects/"):
                return httpx.Response(200, json=page([self.project]))
            if p.endswith("/projects/" + U[2] + "/"):
                return httpx.Response(200, json=self.project)
            if p.endswith("/states/"):
                return httpx.Response(200, json=page(self.states))
            if p.endswith("/work-items/"):
                return httpx.Response(200, json=page([] if self.hide_items else self.items))
            if p.endswith("/links/"):
                return httpx.Response(200, json=page([] if self.hide_links else self.links))
            return httpx.Response(200, json=self.items[0])
        body = json.loads(request.content)
        self.writes.append((request.method, p, body))
        if p.endswith("/links/"):
            self.links.append(
                {
                    "id": U[8],
                    "url": body["url"],
                    "title": body.get("title"),
                    "project": U[2],
                    "workspace": U[1],
                    "issue": U[7],
                }
            )
            result = self.links[-1]
        elif request.method == "POST":
            self.items.append(
                {
                    **body,
                    "id": U[7],
                    "sequence_id": 1,
                    "workspace": U[1],
                    "project": U[2],
                    "archived_at": None,
                }
            )
            result = self.items[-1]
        else:
            self.items[0].update(body)
            result = self.items[0]
        if self.lose == (
            "link"
            if p.endswith("/links/")
            else "create"
            if request.method == "POST"
            else "transition"
        ):
            raise httpx.ReadTimeout("secret response payload")
        return httpx.Response(201 if request.method == "POST" else 200, json=result)
