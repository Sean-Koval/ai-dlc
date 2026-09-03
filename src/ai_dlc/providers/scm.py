"""Authenticated GitHub merge and workflow evidence, pinned to merged manifests."""

import base64
import hashlib
import json
import math
import re
import subprocess
import tempfile
import tomllib
from pathlib import Path


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def required_checks(config):
    from ai_dlc.project import _check_definitions

    required, _ = _check_definitions(config)
    if not required:
        raise ValueError("CI completion requires nonempty required checks")
    return required


def validate_receipt(receipt, sha, config, mise):
    required = required_checks(config)
    expected = {
        "schema": 1,
        "commit": sha,
        "checks_digest": digest(config.get("checks", {})),
        "environment_digest": digest({"mise": mise, "setup": config.get("setup", {})}),
        "dirty": False,
        "target": "github-actions",
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ValueError(f"CI receipt {key} mismatch")
    if type(receipt.get("dirty")) is not bool or type(receipt.get("schema")) is not int:
        raise ValueError("CI receipt schema types invalid")
    if (
        config.get("engine", {}).get("version")
        and receipt.get("engine_version") != config["engine"]["version"]
    ):
        raise ValueError("CI receipt engine version mismatch")
    if not isinstance(receipt.get("engine_version"), str) or not receipt["engine_version"].strip():
        raise ValueError("CI receipt missing engine version")
    declared = receipt.get("required", [])
    if len(declared) != len(set(declared)) or set(declared) != set(required):
        raise ValueError("CI receipt required check mismatch")
    outcomes = receipt.get("outcomes", [])
    ids = [o.get("id") for o in outcomes]
    if len(ids) != len(set(ids)):
        raise ValueError("CI receipt duplicate outcomes")
    if set(ids) != set(required):
        raise ValueError("CI receipt outcomes must exactly match required checks")
    for name in required:
        matches = [o for o in outcomes if o.get("id") == name]
        if len(matches) != 1:
            raise ValueError(f"CI receipt missing check: {name}")
        outcome = matches[0]
        duration = outcome.get("duration_seconds")
        if (
            outcome.get("status") != "passed"
            or type(outcome.get("exit_code")) is not int
            or outcome.get("exit_code") != 0
            or isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(duration)
            or duration < 0
        ):
            raise ValueError(f"CI receipt unsuccessful check: {name}")
    return True


class GitHubSCM:
    def __init__(self, root, config):
        self.root = Path(root)
        self.config = config
        self.scm = config.get("scm", {})
        self.repo = self.scm.get("repository", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repo):
            raise ValueError("SCM repository must be owner/repo")
        self.branch = self.scm.get("target_branch", "main")

    def run(self, *args):
        result = subprocess.run(
            ["gh", *args], cwd=self.root, text=True, capture_output=True, timeout=60, check=False
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return result.stdout

    def api(self, path):
        return json.loads(self.run("api", path))

    def merged(self, reference):
        match = re.fullmatch(r"https://github.com/([^/]+/[^/]+)/pull/(\d+)", str(reference))
        if match:
            if match.group(1) != self.repo:
                raise ValueError("PR repository mismatch")
            number = match.group(2)
        elif str(reference).isdigit():
            number = str(reference)
        else:
            raise ValueError("PR must be a number or matching GitHub URL")
        pr = self.api(f"repos/{self.repo}/pulls/{number}")
        if (
            not pr.get("merged")
            or pr.get("base", {}).get("ref") != self.branch
            or pr.get("base", {}).get("repo", {}).get("full_name") != self.repo
        ):
            raise ValueError("PR must be merged into configured repository and target branch")
        sha = pr.get("merge_commit_sha")
        if not sha:
            raise ValueError("Merged PR has no merge SHA")
        return {"sha": sha, "pr": pr}

    def file_at(self, path, sha):
        value = self.api(f"repos/{self.repo}/contents/{path}?ref={sha}")
        return tomllib.loads(base64.b64decode(value["content"]).decode())

    def ci(self, sha):
        workflow = self.scm.get("workflow", "verify.yml")
        workflow_path = (
            workflow
            if workflow.startswith(".github/workflows/")
            else ".github/workflows/" + workflow
        )
        workflow_name = workflow_path.rsplit("/", 1)[1]
        runs = self.api(
            f"repos/{self.repo}/actions/workflows/{workflow_name}/runs?head_sha={sha}&branch={self.branch}&event=push&status=success&per_page=100"
        )["workflow_runs"]
        matching = [
            r
            for r in runs
            if r.get("head_sha") == sha
            and r.get("head_branch") == self.branch
            and r.get("event") == "push"
            and r.get("conclusion") == "success"
            and r.get("status") == "completed"
            and r.get("path", "").split("@")[0] == workflow_path
            and r.get("repository", {}).get("full_name") == self.repo
        ]
        if not matching:
            raise ValueError("No trusted successful target-branch workflow for merge SHA")
        run = matching[0]
        config = self.file_at("ai-dlc.toml", sha)
        mise = self.file_at(".mise.toml", sha)
        artifact_page = self.api(
            f"repos/{self.repo}/actions/runs/{run['id']}/artifacts?per_page=100"
        )
        artifacts = artifact_page.get("artifacts", [])
        if artifact_page.get("total_count") != len(artifacts):
            raise ValueError("CI artifact listing is incomplete")
        available_names = [artifact.get("name") for artifact in artifacts]
        if len(available_names) != len(set(available_names)):
            raise ValueError("Duplicate CI receipt artifact names")
        merged_scm = config.get("scm", {})
        expected_names = merged_scm.get("receipt_artifacts")
        if expected_names is None:
            expected_names = [merged_scm.get("receipt_artifact", "ai-dlc-receipt")]
        if (
            not isinstance(expected_names, list)
            or not expected_names
            or any(not isinstance(name, str) or not name.strip() for name in expected_names)
            or len(expected_names) != len(set(expected_names))
        ):
            raise ValueError("Merged SCM receipt artifact names are invalid")
        artifacts_by_name = {artifact["name"]: artifact for artifact in artifacts}
        missing = [name for name in expected_names if name not in artifacts_by_name]
        if missing:
            raise ValueError("Missing expected CI receipt artifacts: " + ", ".join(missing))
        receipts = [artifacts_by_name[name] for name in expected_names]
        if any(artifact.get("expired") for artifact in receipts):
            raise ValueError("CI receipt artifact is expired")
        receipt_data = []
        with tempfile.TemporaryDirectory(prefix="ai-dlc-receipt-") as tmp:
            for index, artifact in enumerate(receipts):
                destination = Path(tmp) / str(index)
                self.run(
                    "run",
                    "download",
                    str(run["id"]),
                    "--repo",
                    self.repo,
                    "--name",
                    artifact["name"],
                    "--dir",
                    str(destination),
                )
                files = [
                    path for path in destination.rglob("*") if path.is_file() or path.is_symlink()
                ]
                if len(files) != 1 or files[0].suffix != ".json" or files[0].is_symlink():
                    raise ValueError("Expected exactly one JSON file per CI receipt artifact")
                receipt_data.append(json.loads(files[0].read_text()))
        for receipt in receipt_data:
            validate_receipt(receipt, sha, config, mise)
        return {
            "run_id": run["id"],
            "sha": sha,
            "receipt": receipt_data[0],
            "receipt_count": len(receipt_data),
            "receipts": receipt_data,
        }

    def deployment(self, sha):
        cfg = self.config.get("deploy", {})
        workflow = cfg.get("workflow")
        environment = cfg.get("environment")
        if not workflow or not environment:
            raise ValueError("Deployment evidence requires workflow and environment")
        runs = self.api(
            f"repos/{self.repo}/actions/workflows/{workflow}/runs?head_sha={sha}&status=success"
        )["workflow_runs"]
        valid = [
            r
            for r in runs
            if r.get("head_sha") == sha
            and r.get("conclusion") == "success"
            and r.get("repository", {}).get("full_name") == self.repo
            and r.get("path", "").split("@")[0] == f".github/workflows/{workflow}"
        ]
        deployments = self.api(f"repos/{self.repo}/deployments?sha={sha}&environment={environment}")
        for dep in deployments:
            if dep.get("sha") != sha or dep.get("environment") != environment:
                continue
            for status in self.api(f"repos/{self.repo}/deployments/{dep['id']}/statuses"):
                if status.get("state") == "success" and any(
                    f"/actions/runs/{r['id']}" in status.get("log_url", "") for r in valid
                ):
                    return {"deployment_id": dep["id"], "sha": sha, "environment": environment}
        raise ValueError("No deployment evidence bound to configured revision and environment")
