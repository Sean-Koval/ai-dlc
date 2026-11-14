# ai-dlc provider contract v1

`manifest.json` and operation schemas are generated from `ai_dlc.contracts` Pydantic models.
`service-result.schema.json` is the envelope application services return to the CLI and
MCP; it is generated from `ai_dlc.contracts.ServiceResult` and explained in
`docs/architecture.md`.
They describe tracker, specs, SCM, deploy, knowledge, wiki and transcripts role capabilities.
`knowledge-note.schema.json` is the frontmatter of learnings and decision records,
generated from `ai_dlc.documentation.knowledge_notes.KnowledgeNote`; it is explained
in `docs/design/local-and-shared-knowledge.md`. Decision `checks:` entries use
flightdeck's `flightdeck.spec/v1` grammar and are validated for shape only.
`knowledge-record.schema.json` is the record format knowledge repositories pin
(`[format] version` in `knowledge.toml`), generated from
`ai_dlc.documentation.knowledge_records.KnowledgeRecord`. It will replace the
knowledge-note format ([ADR 0004](../docs/decisions/0004-knowledge-system-scope.md)).
Records are Open Knowledge Format v0.2 documents, and their field names follow OKF's.
The schema does not assert `format`. Consumers that use only the schema must stringify
YAML dates and enable a format checker. `ai-dlc knowledge check` is the authority.
`knowledge-record.versions.toml` publishes the schema's SHA-256 per format version and is
edited by hand. Any schema change bumps `FORMAT_VERSION` and adds a version there;
`scripts/check_generated.py` fails otherwise. A vendored copy is current only when its
canonical hash equals the `sha256` of the version it claims (KAN-504).
`capture-run.schema.json` is one capture batch run (KAN-458): what it pulled, filtered,
extracted and spent. The batch writes one per line of its run log, kept where it runs.
It is generated from `ai_dlc.documentation.knowledge_stats.CaptureRun`;
`ai-dlc knowledge stats --log` reads it and fails on a line that does not match.
A Source's `kind` is `transcript`, `chat`, `note` or `other`. Usage left `null`, or left
out on a failed Source, is unknown; stats leaves it out of the totals and counts it.
The scm role's optional `pull_requests` operation lists pull requests opened since a time,
with their first commit and first-push checks, for the same command.
`ai-dlc knowledge check DIR` (MCP `knowledge_check`) validates a records directory:
each header against the model, Open Knowledge Format v0.2 section 11, the format pin,
typed links that name records, duplicate sources and supersession (one accepted
successor, no cycles). It reads only `[check] roots` and `[repo]` from `knowledge.toml` and never
`README.md`. `derived_from` must name a source record, since raw payloads expire. When that
Source's payload expires (a resource under `inbox/` or `processed/`, or a transcript,
chat or meeting), the citing `sources` entry carries a verbatim `quote` (at most 500
characters), its `speaker`, and `at` (`HH:MM:SS` or a time) or a `permalink`. Jira,
Confluence and ADR sources stay re-fetchable, so a quote there is optional.
A Source record may list its `participants`.
`--base REF` also refuses in-place edits to decisions accepted at the merge base and
deletion of source records. Knowledge repositories run it through `.pre-commit-hooks.yaml` and
the reusable `.github/workflows/knowledge-check.yml`.
The knowledge role must answer `get {id}` (a record by id or alias, with its body)
and `search {type, scope, labels, status, text}` (headers only unless `text` is set;
`labels` match `tags` or `label`). Optional `list_changed {since}` names record files
changed since a revision. Optional `propose {records: [{path, text}], branch, title,
body}` checks the records, pushes a new branch and opens a draft pull request through
the `scm` role; it never writes the base branch. The `git` and `obsidian` providers
answer `get` and `search`; only `git` lists changes and proposes.

A draft record's `id` is a slug. After a merge, `ai-dlc knowledge number` gives it the
next number for its type, keeps the slug in `aliases` and rewrites links to it.
`ai-dlc knowledge index` then writes OKF `index.md` files and derives `superseded_by`.
Knowledge repositories run both through `.github/workflows/knowledge-merge.yml` on
push to main. Main stays protected: the workflow opens or updates one pull request
from `knowledge-number`, and a person merges it. Each run recomputes from the tip of
main, so numbers never collide. The knowledge repository needs these settings:

- A GitHub App installed on the repository with Contents and Pull requests write.
  Pass its installation token as the `token` secret. A pull request opened with
  `GITHUB_TOKEN` starts no checks.
- A ruleset on main that requires a pull request, an approving review and the
  `knowledge check` status check, with the App as the only bypass actor. Personal
  tokens and zero-approval rules are not supported.
- "Require branches to be up to date before merging" on. Otherwise two record pull
  requests that add the same slug can both merge, and numbering then stops.
- "Allow squash merging" on, since main requires linear history.

Automatic merging is off: spec section 10 allows no automatic merges for 1.0. The
`auto-merge: true` input turns on squash auto-merge for the numbering pull request
only; it also needs "Allow auto-merge". Use it only as an explicit exception that
the repository owner decides.

The `wiki` role is a read view of the records, and `ai-dlc knowledge render` is its only
writer. It must answer `upsert_page {key, title, body, properties, labels, parent,
expected_version}`, `get_page_by_key {key}` and `list_children {parent}`. Pages are found
by `key`; `parent` is another page's key, or null for the configured root. No operation
returns a page body. A page reports `version` and `rendered_version`, the version the last
upsert wrote; they differ after a hand edit. An upsert whose `expected_version` is not the
page's current version is refused. The `confluence-cloud` provider implements it.
The `transcripts` role must answer `list_since {since}` (an aware time; items with `id`,
`title`, `start`, `participants` and routing-only `emails`) and `fetch {id}` (the same plus
`segments: [{speaker, at, text}]`, `at` as `HH:MM:SS`). A transcript the caller cannot
read is unavailable, not an error. The `zoom` and `google-meet` providers implement it;
`ai-dlc knowledge pull-transcripts` is its caller.
The keys a knowledge repository's `knowledge.toml` may carry are `[format] version`
(required), `[repo] boundary, project, deny_list` (a customer repository),
`[check] roots`, `[wiki] site, source, project`, and `[transcripts] owner`
(required to pull transcripts), `scope`, `internal` and `[[transcripts.customers]] project, titles,
participants, repo_env`. A customer transcript lands in the customer's own repository,
whose Source records carry `boundary: customer` and the optional record field `project`.
That repository must declare `[repo] boundary = "customer"` and the same `project`.
Completion is a service operation: callers must use `WorkService.finish`.
The public `Registry.invoke` refuses terminal tracker transitions and the optional
terminal planning reconciliation operation `reconcile_closed`.

Executable providers consume one JSON object on stdin and return one JSON object on
stdout. The request envelope contains `schema_version: 1`, `operation`, `payload`, and
`operation_id` (null for reads). Diagnostics belong on stderr; nonzero exit is failure.
Tracker and knowledge mutation payloads include their stable operation ID.
The optional SCM `pull_request_create` payload is `{title, body, base, head, draft}`
(`draft` defaults to false) and returns `{url, number}`. WorkService journals its creation identity locally; a
pending or uncertain creation requires reconciliation instead of a second create.
A durably succeeded result is reused if linking the work record was interrupted. Executables have a configured
`timeout` (30 seconds by default). Invalid output fails response validation.

An executable provider configuration uses `kind = "executable"`, an absolute `command`,
and its SHA-256 `sha256`. Optional `skills` entries each contain `path` and `sha256`.
The command is checked before loading and again before each execution. A script digest
covers that script, not its interpreter or arbitrary imports; use a self-contained
executable or separately controlled runtime. This is an integrity boundary, not a sandbox.

Python entry point providers use `kind = "python"`, `distribution`, and `entry_point`
(group `ai_dlc.providers`). They require `dependency_lock` and `dependency_lock_sha256`,
`distribution_files` containing every installed distribution file digest except generated
bytecode and RECORD, and `dependency_distributions` keyed by normalized package name,
each containing `version` and a complete `files` digest map. The transitive metadata
closure, including optional dependencies, is verified before entry point import. Missing
optional distributions fail closed. Lock verification alone does not verify dependencies.
Providers are trusted code in the current Python environment, not an isolation mechanism.
Python calls have a bounded caller deadline; a timed-out daemon worker may continue,
so mutation outcomes remain uncertain until reconciled with the remote provider.

Bundled adapters use the installed ai-dlc 0.4.0 release identity. GitHub Issues is invoked
through the installed Python module (the `ai-dlc-github-issues` console entry is also
provided) and wraps authenticated `gh`. GitHub Issues without Projects reports unsupported in_progress while
work start creates/reuses its branch and reads the issue. With a configured Project,
its explicitly mapped in-progress option represents planning while the issue stays open.

Capability discovery is opt-in. Executable/Python definitions declare
`operations = ["capabilities"]`; registered providers use
`Registry.register(id, provider, operations=["capabilities"])`. Built-in declarations
are owned by the registry. The operation accepts an empty payload and requires
this strict response shape (booleans are not coerced from strings or numbers):

```json
{"schema":1,"lifecycle":{"in_progress":false,"closed":true},"optional_operations":[]}
```

Only absence of a declaration selects the legacy unverified transition path.
Declared transport or response errors never trigger fallback. Adding configuration
metadata to a retained external binding is subject to the existing fingerprint
and explicit-rebind rules.

Optional `update` accepts `{reference, operation_id, title, body, labels}` and returns
an Item. Omitted fields stay as they are, and `labels` replaces the whole set. It never
changes status. `create` accepts optional `labels`. A provider that writes labels lists
`update` in `optional_operations`; the tracker service refuses labels otherwise.
Optional `query` accepts `{text, labels, state, limit}` and returns `{items}`; it is
read-only. Optional `comment` accepts `{reference, body, operation_id}` and returns
`{id, url}`; the body is plain text. `jira-cloud` implements all four.

Optional `prepare` and `reconcile_closed` accept `{reference, operation_id}` and
return an Item. Providers declare them in capability `optional_operations`;
service dispatch is provider independent. Publish journals prepare after saving the
created or recovered issue reference, and retries reconcile even a previously
successful preparation. Prepare may establish nonterminal planning membership; it
must never perform terminal planning updates. `reconcile_closed` is accessible only
through finish's internal path after fresh gates and a successful terminal read.
It reconciles associated planning for an already completed item without reopening
or reclosing it. Finish rereads/reconciles this opt-in outcome even when its journal
previously succeeded. Failure raises visibly and leaves the reconciliation journal
uncertain; no completed result is returned until the selected outcome is confirmed.
Start also reconciles declared-capability transitions on retry rather than returning
a cached successful Item; adapters must respect stable operation IDs and revalidate
remote state. Undeclared legacy adapters retain their prior retry behavior.
GitHub implements prepare as membership only, preserving concurrent status changes.
Its close transition verifies board Done before native issue close and verifies
both afterward. These are separate remote writes, with no atomicity guarantee.

Create correlation is a stable repository/work hash stored in the remote issue body.
The SQLite journal detects payload conflicts and tracks pending, uncertain, succeeded.
After an uncertain create, search must reconcile an existing item; an empty search does
not authorize another create. Duplicate correlations fail. Cross-computer search is
subject to remote indexing and concurrent requests; exactly-once creation is not claimed.

GitHub completion requires a merged PR in the configured repository/target branch and
an authenticated successful push workflow run at its merge SHA. The downloaded receipt
is compared with `ai-dlc.toml` and `.mise.toml` fetched at that SHA. Local receipt paths
are never accepted. Checks must be nonempty, exact, successful, and have finite timings.
Optional deployment evidence uses a successful configured GitHub workflow and a matching
GitHub deployment environment, SHA, and successful status linked to that run.

Work start validates branch names and refuses switching branches with dirty work; it
never resets an existing branch. Provider configuration/account/workspace fingerprints
are persisted with work and drift blocks further operations until explicit rebind review.
PR merge and trusted CI are mandatory finish gates even if configuration supplies an
empty finish list.

OpenSpec remains the specification system. The adapter requires the current work's
archive, native proposal/tasks, finished tasks, and successful strict OpenSpec validation.
Completion additionally requires local HEAD to equal the authenticated merge SHA and
all OpenSpec files to be clean, tracked, and free of ignored/untracked files or symlinks.
It discovers installed CLI flags and runs native archived validation when available.
