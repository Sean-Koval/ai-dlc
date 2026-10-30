# Configure a project

## Connect tools and configure the project

The generated `ai-dlc.toml` owns shared policy. These sections select providers
and the repository whose merge/CI evidence must be checked.

```toml
[roles]
specs = "openspec"
tracker = "github-issues"
knowledge = "obsidian"
scm = "github"
deploy = "none"
agent-client = ["claude-code", "codex"]

[scm]
repository = "your-org/your-project"
workflow = "verify.yml"
target_branch = "main"
```

Authenticate the GitHub CLI with access to your repository and Project. Then
preview the connection and apply its saved choices from the project root.

```sh
ai-dlc provider connect github-issues \
  --plan-file .ai-dlc/local/github-project.json
ai-dlc provider connect github-issues \
  --plan-file .ai-dlc/local/github-project.json --apply
ai-dlc agents render --apply
ai-dlc project readiness
```

Connection apply can create or reuse a GitHub Project; inspect the preview first.
Readiness checks local requirements; `doctor` also inspects configured provider
health. See [GitHub setup](../github-ticket-setup.md) for existing Projects,
custom statuses, and issues-only mode.

| Configuration | Where it belongs |
| --- | --- |
| Shared providers, setup, checks, gates, agent guidance | Project `ai-dlc.toml`, `.mise.toml`, and repository files |
| Portable tools, personal agent preferences, team subscriptions | Private `ai-dlc-profile.toml` repository |
| Local paths, account selections, credential environment-variable names | Machine binding; use `--machine` where supported |
| Secret values | Password manager, keychain, or injected process environment; never Git |

## Carry preferences and team guidance across machines

Enroll a private profile repository at a reviewed tag or advertised Git ref.
Use the same revision on another machine with its own machine ID.

```sh
ai-dlc machine enroll SOURCE --profile-id my-development --machine-id laptop --ref v1
# Review the plan, then repeat with --apply.
ai-dlc machine status
```

Add reviewed team subscriptions to that profile:

```toml
[[sources]]
id = "engineering"
git = "https://example.com/team/practices.git"
ref = "main"
tags = ["review"]
layout = "ai-dlc" # Use "teamai" for the supported teamai reader.
```

Enrollment locks exact source commits and content digests. `ai-dlc machine sync`
previews newer revisions; `ai-dlc machine sync --apply` activates them. Render the
updated guidance into a project with `ai-dlc agents render --apply --root PATH`.

ai-dlc preserves unrelated client settings and refuses collisions or edits to
owned outputs. [Machine enrollment](../runbooks/machine-enrollment.md) covers
profile setup, role/tag selection, personal MCP servers and source restrictions.
