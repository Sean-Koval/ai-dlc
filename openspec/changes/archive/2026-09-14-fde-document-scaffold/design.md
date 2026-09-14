## Decisions

The repository owns a configured `project.fde.docs_dir` beneath `docs/` (default
`docs/fde_engagements`). The CLI accepts a local override. Slugs use lowercase
letters, digits, underscores and hyphens; paths and symlinks cannot escape docs.
Existing engagements are never overwritten. Dry run returns every planned file
and exact content without creating directories. Output explicitly says remote
publication is unavailable; space/parent options store only user-supplied target
hints on the charter. No page IDs or successful publication receipts are invented.

Stage folders follow #50's underscore convention. Stage YAML frontmatter owns
`status`, `exit_criteria_met` and `exit_evidence`; the charter dashboard links each
stage rather than duplicating changing state. Initial states are ACTIVE, GATED,
GATED, PLANNED, PLANNED, PLANNED, PLANNED. A true exit flag requires nonempty
review evidence; activation or completion of a downstream stage requires every
earlier stage exit flag and evidence. `fde check` reads the eight explicit pages,
never scans linked files or private vaults. Metadata edits are ordinary Git edits;
validation catches manual bypasses, but is not a remote access-control claim.

Generated AGENTS.md contains the engagement rule and CLAUDE.md references it.
Other harnesses must explicitly load that same rule through their supported
project guidance mechanism; native harness qualification is not inferred.

The available local FDE-Kit stage overview confirms stage meanings and backward
iteration. All template technology examples stay generic instead of binding
company accounts, product lines, deployment platforms or proprietary SDKs.
