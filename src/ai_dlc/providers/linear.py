import os

import httpx

from ai_dlc.contracts import validate_request, validate_response


class LinearProvider:
    def __init__(self, config, *, client=None, environ=None):
        self.config = config
        env = os.environ if environ is None else environ
        self.token = env[config.get("token_env", "LINEAR_API_KEY")]
        self.client = client or httpx.Client(timeout=config.get("timeout", 30))

    def query(self, query, variables):
        response = self.client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": self.token},
            json={"query": query, "variables": variables},
            timeout=self.config.get("timeout", 30),
        )
        response.raise_for_status()
        body = response.json()
        if body.get("errors"):
            raise RuntimeError(f"Linear GraphQL error: {body['errors']}")
        return body["data"]

    def invoke(self, operation, payload):
        validate_request(operation, payload)
        fields = "id url description state { id name type }"
        if operation == "find":
            data = self.query(
                "query($filter: IssueFilter) { issues(filter:$filter, first:100) { nodes { "
                + fields
                + " } pageInfo { hasNextPage } } }",
                {"filter": {"description": {"contains": payload["correlation"]}}},
            )["issues"]
            if data.get("pageInfo", {}).get("hasNextPage"):
                raise RuntimeError("Correlation search is incomplete")
            result = {
                "items": [
                    self.item(i)
                    for i in data["nodes"]
                    if payload["correlation"] in (i.get("description") or "")
                ]
            }
        elif operation == "read":
            result = self.item(
                self.query(
                    "query($id:String!) { issue(id:$id) { " + fields + " } }",
                    {"id": payload["reference"]},
                )["issue"]
            )
        elif operation == "create":
            found = self.invoke("find", {"correlation": payload["correlation"]})["items"]
            if len(found) > 1:
                raise ValueError("Duplicate correlation conflict")
            if found:
                return found[0]
            inp = {
                "teamId": self.config["team_id"],
                "title": payload["title"],
                "description": payload.get("body", "") + "\n" + payload["correlation"],
            }
            data = self.query(
                "mutation($input:IssueCreateInput!) { issueCreate(input:$input) { success issue { "
                + fields
                + " } } }",
                {"input": inp},
            )["issueCreate"]
            if not data["success"]:
                raise RuntimeError("Linear issue creation failed")
            result = self.item(data["issue"])
        else:
            if operation == "transition":
                state = self.config.get("statuses", {}).get(payload["state"])
                if not state:
                    raise ValueError(f"Unsupported Linear state: {payload['state']}")
                inp = {"stateId": state}
            else:
                current = self.query(
                    "query($id:String!) { issue(id:$id) { description } }",
                    {"id": payload["reference"]},
                )["issue"]
                body = current.get("description") or ""
                inp = {
                    "description": body if payload["url"] in body else body + "\n" + payload["url"]
                }
            data = self.query(
                "mutation($id:String!,$input:IssueUpdateInput!) { issueUpdate(id:$id,input:$input) { success issue { "
                + fields
                + " } } }",
                {"id": payload["reference"], "input": inp},
            )["issueUpdate"]
            if not data["success"]:
                raise RuntimeError("Linear issue update failed")
            result = self.item(data["issue"])
        return validate_response(operation, result)

    def item(self, data):
        native = data["state"]
        mapped = next(
            (
                key
                for key, value in self.config.get("statuses", {}).items()
                if value == native.get("id")
            ),
            None,
        )
        names = {
            "todo": "open",
            "backlog": "open",
            "unstarted": "open",
            "started": "in_progress",
            "done": "closed",
            "completed": "closed",
            "canceled": "cancelled",
        }
        state = (
            mapped
            or names.get(native.get("type", "").lower())
            or names.get(native["name"].lower(), native["name"].lower())
        )
        return {**data, "state": state, "native_state": native}
