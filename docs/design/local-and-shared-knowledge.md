# Local and shared knowledge relationship

Know where private notes, team pages and learnings live, and how an agent
reads, recalls and publishes each without mixing them.

Status: second brain built by ADR 0003, November 8, 2026; the rest proposed September 7, 2026.
Parent: [provider toolsets PRD](provider-toolsets-prd.md).

## Ownership and movement

| Material | Home | How it is used elsewhere |
| --- | --- | --- |
| Journal, scratch notes, daily work log and personal learnings | Local Obsidian vault | Selected local context for personal assistant agents; no automatic publication |
| Existing product knowledge, team guides and shared documents | Confluence Cloud | Relevant page links and on-demand reads; optional deliberate local summaries |
| A new document intended for teammates | Explicit local shared-draft location, initially repository `docs/` | Reviewed publication to a selected Confluence destination |

Confluence is authoritative for existing team pages. A local summary is a dated
derivative, not a synchronized replacement. For an explicitly enrolled local
publication source, retain its page binding and expected version. A teammate
edit requires reconciliation instead of overwriting or silently choosing a winner.

For example, link a team guide in a daily note for an agent to read. An
optional summary records source URL, version and retrieval date, apart from
personal observations.

Later, draft a team guide from selected learnings in a shared-doc location. Review the entire outgoing document and destination before publishing.
Private note inclusion is never inferred from a link, tag or neighboring file.

## Second brain

[ADR 0003](../decisions/0003-second-brain-capture-and-publish.md) builds the
reviewed publication this page proposed. Daily notes, meeting notes and pasted
threads are written in the vault. Confluence holds the durable pages.

| Skill | Writes | Never |
| --- | --- | --- |
| `daily-note` | `Daily/YYYY-MM-DD.md`, a read-only lane summary, then what moved | Touches a ticket |
| `capture` | `Meetings/` or `Threads/` notes: decisions, actions, knowledge, questions | Stores a raw transcript or files a ticket |
| `kb-publish` | One confirmed page, then `publish.page_id` and `version` in the note | Publishes a daily note |

Capture notes add `origin` (`work` or `home`), `lane` (an epic key) and
`source: {file | room, sha256}` to the frontmatter below.
`ai-dlc knowledge captured FILE --vault PATH` exits 1 for a digest already in the
vault, so the same transcript is never captured twice.

Each vault declares `origin`, `site`, `space` and an optional `parent` in
`<vault>/.ai-dlc/publish.toml`. There is no default.
`ai-dlc knowledge publish-plan NOTE --vault PATH` returns the exact page payload or
refuses. It refuses a note whose origin or site differs from the vault's, and a
bound page whose current version (`--remote-version`) is not the recorded one.

The agent then publishes through the client's existing Atlassian connection, after
the user confirms. `ai-dlc knowledge publish-record` writes the binding back. ai-dlc
itself never calls Confluence. The provider contract's optional knowledge
operation `publish` describes the same payload for a future adapter.

## Knowledge repository

The `git` provider serves `knowledge` from a record repository
([ADR 0004](../decisions/0004-knowledge-system-scope.md)); `contracts/README.md`
lists operations.

```toml
[providers.team-knowledge]   # or set KNOWLEDGE_REPO to a clone or URL
kind = "git"
location = "https://github.com/<owner>/<repo>.git"
repository = "<owner>/<repo>"  # where draft pull requests open, through scm
```

```sh
ai-dlc knowledge records template decision                      # --list names the types
ai-dlc knowledge records get DEC-0001
ai-dlc knowledge records search --type decision --label harness   # --text reads bodies
ai-dlc knowledge records changed <revision>
ai-dlc knowledge records captured transcript.vtt                  # exit 1 when seen
ai-dlc knowledge records propose draft.md --path decisions/x.md --branch k/x --title T
```

## Qualification examples

- Reading one selected page does not create any vault files or bulk read its space.
- Saving a requested summary records provenance and keeps personal annotations
  distinct. Refresh does not erase them or misrepresent inaccessible content as fresh.
- Drafting from private notes produces a separate candidate shared document; only
  its reviewed body is published, without linked daily notes or vault attachments.
- Editing a team page after a publication preview produces a conflict in any
  workflow claiming ai-dlc's deterministic publication guarantee.

Fixture tests cover the guard and the write-back. Publishing through a live
Atlassian connection still needs its own qualification.

## Project navigation

The [project documentation model](project-documentation.md) defines canonical navigation, optional catalog diagnostics and local Obsidian portals. It preserves OpenSpec ownership and does not introduce Confluence publication or synchronization.


Explicit `link-vault --mode mount` can additionally expose a stable Git checkout's
existing `docs/` and `openspec/` as sibling folders beneath `Projects/<name>/`.
Portal linking remains the default. Mount identities are ignored machine-local
bindings; existing matching links need explicit adoption before ai-dlc owns the
binding.

Setup refuses overlapping targets and nested traversal, and preserves partial
output for inspection. This does not broaden the private knowledge API's
filesystem boundary. See the [portable documentation guide](https://github.com/Sean-Koval/ai-dlc/blob/main/project-templates/project/docs/documentation-guide.md#opt-in-to-native-project-folders)
for preview/apply and recovery. Filesystem verification alone does not qualify
Obsidian indexing, file watching or synchronization.

Harnesses reach repository documents, including those visible through a mount,
with `docs search` and `docs read`. These operations are scoped to
the selected repository's `docs/`, `openspec/` and per-call declared Markdown, and
return canonical repository paths for ordinary Git edits. They never read vault
notes; the knowledge tools remain the only private-note interface. See the
[documentation guide](https://github.com/Sean-Koval/ai-dlc/blob/main/project-templates/project/docs/documentation-guide.md#search-and-read-project-documents).

`project workspace-check` explains why a mounted workspace does not behave as
expected without changing it. It reports the PATH-selected executable, owned shell
activation, the checkout the shared bootstrap alias runs, each machine-local mount
binding and link reachability as separate results. Links to repository files outside `docs/` and `openspec/` remain
repository-only; the diagnostic never widens mounts or the private-note boundary,
and it cannot qualify Obsidian. See the
[documentation guide](https://github.com/Sean-Koval/ai-dlc/blob/main/project-templates/project/docs/documentation-guide.md#diagnose-the-local-workspace).

## Session learnings

An agent may select one short lesson for the knowledge provider at
`learnings/<YYYY-MM-DD>-<work-id>.md`. The tool stores the supplied text with
provenance frontmatter; it does not summarize logs or publish notes.

Every note carries the knowledge-note frontmatter that learnings and decision
records share. The JSON Schema is
[`contracts/knowledge-note.schema.json`](https://github.com/Sean-Koval/ai-dlc/blob/main/contracts/knowledge-note.schema.json),
generated from `ai_dlc.documentation.knowledge_notes`:

```markdown
---
id: learning/2026-10-20-fix-receipts       # kind/<date>-<work-id>
kind: learning                              # learning | decision | runbook | note
scope: personal                             # personal | project | team
label: internal                             # internal | confidential (free text is recorded)
sources:                                    # at least one for a learning
  - uri: https://github.com/owner/project/pull/123
    hash: git:<merge commit SHA>
author: human:github-login                  # or agent:<client>@<plugin digest>
confidence: medium                          # low | medium | high
valid_from: 2026-10-20
valid_to: null
review_by: 2027-01-18                       # valid_from + 90 days by default
supersedes: []
work: fix-receipts                          # kept for older learnings
repository: owner/project
---
## What happened
A concise observation, including its limits.

## What to do differently
A concrete practice to try next time.

## Links
- Link the authoritative work, specification, or evidence.
```

Decision records add `status` and an optional `checks:` block (see
[project documentation](project-documentation.md)); `status` and `checks` are
refused on other kinds. Keys outside the schema are kept, so neighbouring tools
can extend notes additively.

After the normal completion gates pass, `ai-dlc work finish <id> --learning FILE`
stores the file through the existing knowledge provider's idempotent `note`
operation. MCP `work_finish` accepts the equivalent `learning` text; its existing
`handoff` text remains a separate append operation.

A body without frontmatter gets frontmatter generated from the work record. A
body with frontmatter is validated and only missing fields are added. Supplied
values, including a wider `scope`, are never changed, and ai-dlc never widens
`scope` itself.

Generated fields are `id`, `kind`, `scope: personal`, `label: internal`,
`sources`, `author`, `confidence: medium`, `valid_from` (UTC date),
`valid_to: null`, `review_by` (+90 days), `supersedes`, `work` and
`repository`. `sources` holds the merged PR URL, the merge commit the finish
gate verified, and the CI run URL.

`author` is `AI_DLC_AUTHOR` when set; the workflow plugin's guide skill tells
agents to set it to `agent:<client>@<plugin content digest>`. Otherwise it is
`human:<gh login>` for the CLI and `agent:unknown` for MCP, never inferred from
another session. The only personal data is the GitHub login. Invalid
frontmatter or a note over 64 KB leaves the learning pending with the reason.

The first attempt records the UTC date, note path and final note locally. Retries
on later days therefore write byte-identical content under the same operation
identity. Reusing the operation with different input text reports a conflict;
it never overwrites the stored note. A failed or unavailable vault leaves a
`learning_pending` result without reversing tracker completion. Finish without a
learning completes and returns a one-line reminder.

An agent may instead call
`ai-dlc knowledge note learnings/<date>-<work-id>.md --body FILE --operation-id ID --vault PATH`
using the configured vault and a stable operation ID.
`ai-dlc knowledge check --vault PATH` reads the notes under `learnings/` and
exits 1 when any frontmatter fails the schema. Notes without frontmatter, or
with the older `work/repository/pr/tags` frontmatter, are listed as legacy and
do not fail.

`work start` and the session-start hook recall at most five matching learning
paths and first content lines. Recall uses title words and the specification
change name; the session hook selects the record bound to the current branch.
It reads only `learnings/`, never writes, and stays quiet when the vault is
missing or has no matches.

For notes with frontmatter, recall skips those whose `valid_to` has passed. It
also returns `kind`, `author`, `review_by` and `stale` (`review_by` has
passed); the session hook prefixes stale notes with `(stale)`. Notes without
frontmatter recall as before. Read relevant recalled notes as personal context
and reconcile them against current repository authority.

The stop hook skips payloads without a usable session ID. It recognizes direct
results, shell stdout JSON, and MCP text or structured results. It records
friction counts and a hash of the preceding command beneath
`.ai-dlc/local/session/`. It counts hook denials, repeated commands, and failed
or blocked work results when a tool response is provided. At three events it
suggests a learning note.

Tool-response coverage depends on the harness; this does not install a new
post-tool hook or claim to observe every failure. Counters and command hashes
are local and are never transmitted or copied into learning notes. This is a
reminder, not a completion gate.
