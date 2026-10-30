# Jira Cloud new-work adapter

Understand what the Jira Cloud tracker adapter does and refuses, and how GitHub
delivery links to Jira outcomes by hand today.

This optional tracker kind implements create/find/read/transition/link and
capabilities behind the existing Registry and WorkService. GitHub remains the
personal tracker; this adapter does not migrate tickets or install Plane.

The adapter serves the local developer lifecycle only. hangar intake starts agent
jobs from Jira statuses or labels and writes job progress back; ai-dlc publishes
reviewed work, binds branches and closes tickets after merged CI evidence. Use
`[work] tracker_writes = "finish-only"` where hangar works the same project so
`work start` does not race hangar's status transitions; see the
[tracker boundary](../architecture.md#tracker-boundary-with-hangar).

## Connection and configuration

The implementation accepts a bare HTTPS `*.atlassian.net` site and canonical
Cloud UUID, and sends requests only to
`https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/`. Before lifecycle
operations it checks serverInfo deployment/base URL and the authenticated account.
Explicit account/project/type mappings are retained with work bindings.

An incomplete starting configuration has `kind="jira-cloud"`, `site_url`,
`cloud_id`, `auth_mode` and `token_env`; Basic also needs `email_env`. Do not invent
the actual site or Cloud UUID. Supported modes are externally managed
`oauth_bearer` and approved personal-scoped-token `personal_scoped_token_basic`.

Both modes are documented by Atlassian; service-account token conventions and
unscoped site-routed tokens are deliberately not guessed. OAuth refresh/token
distribution and company policy remain external inputs. See
[OAuth gateway routing](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)
and [personal scoped-token Basic routing](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/).

The common connection handler discovers named projects, composite project:type
identities, type-specific status membership, create metadata and resolutions.
`--select` resolves unique names or IDs; patch selection checks cross-resource
membership and disjoint state/resolution mappings. Complete plans bind metadata,
identity and local source/runtime/work snapshots.

The common service owns saving and authored-safe application; Jira setup performs
no remote writes. Reviewed create_fields/transitions are validated and left in
their authored configuration instead of being guessed or rewritten by onboarding.

## Publication and reconciliation

Publication writes the exact WorkService correlation as ADF text and an `ai-dlc`
issue property in the same create request. The property stores schema, correlation,
operation ID and Cloud/account/project/type identity. A fresh issue read validates
that evidence before success. Property values are not presumed JQL indexed.
[Create, metadata and transitions](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/),
[ADF](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)
and [issue properties](https://developer.atlassian.com/cloud/jira/platform/jira-entity-properties/).

Reconciliation uses enhanced POST search/jql restricted to the selected project.
It traverses every continuation token and checks exact marker/property matches.
Missing optional property maps trigger an explicit property lookup. A property
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

## Fields, transitions and links

Create re-reads project/type/field metadata. Current required fields need reviewed
supported values or a server-declared default. Supported schemas are strings,
finite numbers/integers, booleans, simple ID objects, arrays and ADF textarea data;
unsupported required schemas are a visible limitation. Remote validators can still
refuse.

Transitions discover current routes with `expand=transitions.fields` and
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

## GitHub delivery with Jira outcomes

Sean's personal profile selects GitHub Issues for delivery, with a GitHub Project
configured per repository for planning. Jira is the upstream owner of business
outcomes when work needs it. One Jira story or epic can link to several GitHub
delivery issues. Small fixes and maintenance may start in GitHub without a Jira
parent; link them upstream when they affect a business commitment.

This is a manual workflow today. The profile comments express intent, not an
enabled Jira connection or synchronization service. Each work record still has
one selected tracker. Selecting `jira-cloud` instead makes Jira that delivery
tracker; it does not connect Jira outcomes to GitHub issues.

| Location | Owns |
| --- | --- |
| Jira | Business outcome, stakeholder priority, scope and acceptance |
| Repository documents | Discovery, product rationale and design decisions |
| OpenSpec | Required behavioral specifications |
| GitHub Issues | Deliverable engineering tasks, dependencies and acceptance evidence |
| GitHub Projects | Delivery planning, sequencing and progress |
| Pull requests and CI | Review, merge and verification evidence |

### From intake to business acceptance

1. **Intake:** A Jira ticket identifies an outcome. Triage decides whether it
   needs discovery, clarification or delivery planning. Creating the ticket does
   not authorize development. GitHub-originated engineering work enters the same
   shaping and specification decision stages at the depth it needs.
2. **Shaping:** Capture discovery, product requirements when needed, and design
   decisions in repository documents. Review the requirements and record the
   formal specification decision; keep required OpenSpec artifacts current.
3. **Breakdown:** Create reviewed work records for independently deliverable
   GitHub issues. Link their requirements, design and specification, and record
   the Jira outcome URL as `artifacts.jira_parent` when applicable. Sequence the
   issues and their dependencies in GitHub Projects.
4. **Delivery:** Publish and start the reviewed work through ai-dlc, implement
   through pull requests, run required checks, and use `ai-dlc work finish` after
   merge to verify the configured completion gates. A board status alone is not
   delivery evidence.
5. **Acceptance:** When all agreed delivery work is verified, summarize the
   evidence and remaining concerns on Jira as ready for acceptance. Business
   acceptance controls Jira closure. One merged PR or completed child issue does
   not complete the outcome; partial delivery remains visible as outstanding work.

"Ready for acceptance" describes a handoff, not a prescribed Jira status ID or
automatic transition. Use the actual team's reviewed workflow. Jira scope changes
return to shaping and a review of affected specifications and delivery issues.
Cancellation or reopening requires explicit reconciliation of remaining work;
neither system's status automatically propagates to the other.

### Manual links now

Add the parent to the existing artifact table in each applicable work record:

```toml
[artifacts]
# Illustrative URL: replace with the actual Jira outcome's full URL.
jira_parent = "https://example.atlassian.net/browse/TEAM-123"
```

Retain the record's other artifact entries. `jira_parent` is an artifact naming
convention, not a second tracker binding or a validated cross-system parent-child
relationship. New GitHub issue publication includes these artifact references.

Repeat publication preserves authored issue descriptions, so adding the reference
later does not update an already published issue: manually add the link there too.
Maintain reciprocal links and concise delivery summaries on the Jira outcome.
Keep business rationale, design and formal behavior in their owned locations and
link them instead of maintaining competing copies.

Where configured, Atlassian's GitHub integration can show branches, commits and
pull requests on Jira work items when their keys appear in development work.
This provides development visibility; the workflow above still needs its manual
issue links and outcome summaries. See
[Atlassian's GitHub integration guidance](https://support.atlassian.com/jira-cloud-administration/docs/use-the-github-for-jira-app/).

### Gaps before automated synchronization

The existing Jira Cloud adapter supports Jira as the selected tracker. The
following coordination capabilities remain future work:

- Explicit Jira intake that prepares reviewable local discovery and work context.
- Structured outcome-to-delivery mappings across work items and repositories.
- Aggregate reporting of verified, outstanding and blocked delivery work.
- Field ownership and conflict handling: Jira supplies business scope and priority;
  GitHub supplies engineering progress. Changed scope returns for review.
- Retry-safe synchronization that preserves authored content, reconciles uncertain
  writes, and never closes a Jira outcome merely because one PR merged.

Company Jira access and workflow compatibility remain unverified. Manual linking
does not require enabling the Jira adapter; future automation needs the actual
approved company connection and workflow mappings. See
[work-computer setup](../workflows/work-computer-setup.md) for GitHub delivery setup
and the explicit Jira-only alternative.
