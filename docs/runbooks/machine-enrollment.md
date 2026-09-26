# Portable profile and machine enrollment

Keep a personal `ai-dlc-profile.toml` in a separate private Git repository and
pin the revision enrolled on each machine. The profile owns portable modules,
logical credential requirements, and agent preferences; the project repository
owns shared policy and durable docs. Each machine independently owns its
binding, including paths, account selection, and environment-variable names.
Credential values belong only to a password manager, keychain, or process
environment. Generated Codex and Claude client files remain owned by their
client configuration, which AI-DLC updates through its ownership rules.

Use `ai-dlc machine status`, `plan`, `apply`, `sync`, and `doctor` to inspect,
preview, reconcile, update, and diagnose local enrollment. Local CLI and MCP
execution are the current control plane; hosted or cloud execution is a later
qualification target. Obsidian portals link an explicitly selected existing vault. Provider discovery
and onboarding use the selected adapter; offline readiness is not live qualification.

Use `ai-dlc project readiness --root PATH` to inspect the selected component
requirements offline. Its JSON separates tool availability, provider configuration,
credential presence, harness guidance, and provider health, with a next action for
each gap. Exit 0 means all required offline checks are ready; missing, blocked, or
unverified required checks return 1. Tools are located on the current environment's
PATH without execution. Credentials are checked only in that environment; secret
files are never loaded. Provider health stays informational and unverified, and
`qualification` is always `not-assessed`.

When `ai-dlc` is missing, reports an unexpected version, or works only in new
terminals, run `ai-dlc project workspace-check --root PATH`. It separates the
executable PATH selects from the AI-DLC-owned shell activation. If no `ai-dlc` is on
PATH, run the same check through the bootstrap's published alias by its full path,
by default `~/.local/share/ai-dlc/bootstrap/bin/ai-dlc`. `configured-for-next-shell`
needs only a new terminal or sourcing the shell file. Missing activation includes a
copy-pasteable PATH command for bash, zsh or fish. Preview permanent repair with
`ai-dlc project workspace-init --shell`; add `--apply` to write only the owned
section. Authored content and other owned lines are preserved; symlinked,
unreadable, non-regular files and edited owned sections are refused.
When mise is missing from PATH, project checks use the executable in the bootstrap
bin directory and emit one stderr note. Checks never install tools, and the
receipt's environment digest is independent of this fallback. When neither
location supplies mise, the command refuses before running checks or writing a
receipt. Rerun the bootstrap if its bin directory is absent.

The shared `ai-dlc` and `ai-dlc-cli` aliases are one machine-wide selection. Source
bootstrap prepares a separate environment per checkout and leaves an existing
working alias alone, so bootstrapping a linked worktree no longer changes the
`ai-dlc` other shells use; it publishes the aliases only with `--publish-aliases`
or when no working alias exists. Bootstrap output names the checkout the alias runs
and the executable for the current checkout. When the alias belongs to another
checkout, `project workspace-check` reports that checkout under activation.
Missing custom Markdown instructions produce a component-specific guidance gap
and a restoration action while independent checks continue. Manifest digest,
schema, path, and symlink violations still block catalog inspection.

`ai-dlc agents render --apply --root PATH` delivers the project-owned provider/tool
index in `AGENTS.md`, which Claude Code receives through its managed `CLAUDE.md`
import. Packaged instructions are owned copies in `.ai-dlc/providers/`; custom
component instructions remain linked project files. Edited or authored copies
are preserved through the existing conflict rules. A provider selected only in a
personal profile can have a missing-delivery gap: declare the intended shared
provider in `ai-dlc.toml` before rendering. Rendering does not promote private
configuration automatically. Missing component metadata is reported explicitly;
the index does not establish new provider or client support.
Rendering refuses any managed removal that would leave selected instructions
with a dangling link, including deselected skills in either client directory.
Move those instructions to a project-owned path and update the manifest first.

Setup plan/apply with `--root` adds selected project component requirements to
machine provisioning. Global MCP settings continue to use the personal profile
and machine configuration; project server lists remain scoped to the project.

Root and machine doctor retain their enrollment and readiness decisions and add
these offline diagnostics under `project_readiness`. Their existing explicit
provider-health inspection remains separate, as do work finish and release gates.

Preview a private profile enrollment can materialize an inactive cache, but it
does not change active enrollment, client configuration, or package state.
Repeat the same command with `--apply` to activate it:

```sh
ai-dlc machine enroll SOURCE --profile-id example-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG
ai-dlc machine enroll SOURCE --profile-id example-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG --apply
```

The lock always records the exact resolved commit. An immutable advertised tag
or ref gives cross-machine reproducibility, and `ai-dlc machine sync` is
idempotent for it. An intentionally movable advertised branch instead enables
`ai-dlc machine sync` to preview a candidate and `ai-dlc machine sync --apply`
to activate it after validation and reconciliation. To move from one immutable
tag to another, reenroll with the new ref. Enroll a second machine with the
same advertised ref under the selected policy and a different machine ID; its
local binding remains independent.

## Project guidance follows selected capabilities

Shared and native guidance follows the project's selected provider roles. Local
projects keep configuration, durable documentation and required checks without
instructions to use unavailable trackers or finish commands. OpenSpec archive
instructions require the OpenSpec runtime provider; a custom specification
provider retains its own linked instructions. Built-in merge/finish guidance
applies to supported selected SCM/tracker combinations. Removing prose never
relaxes configured checks or runtime completion gates.

For one repository, start with its existing tools and a small `agents.skills`
selection. A separate personal profile or team-source repository is useful when
sharing practices across projects, but is not needed merely to adopt local checks.

## Team sources

A personal profile can subscribe to reviewed team repositories without installing
or running their contents. Add subscriptions to the private profile, then enroll
it as usual. Source definitions cannot be set by project or machine layers:

```toml
[[sources]]
id = "engineering"
git = "https://example.com/team/practices.git"
ref = "main"
roles = []
tags = ["review"]
# layout = "teamai" # default: "ai-dlc"
```

Each source has an exact commit and content digest in the machine enrollment
lock. Rendering verifies this cache offline. `ai-dlc machine sync` fetches and
validates candidates but only previews them; `ai-dlc machine sync --apply`
activates them after machine reconciliation succeeds. Run
`ai-dlc agents render --apply --root PATH` to deliver the selected source revision
to a project. Session-start checks advertised refs within a three-second total
budget and only reports `team source <id> has a newer revision; run
\`ai-dlc machine sync\``. It never fetches source contents, changes locks or writes
client configuration. Offline status and rendering do not inspect remote refs.

A machine binding may add the person's roles with a top-level
`roles = ["developer"]` string list. This is distinct from the profile/project
`[roles]` table selecting providers; machine roles never replace that table.
Role, namespace and tag identifiers may contain lowercase letters, digits,
hyphens and underscores (for example `hai_dev`). Source `roles` and machine roles
are combined, while source `tags` select tag
subscriptions. Items without selectors are universal; other items require any
matching role or tag. Validation applies to every item before filtering, so an
unselected item cannot hide unsafe content. Unenrollment or role deselection
removes only previously owned source outputs on the next render. Source skill
names cannot collide with any shipped or selected bundled skills, other source skills,
or authored client skills; even an identical authored file remains unowned.
Edited owned outputs are also preserved through refusal. Source rules appear in
AGENTS.md's owned section, and skills also appear in selected client skill files.
Shared guidance indexes each selected team skill by name, source, bounded
description and links to its complete native skill files. Rules remain inline.
Read an applicable skill's linked file before using it; file generation alone
does not establish native discovery or authentication. Codex and Antigravity
share `.agents/skills`; Claude uses `.claude/skills`. An explicit client render
indexes that operation's destinations. When no client is rendered, full skill
bodies remain inline so the selected instructions are still accessible.

An ordinary render upgrades intact generated sections to this index without
changing source locks or skill bytes. Edited owned sections and authored conflicts
still refuse. Narrow role/tag subscriptions and `agents.skills` keep selection
relevant; measured guidance bytes are not evidence of actual model token savings.

The native layout contains `manifest.toml`, `skills/<name>/SKILL.md`,
`rules/<name>.md`, and optional `mcp/servers.toml` and `hooks/hooks.toml`.
Every exported item is listed in the manifest; other files are refused:

```toml
schema = 1

[[items]]
kind = "skill"
name = "team-review"
path = "skills/team-review/SKILL.md"
roles = ["developer"]
tags = ["review"]

[[items]]
kind = "rule"
name = "review"
path = "rules/review.md"

[[items]]
kind = "mcp"
name = "team-tools"
path = "mcp/servers.toml"

[[items]]
kind = "hook"
name = "session-context"
path = "hooks/hooks.toml"
```

`mcp/servers.toml` declares `[[servers]]` entries with `id`, `command` and optional
`args = ["serve"]`. Commands are portable executable names; AI-DLC imports the
configuration without executing the command. URLs, headers, environment values,
credential arguments and machine paths are refused. Hook content is only
`features = ["session-context"]` or other existing `bound-push` and
`stop-reminder` features. Arbitrary shell hooks are refused. The selected client's
configured version must already support those features in AI-DLC's capability
matrix. All source paths must be regular UTF-8 files without symlinks or execute
bits, up to 2 MiB each and 10 MiB total, with at most 1,024 files and 16 path
segments. Structured manifests are limited to 1 MiB. `env/` directories are
refused, and credential diagnostics name the source path without echoing values.

Set `layout = "teamai"` to read an existing
[Tencent teamai repository](https://github.com/Tencent/teamai-cli). AI-DLC imports
flat or namespaced skills, flat rules, `culture.md` as the `culture` rule, and
`mcp/mcp.yaml`'s `servers` list with `name`, optional `transport: stdio`, `command`
and `args`. It reads role/tag metadata from `teamai.yaml` when present, Markdown
frontmatter, and the current upstream `manifest/roles.yaml` role-to-skill-namespace
mapping and `tags.yaml` skill/rule tag maps. AI-DLC applies the selection rule
above rather than upstream's permissive no-subscription fallback. Hooks, agents
and docs are ignored with notes after safety validation; `env/` and embedded
MCP token/environment values are refused. YAML aliases and duplicate keys are
refused. This is a deliberately limited source reader: it does not install
teamai, execute its hooks, import packages, write back, or access its dashboards.
