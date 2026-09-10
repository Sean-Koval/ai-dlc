# Distribute versioned SDK skills with supporting references

## Decisions

Use existing Python application services for shared CLI/MCP behavior. OpenSpec owns proposal, design, behavioral specification and tasks. Repository docs own durable explanations; Obsidian owns private continuity. Existing harnesses perform semantic reasoning. Source citations are evidence, not automatic authority or permission to fetch.

## Scope and verification

- CG-01: Pinned skill references. Verify through the linked scenario and observable negative cases.
- CG-02: Applicable owned guidance. Verify through the linked scenario and observable negative cases.
- CG-03: Deliberate knowledge promotion. Verify through the linked scenario and observable negative cases.

Preserve authored content and filesystem boundaries. No automatic deletion, remote publication or freshness certification. Required checks and independent review precede integration. Live qualification is distinct from fixtures.

## Schema and selection contract

Schema 1 remains unchanged. Schema 2 requires exactly schema, id, skills,
templates, files, references and guidance. References map exported skill names to
lists of safe Markdown paths strictly below that skill's source directory. Each
payload has one owner; all files must be accounted for. References retain their
relative paths next to every selected native SKILL.md and share its transactional
ownership checks. No source URL is fetched.

Guidance maps exported skill names to owner (nonempty string), status
(approved, draft or superseded), sources (nonempty HTTPS URL list), and sdk
(name slug and nonempty exact versions list). Empty maps are allowed for ordinary
workflow assets. Project-only agents.sdk_versions maps SDK slugs to exact selected
version strings; no cross-ecosystem version range interpretation is attempted.
Candidate import remains available regardless of review status. Rendering blocks
unapproved guidance, unknown applicability, version mismatch and selections whose
same-SDK supported version sets have no shared version. Readiness reports those
conditions with corrective actions. Multiple approved skills supporting the selected
version coexist; metadata does not certify semantic correctness. Bundles are whole
selection units, so unrelated company contexts belong in separate bundles.

Schema 2 skill entrypoints use the exact SKILL.md filename so references cannot
alias the native rendered entrypoint. Schema-2 import results include references
and guidance for review, while schema-1 results retain their existing shape.

## Delivery evidence

Scoped and integrated independent review approved. All six required local checks passed with 2022 tests and8 skips before archival-only metadata finalization. See docs/verification/documentation-workflow.md for exact scope and live qualification limits.
