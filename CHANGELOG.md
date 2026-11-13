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

- A session join key, `aidlc1:<tracker>:<work>:<session>` (KAN-463,
  [format](docs/design/session-join-key.md)). The session-start hook derives it from
  the branch and its work record, exports `AI_DLC_SESSION_KEY` and logs it in the
  ignored `.ai-dlc/local/sessions/`. `work pr` writes `Work-Session:` lines, `work
  finish` copies the keys into the record once, and `work show` resolves a key,
  session ID or ticket back to its record. `work hooks install` adds an opt-in
  `commit-msg` hook for the trailer.
- `ai-dlc knowledge migrate` (KAN-452, [ADR 0005](docs/decisions/0005-migrate-knowledge-notes-to-records.md))
  rewrites knowledge-note frontmatter as knowledge records. It is a dry run unless
  `--write`, idempotent, and reversible with `--revert JOURNAL`. This repository's
  decisions and the ADR templates are records now, and `work finish --learning`
  writes `lesson` records.
- A `wiki` role (`upsert_page`, `get_page_by_key`, `list_children`) with a
  `confluence-cloud` provider, and `ai-dlc knowledge render --changed-since SHA
  [--dry-run]` (MCP `knowledge_render`), the wiki's only writer (KAN-430). It renders
  each changed record and one index page per scope, with a do-not-edit banner, and
  skips pages whose content hash and version are unchanged. A hand edit is restored.
- `knowledge render` drops a page's old status label when its record changes status,
  and marks the page of a deleted record removed instead of leaving it live (KAN-430).
- `ai-dlc knowledge check DIR` (and MCP `knowledge_check`) validates a records
  directory against `KnowledgeRecord`, Open Knowledge Format v0.2 section 11, the
  `knowledge.toml` pin, typed-link integrity, duplicate sources and supersession;
  `--base REF` refuses in-place edits of accepted decisions. Knowledge repositories
  call it through `.pre-commit-hooks.yaml` or the reusable
  `.github/workflows/knowledge-check.yml`. `--vault` keeps checking learnings.
  It also fails a `sources` path in the repository that is missing or whose sha256
  `hash` matches neither the file nor its record body, a record whose `scope` differs
  from its `team/` or `projects/<p>/` folder, and a `belongs_to` that is not a
  work-item key, URL, record id or project under `projects/` (KAN-478). A missing
  `inbox/` or `processed/` payload and an external hash are reported as warnings.
  `--base` also refuses a new record whose slug is already an id or alias on the base.
- A `retracts` link (KAN-479) corrects a decision accepted by mistake without editing
  it. A later accepted decision names it and says why. Index, search and render derive
  `retracted_by` and show the original as `retracted`, not accepted, and
  `search --status accepted` leaves it out. `knowledge check` requires the link to go
  from a decision to an accepted decision, and `--base` allows the new record while it
  still refuses edits to the retracted one.
- A `git` provider for the `knowledge` role (KAN-455): `get`, `search`, `list_changed`
  and `propose` over a repository of knowledge records named by `KNOWLEDGE_REPO` or
  the provider's `location`, through `ai-dlc knowledge records`. `propose` checks the
  records, pushes a new branch and opens a draft pull request through the `scm` role;
  it never writes the base branch. The knowledge role now requires `get` and `search`
  (the Obsidian provider answers both) and `append` is optional. The SCM
  `pull_request_create` payload gains `draft`.
  `ai-dlc knowledge records template TYPE` prints a packaged record template;
  `--list` names the types.
- `ai-dlc knowledge number` and `ai-dlc knowledge index`, with MCP `knowledge_number_plan`
  and `knowledge_index`. After a merge, CI gives slug-id records the next number for
  their type, keeps the slug in `aliases` and rewrites links to it. It then writes one
  OKF v0.2 `index.md` per directory, deriving `superseded_by`. Knowledge repositories
  call `.github/workflows/knowledge-merge.yml` on push to main. It opens a numbering
  pull request that a person merges; `auto-merge` is off by default. `knowledge check
  --base` accepts the slug-to-number changes it makes to links and sources (KAN-456).
- `ai-dlc knowledge why <id>` (`--json`; MCP `knowledge_why`) reconstructs a decision
  from local records: status and dates, the supersession chain both ways, linked
  conventions and lessons, ticket keys and quoted evidence. Each quote sits beside its
  Source record's metadata, and the payload shows `present` or `expired`. `sources`
  entries gain `quote`, `speaker`, `at` and `permalink`, and Source records gain
  `participants`. `knowledge check` fails a `derived_from` link with no quote when the
  Source's payload expires; re-fetchable sources show where to fetch them (KAN-466).
- The knowledge-record contract: `KnowledgeRecord` in
  `ai_dlc.documentation.knowledge_records`, its generated
  `contracts/knowledge-record.schema.json`, format version 1 for knowledge repositories
  to pin, and six templates under `agents/templates/knowledge/`. Records are Open
  Knowledge Format v0.2 documents with OKF field names (KAN-471). It sits beside the
  knowledge-note format, which is unchanged;
  [ADR 0004](docs/decisions/0004-knowledge-system-scope.md) puts the knowledge system
  in scope (KAN-421, KAN-454).
- The second brain, phase A ([ADR 0003](docs/decisions/0003-second-brain-capture-and-publish.md),
  KAN-323). The knowledge-note schema gains `daily`, `meeting` and `thread` notes with
  `origin`, `lane`, `source` and `publish`. `ai-dlc knowledge captured`, `publish-plan`
  and `publish-record` refuse a seen transcript, a note across the work/home wall and
  a page changed since publication. The provider contract gains an optional
  knowledge `publish` operation. The workflow plugin (`0.4.0-r7`) ships the
  `daily-note`, `capture` and `kb-publish` skills.
- `ai-dlc work review WORK_ID [--reviewer NAME]` and MCP `work_review` mark a draft
  reviewed after validating it and its dependencies. They refuse leftover TODOs and
  started work, and record `reviewed_by` and `reviewed_at`, so the review is no longer
  a hand edit of `reviewed = true` (KAN-262).
- [ADR 0002](docs/decisions/0002-jira-work-tracker-and-trace-correlation.md): the Jira
  Cloud adapter moves from frozen to active, and the workflow plugin will give
  sessions a work-ID join key while ai-dlc still emits no traces (KAN-284).
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
- The `ai-dlc` command reports expected failures (a missing `ai-dlc.toml`, an
  unreviewed work record, an unconnected provider, a failed `mise install`) as one
  `Error:` line instead of a traceback, with the same exit status 1;
  `AI_DLC_TRACEBACK=1` restores the traceback (KAN-251).
- `project init` and `project adopt` write an `ai-dlc.toml` with single blank lines
  between sections instead of runs of two to four; the settings are unchanged.
  A project that edited its `[roles]` or `[providers.*]` lines gets one
  `project sync` conflict on that file, to resolve by hand (KAN-263).

### Deprecated

- Knowledge-note frontmatter (`kind:`). The docs gate, recall, `knowledge check
  --vault` and capture dedupe still read it, with a deprecation line, until the
  release after 1.0 (KAN-453). Run `ai-dlc knowledge migrate --write`.
- The Plane tracker adapter: shipped but unsupported and unqualified.
  `project init` and `project adopt` refuse `--tracker plane` without
  `--allow-unsupported` (#200; PR #211).

### Removed

- `publish` on the `knowledge` role, `ai-dlc knowledge publish-plan`,
  `publish-record` and the `kb-publish` skill. The git knowledge repository is
  canonical and `knowledge render` writes the wiki (KAN-430, ADR 0004). Vault
  `.ai-dlc/publish.toml` files are no longer read; declare `[wiki] site` in the
  knowledge repository's `knowledge.toml` instead.
- The `day-start`, `day-end`, `review-inbox` and `needs-spec` skills, replaced by
  `daily-note` and `capture`; `spec-from-prd` now makes the specification decision.
  Remove them from any `[agents] skills` list (KAN-323).
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

### Fixed

- The Jira Cloud adapter works on a project's own tickets. It reads, transitions and
  links issues filed outside ai-dlc, which carry no `ai-dlc` property; `find` and
  `create` still require it. `issue_type_ids` widens the types it reads. A state in
  `statuses` may take a list of IDs, and optional `in_review` and `needs_decision`
  states are transition targets. Before, a ticket in Ready for Agent, In Review or
  Needs Decision read as unknown and refused start and finish (KAN-317).
- Hooks: a chained shell line (`&&`, `;`, `||`, a pipe, a newline or a substitution)
  is classified by its strictest command, so `ls && rm -rf x` is denied and
  `git add -A && git push` gets the bound-push policy; before, any chain was allowed
  as unsupported. The plugin's Claude Code PreToolUse matcher now includes Edit and
  Write, so the `docs/specs` edit warning can fire; other edits skip the CLI. The
  Stop reminder, which went to stdout where the agent never saw it, now reaches the
  agent once per session through exit 2, and only on a branch bound to a work
  record. Plugin revision r6 (KAN-318).
- Guidance: the managed AGENTS.md section, the workflow guide and the discovery,
  review-inbox, prd-draft and handoff skills send a question only a person can
  answer to a tracker decision work item that blocks the work, not to chat. Only a
  decision that binds code or architecture also becomes an ADR in `docs/decisions`
  (KAN-318).
- ai-dlc's AGENTS.md Tracking block, the personal profile and the Jira design page
  say Jira project KAN is the work tracker; `ai-dlc.toml` still selects GitHub Issues
  until KAN-51 (KAN-318).

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
