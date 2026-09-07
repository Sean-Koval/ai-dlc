"""Production executable tracker adapter; JSON in/out, gh diagnostics on stderr."""

import json
import os
import re
import subprocess
import sys
from urllib.parse import urlsplit

from ai_dlc.contracts import Request, validate_request, validate_response
from ai_dlc.providers.github_projects import GitHubProjects

ISSUE_FIELDS = "id,number,url,state,stateReason,body"


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
            raise RuntimeError(result.stderr.strip())
        return result.stdout.strip()

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

    def verify_viewer(self):
        if "viewer_id" in self.config:
            expected = self.config["viewer_id"]
            viewer = self.graphql("query Viewer { viewer { id } }", {}).get("viewer")
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
            result["project"] = self.project.snapshot(result)
            if (
                native == "open"
                and result["project"]["status_option_id"]
                == self.project.config["statuses"]["in_progress"]
            ):
                result["state"] = "in_progress"
        return result

    def read(self, reference):
        number = self.reference(reference)
        item = self.item(json.loads(self.gh("issue", "view", number, "--json", ISSUE_FIELDS)))
        if item["id"] != number:
            raise ValueError("Issue response identity mismatch")
        return item

    def invoke(self, operation, payload):
        payload = validate_request(operation, payload).payload
        if operation == "capabilities":
            if self.project:
                self.project.validate()
            result = {
                "schema": 1,
                "lifecycle": {"in_progress": self.project is not None, "closed": True},
                "optional_operations": ["link", "prepare", "reconcile_closed"]
                if self.project
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
            if self.project:
                self.project.validate()
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
            if self.project:
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
                self.gh("issue", "close", current["id"], "--reason", "completed")
            elif state == "open" and current["issue_state"] != "open":
                self.gh("issue", "reopen", current["id"])
            result = self.read(payload["reference"])
            if result["state"] != state or (
                self.project
                and result["project"]["status_option_id"] != self.project.config["statuses"][state]
            ):
                raise RuntimeError("Issue or project transition remains uncertain")
        elif operation == "link":
            current = self.read(payload["reference"])
            body = current.get("body", "")
            if payload["url"] not in body:
                self.verify_viewer()
                self.gh("issue", "edit", current["id"], "--body", body + "\n" + payload["url"])
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
