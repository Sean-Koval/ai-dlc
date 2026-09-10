# Prepare and validate evidence-backed semantic document reviews

## Decisions

Use existing Python application services for shared CLI/MCP behavior. OpenSpec owns proposal, design, behavioral specification and tasks. Repository docs own durable explanations; Obsidian owns private continuity. Existing harnesses perform semantic reasoning. Source citations are evidence, not automatic authority or permission to fetch.

## Scope and verification

- DE-01: Bounded harness review. Verify through the linked scenario and observable negative cases.
- DE-02: Grounded findings. Verify through the linked scenario and observable negative cases.
- DE-03: Reviewed consolidation. Verify through the linked scenario and observable negative cases.

Preserve authored content and filesystem boundaries. No automatic deletion, remote publication or freshness certification. Required checks and independent review precede integration. Live qualification is distinct from fixtures.

## Review interchange schema (version 1)

Preparation accepts 1–32 unique catalog document paths, a Git commit base and a
positive integer body budget at most 1 MiB. It resolves the commit, enumerates Git
paths (including untracked nonignored paths), and expands only the selected
catalog mappings. It reads whole UTF-8 regular files only when they fit the
remaining body budget; omitted bodies are never citation evidence. Documents are
prioritized before sources. Files beyond budget, missing paths, unsafe files and
binary content have explicit omissions. Nonselected catalog documents are listed
as unreviewed candidates without reading their bodies. No links are fetched.

Packets contain schema, base, selected, max_bytes, catalog_digest, documents,
evidence, omitted, unreviewed, constraints, rubric and snapshot. Each included
body has path, content, SHA-256 digest and inclusive start_line/end_line. Empty
files have end_line zero. Snapshot hashes all packet fields except snapshot.
Validation reconstructs the packet from current local bytes and mappings and
requires exact equality, preventing forged body/hash claims. Omitted oversized
bodies are not read or hashed and have no freshness or review claim.

Review JSON contains schema=1, packet_snapshot, reviewed (unique selected paths),
unreviewed (the remaining selected paths), and findings. Reviewed and unreviewed
must partition selection. An omitted document must remain unreviewed. Each
finding contains category, target, supporting (nonempty citation list), uncertainty
(nonempty text), suggested_disposition, and rationale (nonempty text). Categories
are contradiction, unsupported-claim, obsolete-instruction, unnecessary-repetition,
missing-explanation, vague-prose and useful-repetition. Dispositions are revise,
consolidate, retain and investigate; useful-repetition requires retain. Citations
contain path, start_line, end_line and quote: integer inclusive line bounds and
an exact nonempty complete passage (joining the specified lines with newlines).
Target must belong to a reviewed selected document; supporting paths must be
included evidence or selected documents. Every finding needs real nonempty
supporting evidence. Unknown/malformed scope, schema and citations are rejected.

Validation reports valid/errors, reviewed/unreviewed, omitted, and the limitation
that citation grounding does not establish semantic truth or repository-wide
accuracy. Harness reviewers judge facts and propose edits; services never edit,
delete, claim freshness beyond included bytes, or approve consolidation. The
rubric preserves unique information, rationale and useful audience summaries.

## Delivery evidence

Scoped and integrated independent review approved. All six required local checks passed with 2022 tests and8 skips before archival-only metadata finalization. See docs/verification/documentation-workflow.md for exact scope and live qualification limits.
