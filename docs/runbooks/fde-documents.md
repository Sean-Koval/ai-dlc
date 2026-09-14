# FDE engagement documents

`ai-dlc fde scaffold` creates a local engagement charter and seven stage landing
pages. It implements the local portion of issue #50. Confluence conversion,
publication, synchronization, remote hierarchy registration and native harness
qualification remain unavailable pending review of the referenced production
ai-docs implementation. Destination hints do not create or bind remote pages.

## Create an engagement

Run from the repository root (or supply `--root PATH`):

```sh
ai-dlc fde scaffold customer_delivery --title "Customer delivery" --dry-run
ai-dlc fde scaffold customer_delivery --title "Customer delivery"
ai-dlc fde check customer_delivery
```

Dry run returns exact prospective paths and content without writing anything.
The normal command writes the engagement and returns its paths and contents.
Existing destinations refuse even in dry run: rerunning cannot overwrite authored
work. If a filesystem error interrupts creation, inspect the partial engagement;
the command retains it for recovery and does not overwrite it on retry.

The default directory is `docs/fde_engagements`. Configure a dedicated repository
docs subdirectory in `ai-dlc.toml`:

```toml
[project.fde]
docs_dir = "docs/company/engagements"
```

Both commands accept `--docs-dir docs/company/engagements` as a per-call override.
The directory must be below `docs/`; traversal, absolute paths and symlinks are
refused. Local vault paths and machine-specific account choices do not belong in
this setting. The command creates files locally; it does not stage a Git commit.

Optional `--space TEAM --parent 123` values preserve a chosen Confluence space
and engagement-parent ID as charter frontmatter. Supply both or neither. The
values are non-secret hints supplied explicitly by the caller, not verified
access or publication receipts. Stage pages intentionally have no invented
remote page IDs or parent IDs. Company-specific taxonomy belongs in the actual
project's reviewed documents, not AI-DLC's portable defaults.

## Work through the stages

Each engagement contains `_index.md`, `AGENTS.md`, `CLAUDE.md` and seven folders:

| Folder | Initial status | Focus |
| --- | --- | --- |
| `01_discover` | ACTIVE | Customer context, stakeholders, workflows and constraints |
| `02_frame` | GATED | Problem, success measures and scope |
| `03_design` | GATED | Architecture, interfaces, experience and risks |
| `04_build` | PLANNED | Implementation and verification |
| `05_deploy` | PLANNED | Deployment, monitoring and recovery |
| `06_enable` | PLANNED | User adoption and operator guidance |
| `07_expand` | PLANNED | Outcomes and further opportunities |

Every stage's `_index.md` is the local landing page and intended future parent
for that stage's child deliverables. Store deliverables beside that page. The
charter has sponsor and business-goal sections and a dashboard linking current
stage records. Stage frontmatter owns current state; the dashboard does not
maintain a second status copy.

After reviewing a stage's exit criteria, edit its frontmatter in Git:

```yaml
status: "ACTIVE"
exit_criteria_met: true
exit_evidence: "Review PR 12: approved discovery findings and stakeholder map"
```

Then change the next stage's `status` to `ACTIVE` and run `ai-dlc fde check SLUG`.
All earlier stages must have `exit_criteria_met: true` and nonempty review
evidence before a downstream stage becomes ACTIVE or records completed exits.
There is no separate DONE status: exit completion and lifecycle status describe
different facts. Check prints current stages and evidence, reports all available
findings and exits nonzero on invalid structure or gates. It reads only the eight
known landing pages, each at most 256000 bytes; it does not traverse deliverable
links. Invalid YAML (including duplicate fields), missing pages and symlinks refuse
validation.

A review-evidence string records the team's assertion; AI-DLC does not prove that
a linked approval occurred or that prose exit criteria were satisfied. To make
this check a project gate, add the actual engagement command to that project's
required checks. It does not become a work-finish gate automatically. When new
evidence invalidates an earlier stage, reopen that exit and gate downstream
stages again before proceeding.

## Agent guidance and publication boundary

The engagement's `AGENTS.md` explains stage ownership, validation, supplied target
hints and private/shared boundaries. `CLAUDE.md` references it. Explicitly load the
same rule through another harness's supported project guidance mechanism; creating
files alone does not establish native harness behavior or qualification.

Only explicitly selected, reviewed team documents may be published through a
separately reviewed existing connection. Never scan or mirror private Obsidian
vaults, infer publication from tags, or follow private source links into outgoing
payloads. Relevant team pages can be read on request. A requested local summary
records the source URL, available version and retrieval date; explicit refresh
preserves personal annotations and reports inaccessible or stale sources honestly.

This scaffold has no XHTML dry-run, lint-conversion or sync command. `fde check`
checks local structure and metadata only. The existing
[publication proposal](../../openspec/changes/team-document-publication/proposal.md)
retains converter fidelity, selected-source preview/apply, conflict refusal,
uncertain-operation recovery and live qualification requirements. The production
source was not available in this checkout environment; a different converter or
an unverified Cloud adapter has not been substituted for its requested port.
