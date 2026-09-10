# Work-computer setup

AI-DLC installs the engine and prepares individual repositories. Cloning this
repository gives you the engine source; its own GitHub Project and account
configuration belong to AI-DLC development. Adopt each work repository with its
own project policy and local credentials.

## Install the engine

Clone the reviewed AI-DLC revision and run `sh scripts/bootstrap.sh --source` from
that clone. Follow the bootstrap's printed PATH instruction, then verify
`ai-dlc --help`. Source mode is the currently verified installation path; do not
substitute an unverified package download. The current release evidence remains
in [release verification](../release-verification.md).

## Prepare a work repository

For GitHub delivery with optional upstream Jira outcomes, preview from the target
repository:
`ai-dlc project adopt --root . --preset python --tracker github-issues --knowledge obsidian --agent-client claude-code --agent-client antigravity`
(or the applicable language preset and explicitly selected tracker). Inspect proposed files and resolve authored
conflicts, then repeat with `--apply`. Existing configured repositories use their
reviewed configuration and `project sync` workflow instead of adoption.

Omitting tracker selection preserves the legacy scaffold default. Explicitly choose
`--tracker github-issues` for this delivery model, for personal or work repositories.
Its guided connection proposes a repository-associated Project. Run
`ai-dlc provider connect github-issues`
to preview it; `--issues-only` is an option of that connection command. Follow the
[GitHub saved-plan setup instructions](../github-ticket-setup.md) for exact
preview, saved-plan apply, permissions and recovery steps. Keep repository, account
and board mappings specific to the target project; do not copy AI-DLC's own IDs.

Jira can own business outcomes while GitHub owns the delivery issues. Use manual
`artifacts.jira_parent` URL references and reciprocal links as described in
[GitHub delivery with Jira outcomes](../development-workflow.md#github-delivery-with-jira-outcomes).
Jira intake and progress synchronization are planned, not enabled by the personal
profile. This arrangement does not require selecting or connecting `jira-cloud`.

If a repository should use **Jira as its delivery tracker**, explicitly substitute
`--tracker jira-cloud` in the adoption command. Follow the
[Jira Cloud setup](../runbooks/jira-cloud-setup.md) to select the actual site,
account, project, issue type and workflow through reviewed discovery. This is an
alternative single-tracker lifecycle, not Jira/GitHub synchronization. Actual
company permissions and workflow compatibility still need verification on the
work computer. Do not publish work to an incomplete scaffold merely because its
tracker appears in a preview.

The repeated `--agent-client` options persist this shared selection during
`project adopt` or `project init`. Existing configured repositories can review the
equivalent `ai-dlc.toml` selection:

```toml
[roles]
agent-client = ["claude-code", "antigravity"]
```

Keep the rest of its selected roles and repository-specific settings. For reviewed
role/account connections, follow [native connection setup](../design/native-tool-composition.md):
preview explicit bindings, save and apply the exact configuration plan, then
render the native files separately. Identical shared connections deduplicate;
conflicting account or transport identities refuse. The existing manual format
also remains supported. To expose AI-DLC's local MCP service manually, add this
definition if it is not already configured:

```toml
[[agents.servers]]
id = "ai-dlc"
command = "ai-dlc"
args = ["mcp", "serve"]
```

The client must launch it in the target repository with the prepared executable
on PATH. OAuth-capable remote tools use an explicit `url` server definition;
login takes place in each native client. AI-DLC lifecycle transport credentials
and native MCP OAuth are separate connections. Configure each for the intended
account; neither is evidence of the other's access.

Preview `ai-dlc agents render`, then use `--apply` after reviewing changed files.
Authored conflicts refuse before changes. `ai-dlc agents render --check` checks
owned configuration; `ai-dlc project readiness --root .` reports missing tools,
configuration and credentials without contacting providers.

## Bind the private vault through machine enrollment

Enrollment is the existing way to select a machine file for ordinary project
commands. Use an explicitly reviewed profile Git repository and advertised branch
or tag; inspect the preview's `resolved_commit`. A raw commit ID is not an
advertised ref. This does not install tools or authenticate accounts.

If you already have a reviewed portable profile, use its source, `profile_id` and
ref. For a first local-only setup, create a new Git repository **outside the work
repository** with `git init /path/to/reviewed-profile`, then add this minimal
`ai-dlc-profile.toml` there:

```toml
schema = 4
profile_id = "work-profile"
```

Commit the reviewed file and create its explicit tag:

```sh
git -C /path/to/reviewed-profile add ai-dlc-profile.toml
git -C /path/to/reviewed-profile commit -m "chore: declare work profile"
git -C /path/to/reviewed-profile tag reviewed-v1
```

This minimal profile supplies no tracker/account/client override. A local source
is reported `portable=false`; use an approved accessible Git source when you need
the same profile on another machine. Do not copy credentials or vault contents into
that profile repository.

Replace `/path/to/reviewed-profile` with that actual Git source. From the intended
work repository, run:

```sh
ai-dlc machine enroll /path/to/reviewed-profile \
  --profile-id work-profile --machine-id work-laptop --ref reviewed-v1
# Inspect profile identity, resolved_commit, any profile change, and machine.path.
ai-dlc machine enroll /path/to/reviewed-profile \
  --profile-id work-profile --machine-id work-laptop --ref reviewed-v1 --apply
```

Edit **the `machine.path` printed by the result**, preserving its existing settings,
and add the actual existing vault directory:

```toml
[paths]
vault = "/path/to/private-vault"
```

Normally that file is under `$XDG_CONFIG_HOME/ai-dlc/machines/work-laptop.toml`
(or `~/.config/ai-dlc/machines/work-laptop.toml` when XDG is unset). It is outside
the shared work repository. Verify the selected layer and then use ordinary readiness:

```sh
ai-dlc profile show --project ai-dlc.toml
ai-dlc project readiness --root .
```

The first result should show `sources.paths.vault = "machine"`; the second should
report that Obsidian's directory exists. Other missing requirements still block
readiness. Project tracker/client choices remain authoritative. No `--machine`
option is needed on project readiness after enrollment, and no native login,
vault write-access test or service qualification follows from directory presence.

The default GitHub SCM role separately requires `git` and `gh` on PATH. Add or
update the existing shared SCM table, replacing `OWNER/REPO` with the actual target
code repository (not AI-DLC's engine repository or the Jira project):

```toml
[scm]
repository = "OWNER/REPO"
```

Preserve any existing SCM workflow, target branch and receipt settings. A missing
CLI, missing/malformed repository configuration, and an unauthenticated account
are different conditions. Readiness checks the first two offline; use the approved
local `gh` authentication for the intended account separately. Credentials stay in
that local mechanism, never in this table. Offline readiness does not verify
account access, PR merge or exact merged-CI evidence. The `none` deployment selection
is explicitly inactive and requires no deployment tool or service qualification.

## Recognize the project in each client

Claude Code uses `CLAUDE.md`, `.claude/skills` and `.mcp.json`. Open the target
repository, review its project MCP prompt and use `/mcp` to inspect/authenticate
selected servers. Remote definitions include Claude's required HTTP type.
See [Claude MCP documentation](https://code.claude.com/docs/en/mcp).

Antigravity's current documented workspace contract uses `.agents/skills`,
`.agents/rules` and `.agents/mcp_config.json`; remote entries use `serverUrl`.
Open the project rule in the native rules UI and activate it as **Always On**.
Inspect skills and the MCP manager, then authenticate selected remote servers.
Native metadata outside the managed rule section is preserved on regeneration;
keep the managed guidance body intact.
The renderer supplies files; it does not fabricate a rule activation setting or
claim the client has loaded them. See [skills](https://www.antigravity.google/docs/skills),
[rules](https://www.antigravity.google/docs/rules-workflows) and
[MCP](https://www.antigravity.google/docs/mcp).

Antigravity project rendering supports OAuth URLs and stdio commands without
generated environment overrides. It refuses environment-name interpolation
because that mapping has not been qualified for the selected client version.
Use a locally configured executable/credential mechanism when necessary; never
paste secret values into shared server definitions. Personal/global Antigravity
rendering and new hook support are not implemented by this project-only slice.

## Record an actual fresh-session check

Record OS/architecture, exact AI-DLC revision and installed client edition/version.
Start a new session in a disposable adopted repository and verify that the agent
can identify its selected tracker/spec provider, read its shared policy, find a
shipped skill and list the intended MCP service's tools. First inspect harmless
context/status; ticket publication or transitions require their own reviewed work
and destination. Confirm another project's account or tracker is not substituted.

Capture native recognition, OAuth status and observed tool results separately
from offline rendering/check results. An absent or failed native check stays
unverified. Unsupported required hooks refuse rendering; AI-DLC's actual workflow
service still enforces completion gates independently of native hook support.

Keep Obsidian as the selected private notes/knowledge location with the machine's
own vault path. Confluence publication and its custom MCP integration remain
separate and deferred; this setup does not copy the vault or team spaces.

## Toolset choices and local notes

Scaffold provider choices come from trusted definitions, independently of the
language preset. Jira Cloud is selectable in this integrated candidate;
scaffolding alone supplies no account identity or credentials. Use its explicit
connection setup for the intended work site and project. Plane is an optional implemented lifecycle adapter with explicit deployment,
account, workspace/project and state configuration. Follow the
[Plane setup runbook](../runbooks/plane-setup.md); no installed deployment is
qualified by the adapter fixtures. Plane is not a prerequisite for GitHub or Jira projects. Selective Confluence work remains deferred.

Copier answers retain selected clients and tracker configuration across updates.
Omitted options preserve the historical Linear and Claude Code/Codex defaults;
this compatibility behavior does not choose a work account. Preview output includes
the selected toolset and known limitations. Review conflicts before applying.

Configure `paths.vault` in the machine layer for Obsidian's existing filesystem
notes. Readiness requires a real existing directory and reports its optional
desktop viewer separately. It does not inspect note content, create directories,
test write permissions or qualify a client session. A provider-local `vault_path`
does not substitute for the runtime setting. Keep private paths and notes out of
the shared work repository.
