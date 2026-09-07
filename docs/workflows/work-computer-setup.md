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

From the target repository, preview `ai-dlc project adopt --root . --preset python`
(or the applicable language preset). Inspect proposed files and resolve authored
conflicts, then repeat with `--apply`. Existing configured repositories use their
reviewed configuration and `project sync` workflow instead of adoption.

Omitting tracker selection preserves the legacy scaffold default. Choose
`--tracker github-issues` for a personal GitHub repository; its guided connection
proposes a repository-associated Project, with `--issues-only` available. Jira
Cloud onboarding and lifecycle support are a separate #20 deliverable. Until its
adapter is integrated and configured, native Jira access does not make AI-DLC
publish/start/finish usable with Jira. Do not publish work to the scaffold default
merely because it appears in an initial preview.

Set the project's shared client selection in `ai-dlc.toml`:

```toml
[roles]
agent-client = ["claude-code", "antigravity"]
```

Keep the rest of its selected roles and repository-specific settings. To expose
AI-DLC's local MCP service, add this definition if it is not already configured:

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

## Recognize the project in each client

Claude Code uses `CLAUDE.md`, `.claude/skills` and `.mcp.json`. Open the target
repository, review its project MCP prompt and use `/mcp` to inspect/authenticate
selected servers. Remote definitions include Claude's required HTTP type.
See [Claude MCP documentation](https://code.claude.com/docs/en/mcp).

Antigravity's current documented workspace contract uses `.agents/skills`,
`.agents/rules` and `.agents/mcp_config.json`; remote entries use `serverUrl`.
Open the project rule in the native rules UI and activate it as **Always On**.
Inspect skills and the MCP manager, then authenticate selected remote servers.
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
