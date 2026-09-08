"""Read-only Plane discovery and pure patches for common connection persistence."""

import copy

from ai_dlc.providers.plane import GROUPS, MAX_ROWS, STATES, PlaneProvider, settings, uid


def make_provider(config, environ):
    return PlaneProvider(config, environ=environ, selected=False)


def discover(config, alias, *, environ):
    selected = config.get("providers", {}).get(alias, {})
    provider = make_provider(selected, environ)
    try:
        account = provider.identity()
        projects = provider.pages(provider.workspace_path)
        resources = {key: [] for key in ("project", *STATES)}
        workspace = None
        for project in projects:
            project_id = uid(project["id"])
            workspace_id = uid(project.get("workspace"))
            if workspace is not None and workspace != workspace_id:
                raise ValueError("Plane discovery crossed workspace identity")
            workspace = workspace_id
            if project.get("archived_at"):
                continue
            if not isinstance(project.get("name"), str) or not project["name"]:
                raise ValueError("Plane project name is unavailable")
            resources["project"].append(
                {
                    "id": project_id,
                    "name": project["name"],
                    "workspace_id": workspace_id,
                    "key": project.get("identifier"),
                }
            )
            rows = provider.pages(provider.workspace_path + project_id + "/states/")
            for row in rows:
                if (
                    row.get("project") != project_id
                    or row.get("workspace") != workspace_id
                    or not isinstance(row.get("name"), str)
                    or not row["name"]
                ):
                    raise ValueError("Plane state identity is incomplete or foreign")
                for key in STATES:
                    if row.get("group") in GROUPS[key]:
                        resources[key].append(
                            {
                                "id": row["id"],
                                "name": row["name"],
                                "project_id": project_id,
                                "group": row["group"],
                            }
                        )
                if sum(len(rows) for rows in resources.values()) > MAX_ROWS:
                    raise ValueError("Plane discovery exceeds complete resource budget")
        return {
            "schema": 1,
            "complete": True,
            "account": {"id": account},
            "resources": resources,
            "settings": {
                key: copy.deepcopy(selected[key])
                for key in (
                    "deployment",
                    "api_url",
                    "web_url",
                    "workspace_slug",
                    "auth_mode",
                    "token_env",
                )
            },
        }
    finally:
        provider.close()


def configure(discovery, selected):
    resources = discovery["resources"]
    project = next(row for row in resources["project"] if row["id"] == selected["project"])
    for state in STATES:
        row = next(row for row in resources[state] if row["id"] == selected[state])
        if row["project_id"] != project["id"] or row["group"] not in GROUPS[state]:
            raise ValueError("Plane selected states cross project or lifecycle boundaries")
    patch = {
        "kind": "plane",
        "account_id": discovery["account"]["id"],
        "workspace_id": project["workspace_id"],
        "project_id": project["id"],
        "project_key": project["key"],
        "statuses": {state: selected[state] for state in STATES},
    }
    settings({**discovery["settings"], **patch})
    return patch
