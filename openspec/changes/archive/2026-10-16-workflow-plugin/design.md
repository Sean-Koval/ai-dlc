# Design: workflow plugin

## Observed implementation

`harness/agents.py` renders three channels into adopted repositories: the AGENTS.md
managed section from `_shared_guidance_lines`, hooks from `_plan_hooks` that run
`ai-dlc hook <event> --root "$(git rev-parse --show-toplevel)"`, and skills from
`agents/skills/` verified by `_skill_sources` against `agents/skills.lock.json`.
`harness/hooks.py` classifies shell commands and applies the bound-push policy.

## Decisions

- **Generated, committed directory.** The plugin is a build output checked into
  `plugins/ai-dlc-workflow/` so a harness repository can pin a commit. The builder
  reuses `_skill_sources` and `_shared_guidance_lines`; skills stay single-sourced
  in `agents/skills/`. Only the plugin README is authored.
- **Guide skill.** Plugin `CLAUDE.md` files are not loaded, so the guidance ships
  as the `ai-dlc-workflow` skill. The builder renders the shared guidance for a
  fully featured synthetic configuration, stops at the first `##` section (the
  project's checks), drops lines naming providers or the documentation gate, and
  prefixes lines that need the CLI with the adoption condition. Adopted
  repositories still get the full managed section.
- **Determinism and versioning.** Files use sorted-key JSON with no timestamps or
  absolute paths. `plugin.lock.json` records `sha256` digests per component and a
  content digest over the canonical component JSON. The revision increases only
  when the content digest changes, and `version` is `<engine>-r<revision>`, so
  installed copies move only on content changes. `metadata.source` names the
  directory, not a commit: a committed file cannot contain its own commit, so the
  pinning harness records the commit.
- **Opt-in.** `defaultEnabled: false`. Verified with Claude Code 2.1.301: a
  `--plugin-dir` load stays off until `enabledPlugins` sets
  `ai-dlc-workflow@inline` to true, then exposes 11 namespaced skills.
- **Hook shim.** One stdlib module in `src/ai_dlc/harness/hook_shim.py`, copied
  byte for byte into the plugin, so it is unit-tested and type-checked in place.
  `hooks.py` imports its `classify_command`, making classifier parity structural.
  Hangar is detected by `HANGAR_WORKSPACE` (set in every sandbox image) or
  `HANGAR_JOB_ID` (set for jobs). In hangar the shim never delegates, so the
  bound-push policy cannot deny hangar's pushes; hangar's verify gate and landing
  own publication. Only exit 2 blocks; delegate failures and timeouts (8 s inside
  the 10 s hook timeout) allow with a one-line note.
- **Drift check placement.** `scripts/check_generated.py` calls the builder's
  drift function, so the existing `generated` command covers the plugin without
  changing `ai-dlc.toml` or the rendered verification list.

## Documentation impact

Architecture gains the plugin build as the distribution path for guidance, hooks
and skills, and notes that `ai-dlc hook` stays a hidden CLI-only command used by
repository-rendered hooks. The tool map, README and playbook describe the plugin.
The plugin README owns enablement, the hangar hardening caveat and the `python3`
requirement.
