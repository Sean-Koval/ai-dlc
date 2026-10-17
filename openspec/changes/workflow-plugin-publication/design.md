# Design

## Spike (Codex 0.162.1, hangar's lock)

`codex debug prompt-input` lists plugin skills without a model. Hooks were observed
with `codex exec` against a local stand-in for the Responses API that requests one
`git reset --hard HEAD` call. Findings: Codex reads `.claude-plugin/` marketplaces
and plugins, so the Claude plugin's skills load, but its exec-form hooks lose their
`args` and never run the shim. A `.codex-plugin/plugin.json` plugin with
`skills: ./skills/` and `hooks: ./hooks.json` (command strings) loads all eleven
skills and, once its hooks are trusted, runs SessionStart, PreToolUse (blocking the
destructive command) and Stop. Untrusted hooks are skipped silently. Codex sets
`PLUGIN_ROOT` for plugin hooks.

## Decisions

- **One directory, two uses.** `native/codex/` is a complete Codex local plugin and
  also a native fragment: its hook command uses
  `${PLUGIN_ROOT:-${CODEX_HOME:-$HOME/.codex}/ai-dlc-workflow}`, so the same
  `hooks.json` works when the directory is copied to `$CODEX_HOME/ai-dlc-workflow/`
  (where a harness's `native/codex/ai-dlc-workflow/` maps) and merged into
  `$CODEX_HOME/hooks.json`.
- **Digests.** The Claude `content_digest` is unchanged in meaning. The Codex form
  has its own `content_digest` over its files except its manifest (the manifest
  carries the version, which depends on the revision). `files` maps let a publisher
  prove a target is an unmodified earlier publication.
- **Publication safety.** The publisher writes only under
  `plugins/ai-dlc-workflow/` and `native/codex/ai-dlc-workflow/` of the harness
  directory; it refuses unknown or edited files there, refuses a stale build, and
  never edits `harness.lock` or `marketplace.json`. A lock from before per-file
  digests is accepted when its components and content digest recompute from the
  target. It prints both this lock's digests and hangar's `files_digest`, so the
  harness lock's digest algorithm and ours are both recorded.
