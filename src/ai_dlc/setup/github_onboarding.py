"""Read-only named GitHub discovery and reviewed local connection plans."""

import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit

from ai_dlc.config import digest, resolve_runtime
from ai_dlc.locking import project_write_lock
from ai_dlc.providers.github_issues import GitHubIssuesProvider
from ai_dlc.providers.github_projects import FIELDS
from ai_dlc.setup.provider_onboarding import _connection_plan_parent

VIEWER = "query DiscoveryViewer { viewer { id login } }"
REPOSITORY = """query DiscoveryRepository($owner: String!, $name: String!) {
 repository(owner: $owner, name: $name) { id nameWithOwner hasIssuesEnabled viewerPermission }
}"""
REPOSITORIES = """query DiscoveryRepositories($after: String) {
 viewer { repositories(first: 100, after: $after, affiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) {
 nodes { id nameWithOwner hasIssuesEnabled viewerPermission } pageInfo { hasNextPage endCursor }
 } }
}"""
PROJECTS = """query DiscoveryProjects($owner: String!, $after: String) {
 repositoryOwner(login: $owner) { login
 ... on User { projectsV2(first: 100, after: $after) {
 nodes { id title number url } pageInfo { hasNextPage endCursor } } }
 ... on Organization { projectsV2(first: 100, after: $after) {
 nodes { id title number url } pageInfo { hasNextPage endCursor } } }
 }
}"""


def _query(provider, query, variables, *, projects=False):
    try:
        result = provider.graphql(query, variables)
    except (RuntimeError, OSError, ValueError, TypeError):
        if projects:
            raise RuntimeError(
                "GitHub Projects discovery failed; verify Project access and read:project "
                "permission (or equivalent fine-grained access). No authentication was changed."
            ) from None
        raise RuntimeError(
            "GitHub discovery failed; verify host, gh sign-in and repository access"
        ) from None
    if not isinstance(result, dict):
        raise TypeError("Incomplete GitHub discovery response")
    return result


def _pages(fetch):
    after = None
    seen = set()
    rows = []
    identities = set()
    while True:
        page = fetch(after)
        if not isinstance(page, dict) or not isinstance(page.get("nodes"), list):
            raise TypeError("Incomplete GitHub discovery connection")
        if not all(isinstance(row, dict) for row in page["nodes"]):
            raise ValueError("Inaccessible GitHub discovery entry")
        for row in page["nodes"]:
            _require(row, "id")
            if row["id"] in identities:
                raise ValueError("GitHub discovery contains duplicate, ambiguous identities")
            identities.add(row["id"])
        rows.extend(page["nodes"])
        info = page.get("pageInfo", {})
        if info.get("hasNextPage") is False:
            return rows
        after = info.get("endCursor")
        if (
            info.get("hasNextPage") is not True
            or not isinstance(after, str)
            or not after
            or after in seen
        ):
            raise ValueError("Incomplete GitHub discovery pagination")
        seen.add(after)


def _require(row, *fields):
    if not isinstance(row, dict) or any(
        not isinstance(row.get(f), str) or not row[f] for f in fields
    ):
        raise ValueError("Incomplete GitHub discovery identity or names")
    return row


def _choose(rows, selected, fields, label):
    matches = [row for row in rows if any(str(row.get(field)) == selected for field in fields)]
    if len(matches) != 1:
        raise ValueError(f"GitHub {label} selection is unavailable or ambiguous")
    return matches[0]


def discover_github(settings, *, environ, repository=None, project=None):
    # A syntactically valid placeholder allows account/repository discovery before selection.
    provider = GitHubIssuesProvider(
        {**settings, "repository": repository or "discovery/placeholder"}, environ=environ
    )
    viewer = _require(_query(provider, VIEWER, {}).get("viewer"), "id", "login")
    result = {"host": provider.host, "viewer": viewer}
    if repository is None:
        rows = _pages(
            lambda after: (
                _query(provider, REPOSITORIES, {"after": after})
                .get("viewer", {})
                .get("repositories")
            )
        )
        for row in rows:
            _require(row, "id", "nameWithOwner", "viewerPermission")
        result["repositories"] = rows
        return result
    owner, name = repository.split("/")
    repo = _require(
        _query(provider, REPOSITORY, {"owner": owner, "name": name}).get("repository"),
        "id",
        "nameWithOwner",
        "viewerPermission",
    )
    if (
        repo["nameWithOwner"].lower() != repository.lower()
        or repo.get("hasIssuesEnabled") is not True
    ):
        raise ValueError("GitHub repository identity mismatch or Issues unavailable")
    if repo["viewerPermission"] not in {"WRITE", "MAINTAIN", "ADMIN"}:
        raise ValueError("GitHub repository write permission is required for tracker workflows")
    result["repository"] = repo
    if project is None:
        return result
    if project.startswith("https://"):
        parsed = urlsplit(project)
        match = re.fullmatch(
            r"/(?:orgs|users)/([A-Za-z0-9_.-]+)/projects/([1-9][0-9]*)/?", parsed.path
        )
        if (
            parsed.netloc.lower() != provider.host.lower()
            or parsed.query
            or parsed.fragment
            or not match
        ):
            raise ValueError("Project URL must belong to the selected GitHub host")
        owner = match[1]
        project = match[2]

    def fetch(after):
        actor = _query(provider, PROJECTS, {"owner": owner, "after": after}, projects=True).get(
            "repositoryOwner"
        )
        if not isinstance(actor, dict) or str(actor.get("login", "")).lower() != owner.lower():
            raise ValueError("GitHub Project owner identity mismatch")
        return actor.get("projectsV2")

    projects = _pages(fetch)
    for row in projects:
        _require(row, "id", "title", "url")
        if type(row.get("number")) is not int or row["number"] < 1:
            raise ValueError("Incomplete GitHub project number")
    result["projects"] = projects
    if project == "*":
        return result
    selected = _choose(projects, project, ("url", "title", "number"), "Project")

    def fields(after):
        node = _query(
            provider,
            FIELDS.replace("ProjectV2FieldCommon { id }", "ProjectV2FieldCommon { id name }"),
            {"project": selected["id"], "after": after},
            projects=True,
        ).get("node")
        if (
            not isinstance(node, dict)
            or node.get("id") != selected["id"]
            or node.get("__typename") != "ProjectV2"
        ):
            raise ValueError("GitHub Project identity mismatch")
        return node.get("fields")

    discovered_fields = _pages(fields)
    for field in discovered_fields:
        _require(field, "id", "name", "__typename")
        if field["__typename"] == "ProjectV2SingleSelectField":
            if not isinstance(field.get("options"), list):
                raise ValueError("Incomplete GitHub status options")
            for option in field["options"]:
                _require(option, "id", "name")
            ids = [option["id"] for option in field["options"]]
            if len(ids) != len(set(ids)):
                raise ValueError("GitHub status options contain duplicate, ambiguous identities")
    result["project"] = {**selected, "fields": discovered_fields}
    return result


def _snapshot(root):
    from ai_dlc.setup.connections import snapshot_work

    return snapshot_work(root)


def _render(text, alias, patch):
    from ai_dlc.setup.connections import render_patch

    return render_patch(text, alias, patch, require_project=True)


def _guard_bound(root, config, alias, patch):
    from ai_dlc.setup.connections import guard_bound_tracker

    return guard_bound_tracker(root, config, alias, patch)


def _save_plan(root, path, plan):
    from ai_dlc.setup.connections import save_exclusive_plan

    return save_exclusive_plan(root, path, plan)


def _load_plan(root, path):
    with _connection_plan_parent(root, path, create=False) as (_, parent, leaf):
        descriptor = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor) as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("GitHub plan must be a regular file")
            plan = json.load(stream)
    if isinstance(plan, dict) and plan.get("kind") == "github-project-setup":
        from ai_dlc.setup.github_project_setup import validate_plan

        return validate_plan(plan)
    if not isinstance(plan, dict) or plan.get("schema") != 1 or plan.get("kind") != "github-issues":
        raise ValueError("Invalid GitHub connection plan")
    selected = plan.get("selected")
    if (
        set(plan)
        != {
            "schema",
            "kind",
            "provider",
            "before_digest",
            "runtime_digest",
            "work_digest",
            "selected",
            "discovery",
            "patch",
        }
        or not isinstance(selected, dict)
        or set(selected)
        != {"host", "repository", "project", "status_field", "open", "in_progress", "closed"}
        or any(
            value is not None and (not isinstance(value, str) or not value)
            for value in selected.values()
        )
    ):
        raise ValueError("Invalid GitHub connection plan")
    return plan


def _connect_existing_github(
    root: Path,
    *,
    alias="github-issues",
    host=None,
    repository=None,
    project=None,
    status_field=None,
    open=None,
    in_progress=None,
    closed=None,
    plan_file=None,
    apply=False,
    environ: Mapping[str, str],
):
    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", alias):
        raise ValueError("GitHub provider alias must use letters, digits, underscore or hyphen")
    selections = {
        "host": host,
        "repository": repository,
        "project": project,
        "status_field": status_field,
        "open": open,
        "in_progress": in_progress,
        "closed": closed,
    }
    if apply:
        if plan_file is None or any(value is not None for value in selections.values()):
            raise ValueError("GitHub apply requires --plan-file and consumes its saved selections")
        saved = _load_plan(root, plan_file)
        if saved.get("provider") != alias or not isinstance(saved.get("selected"), dict):
            raise ValueError("GitHub plan provider identity mismatch")
        if (
            hashlib.sha256((root / "ai-dlc.toml").read_bytes()).hexdigest()
            != saved["before_digest"]
            or _snapshot(root) != saved["work_digest"]
            or digest(resolve_runtime(root, environ=environ).values) != saved["runtime_digest"]
        ):
            raise ValueError("GitHub connection source or work bindings changed")
        fresh = _connect_existing_github(root, alias=alias, environ=environ, **saved["selected"])
        if fresh.get("plan") != saved:
            raise ValueError(
                "GitHub connection plan drift: configuration, work or remote identity changed"
            )
        from ai_dlc.setup.connections import apply_exact_patch

        apply_exact_patch(
            root,
            alias,
            saved,
            environ=environ,
            snapshot=_snapshot,
            render=_render,
            lock=project_write_lock,
            label="GitHub",
            stage_prefix=".ai-dlc-github-",
        )
        return {"provider": alias, "status": "applied", "selected": saved["selected"]}
    path = root / "ai-dlc.toml"
    if path.is_symlink():
        raise ValueError("GitHub configuration must not be a symlink")
    before = path.read_bytes()
    work_digest = _snapshot(root)
    runtime = resolve_runtime(root, environ=environ).values
    settings = runtime.get("providers", {}).get(alias, {})
    if settings.get("kind", settings.get("type", "github-issues")) != "github-issues":
        raise ValueError("Configured alias does not use GitHub Issues")
    selected_host = host or settings.get("host", "github.com")
    # Account discovery must not validate old Project settings before selecting a replacement.
    discovery = discover_github(
        {"host": selected_host}, environ=environ, repository=repository, project=project
    )
    supplied_states = [status_field, open, in_progress, closed]
    if repository is None or (project is not None and not all(supplied_states)):
        if any(supplied_states) or plan_file is not None:
            raise ValueError(
                "Saving a Project plan requires repository, Project, status field and all status names"
            )
        return {
            "provider": alias,
            "status": "discovered",
            "discovery": discovery,
            "next": 'Select --repository; optionally discover --project "*", then choose --project, --status-field, --open, --in-progress and --closed.',
        }
    if project is None and any(supplied_states):
        raise ValueError("Project status selections require --project")
    patch = {
        "kind": "github-issues",
        "host": discovery["host"],
        "repository": discovery["repository"]["nameWithOwner"],
        "viewer_id": discovery["viewer"]["id"],
    }
    if project is not None:
        field = _choose(discovery["project"]["fields"], status_field, ("name",), "status field")
        if field["__typename"] != "ProjectV2SingleSelectField":
            raise ValueError("GitHub status field must be single-select")
        statuses = {
            key: _choose(field["options"], value, ("name",), key)["id"]
            for key, value in {"open": open, "in_progress": in_progress, "closed": closed}.items()
        }
        if len(set(statuses.values())) != 3:
            raise ValueError("GitHub status mappings require three distinct options")
        patch["project"] = {
            "id": discovery["project"]["id"],
            "status_field_id": field["id"],
            "statuses": statuses,
        }
    _guard_bound(root, runtime, alias, patch)
    _render(before.decode(), alias, patch)
    plan = {
        "schema": 1,
        "kind": "github-issues",
        "provider": alias,
        "before_digest": hashlib.sha256(before).hexdigest(),
        "runtime_digest": digest(runtime),
        "work_digest": work_digest,
        "selected": selections,
        "discovery": discovery,
        "patch": patch,
    }
    result = {
        "provider": alias,
        "status": "planned",
        "plan": plan,
        "guidance": "Project status records planning. Completion requires native issue CLOSED/COMPLETED and finish gates; NOT_PLANNED is cancelled. Issues-only setup cannot represent in-progress.",
    }
    if plan_file is not None:
        result["plan_file"] = _save_plan(root, plan_file, plan)
    return result


def connect_github_provider(
    root: Path, *, alias="github-issues", issues_only=False, environ, **options
):
    """Default new GitHub connections to a reviewed repository Project."""
    from ai_dlc.setup.github_project_setup import KIND, apply_plan, preview

    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", alias):
        raise ValueError("GitHub provider alias must use letters, digits, underscore or hyphen")
    if options.get("apply"):
        if issues_only or any(
            value is not None for key, value in options.items() if key not in {"apply", "plan_file"}
        ):
            raise ValueError("GitHub apply consumes only its saved selections")
        if options.get("plan_file") is None:
            raise ValueError("GitHub apply requires --plan-file")
        saved = _load_plan(root, options["plan_file"])
        if saved["provider"] != alias:
            raise ValueError("GitHub plan provider identity mismatch")
        if saved["kind"] == KIND:
            return apply_plan(root, saved, environ=environ)
        return _connect_existing_github(root, alias=alias, environ=environ, **options)
    runtime = resolve_runtime(root, environ=environ).values
    settings = runtime.get("providers", {}).get(alias, {})
    options["repository"] = (
        options.get("repository")
        or settings.get("repository")
        or runtime.get("scm", {}).get("repository")
    )
    if issues_only:
        if any(
            options.get(key) is not None
            for key in ("project", "status_field", "open", "in_progress", "closed")
        ):
            raise ValueError("--issues-only cannot include Project selections")
        return _connect_existing_github(root, alias=alias, environ=environ, **options)
    if options.get("project") is not None or options["repository"] is None:
        return _connect_existing_github(root, alias=alias, environ=environ, **options)
    if any(
        options.get(key) is not None for key in ("status_field", "open", "in_progress", "closed")
    ):
        raise ValueError("Custom status selections require --project")
    return preview(
        root,
        alias=alias,
        host=options.get("host") or settings.get("host", "github.com"),
        repository=options["repository"],
        environ=environ,
        plan_file=options.get("plan_file"),
    )
