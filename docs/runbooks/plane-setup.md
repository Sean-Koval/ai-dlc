# Configure optional Plane for new work

This runbook assumes you already have an authorized Plane deployment and token.
It does not install or deploy Plane or migrate GitHub/Jira tickets. GitHub/Jira
projects can keep using their selected tracker without Plane.

Use the current `/api/v1/.../work-items/` contract. The adapter was developed from
public API documentation and upstream source revision
`1fec307f91003df96351557af32ce87891a3678a`; no installed Plane edition/version or
Cloud account has been qualified by these fixtures. Older or differing API shapes
fail closed. Local deployment and a live tracker swap remain separate evidence.

First review the existing provider configuration and work bindings. Use a new
alias/project for new work; shared connection apply refuses changing an already
bound tracker. Supply nonsecret configuration in provider tables:

```toml
[roles]
tracker = "local-plane"

[providers.local-plane]
kind = "plane"
deployment = "self_hosted"
api_url = "http://localhost:3000"
web_url = "http://localhost:3000"
workspace_slug = "replace-with-your-workspace"
auth_mode = "api_key"
token_env = "PLANE_LOCAL_TOKEN"
```

The port above is an example, not an installer default. Set both origins to your
actual deployment. HTTP accepts only explicit self_hosted `localhost` or literal
loopback IPv4/IPv6, such as `http://127.0.0.1:8080` or `http://[::1]:8080`.
Non-loopback origins require HTTPS; paths, credentials, fragments, queries and
redirects in origins are refused. For Cloud use `deployment = "cloud"`,
`api_url = "https://api.plane.so"` and `web_url = "https://app.plane.so"`.

Set the named environment variable through your approved local secret mechanism.
Never paste a token into project/profile files, plans, commands saved in history,
issues, logs or native-client settings. `api_key` uses `X-API-Key`.
`oauth_bearer` uses an externally managed OAuth access token from the named env
reference; the adapter does not perform login or refresh. Native client login is
separate. The required API scopes are profile:read, projects:read,
projects.states:read, projects.work_items:read/write and
projects.work_items.links:read/write. Actual grants and policy remain to be checked
against the selected deployment.

Read-only discovery displays the authenticated account and named projects/states:

```sh
ai-dlc provider connect local-plane --root .
```

Review account identity, project UUID/identifier, workspace UUID and state groups.
Select exact IDs from that output or unambiguous names. Replace every angle-bracket
placeholder below before running:

```sh
ai-dlc provider connect local-plane --root . \
  --select 'project=<project UUID or unambiguous name>' \
  --select 'open=<backlog/unstarted state>' \
  --select 'in_progress=<started state>' \
  --select 'closed=<completed state>' \
  --select 'cancelled=<cancelled state>' \
  --plan-file .ai-dlc/local/plane-plan.json
```

The common service saves a reviewable local plan and does not alter the manifest.
Inspect it, then apply; live read-only rediscovery and exact authored-file checks
must still agree. This writes only the selected local configuration:

```sh
ai-dlc provider connect local-plane --root . \
  --plan-file .ai-dlc/local/plane-plan.json --apply
```

Use the standard work publish/start/link/finish flow for explicitly authorized new
work. Finish still needs its ordinary specification, merged-PR and CI evidence.
The adapter supports ordinary work items, not custom property/type workflows,
imports, attachments, Jira migration, Plane installation or automatic integration
configuration. A server that rejects the bounded request needs manual inspection.

Before any mutation, AI-DLC persists immutable intent under the local state home:
`ai-dlc/provider-attempts/plane/<root digest>/<operation digest>.json`. State home is
`XDG_STATE_HOME`, or the account home `.local/state`; it is supplied as trusted
local runtime context, never shared provider configuration. Preserve these files.
Intent creation permits one sender. On a lost response, crash or rejection, later
invocations only look for exact remote evidence; absent/partial/duplicate evidence
remains unresolved. The diagnostic names the operation for inspection. A visible
exact result can reconcile by rerunning the same work command. There is no force
retry, reset, cleanup or deletion command for intents.

Changing roots/state homes/machines, removing intent files or manufacturing a new
operation ID loses the original local-attempt protection. Do not use those actions
to retry uncertainty. Cross-machine exactly-once behavior is not claimed.
