"""Reviewed repository Project creation/reuse for default GitHub onboarding."""

import hashlib
from pathlib import Path
from typing import TypedDict

from ai_dlc.config import digest, resolve_runtime
from ai_dlc.locking import project_write_lock
from ai_dlc.providers.github_issues import GitHubIssuesProvider
from ai_dlc.work.journal import Journal

OWNER = "query ProjectSetupOwner($owner: String!) { repositoryOwner(login: $owner) { id login } }"
CREATE = """mutation CreateDefaultProject($owner: ID!, $repository: ID!, $title: String!) {
 createProjectV2(input: {ownerId: $owner, repositoryId: $repository, title: $title}) {
 projectV2 { id title number url } }
}"""
LINK = """mutation LinkDefaultProject($project: ID!, $repository: ID!) {
 linkProjectV2ToRepository(input: {projectId: $project, repositoryId: $repository}) {
 repository { id } }
}"""
KIND = "github-project-setup"


class DefaultStates(TypedDict):
    status_field: str
    open: str
    in_progress: str
    closed: str


DEFAULT_STATES: DefaultStates = {
    "status_field": "Status",
    "open": "Todo",
    "in_progress": "In Progress",
    "closed": "Done",
}


def validate_plan(plan):
    if (
        not isinstance(plan, dict)
        or set(plan)
        != {
            "schema",
            "kind",
            "provider",
            "before_digest",
            "runtime_digest",
            "work_digest",
            "host",
            "repository",
            "repository_id",
            "owner",
            "viewer",
            "title",
            "project",
        }
        or plan.get("schema") != 1
        or plan.get("kind") != KIND
        or any(
            not isinstance(plan.get(k), str) or not plan[k]
            for k in (
                "provider",
                "before_digest",
                "runtime_digest",
                "host",
                "repository",
                "repository_id",
                "title",
            )
        )
        or not isinstance(plan.get("work_digest"), dict)
    ):
        raise ValueError("Invalid GitHub Project setup plan")
    from ai_dlc.setup.github_onboarding import _require

    _require(plan["owner"], "id", "login")
    _require(plan["viewer"], "id", "login")
    if plan["project"] is not None:
        _require(plan["project"], "id", "url", "title")
    return plan


def preview(root, *, alias, host, repository, environ, plan_file=None):
    from ai_dlc.setup.github_onboarding import (
        _guard_bound,
        _query,
        _render,
        _require,
        _save_plan,
        _snapshot,
        discover_github,
    )

    root = Path(root).resolve()
    path = root / "ai-dlc.toml"
    if path.is_symlink():
        raise ValueError("GitHub configuration must not be a symlink")
    before = path.read_bytes()
    runtime = resolve_runtime(root, environ=environ).values
    settings = runtime.get("providers", {}).get(alias, {})
    if settings.get("kind", settings.get("type", "github-issues")) != "github-issues":
        raise ValueError("Configured alias does not use GitHub Issues")
    discovery = discover_github({"host": host}, environ=environ, repository=repository, project="*")
    title = runtime.get("project", {}).get("name") or repository.split("/")[1]
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Project name must be nonempty text")
    owner_login = discovery["repository"]["nameWithOwner"].split("/")[0]
    provider = GitHubIssuesProvider({"host": host, "repository": repository}, environ=environ)
    owner = _require(
        _query(provider, OWNER, {"owner": owner_login}, projects=True).get("repositoryOwner"),
        "id",
        "login",
    )
    if owner["login"].lower() != owner_login.lower():
        raise ValueError("GitHub Project owner identity mismatch")
    configured_id = settings.get("project", {}).get("id")
    matches = (
        [p for p in discovery["projects"] if p["id"] == configured_id]
        if configured_id
        else [p for p in discovery["projects"] if p["title"] == title]
    )
    if len(matches) > 1 or (configured_id and len(matches) != 1):
        raise ValueError("GitHub default Project selection is unavailable or ambiguous")
    selected = matches[0] if matches else None
    patch = {
        "kind": "github-issues",
        "host": host,
        "repository": discovery["repository"]["nameWithOwner"],
        "viewer_id": discovery["viewer"]["id"],
    }
    if selected:
        # Verify mappings before offering an existing Project; custom names stay explicit.
        from ai_dlc.setup.github_onboarding import _connect_existing_github

        connection = _connect_existing_github(
            root,
            alias=alias,
            host=host,
            repository=repository,
            project=selected["url"],
            environ=environ,
            **DEFAULT_STATES,
        )
        patch = connection["plan"]["patch"]
    else:
        # A placeholder protects bound aliases and authored TOML before a remote create.
        patch["project"] = {
            "id": "pending-creation",
            "status_field_id": "pending-creation",
            "statuses": {"open": "todo", "in_progress": "doing", "closed": "done"},
        }
    _guard_bound(root, runtime, alias, patch)
    _render(before.decode(), alias, patch)
    plan = {
        "schema": 1,
        "kind": KIND,
        "provider": alias,
        "before_digest": hashlib.sha256(before).hexdigest(),
        "runtime_digest": digest(runtime),
        "work_digest": _snapshot(root),
        "host": host,
        "repository": discovery["repository"]["nameWithOwner"],
        "repository_id": discovery["repository"]["id"],
        "owner": owner,
        "viewer": discovery["viewer"],
        "title": title,
        "project": selected,
    }
    result = {
        "provider": alias,
        "status": "planned",
        "plan": plan,
        "guidance": "Apply the saved plan to create/reuse and link the repository Project. Status/Todo/In Progress/Done are verified before configuration; use explicit mappings for custom workflows. Use --issues-only to opt out.",
    }
    if plan_file is not None:
        result["plan_file"] = _save_plan(root, plan_file, plan)
    return result


def _check_local(root, saved, environ):
    from ai_dlc.setup.github_onboarding import _snapshot

    path = root / "ai-dlc.toml"
    if (
        path.is_symlink()
        or hashlib.sha256(path.read_bytes()).hexdigest() != saved["before_digest"]
        or _snapshot(root) != saved["work_digest"]
        or digest(resolve_runtime(root, environ=environ).values) != saved["runtime_digest"]
    ):
        raise ValueError("GitHub Project setup source or work bindings changed")


def apply_plan(root, saved, *, environ):
    from ai_dlc.setup.github_onboarding import (
        _connect_existing_github,
        _connection_plan_parent,
        _query,
        _require,
        _save_plan,
        discover_github,
    )

    root = Path(root).resolve()
    validate_plan(saved)
    with project_write_lock(root):
        _check_local(root, saved, environ)
        provider = GitHubIssuesProvider(
            {"host": saved["host"], "repository": saved["repository"]}, environ=environ
        )
        # Identity is freshly observed even when resuming a recorded successful create.
        current = discover_github(
            {"host": saved["host"]}, environ=environ, repository=saved["repository"]
        )
        owner = _query(provider, OWNER, {"owner": saved["owner"]["login"]}, projects=True).get(
            "repositoryOwner"
        )
        if (
            current["viewer"] != saved["viewer"]
            or current["repository"]["id"] != saved["repository_id"]
            or owner != saved["owner"]
        ):
            raise ValueError("GitHub Project setup remote identity changed")
        journal_path = root / ".ai-dlc/local/project-setup.sqlite3"
        with _connection_plan_parent(root, journal_path, create=True):
            if journal_path.is_symlink():
                raise ValueError("Project setup journal cannot be a symlink")
            journal = Journal(journal_path)
        identity = {
            "host": saved["host"].lower(),
            "repository_id": saved["repository_id"],
            "owner_id": saved["owner"]["id"],
            "title": saved["title"],
        }
        operation = "github-project-create:" + digest(identity)
        try:
            selected = saved["project"]
            if selected is None:
                record = journal.db.execute(
                    "SELECT status,result FROM operations WHERE id=?", (operation,)
                ).fetchone()
                if record is not None:
                    if record[0] != "succeeded" or not record[1]:
                        raise RuntimeError(
                            "GitHub Project creation remains uncertain; inspect the remote Project and select its exact URL. Refusing duplicate create."
                        )
                    import json

                    selected = json.loads(record[1])
                else:
                    fresh = preview(
                        root,
                        alias=saved["provider"],
                        host=saved["host"],
                        repository=saved["repository"],
                        environ=environ,
                    )["plan"]
                    if fresh != saved:
                        raise ValueError("GitHub Project setup plan drift; preview again")
                    _check_local(root, saved, environ)
                    journal.begin(operation, identity)
                    try:
                        selected = _require(
                            provider.graphql(
                                CREATE,
                                {
                                    "owner": saved["owner"]["id"],
                                    "repository": saved["repository_id"],
                                    "title": saved["title"],
                                },
                            )
                            .get("createProjectV2", {})
                            .get("projectV2"),
                            "id",
                            "title",
                            "url",
                        )
                        if selected["title"] != saved["title"]:
                            raise ValueError("Created Project title mismatch")
                    except (OSError, RuntimeError, ValueError, TypeError):
                        journal.uncertain(operation)
                        raise RuntimeError(
                            "GitHub Project creation is uncertain; inspect remote state before retrying. No local binding was changed."
                        ) from None
                    journal.succeed(operation, selected)
            else:
                fresh = preview(
                    root,
                    alias=saved["provider"],
                    host=saved["host"],
                    repository=saved["repository"],
                    environ=environ,
                )["plan"]
                if fresh != saved:
                    raise ValueError("GitHub Project setup plan drift; preview again")
            # URL lookup checks owner/host; compare the returned immutable Project identity.
            connection = _connect_existing_github(
                root,
                alias=saved["provider"],
                host=saved["host"],
                repository=saved["repository"],
                project=selected["url"],
                environ=environ,
                **DEFAULT_STATES,
            )
            if (
                connection["plan"]["patch"]["project"]["id"] != selected["id"]
                or connection["plan"]["discovery"]["viewer"] != saved["viewer"]
                or connection["plan"]["discovery"]["repository"]["id"] != saved["repository_id"]
            ):
                raise ValueError("GitHub Project setup identity changed")
            _check_local(root, saved, environ)
            try:
                linked = provider.graphql(
                    LINK, {"project": selected["id"], "repository": saved["repository_id"]}
                )
                if (
                    linked.get("linkProjectV2ToRepository", {}).get("repository", {}).get("id")
                    != saved["repository_id"]
                ):
                    raise ValueError("Project repository association mismatch")
            except (OSError, RuntimeError, ValueError, TypeError):
                raise RuntimeError(
                    "GitHub Project repository association failed; retry the saved plan. The Project is retained."
                ) from None
            _check_local(root, saved, environ)
            # Save the observed IDs before using the existing authored-safe connection writer.
            child = Path(".ai-dlc/local") / (
                "project-connection-" + digest(connection["plan"]) + ".json"
            )
            if not (root / child).exists():
                _save_plan(root, child, connection["plan"])
        finally:
            journal.db.close()
    result = _connect_existing_github(
        root, alias=saved["provider"], environ=environ, plan_file=child, apply=True
    )
    return {**result, "project": selected, "repository_association": saved["repository"]}
