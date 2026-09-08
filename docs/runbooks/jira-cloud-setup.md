# Connect a work repository to Jira Cloud

Run these steps in the intended work repository with its own `ai-dlc.toml`.
The framework checkout and your personal GitHub backlog are separate. This
connection creates no Jira issue and migrates no existing ticket.

## 1. Choose the approved credential method and site

Obtain the actual site URL and Cloud UUID through your approved account tooling.
Confirm that the organization allows the selected lifecycle credential. Populate
its named environment variable through that tooling; never put token values in
TOML, a saved plan, native-client settings or this runbook.

For an externally managed OAuth access token, use this alias configuration,
replacing the uppercase identity placeholders with your actual site/Cloud ID:

```toml
[providers.work]
kind = "jira-cloud"
site_url = "https://YOUR_SITE.atlassian.net"
cloud_id = "YOUR_CLOUD_UUID"
auth_mode = "oauth_bearer"
token_env = "JIRA_WORK_ACCESS_TOKEN"
```

For an approved personal API token **with scopes**, replace the last two lines
with the following, and populate both named environment variables. The email is
the account that owns the token. This mode uses email/token Basic authentication
through the Cloud gateway; it does not accept a password or guess service-account
or unscoped-token conventions.

```toml
auth_mode = "personal_scoped_token_basic"
token_env = "JIRA_WORK_API_TOKEN"
email_env = "JIRA_WORK_EMAIL"
```

Native Claude/Antigravity Atlassian MCP login does not supply these credentials.
OAuth issuance/renewal stays in the approved external tooling. The initial TOML
is intentionally incomplete until reviewed discovery selects the remaining IDs.
For a newly adopted repository with no bound work, select this alias in the
existing `[roles]` table with `tracker = "work"`; keep the other role choices.
If you instead retain the scaffold's `jira-cloud` alias, use
`[providers.jira-cloud]` and `provider connect jira-cloud` throughout these steps.
Connect does not change roles or existing work bindings. Existing bound work
requires a separate reviewed provider-switch plan; this guide performs no migration.

## 2. Discover and review the real metadata

```sh
ai-dlc provider connect work --root .
```

Review the authenticated account, project, standard issue type, required create
fields, type-specific statuses and resolutions. Projects are limited to those
where the account has Create Issues permission. `issue_type` uses the returned
`PROJECT_ID:TYPE_ID` composite ID, or its unique `Project name / Type name` label.

Select four distinct status IDs for open, in-progress, successful completion and
cancellation, plus distinct successful/cancelled resolution IDs. A Done category
alone is insufficient. Add any supported required create values under
`providers.work.create_fields`; configure a needed transition ID and field values
under `providers.work.transitions.in_progress` or `.closed`. Use returned field
IDs and explicit values; do not guess user objects, cascading fields or workflow
validators. Required unsupported fields prevent this adapter from qualifying for
that selected issue type.

## 3. Save and apply the reviewed local plan

Replace every uppercase selection placeholder below with a returned ID. Unique
names also work. This command previews the mapping and creates an exclusive local
plan; choose a new plan filename when re-planning rather than overwriting an
existing reviewed plan.

```sh
ai-dlc provider connect work --root . \
  --select project=PROJECT_ID \
  --select issue_type=PROJECT_ID:TYPE_ID \
  --select open=OPEN_STATUS_ID \
  --select in_progress=IN_PROGRESS_STATUS_ID \
  --select closed=SUCCESS_STATUS_ID \
  --select cancelled=CANCELLED_STATUS_ID \
  --select closed_resolution=SUCCESS_RESOLUTION_ID \
  --select cancelled_resolution=CANCELLED_RESOLUTION_ID \
  --plan-file .ai-dlc/local/jira-plan.json

ai-dlc provider connect work --root . \
  --plan-file .ai-dlc/local/jira-plan.json --apply
```

Apply rediscovers the metadata and checks account, selection, source, runtime and
work snapshots. Drift, ambiguous choices or bound-work changes cause refusal.
It writes only local provider configuration. No Project administration, issue
creation or workflow changes occur during this setup.

## 4. Qualify separately before real work

The implementation's fixtures do not prove company access. A live probe requires
approval for a disposable new issue, actual scopes/permissions, create-field values,
current transitions, successful/cancelled outcomes and PR-link permissions.
Classic OAuth access commonly includes read:jira-work, write:jira-work and
read:jira-user; actual endpoint/granular scopes must match the approved credential.
Issue linking must be enabled with Browse Projects and Link Issues permissions.
No live probe was performed for this child.

Once separately qualified, the existing work publish/start/link/finish commands
use this alias through the shared lifecycle and unchanged finish gates. If create
becomes uncertain, retain the journal and reconcile the existing issue. Do not
clear local state to force another create, especially after moving computers.
For limits and supported metadata see the [adapter design](../design/jira-cloud.md).
