# GitHub Issues and Projects setup

Connect a project to GitHub Issues for ticket identity and, optionally, a
Projects v2 board for planning status.

ai-dlc keeps the specification, review and CI completion gates. A board item
in Done does not establish that the issue or work is completed.

## New projects

Choose the tracker while creating the scaffold:

```sh
ai-dlc project init ./my-project --tracker github-issues
```

For an existing repository without ai-dlc, preview adoption with
`ai-dlc project adopt --root . --tracker github-issues`, then apply the reviewed
scaffold. Omitting the tracker option preserves the existing default behavior.
Do not use scaffold adoption to migrate retained ai-dlc work.

## Native tools and repository selection

For ai-dlc itself, the repository is `Sean-Koval/ai-dlc`. For other projects, use
their configured SCM repository/verified Git remote as the proposed default; ask
only when it is ambiguous or an override is intended. A GitHub Project is a
separate planning resource whose name/number is discovered under its owner.

A connected GitHub MCP app can expose issue tools. Installed tool names and
account repository permissions do not prove its write grants or Projects access.
The official GitHub MCP server supports a Projects toolset and local OAuth login.
The current ai-dlc lifecycle adapter uses `gh`; its authentication is separate.
See the [actual adoption/access findings](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/archive/planning/github-backlog-migration.md).

## Connect a repository and optional Project

1. Install and authenticate the GitHub CLI locally. The selected account needs
   repository access and, when using Projects, Project read/write access.
2. Add the Project scopes. A default `gh auth login` token carries `repo` but no
   Project scope: tracker reads need `read:project`, and status changes need
   `project`. Run `gh auth refresh --hostname github.com --scopes project`. A
   read without the scope refuses and names the missing scope and this command.
3. Preview the connection, inspect it, then apply the saved plan:
   ```sh
   ai-dlc provider connect github-issues --root . \
     --plan-file .ai-dlc/local/github-project.json
   ai-dlc provider connect github-issues --root . \
     --plan-file .ai-dlc/local/github-project.json --apply
   ```

Never paste tokens into project configuration or chat. Machine authentication and
shared non-secret connection choices have separate lifetimes.

Default onboarding proposes a Project using the configured project name (or the
repository name). It uses the provider's repository or the project SCM repository
when available, so most projects do not need another repository selection.

The preview lists the verified owner/repository and either the exact existing
Project or a proposed create. Apply creates or reuses it, links it to the
repository, verifies Status/Todo/In Progress/Done, and saves the actual field and
option IDs. Repeated setup reuses the configured Project; preview and offline
scaffold generation never create remote resources.

Missing Project permission is an actionable error, not an automatic downgrade. A
newly created Project is retained if later setup fails; retry uses the recorded
identity. An uncertain create is never blindly repeated: inspect the remote
result, then select its verified URL explicitly.

For an existing Project with custom states, discover then select its actual names:

```sh
ai-dlc provider connect github-issues --root . --project '*'
ai-dlc provider connect github-issues --root . \
  --project 'https://github.com/users/owner/projects/1' \
  --status-field Status --open Todo --in-progress Doing --closed Done \
  --plan-file .ai-dlc/local/github-custom.json
ai-dlc provider connect github-issues --root . \
  --plan-file .ai-dlc/local/github-custom.json --apply
```

Use a new plan filename when revising choices. Apply consumes the saved choices
and refuses local/runtime/remote drift. Existing schema-1 saved connection plans
retain their reviewed meaning, including earlier issue-only plans.

Issues-only is an explicit opt-out and does not require Project permissions:

```sh
ai-dlc provider connect github-issues --root . --issues-only \
  --plan-file .ai-dlc/local/github-issues-only.json
```

Apply that saved plan in the same way. Do not combine `--issues-only` with Project
or status selections. Issue-only start leaves the remote issue open and reports
the missing in-progress capability.

Connecting an alias does not switch the default tracker or redirect existing
work. An already-used alias is protected from connection changes. Configure a
new alias and migrate explicitly when replacing an existing connection.

## Existing work and qualification

Choose separately between changing the default for future work and mapping
selected existing work to verified target tickets. Preserve the old tracker alias
and source references. Local records do not necessarily contain the complete
remote active/planned backlog; reconcile source inventory before migration.
Remote target creation is a separate reviewed action, never an implicit rebind.
Use the [tracker migration commands and recovery guidance](migration.md#tracker-default-and-selected-work-migration)
for the exact preview/apply steps.

`ai-dlc project readiness --root .` inspects offline requirements. Explicit doctor
inspection contacts configured providers; successful health reads do not prove
ticket creation, status mutation or recovery. Qualify those in designated
disposable data before production migration.

The [verification record](https://github.com/Sean-Koval/ai-dlc/blob/main/docs/verification/github-ticket-workflows.md) identifies
current fixture results and remaining live gates. Plane installation and the
custom Confluence MCP server are not prerequisites for this setup. Obsidian and
other non-tracker provider choices remain independent.

The bundled GitHub Issues adapter allows 120 seconds for a complete operation
and 30 seconds for each GitHub CLI request. An explicit provider `timeout`
overrides both. A timeout still leaves an uncertain mutation
for normal reconciliation. Retry through `ai-dlc work finish` so merge, CI,
issue state and Project readback are verified again.

A proxy or policy may refuse the GraphQL endpoint itself (an HTTP 403, 404 or
410 from `api.github.com/graphql`). The adapter then falls back to REST for
issue reads, closes, reopens and links, so `ai-dlc work finish` still completes.

Projects v2 has no repository-scoped REST route, so the Project stays as it was
and the finish result reports `project.reconciled = false` with the reason.
Rerun `ai-dlc work finish` where GraphQL is reachable to move it to Done. Start
and Project attachment still fail there; scope, rate-limit and server errors
never fall back.
