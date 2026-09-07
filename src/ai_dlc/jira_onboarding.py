"""Read-only Jira discovery and pure selection behind the common connection service."""

import copy

from ai_dlc.providers.jira_cloud import (
    MAX_ROWS,
    RESERVED,
    STATES,
    JiraCloudProvider,
    adf,
    cloud_settings,
    identity,
    validate_fields,
)

SELECTIONS = frozenset(
    {"project", "issue_type", *STATES, "closed_resolution", "cancelled_resolution"}
)


def make_provider(settings, environ):
    return JiraCloudProvider(settings, environ=environ, selected=False)


def named(rows, *, numeric=True):
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError("Jira named resource discovery is incomplete")
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("Jira resource identity is incomplete")
        row_id = identity(row.get("id"), "resource ID", numeric=numeric)
        identity(row.get("name"), "resource name")
        if row_id in seen:
            raise ValueError("Jira resource IDs are duplicated")
        seen.add(row_id)
    return rows


def discover(config, alias, *, environ):
    settings = config.get("providers", {}).get(alias, {})
    provider = make_provider(settings, environ)
    try:
        account = provider.identity()
        projects = named(provider.pages("project/search", "values", params={"action": "create"}))
        resources = {key: [] for key in SELECTIONS}
        types, statuses = [], {}
        for project in projects:
            project_id = project["id"]
            key = identity(project.get("key"), "project key")
            resources["project"].append({"id": project_id, "name": project["name"], "key": key})
            path = "issue/createmeta/" + project_id + "/issuetypes"
            project_types = named(provider.pages(path, "issueTypes"))
            status_groups = named(provider.request("GET", "project/" + project_id + "/statuses"))
            for issue_type in project_types:
                if type(issue_type.get("subtask")) is not bool:
                    raise ValueError("Jira standard/subtask issue type metadata is incomplete")
                if issue_type["subtask"]:
                    continue
                matches = [group for group in status_groups if group["id"] == issue_type["id"]]
                if len(matches) != 1:
                    raise ValueError("Jira issue-type status membership is incomplete")
                rows = named(matches[0].get("statuses"))
                for row in rows:
                    entry = {"id": row["id"], "name": row["name"]}
                    if row["id"] in statuses and statuses[row["id"]] != entry:
                        raise ValueError("Jira status identity changed during discovery")
                    statuses[row["id"]] = entry
                fields = provider.pages(path + "/" + issue_type["id"], "fields", id_key="fieldId")
                types.append(
                    {
                        "id": project_id + ":" + issue_type["id"],
                        "name": project["name"] + " / " + issue_type["name"],
                        "project_id": project_id,
                        "issue_type_id": issue_type["id"],
                        "status_ids": [row["id"] for row in rows],
                        "fields": {row["fieldId"]: row for row in fields},
                    }
                )
                if len(types) > MAX_ROWS:
                    raise ValueError("Jira discovery exceeds complete resource budget")
        resources["issue_type"] = types
        for key in STATES:
            resources[key] = list(statuses.values())
        resolutions = [
            {"id": row["id"], "name": row["name"]}
            for row in named(provider.request("GET", "resolution"))
        ]
        resources["closed_resolution"] = resolutions
        resources["cancelled_resolution"] = copy.deepcopy(resolutions)
        return {
            "schema": 1,
            "complete": True,
            "account": {"id": account},
            "resources": resources,
            "settings": {
                key: copy.deepcopy(settings[key])
                for key in (
                    "site_url",
                    "cloud_id",
                    "auth_mode",
                    "token_env",
                    "email_env",
                    "create_fields",
                    "transitions",
                )
                if key in settings
            },
        }
    finally:
        provider.close()


def configure(discovery, selected):
    resources = discovery["resources"]
    project = next(row for row in resources["project"] if row["id"] == selected["project"])
    issue_type = next(row for row in resources["issue_type"] if row["id"] == selected["issue_type"])
    if issue_type["project_id"] != project["id"] or any(
        selected[state] not in issue_type["status_ids"] for state in STATES
    ):
        raise ValueError("Jira selections cross project/issue-type status boundaries")
    patch = {
        "kind": "jira-cloud",
        "account_id": discovery["account"]["id"],
        "project_id": project["id"],
        "project_key": project["key"],
        "issue_type_id": issue_type["issue_type_id"],
        "statuses": {state: selected[state] for state in STATES},
        "resolutions": {
            state: [selected[state + "_resolution"]] for state in ("closed", "cancelled")
        },
    }
    config = cloud_settings({**discovery["settings"], **patch})
    if RESERVED & config.get("create_fields", {}).keys():
        raise ValueError("Jira create_fields cannot override generated fields")
    validate_fields(
        issue_type["fields"],
        {
            **config.get("create_fields", {}),
            "project": {"id": patch["project_id"]},
            "issuetype": {"id": patch["issue_type_id"]},
            "summary": "Reviewed work title",
            "description": adf(["Reviewed work description"]),
        },
    )
    return patch
