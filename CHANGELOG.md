# Changelog

Notable changes to ai-dlc, newest first, in the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. ai-dlc has one
published release, [v0.4.0](https://github.com/Sean-Koval/ai-dlc/releases/tag/v0.4.0);
everything since is unreleased on `main`, where the package version is still 0.4.0.
Two tags mark points in that history: `eval-handoff-2026-10` (the last commit with
the evaluation runner) and `docs-prune-2026-10` (the last commit before the
documentation archive was pruned). [Migration notes](docs/migration.md) say what to
change for each removal.

## Unreleased

The refocus ([ADR 0001](docs/decisions/0001-refocus-ai-dlc.md), epic
[#189](https://github.com/Sean-Koval/ai-dlc/issues/189), October 2026): ai-dlc is a
workflow-plugin author, machine provisioner and CI-receipt-gated work lifecycle.
Everything else is frozen to bug fixes, moved to hangar or flightdeck, or cut.

### Added

- The workflow plugin: `plugins/ai-dlc-workflow/`, one optional Claude Code plugin
  with the workflow guidance, ten team skills and three hooks that run without the
  `ai-dlc` CLI and stay out of the way in hangar sandboxes, off by default
  (#191, #192; PRs #210, #214).
- The plugin's Codex form (`native/codex/`) and
  `scripts/publish_workflow_plugin.py`, which publishes both forms into a team
  harness, including hangar's directory-marketplace layout (#193; PRs #222, #225).
- `[work] tracker_writes = "finish-only"` for repositories whose agent jobs start
  through hangar intake: `work start` stops moving the ticket (#205; PR #211).
- Decision records in `docs/decisions/` with knowledge-note frontmatter and optional
  `checks:`, starting with ADR 0001 (#190, #207; PRs #209, #220).
- `ai-dlc knowledge check --vault PATH`, a read-only check of learning-note
  frontmatter (#206; PR #220).
- The documentation site in the Airframe theme, a front page with recordings
  generated from the real CLI and checked in CI, and `scripts/docs_site_links.py`
  (#213; PRs #212, #215, #224, #229).
- `CHANGELOG.md` (#208).

### Changed

- New projects and the base profile default to the `github-issues` tracker; the
  base profile selected Linear in v0.4.0 (#199; PR #211).
- Hooks gate on a minimum client version (`claude-code` 2.1.0, `codex` 0.151.0)
  instead of an exact pin, and the module catalog pins Claude Code 2.1.296 and
  Codex 0.162.1, matching hangar's harness lock (#197; PR #216).
- `work finish --learning` writes knowledge-note frontmatter (author, sources,
  validity) generated from the record and the finish evidence (#206; PR #220).
- This repository stops committing rendered skill copies; contributors load the
  workflow plugin instead (#202; PR #218).
- `work finish` falls back to REST when GitHub GraphQL is refused, and
  `project init` points to `project setup` (#226, #227; PR #228).
- The tool name is written `ai-dlc`, lowercase, in prose and user-facing strings
  (KAN-19; PR #243).
- The documentation site is split into one page per question and held to the
  suite's editorial rule by `tests/test_editorial.py`; its theme follows Airframe
  through theme-v15, and the front page adds a demo clip (PRs #231, #234, #236,
  #240–#242, #244–#247).

### Deprecated

- The Plane tracker adapter: shipped but unsupported and unqualified.
  `project init` and `project adopt` refuse `--tracker plane` without
  `--allow-unsupported` (#200; PR #211).

### Removed

- `ai-dlc eval`, the evaluation runner and skill evaluation, now flightdeck's. The
  command is a hidden stub that exits 2 with a pointer for one release (#194, #195;
  PRs #221, #223).
- `ai-dlc scaffold`, its `templates/` assets and the root `copier.yml`; use
  `ai-dlc project init` or `project adopt`. The command is a stub that exits 2 for
  one release (#201; PR #217).
- The Linear adapter, its guided connection, conformance target and module; a
  configuration that selects Linear gets a typed refusal (#199, #200; PR #211).
- The `devcontainer`, `codex-cloud` and `claude-cloud` execution targets, and the
  unused `target=` argument of `render_agents` and `render_windows`; cloud
  sandboxes are rendered by hangar (#196; PR #216).
- Archived plans, cancelled OpenSpec changes and dated evidence captures, kept in
  git history at tag `docs-prune-2026-10` (#204; PR #219).

### September 2026, after v0.4.0

Merged between the v0.4.0 tag and the refocus. Several of these areas are now
frozen.

- Work lifecycle: delivery records committed and pull requests opened by `work pr`
  (#123), unreviewed records from tracker issues (`work new --from-issue`, #125),
  specifications archived before merge (`work archive`, #127), optional session
  learnings (#120), offline next actions (`ai-dlc next`) and binding-drift
  explanations (#124), content-bound documentation evidence per work item (#149),
  an explicit lightweight push policy (#187), and finishing from an isolated
  checkout of the exact merge commit (`work finish --at-merge`, #188).
- Documentation commands consolidated under `ai-dlc docs`; the former
  `project docs-*` names still run for one release and name their replacement
  (#121).
- Setup and onboarding: pinned team sources and teamai imports (#134), tailored
  team guidance and focused checks (#170), behavioral acceptance checks (#186),
  native Windows core project workflows (#181), the read-only `project onboard`
  planner (#183) and effective-environment reports (#184).
- Optional backend API contract checks (#128), frontend smoke checks and design
  capture (#129), and local FDE engagement documents (#133).
- Fixes: separate GitHub operation and request budgets (#122), a missing GitHub
  token scope explained with its repair (#150), actionable refusals for a skill
  digest mismatch and missing Git (#161), and the release replay after first-use
  setup (#130).

The evaluation runner work merged in the same weeks (#152-#157, #163-#165) was
removed in the refocus above.

## [0.4.0] - 2026-09-14

First published release: hash-bound bootstrap assets (wheel, locked constraints,
`release.sh`, `bootstrap.sh`, `versions.sh`, `download.sh`, `SHA256SUMS`) built by
the `Release` workflow from tag `v0.4.0`. The Python CLI and local MCP server,
machine enrollment from pinned profiles, project scaffolding and adoption, GitHub
Issues/Projects, Jira Cloud, Linear and Plane tracker adapters, OpenSpec and
Obsidian, and the CI-receipt-gated `work finish`. What the release proved, and did
not, is in [release verification](docs/release-verification.md).

[0.4.0]: https://github.com/Sean-Koval/ai-dlc/releases/tag/v0.4.0
