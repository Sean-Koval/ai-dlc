# Documentation and knowledge workflow verification

Status: implementation candidate, September 10, 2026. GitHub issues29–34 track
delivery; no issue is complete merely because the implementation is locally tested.

## Scope

The change reconciles existing documentation, adds content-bound impact review,
prepares bounded evidence for existing harnesses, validates citations, creates
additive private workspaces, and extends pinned SDK skills with references.
Formal scenarios live in the six named OpenSpec changes. The
[historical baseline](documentation-baseline.json) owns the initial inventory and
its dated dispositions; later changes do not silently refresh that record.

## Required local checks

All six manifest checks passed: generated, format, lint, types, test and
documentation. The full suite passed 2,022 tests with 8 skips in 463.73 seconds.
The receipt describes the reviewed working tree based on 74b90c6 (dirty=true),
not a merged-revision qualification. Source remained unchanged during the run.
Scoped integration earlier passed 375 tests. All 30 strict OpenSpec validations
passed before archive finalization. The final source review approved the branch.

Only OpenSpec archival, artifact-link and verification metadata are finalized
after that full run; the corresponding structural and evidence checks are rerun.
No full-test or live-CI result is inferred from an archive operation.

## Qualification boundaries

Original fictional SDK examples exercise the workflow without importing company
data. Citation validation establishes grounding and included-source freshness, not
semantic correctness or company-wide accuracy. SDK metadata describes reviewed
selection; it is not a guarantee of policy correctness. The five shipping client
CI targets remain distinct from actual native client walkthroughs.

Company SDK examples and the custom Confluence MCP remain unavailable. Antigravity
is not installed on this machine, so its actual client walkthrough remains pending;
rendering tests do not establish that qualification. Obsidian 1.13.7 is installed;
native workspace inspection was attempted twice but the UI automation interface timed out before returning app state, so native Obsidian qualification remains pending. No publication or mirroring is added.

## Scoped verification

Independent reviewers approved lifecycle reconciliation, impact/disposition services,
semantic review preparation/validation, private workspace creation, and schema-2
SDK guidance. Review found and repaired self-referential evidence hashes under
broad source mappings, and incomplete retained-path reporting on fsync failure.
Both defects have failing-then-passing regressions and scoped reviewer approval.

The fictional brownfield walkthrough uses three selected documents, a retry loop
and a formal timeout requirement. A fresh harness produced four findings: retry
count conflict, redundant reference, useful onboarding summary, and code/spec
timeout disagreement. All citations and current-source checks passed. This is a
bounded judgment exercise, not a statistical calibration or company qualification.
An earlier unassisted case had an ambiguous how-to audience; it is not used to
claim a measured improvement.

Claude Code 2.1.263 read the native rendered document-review skill and original
project files in restricted read-only mode. It identified the same distinctions
and refused to call an unbound narrative a completed review. The first structured
attempt revealed underspecified allowed enum values in the skill; validation
rejected them. The skill now declares the exact allowed categories/dispositions;
its fresh structured rerun is recorded separately below.

AI-DLC now opts into the documentation manifest check. Historical exemptions and
current dispositions are explicit reviewed JSON under `.ai-dlc/documentation/`.
Those records bind source bytes and the selected base; they do not prove the
reviewer's semantic judgment. Fresh project adoption does not enable this gate
automatically. CI may independently pin the comparison using `docs-gate --base`.

The fresh native Claude structured rerun passed current-source/citation validation:
three documents reviewed, four findings, no omitted bodies. No source edits or
external reads were enabled. The earlier invalid response and this correction are
retained in local run evidence; they are not represented as a statistical quality
score. Antigravity remains unavailable and Obsidian UI access remains blocked as
described above.

GitHub CI fetches comparison history and supplies `AI_DLC_DOCS_BASE` from the PR
base or push predecessor. The CLI pins that independently supplied revision, so
changing only the evidence's base cannot bypass the intended CI comparison.

The brownfield evolution then changed the fictional code/documents deliberately:
a probe failed for the 10-second implementation and passed after the15-second
spec-aligned repair; the duplicate reference became a canonical link and onboarding
kept its rationale. The previous review was rejected as stale; new dispositions
validated, and repeat workspace setup created no files or replaced annotations.

The six implementation changes have been archived with canonical purpose text and
work references updated. Their GitHub issues remain open until integration and
AI-DLC completion gates pass. Archival does not certify the pending native or
company-specific walkthroughs.
