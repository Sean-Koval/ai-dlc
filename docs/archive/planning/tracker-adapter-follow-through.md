> Historical record. Retained for provenance, not current implementation guidance.
> Consult docs/index.md, canonical OpenSpec requirements and the tracker.

# Tracker adapter follow-through

The authorized first implementation is GitHub Issues with optional Projects v2.
AI-DLC remains a scaffolding and workflow harness: the shared workflow consumes
declared capabilities and verified provider operations. A provider adapter owns
service-specific requests, native state mappings, identity and reconciliation.
Harness MCP access and AI-DLC lifecycle support are separate qualifications.

Changing between implemented providers should require connection setup, named
resource selection and a reviewed binding migration. Adding a previously
unsupported service still requires a narrow adapter and qualification. The GitHub
child does not establish that Plane or Jira are already supported.

## Plane, if selected later

No installation is needed for GitHub. If Plane is selected, pin the self-hosted
edition/version and local service origin before live qualification. Its documented
current API uses `/work-items/` routes. Native states have groups including
`started`, `completed` and `cancelled`; cancellation must stay distinct from
successful completion. [API introduction](https://developers.plane.so/api-reference/introduction),
[state model](https://developers.plane.so/api-reference/state/overview).

Use the documented `external_source` and `external_id` fields for correlation:
creation accepts them and list/retrieve document matching filters. Prove their
lossless create/read/list round-trip against the selected deployment, since sample
response bodies do not establish that behavior. Exhaust cursor pagination and
reject duplicate or incomplete reconciliation. An uncertain create must not
become a blind retry. [Create](https://developers.plane.so/api-reference/issue/add-issue),
[list](https://developers.plane.so/api-reference/issue/list-issues),
[retrieve](https://developers.plane.so/api-reference/issue/get-issue-detail).

Native work-item links are documented. Reconcile exact URL/title after uncertain
writes; the link-create schema does not provide an idempotency key. Qualify link
create/list with the same pinned deployment. [Create link](https://developers.plane.so/api-reference/link/add-link),
[list links](https://developers.plane.so/api-reference/link/list-links).

Required later inputs: deployment version/origin, workspace and project, local
credential reference, intended state mappings and disposable qualification data.
Credentials stay outside tracked configuration.

## Jira Cloud for work

Maintainer clarification: Jira is a work onboarding/new-work target. Personal
AI-DLC work moves to GitHub; there is no request to migrate tickets into Jira.


Use REST v3 with an explicitly selected Cloud origin and authentication mode.
Discover project, issue type, required create fields and actual per-issue
transitions. A destination status ID is not a transition ID. Tenant-specific
success/cancellation rules must use verified status and resolution mappings;
the Done category alone does not establish successful completion.
[Issues and transitions](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/).

Create can store an `ai-dlc.correlation` issue property atomically with the issue.
Use ADF for description content. For reconciliation, use current enhanced
`/rest/api/3/search/jql` and exhaust token pagination, requesting the correlation
property and comparing exact values. Do not assume arbitrary REST-set properties
are indexed for JQL. Full project scans have a real latency/rate cost and
permission-filtered or incomplete results cannot prove absence.
[Issue properties](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-properties/),
[enhanced search](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/).

Native remote links support a stable `globalId` for updating the same link.
Verify project permissions and post-write outcomes before reporting success.
[Remote issue links](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-remote-links/).

Required later inputs: Cloud site, approved authentication path, project and issue
type, workflow/resolution rules, required fields and disposable qualification
data. The custom Confluence MCP server is not a prerequisite for ticket support.

## Acceptance for each later adapter

- Register capabilities, setup guidance and connection discovery through shared
  extension points; add no tracker-name dispatch to work lifecycle services.
- Run contract fixtures for identity, cancellation, pagination, ambiguous
  correlation, uncertain writes and recovery before disposable live qualification.
- Exercise the same default-only and selected migration service against configured
  aliases, preserving existing work bindings and non-tracker references.
- Record fixture evidence separately from live reads and mutations. Neither
  documentation nor successful authentication alone qualifies a provider.

This is implementation preparation from official API documentation reviewed on
September 7, 2026. Neither Plane nor Jira was installed or live-qualified.
