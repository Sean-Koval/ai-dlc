# Require revision-bound documentation impact dispositions

## Decisions

Use existing Python application services for shared CLI/MCP behavior. OpenSpec owns proposal, design, behavioral specification and tasks. Repository docs own durable explanations; Obsidian owns private continuity. Existing harnesses perform semantic reasoning. Source citations are evidence, not automatic authority or permission to fetch.

## Scope and verification

- DI-01: Scoped impact inspection. Verify through the linked scenario and observable negative cases.
- DI-02: Revision-bound dispositions. Verify through the linked scenario and observable negative cases.
- DI-03: Prevent new objective debt. Verify through the linked scenario and observable negative cases.

Preserve authored content and filesystem boundaries. No automatic deletion, remote publication or freshness certification. Required checks and independent review precede integration. Live qualification is distinct from fixtures.

## Public interfaces and evidence

`inspect_impact(root, base=...)` is shared by `project docs-impact --base` and `project_docs_impact`. Optional catalog `code_paths`, `requirements` and `verification_paths` are repository-relative path/glob lists; existing catalogs remain valid. Git comparison includes current tracked edits, deletions and untracked files. Unknown changes remain explicit.

`prepare_disposition(root, base, decisions, reviewer)` emits schema-1 JSON with resolved base, source digest map, snapshot and per-target outcome/reason. Outcomes are `updated`, `reviewed-no-change`, `no-impact`. Every impacted document and unmapped change needs a disposition. This records accountable review, not independently proven truth. CLI emits JSON; it never overwrites evidence implicitly.

`prepare_baseline` emits objective findings with source digest, owner and reason. `check_gate` consumes reviewed evidence and baseline paths, defaulting to `.ai-dlc/documentation/current.json` and `baseline.json`. That evidence-only subtree is excluded from change discovery to avoid self-referential hashes; it must not hold source documents. The comparison base is part of reviewed evidence; callers/CI can pin `--base` to reject another base. A baseline change needs review just like a changed check configuration. Evidence digests detect drift, not malicious reviewers.

The required project gate checks errors plus owner/coverage findings. Review age and similarity remain advisory. Historical exemptions bind document bytes, so editing an exempt document requires resolving its old objective defects or an explicitly reviewed new disposition. Missing comparison/catalog/evidence fails closed. No external content is read.

## Delivery evidence

Scoped and integrated independent review approved. All six required local checks passed with 2022 tests and8 skips before archival-only metadata finalization. See docs/verification/documentation-workflow.md for exact scope and live qualification limits.
