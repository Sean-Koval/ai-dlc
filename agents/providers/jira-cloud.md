# Jira Cloud provider guidance

Use Jira Cloud for new work in the explicitly selected site, account, project and
standard issue type. Existing work uses its pinned identity. Do not migrate
personal tickets or change workflow/schema/permissions as part of connection.
Jira Data Center, service-management request APIs and subtask creation are unsupported.

Select `oauth_bearer` for an externally managed approved OAuth access token, or
`personal_scoped_token_basic` for an organization-approved personal scoped API
token with `email_env` and `token_env`. Both use the selected Cloud UUID gateway.
Credentials stay in environment variables. Never extract native-client login,
store credential values in project files, guess token type or silently switch
accounts. Native Atlassian MCP authentication is a separate connection.

First configure the non-secret site URL, Cloud UUID, auth mode and environment
references. `provider connect <alias>` reads account identity, accessible projects,
standard types, status membership, field metadata and resolutions. Named selections
use `--select project=NAME`, `--select issue_type=PROJECT_ID:TYPE_ID`, plus open,
in_progress, closed, cancelled, closed_resolution and cancelled_resolution.
A type's display name includes its project. Duplicate names refuse; use the
returned IDs. Save a complete reviewed plan under `.ai-dlc/local`, then apply
that plan without new selections. Local setup creates no Jira issue.

Create fields must have explicit reviewed values when current metadata has no
usable server default. Supported values are strings, finite numbers/integers,
booleans, simple ID objects, arrays of these, and ADF text documents for description
or textarea fields. Other schemas, user objects and cascading custom values are
unsupported. Generated project/type/title/description/correlation cannot be
replaced through create_fields. Current metadata is checked again before create;
workflow validators may still refuse remotely. Configure any transition ID and
field values explicitly under transitions.in_progress or transitions.closed.

Successful and cancelled status/resolution mappings are distinct. Done category
alone never means success. The adapter refuses ambiguous current transition routes,
unavailable fields, cancelled/unknown state and false completion read-back.
Existing work finish gates remain mandatory; native status IDs cannot bypass them.

Publish places the literal work correlation in ADF and a scoped issue property in
the same request, then verifies it by fresh read. Find scans the selected project
with complete bounded pagination; property/marker disagreement, duplicate results,
warnings, changed identity or exhausted budgets prevent a new create. An uncertain
create with delayed search visibility must reconcile; do not clear its journal to
force another issue. A fresh computer without the earlier journal cannot establish
that a prior issue was never created. Recover the known numeric reference after
inspection instead. No exactly-once cross-machine guarantee is claimed.

PR/spec links use the documented remote-link endpoint and a deterministic scoped
globalId, with read-back on success or uncertain response. Existing matching links
and authored issue descriptions are preserved. Link Issues permission and enabled
issue linking are required. No prepare/reconcile_closed operations are advertised.

Remote reads and mutations require the selected tenant's actual permissions,
scopes and workflow. Fixture checks and offline credential presence do not prove
live access, organizational approval, platform support or native-client readiness.
