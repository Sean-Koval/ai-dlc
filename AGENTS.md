# Repository guidance

ai-dlc is a local workflow, machine-provisioning and work-lifecycle tool. It
prepares developer machines, authors one optional workflow plugin and gates work
completion on CI receipts; it is not a hosted autonomous development orchestrator,
a harness evaluator or the definition of what runs in cloud sandboxes.
CLI and MCP entry points share application services. Provider details belong behind
contracts; credentials and machine paths never belong in shared configuration.

Before preparing this checkout, identify the intended repository. A teammate who
cloned ai-dlc only to install it for another project should follow the consumer
route in [Get started](docs/workflows/get-started.md#add-it-to-an-existing-repository), pass that work repository explicitly
to `project onboard --root`, and keep this engine checkout's providers and accounts
out of the target. Native Windows consumer installation is unsupported in this
revision; [#172](https://github.com/Sean-Koval/ai-dlc/issues/172) tracks installation
and [#53](https://github.com/Sean-Koval/ai-dlc/issues/53) tracks client/cross-machine
qualification. Do not present the POSIX bootstrap below as native Windows guidance.
Only contributors changing ai-dlc itself should prepare this checkout and run its
full required checks.

Prepare this checkout with `sh scripts/bootstrap.sh --source`; run
`ai-dlc project check --required`. That prepares this checkout's own environment
and leaves the shared `ai-dlc` alias alone; use the printed environment path, or
pass `--publish-aliases` to repoint the alias deliberately. Use the Python implementation in `src/ai_dlc/`.
The [architecture](docs/architecture.md) maps its packages and entry points.
This checkout commits no rendered skill copies; load the team skills from the
workflow plugin, enabled for the session because it is off by default
(`claude --plugin-dir plugins/ai-dlc-workflow --settings '{"enabledPlugins":{"ai-dlc-workflow@inline":true}}'`;
`claude <the same flags> plugin list` shows `√ loaded`), or read
`plugins/ai-dlc-workflow/skills/` from Codex, and edit them under `agents/skills/`.
The Rust implementation is retired and removed; its plans are in git history before tag `docs-prune-2026-10`.
`ai-dlc project init` and `project adopt` copy the packaged `project-templates/`;
the legacy `templates/` scaffold and the root `copier.yml` are removed. Preserve
packaged assets.

## Scope freeze

ai-dlc is feature-frozen as of 2026-10. New features, documentation growth and new
OpenSpec capabilities outside the in-scope list in
[ADR 0001](docs/decisions/0001-refocus-ai-dlc.md), as amended by
[ADR 0002](docs/decisions/0002-jira-work-tracker-and-trace-correlation.md),
[ADR 0003](docs/decisions/0003-second-brain-capture-and-publish.md) (the second-brain module) and
[ADR 0004](docs/decisions/0004-knowledge-system-scope.md) (the knowledge system), stop; changes outside that list
are closed with a pointer to it, and bug fixes in frozen areas are welcome. Harness
evaluation belongs to flightdeck and sandbox runtime rendering to hangar. Check the
list before starting work, and do not grow moved or cut areas.

## Placement and upkeep

- Docs follow the suite's editorial rule: paragraphs of at most 60 words, sentences of at most
  25 and pages of at most 700. `tests/test_editorial.py` ratchets it against
  `tests/editorial_baseline.json`; no page may get longer, and no new page may go over.
- Read [docs/index.md](docs/index.md) before creating documentation. Update the
  canonical explanation instead of adding another summary or completion report.
- Keep proposal, design, requirements and tasks together in `openspec/changes/`.
  Keep durable explanations in `docs/design/`, procedures in `docs/runbooks/` or
  `docs/workflows/`, and actual qualification evidence in `docs/verification/`.
- `docs/archive/` preserves explicitly historical material. Its old commands and
  tool instructions are not current guidance. Never manufacture review freshness.
- Growth is frozen (ADR 0001): open new OpenSpec changes only for in-scope areas
  (work lifecycle, enrollment and provisioning, managed sections, the workflow
  plugin, the second-brain module of ADR 0003). Update canonical documents instead of adding new ones, and do not add to
  `docs/archive/`; older material lives in git history.
- Keep disposable execution logs in ignored `.ai-dlc/local/`; do not create root
  planning files, `.superpowers/`, or tool-specific planning hierarchies.
- Enroll a new durable document in its own `docs/catalog.d/<id>.toml` (see CONTRIBUTING.md); update code mappings and links
  when moving sources. Record a documentation-impact disposition for changes.
- Put new Python modules in the responsible subpackage; keep CLI/MCP thin and
  provider-specific logic inside adapters. Do not infer dead code from filenames.
- The docs site's look is Airframe, the suite design system owned by Sean-Koval/agent-factory.
  `docs/stylesheets/airframe*` are vendored unmodified (refresh with
  `sh scripts/sync-airframe.sh theme-vN`); other site CSS uses `var(--af-*)` tokens, never colors.
  The README banner, docs mark, favicon and social preview in `docs/assets/brand/` are
  generated by agent-factory's `scripts/banners.py` and vendored unmodified with
  `sh scripts/sync-brand.sh theme-vN`; change the copy or Airframe there, not here.
- Project templates and portable skills serve downstream projects. Keep their
  setup guidance generic; never embed this repository's personal account choices.

Use conventional commit prefixes. Test observable changes and preserve ownership,
recovery and configuration boundaries. Mocked tests do not prove live platform
qualification; consult [release gates](docs/release-verification.md). Do not
publish packages or mutate remote services implicitly.

## Tracking

- Work is tracked in Jira project KAN (<https://seanmkoval.atlassian.net>). GitHub Projects is retired; GitHub Issues are for outside reports only.
- The managed section below still lists `github-issues` as the tracker: that is the binding of the existing `.ai-dlc/work` records, not where new work goes. `ai-dlc.toml` switches to `jira-cloud` only after the live qualification in KAN-51 ([ADR 0002](docs/decisions/0002-jira-work-tracker-and-trace-correlation.md), KAN-286). File and track new work in KAN.
- Work tied to a ticket carries its key, so the GitHub for Jira app links it: the branch starts with it (`KAN-35-apply-atomic`), the PR title starts with it (`KAN-35: make hangar apply all or nothing`) and the PR body has a `Jira: KAN-35` line. Commits may mention it. Work without a ticket (typo fixes, outside contributions) needs no key.
- Lanes: only `lane:agent` tickets (job-sized: one repo or one change-set profile, acceptance criteria, a verify command) start a hangar job, when moved to "Ready for agent". `lane:pair` is Sean with Claude Code; `lane:human` is Sean only.
- Decisions: a question only Sean can answer becomes a KAN work item of type Decision, never a question in chat. Its summary is the question; fill Options, Recommendation, Default if unanswered, Scope and Due. Label it `decision`, `needs-sean`, `lane:human` and `repo:ai-dlc`, and link it as blocking the work, which waits in Needs Decision. Only a decision that binds code or architecture also becomes an ADR in `docs/decisions/`, written in the PR that implements it.

<!-- ai-dlc:begin c141fd56ee2b6bf88f29644de750b0c9e27c13ffbc8a35d9c72b305ea993ab7e -->
# Shared project guidance

Read ai-dlc.toml and the active .ai-dlc/work record, if present, before work.
Use specification artifacts for implementation tasks; finalize required specifications before review and follow the selected specification provider's instructions.
Use the selected tracker for priority and status; follow its provider instructions.
Raise a question only a person can answer as a decision work item in the tracker that blocks the work, with options, a recommendation, the default if unanswered, scope and a due date; do not ask it in chat.
Archive OpenSpec changes on the bound delivery branch before merge with `ai-dlc work archive`.
Immediately before merge, update from the target branch and rerun required checks.
Record documentation dispositions again only for targets the required documentation gate reports stale.
Complete work through `ai-dlc work finish`.
Finish from a checkout at the merge commit; when the target branch has moved, run `ai-dlc work finish <work-id> --at-merge`, or prepare a temporary detached worktree at that commit, finish there, then remove it.
Store architecture, design and runbooks in docs/; record a decision that binds code or architecture as an ADR in docs/decisions.
Keep personal notes in the selected knowledge provider and follow its instructions.

## Verification

- layout: `uv run --locked --no-sync python scripts/check_layout.py`
- generated: `ai-dlc agents render --check && uv run --locked --no-sync python scripts/check_generated.py`
- format: `uv run --locked --no-sync ruff format --check src tests scripts`
- lint: `uv run --locked --no-sync ruff check src tests scripts`
- types: `uv run --locked --no-sync pyright --pythonpath .venv/bin/python`
- test: `uv run --locked --no-sync pytest -q`
- documentation: `ai-dlc docs gate`
- work-records: `ai-dlc work validate --all`

Run `ai-dlc project check --required` in the prepared project environment.

## Selected providers and tools

Read the linked instructions for each configured provider before using its tools.
Modules name installation requirements; their presence does not establish account
access or platform qualification. Run `ai-dlc project readiness --root .` for
offline requirements and use doctor for explicit provider health inspection.

- scm: github (modules: core); [providers/github.md](<.ai-dlc/providers/github.md>)
- tracker: github-issues (modules: core); [providers/github-issues.md](<.ai-dlc/providers/github-issues.md>)
- deploy: none (modules: none); [providers/none.md](<.ai-dlc/providers/none.md>)
- knowledge: obsidian (modules: none); [providers/obsidian.md](<.ai-dlc/providers/obsidian.md>)
- specs: openspec (modules: openspec); [providers/openspec.md](<.ai-dlc/providers/openspec.md>)
<!-- ai-dlc:end -->
