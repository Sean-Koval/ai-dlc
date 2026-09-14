# Team Sources Implementation Plan

> **For agentic workers:** Use executing-plans task-by-task in the assigned isolated worktree.

**Goal:** Implement issues #83 and #84 as pinned, filtered, safe team source subscriptions.
**Architecture:** Reuse Git resolution, enrollment activation and render ownership; separate tree validation and teamai adaptation.
**Tech Stack:** Python 3.12, Pydantic, TOML, PyYAML, pytest and local Git fixtures.
**Spec:** specs/team-sources/spec.md and design.md.

## Global Constraints
- Keep schema 4 additive and source definitions personal-only.
- No network access in tests; reject env/ per explicit acceptance.
- No source executables, credentials, writeback or hosted services.

## Task 1: Enrollment and validated source cache
Files: src/ai_dlc/config.py, environment/enrollment.py, environment/machine.py, environment/team_sources.py; tests/test_team_sources.py.
Interface: resolve_sources(config, paths, environ) returns validated SourceLock entries; load_sources(lock, paths, roles) returns selected declarative items.
- [x] Write local bare-Git tests asserting `preview["lock"]["sources"][0]["resolved_commit"] == commit`, no preview activation, role validation and unsafe-path refusals.
- [x] Run `uv run --locked --no-sync pytest tests/test_team_sources.py -q` and observe missing-source behavior fail.
- [x] Add SourceLock validation and cache resolution; invoke it before enrollment/sync activation; serialize exact pins and verify digests offline.
- [x] Run source and machine/profile regression tests; commit implementation.

## Task 2: Owned rendering and session notices
Files: harness/agents.py, harness/hooks.py and tests/test_team_sources.py.
Interface: enrolled_sources() supplies verified items; source_update_notices() supplies bounded advisory strings.
- [x] Add failing tests asserting rendered role-specific content, local collision refusal and output stability after source-ref changes.
- [x] Merge source content before existing render planning and retain transaction/ownership checks, source skill retirement, safe MCP and native hook features.
- [x] Add failing session test asserting `team source team has a newer revision; run ` plus the sync command while lock bytes remain identical.
- [x] Implement bounded read-only ref notices and test preview versus sync activation, including failure rollback.

## Task 3: Teamai compatibility and delivery
Files: providers/teamai.py, tests/test_team_sources.py, profiles/example/ai-dlc-profile.toml, docs/runbooks/machine-enrollment.md, docs/product-direction.md, docs/catalog.toml.
- [x] Add failing teamai layout tests for skills, rules, culture, MCP server list, metadata selection, ignored notes and path-naming token/env refusals.
- [x] Implement the documented adapter using safe YAML parsing; preserve whole-tree validation before ignores.
- [x] Update canonical docs and example with exact native/teamai formats and source/machine boundaries.
- [x] Run `openspec validate team-sources --strict --no-interactive`, archive the change, update work spec reference and check tasks.
- [x] Record documentation dispositions, run `ai-dlc project check --required`, inspect diff and commit; hand off for controller review without pushing or opening a PR.
