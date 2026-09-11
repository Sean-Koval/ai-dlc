# Documentation and knowledge workflow verification

Status: implementation candidate, September 10, 2026. GitHub issues 29–34 track
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

OpenSpec archival, artifact-link and verification metadata were finalized after
that full run; their structural and evidence checks passed. The initial GitHub CI
run exposed one test isolation defect: the disposable-repository CLI test inherited
the real repository's comparison revision. The test now clears that environment
value before checking the default, then explicitly sets its invalid-base case.
The failure was reproduced locally with CI's environment; all 10 impact tests
passed after the correction. No full-test or live-CI success is inferred from
that focused rerun. [PR #35](https://github.com/Sean-Koval/ai-dlc/pull/35) owns the
current CI results.

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

That pin does not make a passing pull request check current. PR #44 passed against
`2b2bd65`; PR #43 then merged, and #44 merged without fresh checks. The run for
merge commit `a53dee4` compared against `059f1df` and failed with an unknown-target
error, although the merged tree matched the PR head. Replaying `docs-gate` on
`a53dee4` locally reproduced both outcomes. The gate now reports the base mismatch
with both commits, recording refuses a base the checkout lacks, and workflow
guidance requires updating and re-recording before merge. The replay and regression
tests do not qualify repository settings. PR #45 re-recorded evidence against
`a53dee4` and became the delivery PR for #40, so `work finish` verified a successful
merged revision. The `main` ruleset now requires up-to-date branches and the five
Verify jobs as separate checks; its first entry combined four job names into one
check that could never report and was corrected.

The brownfield evolution then changed the fictional code/documents deliberately:
a probe failed for the 10-second implementation and passed after the 15-second
spec-aligned repair; the duplicate reference became a canonical link and onboarding
kept its rationale. The previous review was rejected as stale; new dispositions
validated, and repeat workspace setup created no files or replaced annotations.

The six implementation changes have been archived with canonical purpose text and
work references updated. Their GitHub issues remain open until integration and
AI-DLC completion gates pass. Archival does not certify the pending native or
company-specific walkthroughs.

## Native directory mount qualification — September 11, 2026

A disposable, independently initialized Git checkout and separate local vault were
used with the native mount implementation from commit `3231636`. This exercised
Obsidian 1.13.7 on the current macOS host through the native UI:

- Mount preview/apply exposed `docs/` and `openspec/` beneath the same project.
- Native search for a term in the fixture returned 11 matches across architecture,
  ADR and OpenSpec bodies. Architecture showed two backlinks.
- A relative documentation-to-OpenSpec link opened the specification inside the
  vault, with its project breadcrumb and one backlink.
- An edit typed in Obsidian appeared in the repository's Git diff. An external
  repository edit refreshed in the already open Obsidian editor.
- Qualification markers were removed after checking exact baseline bytes; the
  fixture returned to a clean Git state. Existing personal vault content was not
  changed.

This qualifies those native behaviors on this host and fixture only. Company
repositories, the work-computer vault, Antigravity, other desktop platforms and
synchronization are unverified. Test fixtures remain distinct from this native
walkthrough. The new mode does not qualify portal links as in-vault document access.

## Harness organization qualification — September 11, 2026

A fresh harness received an outcome-level request to organize a disposable Parcel
repository, the shipped document-organize skill and the new CLI. No file-by-file
move list or baseline proposal was supplied. It used repository inventory and
three bounded review packets to inspect all nine initial Markdown documents, then
prepared a concrete proposal for coordinator review.

After review, it moved operational/reference documents into runbook/reference
folders and root/legacy history into an archive; consolidated overlapping
architecture text while preserving unique carrier rationale; repaired links; and
created a documentation map, catalog and archive index. Existing ADR and
architecture conventions were retained. Operational statements unsupported by
the intentionally small source snapshot were preserved with explicit uncertainty.
The OpenSpec document remained byte-identical. The complete working-tree artifact
contained 13 path entries, including three new navigation/catalog files.

The pre-edit review passed citation/current-source validation. Post-edit relative
Markdown links and diff whitespace passed; old moved-path references were absent.
Document checks reported only five unknown-review warnings; dates were not
manufactured. The fixture had no configured project runtime, so its required
manifest check was unavailable and is not claimed. Toolkit required checks and
CI qualify the toolkit independently.

The baseline harness could propose organization using general reasoning, but old
`docs-init` offered only five navigation scaffolds and old `docs-review` could not
prepare a packet without a catalog. This is evidence of a supported workflow, not
a measured semantic-quality improvement. Review corrected both an inference from
missing fixture code and an overly broad intermediate ADR move; this was a
reviewed iterative workflow, not a one-shot or unattended success. Native
Antigravity and company-project qualification remain pending.

## Scoped project-document access routing — September 11, 2026

Claude Code acted as the harness in a local session, using the project-document
access working tree based on `e23413d` against a disposable Git checkout and a
separate local vault:

- Mount setup exposed `docs/` and `openspec/` beneath `Projects/parcel/`.
- Starting from the mounted architecture note, `project docs-search` returned the
  architecture and OpenSpec matches with canonical repository paths, source scopes
  and line numbers, and reported complete coverage. A declared `README.md` joined
  the results for that call only.
- The mounted vault path as a read target, the undeclared root README and the
  vault directory as a repository root were refused.
- An in-process MCP server returned the same search result as the CLI.
- The harness edited the returned canonical path with its ordinary file tool. The
  change appeared in the repository's Git diff and through the mount, and a fresh
  read returned the new digest. No file was created in the vault, and private-note
  search found only the existing private note.

This exercises shared CLI/MCP service routing and ordinary repository edits on
this macOS host. It does not re-qualify native Obsidian behavior, an external MCP
client session, Antigravity, company repositories or other platforms. Automated
fixture tests remain distinct from this exercise.

## Workspace diagnostics qualification — September 11, 2026

Evidence for workspace diagnostics comes from three separate sources:

- **Automated fixtures.** `tests/test_workspace_diagnostics.py` covers missing,
  different and timed-out executables; configured, active, stale and unprovable
  shell activation without returning authored shell content; connected, changed and
  checkout-missing mounts beside an isolated malformed binding; unbound vault states;
  mounted, repository-only and missing links; CLI/MCP parity; and the preserved
  messy-project baseline. These tests do not qualify a live host.
- **Real host run.** On this macOS host, `project workspace-check` against the
  disposable routing fixture reported both mounts connected, its documentation link
  mounted, complete navigation coverage and the native client not assessed. It also
  reported the real PATH-selected `ai-dlc` as unverified while activation through
  the bootstrap alias was active: the installed toolkit predates the root
  `--version` option and lacks the new project commands. Installation and activation
  were therefore diagnosed separately, as intended.
- **Harness and native client evidence.** The messy-project organization exercise
  and the native Obsidian 1.13.7 walkthrough recorded above remain the observed
  harness and client evidence. `tests/fixtures/messy_project.py` preserves that
  baseline, and the [workspace qualification walkthrough](../runbooks/document-workspace-qualification.md)
  repeats both exercises. No new Obsidian session was run for this change.

Work-computer projects and skills, Antigravity, other desktop platforms and
synchronization remain unverified.
