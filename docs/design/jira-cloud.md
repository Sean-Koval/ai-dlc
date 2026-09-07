# Jira Cloud new-work adapter

This optional tracker kind implements create/find/read/transition/link and
capabilities behind the existing Registry and WorkService. GitHub remains the
personal tracker; this adapter does not migrate tickets or install Plane.

The implementation accepts a bare HTTPS `*.atlassian.net` site and canonical
Cloud UUID, and sends requests only to
`https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/`. Before lifecycle
operations it checks serverInfo deployment/base URL and the authenticated account.
Explicit account/project/type mappings are retained with work bindings.

An incomplete starting configuration has `kind="jira-cloud"`, `site_url`,
`cloud_id`, `auth_mode` and `token_env`; Basic also needs `email_env`. Do not invent
the actual site or Cloud UUID. Supported modes are externally managed
`oauth_bearer` and approved personal-scoped-token `personal_scoped_token_basic`.
Both are documented by Atlassian; service-account token conventions and unscoped
site-routed tokens are deliberately not guessed. OAuth refresh/token distribution
and company policy remain external inputs. [OAuth gateway routing](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)
and [personal scoped-token Basic routing](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/).

The common connection handler discovers named projects, composite project:type
identities, type-specific status membership, create metadata and resolutions.
`--select` resolves unique names or IDs; patch selection checks cross-resource
membership and disjoint state/resolution mappings. Complete plans bind metadata,
identity and local source/runtime/work snapshots. The common service owns saving
and authored-safe application; Jira setup performs no remote writes. Reviewed
create_fields/transitions are validated and left in their authored configuration
instead of being guessed or rewritten by onboarding.

Publication writes the exact WorkService correlation as ADF text and an `ai-dlc`
issue property in the same create request. The property stores schema, correlation,
operation ID and Cloud/account/project/type identity. A fresh issue read validates
that evidence before success. Property values are not presumed JQL indexed.
[Create, metadata and transitions](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/),
[ADF](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)
and [issue properties](https://developer.atlassian.com/cloud/jira/platform/jira-entity-properties/).

Reconciliation uses enhanced POST search/jql restricted to the selected project.
It traverses every continuation token and checks exact marker/property matches.
Missing optional property maps trigger an explicit property lookup; a property
404 establishes that property's absence for the visible issue, while other errors
refuse reconciliation. A matching property with an edited marker is a conflict.
Search warnings, repeated pages/IDs, malformed metadata and incomplete traversal
refuse publication. Limits are 100 pages per paginated collection, 10,000 rows per
collection/search, 300 HTTP requests per operation/discovery, and 8 MiB per response.
Large projects may require a future indexed integration; limits never turn a
partial search into absence. [Enhanced search and consistency](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/).

The create operation has no documented idempotency key or atomic correlation
uniqueness guarantee. WorkService retains uncertain publication and refuses a
second create while correlation remains invisible. That local journal does not
provide exactly-once creation across simultaneous new machines or a clone missing
prior state. If prior publication is known, retain/recover its issue reference and
journal after inspection. Fixture tests do not establish live indexing latency.

Create re-reads project/type/field metadata. Current required fields need reviewed
supported values or a server-declared default. Supported schemas are strings,
finite numbers/integers, booleans, simple ID objects, arrays and ADF textarea data;
unsupported required schemas are a visible limitation. Remote validators can still
refuse. Transitions discover current routes with `expand=transitions.fields` and
require one route to the configured status or a selected route ID. Cancellation
status/resolution takes precedence; completion requires both the configured
successful status and a successful resolution. Current issue read-back confirms
actual state, including after an uncertain mutation response. No transition retry
is sent during that reconciliation.

Link uses a scoped globalId derived from Cloud/account/project/type, numeric issue
ID and URL. Exact existing matches are preserved; conflicts refuse. The remote
link upsert is read back, including after uncertainty, and never edits description.
Atlassian requires issue linking enabled and Browse/Link Issues permissions. The
classic OAuth scopes for these endpoints are read:jira-work and write:jira-work;
granular scope equivalents and other endpoint permissions must be checked for the
actual approved credential. [Remote-link API and globalId semantics](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-remote-links/).

The authoritative schema reference used on September 7, 2026 was Atlassian's
[REST v3 OpenAPI](https://dac-static.atlassian.com/cloud/jira/platform/swagger-v3.v3.json).
No company system was contacted. Live qualification still needs the real site,
auth method approval/token renewal, project/type/field values, successful and
cancelled mappings, transition validators, issue-link permissions and authorization
for a disposable new-work probe. Native Claude/Antigravity login remains separate.
