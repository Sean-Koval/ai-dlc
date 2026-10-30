#!/usr/bin/env python3
"""A local stand-in for GitHub (tracker, SCM and CI) used only to record the front-page demo.

It speaks ai-dlc's executable provider contract (one JSON request on stdin, one JSON
response on stdout; contracts/README.md) and keeps its state in ``demo-github.json``
next to itself. ``merged`` answers from the demo repository's Git history: it refuses
while the pull request's branch is not in ``main``, and reports ``main`` as the merge
commit once it is. ``ci`` plays GitHub Actions: it runs ``ai-dlc project check
--required`` at that commit and returns the receipt it wrote, so the finish gates
evaluate real local evidence. Nothing here talks to a network.
"""

import json
import subprocess
import sys
from pathlib import Path

STATE = Path(__file__).with_name("demo-github.json")
REPO = "https://github.com/example/app"


def load() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"issues": {}, "pulls": {}}


def save(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def main() -> int:
    request = json.loads(sys.stdin.read())
    op, payload = request["operation"], request["payload"]
    state = load()
    issues = state["issues"]
    if op == "capabilities":
        result = {
            "schema": 1,
            "lifecycle": {"in_progress": True, "closed": True},
            "optional_operations": [],
        }
    elif op == "find":
        result = {
            "items": [
                {k: v for k, v in issue.items() if k in ("id", "url", "state")}
                for issue in issues.values()
                if issue["correlation"] == payload["correlation"]
            ]
        }
    elif op == "create":
        number = str(len(issues) + state.get("offset", 41) + 1)
        issues[number] = {
            "id": number,
            "url": f"{REPO}/issues/{number}",
            "state": "open",
            "title": payload["title"],
            "correlation": payload["correlation"],
        }
        result = issues[number]
    elif op in ("read", "link", "prepare", "reconcile_closed"):
        result = issues[str(payload["reference"]).rsplit("/", 1)[-1]]
    elif op == "transition":
        issue = issues[str(payload["reference"]).rsplit("/", 1)[-1]]
        issue["state"] = payload["state"]
        result = issue
    elif op == "pull_request_create":
        number = len(state["pulls"]) + len(issues) + state.get("offset", 41) + 1
        state["pulls"][str(number)] = {"title": payload["title"], "head": payload["head"]}
        result = {"url": f"{REPO}/pull/{number}", "number": number}
    elif op == "merged":
        number = str(payload["reference"]).rsplit("/", 1)[-1]
        if git("merge-base", "--is-ancestor", state["pulls"][number]["head"], "main").returncode:
            print(f"PR #{number} is not merged into main", file=sys.stderr)
            return 1
        result = {
            "sha": git("rev-parse", "main").stdout.strip(),
            "pr": {"number": int(number), "merged": True, "html_url": f"{REPO}/pull/{number}"},
        }
    elif op == "ci":
        # CI stand-in: the required checks run at the merge commit and write the receipt.
        receipt_path = Path(".ai-dlc/local/receipt.json")
        run = subprocess.run(
            ["ai-dlc", "project", "check", "--required", "--receipt", str(receipt_path)],
            capture_output=True, text=True, check=False,
        )
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
        if run.returncode or receipt.get("commit") != payload["sha"]:
            print(f"no passing CI run for {payload['sha'][:12]}", file=sys.stderr)
            return 1
        for outcome in receipt["outcomes"]:  # whole seconds, so the recording is reproducible
            outcome["duration_seconds"] = round(outcome["duration_seconds"])
        result = {"sha": payload["sha"], "run_id": 1001, "receipt": receipt}
    else:
        print(f"unsupported operation {op}", file=sys.stderr)
        return 1
    save(state)
    out = {k: v for k, v in result.items() if k not in ("title", "correlation")}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
