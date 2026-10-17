"""Production executable tracker adapter; JSON in/out, gh diagnostics on stderr."""

import json
import os
import re
import subprocess
import sys
from urllib.parse import urlsplit

from ai_dlc.contracts import Request, validate_request, validate_response
from ai_dlc.providers.github_projects import GitHubProjects

ISSUE_FIELDS = "id,number,url,state,stateReason,title,body"
GRAPHQL_UNAVAILABLE = (
    "GitHub GraphQL is unavailable; GitHub Projects planning status needs it. Rerun "
    "where GraphQL is reachable to reconcile the configured Project."
)


class GraphQLUnavailable(RuntimeError):
    """The GraphQL endpoint itself refused the request (proxy, policy or outage)."""


def graphql_refused(error):
    """True when gh reports an HTTP-level refusal of the GraphQL endpoint.

    Scope, rate-limit and query errors are not refusals: REST would fail the same way,
    or the GraphQL answer is authoritative and must surface unchanged.
    """
    lowered = error.lower()
    return (
        "graphql" in lowered
        and re.search(r"\bHTTP (403|404|410)\b", error) is not None
        and "rate limit" not in lowered
        and "scope" not in lowered
    )


class GitHubIssuesProvider:
    def __init__(self, config, *, environ=None):
        self.config = config
        self.environ = os.environ if environ is None else environ
        self.host = config.get("host", "github.com")
        repository = config.get("repository", "")
        if not isinstance(self.host, str) or not re.fullmatch(r"[A-Za-z0-9.-]+", self.host):
            raise ValueError("Invalid GitHub host")
        if not isinstance(repository, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository
        ):
            raise ValueError("GitHub repository must be owner/name")
        self.project = (
            GitHubProjects(config["project"], self.graphql) if "project" in config else None
        )
        # Set once GraphQL is refused; native issue operations then use REST, and
        # Projects planning (GraphQL-only for node-identified projects) is skipped.
        self.rest = False

    def run(self, args, *, input=None):
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            input=input,
            env={**self.environ, "GH_HOST": self.host},
            timeout=self.config.get("timeout", 30),
            check=False,
        )
        if result.returncode:
            error = result.stderr.strip()
            if graphql_refused(error):
                raise GraphQLUnavailable(error)
            raise RuntimeError(self.explain(error))
        return result.stdout.strip()

    def explain(self, error):
        """Turn gh's repeated per-field scope refusals into one repairable explanation."""
        required = re.findall(r"requires one of the following scopes: \[([^\]]*)\]", error)
        if not required:
            return error
        granted = re.search(r"only been granted the: \[([^\]]*)\]", error)
        # gh lists alternatives per field; the first of each is the narrowest that satisfies it.
        scopes = sorted({re.findall(r"'([^']+)'", group)[0] for group in required if "'" in group})
        held = ", ".join(re.findall(r"'([^']+)'", granted.group(1))) if granted else "unknown"
        return (
            f"GitHub token lacks the {', '.join(scopes)} scope needed for the configured "
            f"Project (granted: {held}). Run `gh auth refresh --hostname {self.host} "
            f"--scopes {','.join(scopes)}`, or create the work record from explicit fields."
        )

    def gh(self, *args):
        return self.run([*args, "--repo", f"{self.host}/{self.config['repository']}"])

    def graphql(self, query, variables):
        response = json.loads(
            self.run(
                ["api", "graphql", "--method", "POST", "--hostname", self.host, "--input", "-"],
                input=json.dumps({"query": query, "variables": variables}),
            )
        )
        if response.get("errors") or not isinstance(response.get("data"), dict):
            raise RuntimeError("GitHub GraphQL request failed or returned incomplete data")
        return response["data"]

    def rest_api(self, path, *fields, method="GET"):
        args = ["api", "--hostname", self.host, "--method", method, path]
        for name, value in fields:
            args += ["-f", f"{name}={value}"]
        return json.loads(self.run(args) or "null")

    def issue_path(self, number):
        return f"repos/{self.config['repository']}/issues/{number}"

    def rest_issue(self, number):
        data = self.rest_api(self.issue_path(number))
        if not isinstance(data, dict) or "pull_request" in data:
            raise ValueError("Issue reference does not name a GitHub issue")
        reason = data.get("state_reason")
        return {
            "id": data.get("node_id"),
            "number": data.get("number"),
            "url": data.get("html_url"),
            "state": str(data.get("state", "")).upper(),
            "stateReason": reason.upper() if isinstance(reason, str) and reason else None,
            "title": data.get("title"),
            "body": data.get("body") or "",
        }

    def issue_row(self, number):
        if not self.rest:
            try:
                return json.loads(self.gh("issue", "view", number, "--json", ISSUE_FIELDS))
            except GraphQLUnavailable:
                self.rest = True
        return self.rest_issue(number)

    def native(self, number, action, *args, state=None, fields=()):
        """Close, reopen or edit an issue through gh, or REST once GraphQL is refused."""
        if not self.rest:
            try:
                self.gh("issue", action, number, *args)
                return
            except GraphQLUnavailable:
                self.rest = True
        self.rest_api(
            self.issue_path(number),
            *([("state", state)] if state else []),
            *fields,
            method="PATCH",
        )

    def project_available(self):
        if self.project and not self.rest:
            try:
                self.project.validate()
            except GraphQLUnavailable:
                self.rest = True
        return bool(self.project) and not self.rest

    def require_project(self):
        if self.project and not self.project_available():
            raise RuntimeError(GRAPHQL_UNAVAILABLE)

    def verify_viewer(self):
        if "viewer_id" in self.config:
            expected = self.config["viewer_id"]
            viewer = None
            if not self.rest:
                try:
                    viewer = self.graphql("query Viewer { viewer { id } }", {}).get("viewer")
                except GraphQLUnavailable:
                    self.rest = True
            if self.rest:
                user = self.rest_api("user")
                viewer = {"id": user.get("node_id")} if isinstance(user, dict) else None
            if (
                not isinstance(expected, str)
                or not expected
                or not isinstance(viewer, dict)
                or viewer.get("id") != expected
            ):
                raise ValueError("Authenticated GitHub viewer identity mismatch")

    def reference(self, reference):
        if re.fullmatch(r"[1-9][0-9]*", reference):
            return reference
        parsed = urlsplit(reference)
        prefix = f"/{self.config['repository']}/issues/"
        if (
            parsed.scheme != "https"
            or parsed.netloc.lower() != self.host.lower()
            or parsed.query
            or parsed.fragment
            or not parsed.path.lower().startswith(prefix.lower())
        ):
            raise ValueError("Issue reference belongs to a different GitHub origin")
        number = parsed.path[len(prefix) :]
        if not re.fullmatch(r"[1-9][0-9]*", number):
            raise ValueError("Invalid issue reference")
        return number

    def item(self, row):
        if self.reference(row["url"]) != str(row["number"]):
            raise ValueError("Issue identity mismatch")
        native = row["state"].lower()
        reason = row.get("stateReason")
        if native not in {"open", "closed"}:
            raise ValueError("Unknown native issue state")
        state = native
        if native == "closed":
            state = (
                "closed"
                if reason == "COMPLETED"
                else "cancelled"
                if reason == "NOT_PLANNED"
                else "unknown"
            )
        result = {
            **row,
            "id": str(row["number"]),
            "node_id": row.get("id"),
            "state": state,
            "issue_state": native,
            "state_reason": reason,
        }
        if self.project:
            if not isinstance(result["node_id"], str) or not result["node_id"]:
                raise ValueError("Missing issue node identity")
            if not self.rest:
                try:
                    result["project"] = self.project.snapshot(result)
                except GraphQLUnavailable:
                    self.rest = True
            if self.rest:
                result["project"] = {
                    "id": self.project.config["id"],
                    "item_id": None,
                    "status_field_id": self.project.config["status_field_id"],
                    "status_option_id": None,
                    "reconciled": False,
                    "reason": GRAPHQL_UNAVAILABLE,
                }
                return result
            if (
                native == "open"
                and result["project"]["status_option_id"]
                == self.project.config["statuses"]["in_progress"]
            ):
                result["state"] = "in_progress"
        return result

    def read(self, reference):
        number = self.reference(reference)
        self.verify_viewer()
        item = self.item(self.issue_row(number))
        if item["id"] != number:
            raise ValueError("Issue response identity mismatch")
        return item

    def invoke(self, operation, payload):
        payload = validate_request(operation, payload).payload
        if operation == "capabilities":
            # Without GraphQL the Project cannot be read or written: reconciliation is
            # withheld so completion closes the native issue only, while in_progress stays
            # declared so a start fails visibly instead of silently skipping planning.
            planning = self.project_available()
            result = {
                "schema": 1,
                "lifecycle": {"in_progress": self.project is not None, "closed": True},
                "optional_operations": ["link", "prepare", "reconcile_closed"]
                if planning
                else ["link"],
            }
        elif operation == "find":
            rows = json.loads(
                self.gh(
                    "issue",
                    "list",
                    "--state",
                    "all",
                    "--search",
                    payload["correlation"],
                    "--limit",
                    "100",
                    "--json",
                    ISSUE_FIELDS,
                )
            )
            if len(rows) >= 100:
                raise RuntimeError("Correlation search is incomplete")
            result = {
                "items": [
                    self.item(r) for r in rows if payload["correlation"] in (r.get("body") or "")
                ]
            }
        elif operation == "read":
            result = self.read(payload["reference"])
        elif operation == "create":
            found = self.invoke("find", {"correlation": payload["correlation"]})["items"]
            if len(found) > 1:
                raise ValueError("Duplicate correlation conflict")
            if found:
                return found[0]
            self.require_project()
            self.verify_viewer()
            url = self.gh(
                "issue",
                "create",
                "--title",
                payload["title"],
                "--body",
                payload.get("body", "") + "\n" + payload["correlation"],
            )
            result = self.read(url)
        elif operation == "prepare":
            current = self.read(payload["reference"])
            if not self.project:
                raise ValueError("Project prepare is unsupported")
            self.require_project()
            if current["issue_state"] != "open":
                raise ValueError("Cannot prepare a terminal issue")
            self.verify_viewer()
            if not current["project"]["item_id"]:
                self.project.attach(current)
                # Attachment can race another actor; preserve their planning state.
                # Start applies the requested state, while prepare only adds membership.
            result = self.read(payload["reference"])
        elif operation in {"transition", "reconcile_closed"}:
            state = payload.get("state", "closed")
            if state not in {"open", "closed", "in_progress"} or (
                state == "in_progress" and not self.project
            ):
                raise ValueError(
                    "GitHub Issues supports open/closed; intermediate states unsupported"
                )
            current = self.read(payload["reference"])
            if (operation == "reconcile_closed" or state == "in_progress") and self.project:
                self.require_project()
            if operation == "reconcile_closed" and (
                not self.project or current["state"] != "closed"
            ):
                raise ValueError(
                    "Terminal planning reconciliation requires a successfully closed issue"
                )
            if state == "in_progress" and current["issue_state"] != "open":
                raise ValueError("Cannot start a terminal issue")
            if state == "closed" and current["state"] in {"cancelled", "unknown"}:
                raise ValueError("Cannot complete a cancelled or unknown terminal issue")
            self.verify_viewer()
            if self.project and not self.rest:
                self.project.set_status(current, state)
                current = self.read(payload["reference"])
                if state == "in_progress" and current["issue_state"] != "open":
                    raise RuntimeError("Issue became terminal during planning update")
                if state == "closed" and current["state"] in {"cancelled", "unknown"}:
                    raise RuntimeError("Issue became cancelled during planning update")
            if operation == "reconcile_closed" and current["state"] != "closed":
                raise RuntimeError(
                    "Issue is no longer successfully closed during terminal reconciliation"
                )
            if state == "closed" and current["issue_state"] != "closed":
                self.native(
                    current["id"],
                    "close",
                    "--reason",
                    "completed",
                    state="closed",
                    fields=[("state_reason", "completed")],
                )
            elif state == "open" and current["issue_state"] != "open":
                self.native(current["id"], "reopen", state="open")
            result = self.read(payload["reference"])
            if result["state"] != state or (
                self.project
                and not self.rest
                and result["project"]["status_option_id"] != self.project.config["statuses"][state]
            ):
                raise RuntimeError("Issue or project transition remains uncertain")
        elif operation == "link":
            current = self.read(payload["reference"])
            body = current.get("body", "")
            if payload["url"] not in body:
                self.verify_viewer()
                updated = body + "\n" + payload["url"]
                self.native(current["id"], "edit", "--body", updated, fields=[("body", updated)])
            result = self.read(payload["reference"])
        else:
            raise ValueError(f"Unsupported GitHub operation: {operation}")
        return validate_response(operation, result)


def main():
    try:
        config = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
        request = Request.model_validate_json(sys.stdin.read())
        print(json.dumps(GitHubIssuesProvider(config).invoke(request.operation, request.payload)))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
