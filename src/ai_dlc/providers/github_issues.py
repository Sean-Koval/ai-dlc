"""Production executable tracker adapter; JSON in/out, gh diagnostics on stderr."""

import json
import subprocess
import sys

from ai_dlc.contracts import Request, validate_request, validate_response


class GitHubIssuesProvider:
    def __init__(self, config):
        self.config = config

    def gh(self, *args):
        result = subprocess.run(
            ["gh", *args, "--repo", self.config["repository"]],
            capture_output=True,
            text=True,
            timeout=self.config.get("timeout", 30),
            check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return result.stdout.strip()

    def invoke(self, operation, payload):
        validate_request(operation, payload)
        if operation == "find":
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
                    "number,url,state,body",
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
            result = self.item(
                json.loads(
                    self.gh(
                        "issue", "view", payload["reference"], "--json", "number,url,state,body"
                    )
                )
            )
        elif operation == "create":
            found = self.invoke("find", {"correlation": payload["correlation"]})["items"]
            if len(found) > 1:
                raise ValueError("Duplicate correlation conflict")
            if found:
                return found[0]
            url = self.gh(
                "issue",
                "create",
                "--title",
                payload["title"],
                "--body",
                payload.get("body", "") + "\n" + payload["correlation"],
            )
            result = self.invoke("read", {"reference": url})
        elif operation == "transition":
            if payload["state"] not in {"open", "closed"}:
                raise ValueError(
                    "GitHub Issues supports open/closed; intermediate states unsupported"
                )
            self.gh(
                "issue", "close" if payload["state"] == "closed" else "reopen", payload["reference"]
            )
            result = self.invoke("read", {"reference": payload["reference"]})
        else:
            current = self.invoke("read", {"reference": payload["reference"]})
            body = current.get("body", "")
            if payload["url"] not in body:
                self.gh(
                    "issue", "edit", payload["reference"], "--body", body + "\n" + payload["url"]
                )
            result = self.invoke("read", {"reference": payload["reference"]})
        return validate_response(operation, result)

    @staticmethod
    def item(row):
        return {**row, "id": str(row["number"]), "state": row["state"].lower()}


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
