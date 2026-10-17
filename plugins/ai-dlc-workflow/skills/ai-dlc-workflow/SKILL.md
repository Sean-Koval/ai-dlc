---
name: ai-dlc-workflow
description: Use at the start of development work in any repository to follow the AI-DLC workflow: shape scope, specify when needed, deliver through a reviewed pull request and finish against merged evidence.
---

# AI-DLC workflow

This optional plugin carries the AI-DLC workflow guidance, team skills and safe hooks.
It works in any repository; lifecycle commands apply only to adopted repositories.

## Always

- Use the team skills in this plugin for judgment: discovery, prd-draft, needs-spec,
  spec-from-prd, review-inbox, handoff, document-review, document-organize and the
  optional design-brief and design-evaluate.
- When the repository renders its own copies of these skills (unprefixed, under
  `.claude/skills`), prefer the repository copies and its AGENTS.md guidance.
- Immediately before merge, update from the target branch and rerun required checks.
- Store architecture, design, decisions and runbooks in docs/.

## In adopted repositories

Adopted repositories carry fuller guidance in their AGENTS.md managed section.

- If `ai-dlc.toml` exists at the repo root and `ai-dlc` is on PATH: read ai-dlc.toml and the active .ai-dlc/work record, if present, before work.
- If `ai-dlc.toml` exists at the repo root and `ai-dlc` is on PATH: complete work through `ai-dlc work finish`.
- If `ai-dlc.toml` exists at the repo root and `ai-dlc` is on PATH: finish from a checkout at the merge commit; when the target branch has moved, run `ai-dlc work finish <work-id> --at-merge`, or prepare a temporary detached worktree at that commit, finish there, then remove it.

## Hooks

The plugin hooks deny destructive shell commands such as `rm -rf`. In adopted
repositories with `ai-dlc` installed they delegate to `ai-dlc hook`; inside hangar
sandboxes they never delegate and never block `git push` or `gh pr create`. Set
`AI_DLC_HOOKS=off` to disable them or `AI_DLC_HOOKS=quiet` to drop the session line.
