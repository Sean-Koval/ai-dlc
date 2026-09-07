# GitHub Issues and Projects setup

Use GitHub Issues for ticket identity and optionally Projects v2 for planning
status. AI-DLC keeps specification, review and CI completion gates. A board item
in Done does not establish that the issue or work is completed.

## New projects

Choose the tracker while creating the scaffold:

```sh
ai-dlc project init ./my-project --tracker github-issues
```

For an existing repository without AI-DLC, preview adoption with
`ai-dlc project adopt --root . --tracker github-issues`, then apply the reviewed
scaffold. Omitting the tracker option preserves the existing default behavior.
Do not use scaffold adoption to migrate retained AI-DLC work.

## Connect a repository and optional Project

Install and authenticate the GitHub CLI locally. The selected account needs
repository access and, when using Projects, appropriate Project read/write access.
Never paste tokens into project configuration or chat. Machine authentication and
shared non-secret connection choices have separate lifetimes.

Start with discovery:

```sh
ai-dlc provider connect github-issues --root .
ai-dlc provider connect github-issues --root . --repository owner/repository --project '*'
```

The second command lists Projects for the repository owner. Select a Project by
URL, number or unambiguous name, then inspect its fields and options. Use the
actual discovered names in the saved plan; these are examples:

```sh
ai-dlc provider connect github-issues --root . \
  --repository owner/repository --project 'Personal coding' \
  --status-field Status --open Todo --in-progress 'In Progress' --closed Done \
  --plan-file .ai-dlc/local/github-connection.json
```

For Issues alone, omit the Project and all status flags. Saving a connection plan
does not create tickets or modify the Project. Review the printed plan and saved
non-secret choices before applying:

```sh
ai-dlc provider connect github-issues --root . \
  --plan-file .ai-dlc/local/github-connection.json --apply
```

Apply consumes the exact saved selections and rechecks account, resources,
configuration and retained work. Do not supply selection flags with apply. Use a
new plan filename when revising a plan. Ambiguity, missing permissions or drift
require a fresh preview; they do not silently select another resource.

Connecting an alias does not switch the default tracker or redirect existing
work. An already-used alias is protected from connection changes. Configure a
new alias and migrate explicitly when replacing an existing connection.

## Existing work and qualification

Choose separately between changing the default for future work and mapping
selected existing work to verified target tickets. Preserve the old Linear alias
and source references. Local records do not necessarily contain the complete
remote active/planned backlog; reconcile source inventory before migration.
Remote target creation is a separate reviewed action, never an implicit rebind.

`ai-dlc project readiness --root .` inspects offline requirements. Explicit doctor
inspection contacts configured providers; successful health reads do not prove
ticket creation, status mutation or recovery. Qualify those in designated
disposable data before production migration.

The [verification record](verification/github-ticket-workflows.md) identifies
current fixture results and remaining live gates. Plane installation and the
custom Confluence MCP server are not prerequisites for this setup. Obsidian and
other non-tracker provider choices remain independent.
