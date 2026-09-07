# GitHub Issues provider guidance

Use the selected GitHub Issues provider with its explicitly configured
repository. Preserve existing work bindings; changing a provider requires the
project’s explicit rebind workflow.

Issue operations do not replace project checks or finish gates.

Without a Project, GitHub Issues supports native open/closed state and reports
in_progress as unsupported. An optional `providers.<alias>.project` mapping uses
`id`, `status_field_id`, and `statuses = {open, in_progress, closed}` with three
explicit, distinct single-select option IDs. Invalid selected configuration fails;
it never silently falls back to issue-only behavior. `host` defaults to github.com.
Guided connections may pin non-secret `viewer_id`; writes verify that account.

Publish saves the issue reference before journaled `prepare` attaches it to the
Project. Prepare preserves existing planning status, including on retry; it does
not initialize status because attachment can race a teammate. Start applies the
mapped in-progress option only to an open issue and reads it back afterward.

Results expose native `issue_state`, `state_reason`, `node_id`, and selected
`project` metadata (`id`, `item_id`, `status_field_id`, `status_option_id`). The
normalized state is in_progress for an open issue with the mapped planning option.
Only native CLOSED with COMPLETED reason normalizes to closed; NOT_PLANNED is
cancelled, and other closed reasons are unknown. A board Done option alone never
establishes completion or authorizes reopening a terminal issue.

Finish evaluates its existing gates before terminal planning writes. It sets and
verifies board Done before closing the issue, then reads both states again. For an
already completed issue it uses gated `reconcile_closed`, even after a previously
successful journal result, to repair missing or changed planning status without
reclosing an issue reopened during reconciliation. The public generic provider
invocation blocks this operation like other terminal transitions.

Issue and Project writes are separate operations, not an atomic transaction.
Transport failures, mismatched responses or incomplete pagination fail visibly and
leave journaled mutations uncertain. Retry reconciles current membership/status;
read/find never attach or update. Hidden project content prevents proving absence
and therefore blocks membership mutations. Projects requires authorized read and
write access (`read:project`/`project` for applicable classic token authentication);
fixture checks do not establish live platform access or qualification.

API references: [Projects API](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects),
[gh issue view](https://cli.github.com/manual/gh_issue_view), and
[gh api](https://cli.github.com/manual/gh_api).
