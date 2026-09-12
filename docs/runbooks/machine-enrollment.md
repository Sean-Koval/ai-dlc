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
needs only a new terminal or sourcing the shell file. Repair `stale` or `missing`
activation by rerunning the bootstrap and `ai-dlc setup apply`, not by adding
symlinks or PATH lines. When the runtime manager the project selects is absent,
`ai-dlc project check` refuses before any check runs: it exits nonzero, names the
missing executable, repeats that same activation remedy, and keeps its output
machine-readable without writing a receipt.

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
