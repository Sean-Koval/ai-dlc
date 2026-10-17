# Migration to v4

Inventory existing aliases, shell functions, PATH entries and installed ai-dlc/ai-dlc-cli binaries before selecting the Python entry point. Confirm both aliases resolve to the intended executable after installation. Remove obsolete Rust binaries only after migration fixtures prove supported command, configuration and work-record behavior. Keep a rollback copy until then.

Schema 4 separates portable project configuration from machine bindings. Review old provider selections and credentials; migrate secret values to environment variables. Select scm.repository explicitly. Machine-specific vault paths and account settings belong in machine configuration. Do not copy local journals as a substitute for remote state reconciliation.

For a personal profile such as `profiles/sean.toml`, create a separate private
profile repository and move the portable choices into its canonical
`ai-dlc-profile.toml`. Preview legacy enrollment, then repeat with `--apply`:

```sh
ai-dlc machine migrate SOURCE --profile-file profiles/sean.toml --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG
ai-dlc machine migrate SOURCE --profile-file profiles/sean.toml --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG --apply
```

The legacy preview can materialize an inactive cache, but does not change active
enrollment, client configuration, or package state. Its lock pins the resolved
commit when applied. After moving to the canonical filename, add
`profile_id = "legacy-development"` to `ai-dlc-profile.toml`, commit it, and
normal-enroll with that exact same stable ID:

```sh
ai-dlc machine enroll SOURCE --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG
ai-dlc machine enroll SOURCE --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG --apply
```

For an immutable advertised tag or ref, enroll that same ref on each additional
machine and expect `ai-dlc machine sync` to be idempotent. For an intentionally
movable advertised branch, `ai-dlc machine sync` previews later changes and
`ai-dlc machine sync --apply` activates a verified candidate. To move between
immutable tags, reenroll with the new ref. In every case, edit each machine
binding independently. Move every credential value into a password manager or
keychain that injects its configured environment-variable name; neither AI-DLC
files nor `.env` files are a credential store.

Initialize the specification provider (OpenSpec by default) using its supplied setup instructions, review existing formal specs, and link them to work. Configure the personal knowledge provider (Obsidian by default) with the intended vault and validate access. Preserve repository architecture, product rationale, decisions and runbooks as durable docs rather than copying them into the vault.

Adopting an existing project previews changes and reports path conflicts. Resolve user-authored docs/config deliberately before adoption; do not overwrite them. For upgrades, preserve Copier answers and the original accessible Git release. Bundled local-source adoption is a development fallback and does not promise cross-machine sync. Use the versioned repository template source for released projects.

The existing all-work `project rebind` command remains available for provider-role changes. Existing work retains its old provider until explicitly mapped. An apply refuses affected work without replacement artifact mappings. TOML mappings use work IDs as tables and artifact kinds as keys, for example `[work-123]` with `tracker = "NEW-42"`. PR/branch references must both be mapped when both exist. Local completion claims alone do not prove completion, so the migration treats retained records conservatively. Review old and replacement artifacts before applying.

No Jira, Figma, Windows, hosted orchestration, Obsidian create/attach, or
provider-discovery migration is provided by this release. Local CLI and MCP
execution remain the current control plane; hosted or cloud execution is a
later qualification target.


## Tracker default and selected-work migration

Use `project tracker-migrate` when changing only the default tracker or moving a
selected subset of work. First configure the destination under a distinct
`[providers.ALIAS]` entry using the provider's setup process. Keep the old alias
and its identity settings. The destination must resolve to an available tracker
adapter. A default switch alone does not qualify its live service access.

Preview a default-only switch and save the exact plan:

```sh
ai-dlc project tracker-migrate new-tickets --mode default-only --save-plan .ai-dlc/local/default-move.json
```

This previews the project default change and the records that need their current
effective providers and identity fingerprints frozen. Work that already has an
explicit provider mapping stays byte-for-byte unchanged. A partial mapping such
as `[providers] specs = "openspec"` does not inherit a tracker and is not enrolled
into one by this switch. The project edit preserves comments, unrelated provider
aliases, SCM/PR/CI configuration, and completion gates. Unsupported TOML layouts
are refused instead of being rewritten wholesale.

To move selected work, prepare an explicit mapping file:

```toml
[work-one]
tracker = "TARGET_REFERENCE_1"

[work-two]
tracker = "TARGET_REFERENCE_2"
```

Preview those exact selections:

```sh
ai-dlc project tracker-migrate new-tickets --mode selected --work work-one --work work-two --mappings .ai-dlc/local/selected-mappings.toml --save-plan .ai-dlc/local/selected-move.json
```

The adapter reads each requested target, verifies its configured project/repository
identity, and returns its canonical ID and URL. Different references resolving to
the same ticket are refused across selected work. New schema2 previews explicitly label the source as local-records-only: remote state/history and omitted comments, attachments, assignees, remote edits and remote-only issues remain unknown. They record target logical state and declared lifecycle capabilities; unsupported transitions are listed, and mapping preserves remote state without claiming completion. Legacy schema1 saved plans retain their original validation and recovery behavior. Each source provider, fingerprint
and ticket reference is recorded alongside the requested target reference and
verified identity. Selected work must be reviewed. Only its tracker provider,
fingerprint and ticket reference move; non-tracker references and fingerprints
remain intact. The default and every unselected work file remain unchanged.

Inspect the saved JSON before applying it. Apply accepts the saved plan alone;
new selection or mapping options cannot be combined with it:

```sh
ai-dlc project tracker-migrate --apply-plan .ai-dlc/local/default-move.json
# Or apply the selected-work preview:
ai-dlc project tracker-migrate --apply-plan .ai-dlc/local/selected-move.json
```

Omit `--save-plan` for a read-only preview printed to the terminal. Saving a plan
creates a new JSON file directly under ignored `.ai-dlc/local`; it never replaces
an existing file. Supply `--root PROJECT` when operating elsewhere. If using an
explicit `--machine MACHINE_FILE`, supply the same override at preview and apply.
The normal verified base/personal/project/enrolled-machine resolution applies;
only digests of effective runtime settings enter the plan, not machine settings,
paths, credentials, or account data.

Apply checks the plan schema/digest, project identity, complete config/work-file
snapshot, effective runtime identity, and fresh target reads under the project
write lock. Changes to any work file, provider/account identity, or canonical
target require a fresh preview. The source and runtime are checked again before
each local write and after the batch. No command here creates, closes, deletes,
transitions, or otherwise modifies remote tickets. Optional remote creation uses the separate reviewed creation/reconciliation actions below; it is never performed by tracker-migrate. The rules do not branch on destination vendor; custom
registered-provider fixtures do not establish live Plane support.

## Interrupted tracker migration recovery

Before the first target write, AI-DLC durably writes
`.ai-dlc/migrations/OPERATION_ID.json`. It contains the exact plan, provenance,
and base64-encoded original/proposed bytes for each changed local file. These are
project/work bytes, never resolved machine configuration. A separate immutable
`OPERATION_ID.result.json` records `applied`, `rolled-back`, or
`recovery-required`. Keep both as reviewable migration evidence.

The project lock serializes cooperating AI-DLC writers; arbitrary editors do not
participate in it. Writes and rollback use validated open file descriptors bound
to the original inode. They never replace a pathname, delete a stage file, or
roll back over a detected authored replacement. This preserves file permissions
and pathname replacements but uses in-place writes: readers can see intermediate
content, and a crash can leave partial bytes or a partially changed batch. It is
not a filesystem-wide atomic transaction. Arbitrary concurrent in-place editing
cannot be excluded by this lock; detected unknown bytes are retained for human
reconciliation.

An ordinary failed second write restores earlier writes only while both their
identity and complete contents remain known. A partial write, authored replacement,
interruption, or missing/corrupt result event leaves recovery evidence and prevents
another migration from proceeding. Apply exits unsuccessfully for a rolled-back
or recovery-required result. This subsequent-migration guard checks unresolved
outcomes; it does not verify the integrity of every completed historical prepared
receipt. Clone-safe historical integrity validation is deferred, preserving
continuation in cloned checkouts. Inspect without writing target files:

```sh
ai-dlc project tracker-migrate --inspect-recovery OPERATION_ID
```

The report classifies each current file as `before`, `after`, or `changed` using
the checked recovery digests. Preserve external edits separately, decode the
receipt's before/after bytes into separate review files, and manually reconcile
the affected files with those originals/proposals. Do not blindly copy a backup
over an authored replacement. Choose a complete original batch or a complete
proposed batch; mixed or independently changed contents cannot be acknowledged.
Then record the reviewed reconciliation:

```sh
ai-dlc project tracker-migrate --resolve-recovery OPERATION_ID
```

This command verifies that every affected file matches the same known side,
records `OPERATION_ID.recovered.json`, and does not modify project/work files.
An all-original restoration records `rolled-back`; an all-proposed restoration
records `applied`. This is local reconciliation evidence, not fresh remote
qualification. Retain the original receipt and outcome events, then create a new
migration preview if further changes are needed. A corrupt initial receipt cannot
be used for automated recovery inspection; preserve it and reconcile the project
from independently reviewed copies before repairing its migration evidence.

Plane existing targets must satisfy its exact AI-DLC correlation and scoped external identity contract. Ordinary native-created Plane items without that identity are refused; do not add identity markers blindly or infer ownership from a URL. Adapter fixtures establish local contract behavior only, not live Plane access.


## Optional reviewed target creation

Use this only when the selected work needs a new destination issue. Configure the target alias first. The source choice is explicitly local records: current title, scope, acceptance and traceability are rendered from reviewed work files. No source service is read; remote status/history, comments, attachments, assignees, remote edits and unrecorded issues are not imported. This is not Jira migration or a full-history importer.

Preview and save an exact creation intent:

```sh
ai-dlc project tracker-create-plan new-tickets --work work-one --create work-one --source local-records --save-plan .ai-dlc/local/create-targets.json
```

Every --work needs either --create for the same ID or an existing tracker reference from --mappings using the TOML format above. The sets must be disjoint and complete. At least one --create is required. Preview performs no service calls or writes; saving only persists the local intent. Inspect the saved payloads, source omissions, selected IDs and destination before explicitly authorizing reconciliation:

```sh
ai-dlc project tracker-reconcile --plan .ai-dlc/local/create-targets.json --save-plan .ai-dlc/local/resolved-move.json
```

This action may create the reviewed target issues. It never changes local work bindings. Only when every target has a fresh verified identity and the original local files/configuration remain current does it emit/save an ordinary migration plan. Review that plan and apply separately:

```sh
ai-dlc project tracker-migrate --apply-plan .ai-dlc/local/resolved-move.json
```

Use the same --root and, if selected, --machine override for all steps. Saved files are exclusive: choose a new output filename to retain a prior plan, never overwrite authored plans. A failure saving the resolved output still reports known retained targets and the complete proposed local plan.

Reconciliation binds the full saved intent fingerprint before reusing any remote result. The existing journal stores per-operation durable intent in the private XDG state directory under ai-dlc/tracker-migrations/ROOT_DIGEST/operations.sqlite3. A single Journal.begin sender wins for each stable operation ID. Plane additionally uses its existing trusted-root adapter intent files. Keep the saved intent and local journal; deleting state, changing roots/accounts, or starting a new creation intent is not a safe retry. These guarantees depend on retained local state and reviewed identity, not remote atomic uniqueness or cross-machine exactly-once execution.

Pending or uncertain operations only search/read on retry. Invisible correlation after an interruption never authorizes another create, even if the original process might have stopped before sending. Duplicate/incomplete results remain unresolved for manual inspection. Once a target ID and URL are known, later correlation searches or reads must preserve both. A replacement identity is unresolved, retains the original advisory reference and cannot produce a local migration plan; state refreshes for the same identity remain allowed. The result separates freshly verified targets from retained_targets, which are known references that may currently fail read-back. Those references are advisory recovery evidence, not current access or completion proof.

If local files change after creation, the creation phase has not changed any work bindings. Retry the same saved intent to reconcile prior targets read-only; do not create a fresh intent to bypass uncertainty. For a new local snapshot, put the retained verified target references into explicit existing mappings and use tracker-migrate preview. Configuration/account drift must be resolved before reusing the intent. Created issues are retained after local rollback; no remote deletion imitates an atomic transaction.

The final local receipt carries the creation operation, intent digest and per-work correlation alongside source-to-target provenance. Creation provenance is historical reviewed metadata, not a fresh remote-state claim. A closed or cancelled target does not waive any specification, merge or CI gate. Real Plane substitution/recovery still requires an explicitly chosen deployment and separate live evidence.

## Internal Python source organization

Repository organization moved internal services into responsibility-based packages;
see the [source map](architecture.md#source-layout). Custom Python integrations
that imported internal modules must update those imports, for example
`ai_dlc.agents` becomes `ai_dlc.harness.agents`. Public console entry points,
command arguments, MCP tools and provider wire contracts remain unchanged.

## Tracker defaults and removed Linear adapter

New projects default to the `github-issues` tracker. The packaged base profile,
`project init` and `project adopt` without `--tracker`, the Copier template and the
example profiles no longer select Linear or reference `LINEAR_API_KEY`. Existing
projects keep the tracker their own `ai-dlc.toml` selects: project configuration
wins over the base profile, and `copier update` keeps recorded answers.

The Linear adapter, its guided connection (`provider connect linear`, the
`--organization` and `--team` flags), `project rebind --connection-plan`, the
Linear conformance target and the `linear` module are removed. A configuration
whose tracker resolves to `linear` now receives a typed refusal (exit status 2)
from `work start`, `work publish`, `work finish`, `provider connect`, `project
init`/`adopt` and `project sync`, and `doctor` reports it as a configuration gap:

```text
Error: The Linear tracker adapter was removed after ai-dlc 0.4.0; select github-issues or jira-cloud, or run `ai-dlc project tracker-migrate` from ai-dlc 0.4.0 to move Linear-bound work first
```

To move off Linear:

1. Configure the destination under its own alias, for example
   `[providers.github-issues]` with `repository = "OWNER/REPO"`, and select it with
   `[roles] tracker = "github-issues"`. Remove `[providers.linear]` once no active
   work needs it.
2. Map unfinished Linear-bound work to destination tickets. `ai-dlc project rebind
   tracker github-issues --mappings MAPPINGS --no-plan` rewrites the records without
   reading Linear. To verify the Linear source while moving, run `ai-dlc project
   tracker-migrate` from ai-dlc 0.4.0 before upgrading.
3. Leave finished records alone. `work validate --all` never resolves provider
   bindings for finished records, so records pinned to `tracker = "linear"` remain
   valid history after `[providers.linear]` is deleted; only mutating commands on
   them refuse.

The Plane adapter remains shipped but unsupported and unqualified. `project init`
and `project adopt` refuse `--tracker plane` unless `--allow-unsupported` is also
passed; existing Plane projects keep working and `project sync` accepts their
recorded answers. `doctor` lists the selection under `provider_support` as
`unsupported, unqualified`.

Repositories whose agent jobs start through hangar intake can set `[work]
tracker_writes = "finish-only"` so `work start` does not move the ticket; see the
[tracker boundary](architecture.md#tracker-boundary-with-hangar).

## Execution targets and client hook versions

`project setup --target` and `doctor --target` accept `local` and `github-actions`
only. The `devcontainer`, `codex-cloud` and `claude-cloud` targets were removed under
[ADR 0001](decisions/0001-refocus-ai-dlc.md): they refuse with a message that names
the supported targets, because cloud sandboxes are rendered by hangar at claim time.
The dev container and the `scripts/cloud/` setup shims now bootstrap with the local
target. Python callers of `render_agents` or `render_windows` must drop the unused
`target=` argument; there is no published API contract for it.

Required hooks now check a minimum client version instead of an exact fixture
version. Set `[agents.clients.<client>] version` to the installed CLI version; any
version at or above the floor (`claude-code` 2.1.0, `codex` 0.151.0) renders, a lower
one refuses with `requires <client> >= <floor>`, and an unset version renders with a
warning. `agents/capabilities.toml` is schema 2 and has no `target` key.

The module catalog now pins `claude-code` 2.1.296 and `codex` 0.162.1, matching
hangar's `harnesses.lock.yaml`. `machine provision` installs these on new machines;
existing installs are not upgraded implicitly. Compare the pins locally with
`python scripts/check_client_pins.py --hangar-lock PATH`.

## ai-dlc scaffold removed

The legacy `ai-dlc scaffold` command, its `templates/` assets (packaged as
`ai_dlc/assets/legacy/`) and the stale root `copier.yml` are removed. `ai-dlc
scaffold` now prints a pointer and exits with status 2 for one release.

| Before | After |
| --- | --- |
| `ai-dlc scaffold --all` or `--provider claude` | `ai-dlc project init PATH` for a new repository, `ai-dlc project adopt PATH` for an existing one |
| `copier copy gh:Sean-Koval/ai-dlc DEST` | `ai-dlc project init DEST`, which copies the packaged `project-templates/` |

Repositories already scaffolded keep their copied files, including the
`quality-gate.sh` and `security-check.sh` hooks; nothing in them is changed.

## ai-dlc eval removed

The end-to-end evaluation runner, its contracts and assets, and the prompt-only
skill evaluation moved to [flightdeck](https://github.com/Sean-Koval/flightdeck)
(ADR 0001). `ai-dlc eval` is now a hidden stub that prints a pointer and exits
with status 2 for one release.

| Before | After |
| --- | --- |
| `ai-dlc eval plan`, `run`, `report`, `image`, `base` | flightdeck's local runner (`runner=local`) and task format |
| `python scripts/run_skill_evaluation.py` | `claude plugin eval` for skill smoke tests; flightdeck suites for behavior |
| `evaluations/`, `contracts/evaluation/`, `agents/evaluation*.{toml,json}`, `agents/evaluations/` | ported or archived in flightdeck |

The last AI-DLC version of all of it is tag `eval-handoff-2026-10`, whose
`docs/verification/end-to-end-evaluation.md#handoff-to-flightdeck` lists every
moved file. Provider conformance keeps `verification/test_proxy.py`.
