# Local and shared knowledge relationship

Know where private notes, records and wiki pages live, and which one is the
source of truth when they disagree.

Status: git canonical per [ADR 0004](../decisions/0004-knowledge-system-scope.md),
November 12, 2026; vault capture per ADR 0003.
Parent: [provider toolsets PRD](provider-toolsets-prd.md).

## Ownership and movement

| Material | Home | How it reaches others |
| --- | --- | --- |
| Journal, daily notes, captures and personal learnings | Local Obsidian vault | Never automatically; a capture becomes a record only by a reviewed pull request |
| Decisions, conventions, lessons, questions and sources | A git knowledge repository | Merged records; `knowledge render` shows them in the wiki |
| The team wiki | Confluence Cloud | A rendered, read-only view of the records |

Git is canonical. The wiki is a rendered view, never a source. Only
`ai-dlc knowledge render` writes it, through the `wiki` role. Render never reads
a page body, so a hand edit on a rendered page is overwritten by the next render.
Change the record in git instead.

Private note inclusion is never inferred from a link, tag or neighboring file.

## Second brain

[ADR 0003](../decisions/0003-second-brain-capture-and-publish.md) added capture
to the vault. Its reviewed publish of a note and the `kb-publish` skill are
retired (KAN-430).

| Skill | Writes | Never |
| --- | --- | --- |
| `daily-note` | `Daily/YYYY-MM-DD.md`, a read-only lane summary, then what moved | Touches a ticket or the wiki |
| `capture` | `Meetings/` or `Threads/` notes: decisions, actions, knowledge, questions | Stores a raw transcript or files a ticket |

Capture notes add `origin` (`work` or `home`), `lane` (an epic key) and
`source: {file | room, sha256}` to the frontmatter below.
`ai-dlc knowledge captured FILE --vault PATH` exits 1 for a digest already in the
vault, so the same transcript is never captured twice.

## Knowledge repository

The `git` provider serves `knowledge` from a record repository; `contracts/README.md`
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

## Rendering the wiki

Each knowledge repository declares its one wiki site in `knowledge.toml`. There
is no default. Render refuses, before any request, when the `wiki` provider is
bound to another site. This keeps work records off a home site and the reverse.

```toml
[wiki]
site = "example.atlassian.net"
source = "https://github.com/<owner>/<repo>/blob/main/"  # banner link prefix
```

```toml
[roles]
knowledge = "team-knowledge"
wiki = "team-wiki"

[providers.team-wiki]
kind = "confluence-cloud"
site_url = "https://example.atlassian.net"
cloud_id = "<cloud UUID>"
space = "ENG"
parent_id = "<root page id>"
auth_mode = "oauth_bearer"        # or personal_scoped_token_basic with email_env
token_env = "CONFLUENCE_TOKEN"    # a variable name, never a value
```

```sh
ai-dlc knowledge render --changed-since <sha> --dry-run   # every planned upsert
ai-dlc knowledge render --changed-since <sha>
```

Render upserts one page per changed record, keyed by its id, and one index page
per scope. Frontmatter becomes page properties and
labels; a status change drops the old status label. Every page opens with a
do-not-edit banner that links its source file. A deleted record's page is marked
removed.

A page whose content hash and version match the last render is skipped, so a
rerun writes nothing. A page edited by hand is
restored. An upsert names the version it read; a concurrent change is refused.

Customer records render only to their project's wiki (`[wiki] project`).
The Confluence provider follows the `jira-cloud` credential rules:
a scoped token through the Atlassian gateway, and fixed error messages.
Knowledge repositories run render on merge with the reusable
`.github/workflows/knowledge-render.yml`.

## Qualification examples

- Reading one selected page does not create any vault files or bulk read its space.
- A dry run lists every planned upsert and writes nothing.
- Rendering twice writes nothing the second time; a hand edit is restored.

Fixture tests use a fake Confluence. Rendering to a live Confluence site still
needs its own qualification.

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

Every learning is a `lesson` record in the knowledge-record format that decision
records share. The JSON Schema is
[`contracts/knowledge-record.schema.json`](https://github.com/Sean-Koval/ai-dlc/blob/main/contracts/knowledge-record.schema.json),
generated from `ai_dlc.documentation.knowledge_records`:

```markdown
---
id: learning-2026-10-20-fix-receipts        # slug; LES-NNNN is assigned at merge
type: lesson
scope: personal                             # personal | project | team
status: open                                # open | codified
date: 2026-10-20
owner: github-login
sources:                                    # at least one
  - resource: https://github.com/owner/project/pull/123
    hash: git:<merge commit SHA>
links:
  - {type: belongs_to, target: fix-receipts}
label: internal                             # internal | confidential
valid_from: 2026-10-20
stale_after: '2027-01-18T00:00:00Z'         # valid_from + 90 days by default
confidence: medium                          # low | medium | high
author: human:github-login                  # or agent:<client>@<plugin digest>
---
## What happened
A concise observation, including its limits.

```

`kind:` frontmatter is read until the release after 1.0;
`ai-dlc knowledge migrate --write` rewrites it ([ADR 0005](../decisions/0005-migrate-knowledge-notes-to-records.md)).

After the normal completion gates pass, `ai-dlc work finish <id> --learning FILE`
stores the file through the existing knowledge provider's idempotent `note`
operation. MCP `work_finish` accepts the equivalent `learning` text; its existing
`handoff` text remains a separate append operation.

A body without frontmatter gets frontmatter generated from the work record. A
body with frontmatter is validated and only missing fields are added. Supplied
values, including a wider `scope`, are never changed, and ai-dlc never widens
`scope` itself.

Generated fields are those in the example. Supplied `kind:` frontmatter is
migrated. `sources` holds the merged PR URL, the merge commit the finish
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
exits 1 when any frontmatter fails its schema. Knowledge notes are listed as
`deprecated`. Notes without frontmatter, or with the older
`work/repository/pr/tags` frontmatter, are listed as legacy and do not fail.

`work start` and the session-start hook recall at most five matching learning
paths and first content lines. Recall uses title words and the specification
change name; the session hook selects the record bound to the current branch.
It reads only `learnings/`, never writes, and stays quiet when the vault is
missing or has no matches.

For notes with frontmatter, recall skips those whose `valid_to` has passed. It
also returns `type`, `author`, `stale_after` and `stale` (`stale_after` has
passed), or `kind` and `review_by` for a knowledge note. The session hook
prefixes stale notes with `(stale)`. Notes without frontmatter recall as before. Read relevant recalled notes as personal context
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
