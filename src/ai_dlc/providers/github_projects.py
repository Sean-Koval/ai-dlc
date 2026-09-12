"""Projects v2 planning operations, independent of native issue lifecycle."""

import time

# A newly added item is not always visible in the next item connection read. The
# mutation's item identity is durable, so only the readback is retried, and only
# within a bound: a persistently invisible item must still fail visibly.
READBACK_ATTEMPTS = 4
READBACK_DELAY_SECONDS = 0.5

FIELDS = """query ProjectFields($project: ID!, $after: String) {
  node(id: $project) { __typename id ... on ProjectV2 {
    fields(first: 100, after: $after) { nodes {
      __typename ... on ProjectV2FieldCommon { id }
      ... on ProjectV2SingleSelectField { options { id name } }
    } pageInfo { hasNextPage endCursor } }
  } }
}"""
ITEMS = """query ProjectItems($project: ID!, $after: String) {
  node(id: $project) { __typename id ... on ProjectV2 {
    items(first: 100, after: $after) { nodes { id content {
      __typename ... on Issue { id url } ... on PullRequest { id url }
      ... on DraftIssue { id }
    } } pageInfo { hasNextPage endCursor } }
  } }
}"""
VALUES = """query ItemFields($item: ID!, $after: String) {
  node(id: $item) { id ... on ProjectV2Item { project { id }
    fieldValues(first: 100, after: $after) { nodes { __typename
      ... on ProjectV2ItemFieldSingleSelectValue {
        optionId field { ... on ProjectV2FieldCommon { id } }
      }
    } pageInfo { hasNextPage endCursor } }
  } }
}"""
ATTACH = """mutation AttachIssue($project: ID!, $content: ID!) {
  addProjectV2ItemById(input: {projectId: $project, contentId: $content}) {
    item { id }
  }
}"""
UPDATE = """mutation SetStatus($project: ID!, $item: ID!, $field: ID!, $option: String!) {
  updateProjectV2ItemFieldValue(input: {projectId: $project, itemId: $item,
    fieldId: $field, value: {singleSelectOptionId: $option}}) {
    projectV2Item { id }
  }
}"""


class GitHubProjects:
    def __init__(self, config, graphql):
        self.graphql = graphql
        if not isinstance(config, dict):
            raise TypeError("Project configuration must be a mapping")
        statuses = config.get("statuses")
        if (
            not all(
                isinstance(config.get(k), str) and config[k].strip()
                for k in ("id", "status_field_id")
            )
            or not isinstance(statuses, dict)
            or set(statuses) != {"open", "in_progress", "closed"}
            or not all(isinstance(v, str) and v.strip() for v in statuses.values())
            or len(set(statuses.values())) != 3
        ):
            raise ValueError(
                "Project requires an id, status field and three distinct status options"
            )
        self.config = config

    def pages(self, query, variables, connection, expected_id):
        after = None
        seen = set()
        while True:
            node = self.graphql(query, {**variables, "after": after}).get("node")
            if not isinstance(node, dict) or node.get("id") != expected_id:
                raise ValueError("Project identity is inaccessible or mismatched")
            if connection != "fieldValues":
                if node.get("__typename") != "ProjectV2":
                    raise ValueError("Configured project is not a ProjectV2")
            elif node.get("project", {}).get("id") != self.config["id"]:
                raise ValueError("Project item belongs to another project")
            page = node.get(connection)
            if not isinstance(page, dict) or not isinstance(page.get("nodes"), list):
                raise TypeError("Incomplete project connection")
            for row in page["nodes"]:
                if not isinstance(row, dict):
                    raise TypeError("Inaccessible project connection entry")
                yield row
            info = page.get("pageInfo", {})
            if info.get("hasNextPage") is False:
                return
            after = info.get("endCursor")
            if (
                info.get("hasNextPage") is not True
                or not isinstance(after, str)
                or not after
                or after in seen
            ):
                raise ValueError("Incomplete project pagination")
            seen.add(after)

    def validate(self):
        fields = list(
            self.pages(FIELDS, {"project": self.config["id"]}, "fields", self.config["id"])
        )
        selected = [field for field in fields if field.get("id") == self.config["status_field_id"]]
        if len(selected) != 1 or selected[0].get("__typename") != "ProjectV2SingleSelectField":
            raise ValueError("Configured project status field is missing or not single-select")
        options = selected[0].get("options")
        if not isinstance(options, list) or not all(
            isinstance(o, dict) and isinstance(o.get("id"), str) for o in options
        ):
            raise ValueError("Incomplete project status options")
        ids = [o["id"] for o in options]
        if len(set(ids)) != len(ids) or not set(self.config["statuses"].values()).issubset(ids):
            raise ValueError("Configured project status options are stale or ambiguous")

    def snapshot(self, issue):
        self.validate()
        matches = []
        for row in self.pages(ITEMS, {"project": self.config["id"]}, "items", self.config["id"]):
            content = row.get("content")
            if (
                not isinstance(content, dict)
                or not content.get("id")
                or content.get("__typename") not in {"Issue", "PullRequest", "DraftIssue"}
            ):
                raise ValueError("Inaccessible project content; membership is uncertain")
            if content["id"] == issue["node_id"]:
                if content.get("__typename") != "Issue" or content.get("url") != issue["url"]:
                    raise ValueError("Project issue identity mismatch")
                if not isinstance(row.get("id"), str) or not row["id"]:
                    raise ValueError("Missing project item identity")
                matches.append(row["id"])
        if len(matches) > 1:
            raise ValueError("Ambiguous duplicate project membership")
        item_id = matches[0] if matches else None
        values = []
        if item_id:
            for value in self.pages(VALUES, {"item": item_id}, "fieldValues", item_id):
                if not isinstance(value.get("__typename"), str):
                    raise TypeError("Incomplete project field value")
                if (
                    value.get("__typename") == "ProjectV2ItemFieldSingleSelectValue"
                    and value.get("field", {}).get("id") == self.config["status_field_id"]
                ):
                    values.append(value.get("optionId"))
        if len(values) > 1 or (values and (not isinstance(values[0], str) or not values[0])):
            raise ValueError("Ambiguous project status value")
        return {
            "id": self.config["id"],
            "item_id": item_id,
            "status_field_id": self.config["status_field_id"],
            "status_option_id": values[0] if values else None,
        }

    def attach(self, issue):
        # GitHub returns the existing item if another actor attached it concurrently.
        result = self.graphql(ATTACH, {"project": self.config["id"], "content": issue["node_id"]})
        item_id = result.get("addProjectV2ItemById", {}).get("item", {}).get("id")
        if not item_id:
            raise RuntimeError("Project attachment returned no item identity")
        delay = READBACK_DELAY_SECONDS
        for remaining in range(READBACK_ATTEMPTS - 1, -1, -1):
            current = self.snapshot(issue)
            if current["item_id"] == item_id:
                return current
            # Another visible item is a conflicting attachment, not replication lag.
            if current["item_id"] is not None or not remaining:
                break
            time.sleep(delay)
            delay *= 2
        raise RuntimeError("Project attachment remains uncertain")

    def set_status(self, issue, state):
        current = self.snapshot(issue)
        if not current["item_id"]:
            current = self.attach(issue)
        option = self.config["statuses"][state]
        if current["status_option_id"] != option:
            result = self.graphql(
                UPDATE,
                {
                    "project": self.config["id"],
                    "item": current["item_id"],
                    "field": self.config["status_field_id"],
                    "option": option,
                },
            )
            if (
                result.get("updateProjectV2ItemFieldValue", {}).get("projectV2Item", {}).get("id")
                != current["item_id"]
            ):
                raise RuntimeError("Project status response identity mismatch")
        current = self.snapshot(issue)
        if current["status_option_id"] != option:
            raise RuntimeError("Project status update remains uncertain")
        return current
