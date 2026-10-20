# Migration to v4

Move an older installation, profile or project to schema 4, change its tracker,
and know which commands and adapters this release removed.

## Install and profile

Before selecting the Python entry point, inventory existing aliases, shell
functions, PATH entries and installed `ai-dlc`/`ai-dlc-cli` binaries. Confirm
both aliases resolve to the intended executable after installation. Keep a
rollback copy of obsolete Rust binaries until migration fixtures prove the
supported behavior.

Schema 4 separates portable project configuration from machine bindings. Review
old provider selections and credentials; migrate secret values to environment
variables and select `scm.repository` explicitly. Machine-specific vault paths
and account settings belong in machine configuration.

For a personal profile such as `profiles/sean.toml`, create a separate private
profile repository and move the portable choices into its canonical
`ai-dlc-profile.toml`.

1. Preview the legacy enrollment, then repeat with `--apply`:
   ```sh
   ai-dlc machine migrate SOURCE --profile-file profiles/sean.toml --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG
   ai-dlc machine migrate SOURCE --profile-file profiles/sean.toml --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG --apply
   ```
2. After moving to the canonical filename, add `profile_id = "legacy-development"`
   to `ai-dlc-profile.toml` and commit it.
3. Normal-enroll with that exact same stable ID:
   ```sh
   ai-dlc machine enroll SOURCE --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG
   ai-dlc machine enroll SOURCE --profile-id legacy-development --machine-id MACHINE_A --ref IMMUTABLE_REF_OR_TAG --apply
   ```

The legacy preview can materialize an inactive cache, but does not change active
enrollment, client configuration, or package state. Its lock pins the resolved
commit when applied.

For an immutable tag or ref, enroll that same ref on each additional machine;
`ai-dlc machine sync` is then idempotent. For a movable branch, `sync` previews
later changes and `sync --apply` activates a verified candidate. To move between
immutable tags, reenroll with the new ref. Edit each machine binding
independently. Keep every credential value in a password manager or
keychain; neither ai-dlc files nor `.env` files are a credential store.

## Providers and projects

Initialize the specification provider (OpenSpec by default), review existing
formal specs, and link them to work. Configure the personal knowledge provider
(Obsidian by default) with the intended vault and validate access. Keep
architecture, rationale, decisions and runbooks in the repository rather than
copying them into the vault.

Adopting an existing project previews changes and reports path conflicts;
resolve user-authored docs and config before adoption rather than overwriting
them. For upgrades, preserve Copier answers and the original Git release.
Bundled local-source adoption is a development fallback; use the versioned
template source for released projects.

The all-work `project rebind` command remains available for provider-role
changes. Existing work retains its old provider until explicitly mapped, and an
apply refuses affected work without replacement artifact mappings. TOML mappings
use work IDs as tables and artifact kinds as keys, for example `[work-123]` with
`tracker = "NEW-42"`. PR and branch references must both be mapped when both
exist. Review old and replacement artifacts before applying.

No Jira, Figma, Windows, hosted orchestration, Obsidian create/attach, or
provider-discovery migration is provided by this release. Local CLI and MCP
execution remain the current control plane.

## Tracker default and selected-work migration

Use `project tracker-migrate` when changing only the default tracker or moving a
selected subset of work. First configure the destination under a distinct
`[providers.ALIAS]` entry using the provider's setup process. Keep the old alias
and its identity settings. The destination must resolve to an available tracker
adapter; a default switch alone does not qualify its live service access.

1. Preview a default-only switch and save the exact plan:
   ```sh
   ai-dlc project tracker-migrate new-tickets --mode default-only --save-plan .ai-dlc/local/default-move.json
   ```
2. To move selected work instead, prepare an explicit mapping file and preview
   those exact selections:
   ```toml
   [work-one]
   tracker = "TARGET_REFERENCE_1"

   [work-two]
   tracker = "TARGET_REFERENCE_2"
   ```
   ```sh
   ai-dlc project tracker-migrate new-tickets --mode selected --work work-one --work work-two --mappings .ai-dlc/local/selected-mappings.toml --save-plan .ai-dlc/local/selected-move.json
   ```
3. Inspect the saved JSON, then apply it. Apply accepts the saved plan alone;
   new selection or mapping options cannot be combined with it:
   ```sh
   ai-dlc project tracker-migrate --apply-plan .ai-dlc/local/default-move.json
   ```

A default-only preview shows the project default change and the records whose
current providers and fingerprints need freezing. Work with an explicit provider
mapping stays byte-for-byte unchanged, and a partial mapping such as
`[providers] specs = "openspec"` does not inherit a tracker. The project edit
preserves comments, other aliases and completion gates; unsupported TOML layouts
are refused.

For selected work, the adapter reads each requested target, verifies its
configured project or repository identity, and returns its canonical ID and URL.
Different references resolving to the same ticket are refused. Previews label
the source as local-records-only: remote state, comments, attachments and
remote-only issues remain unknown. Selected work must be reviewed. Only its
tracker provider, fingerprint and ticket reference move; everything else stays
unchanged.

Omit `--save-plan` for a read-only preview printed to the terminal. Saving a plan
creates a new JSON file under ignored `.ai-dlc/local`; it never replaces an
existing file. Supply `--root PROJECT` when operating elsewhere, and the same
`--machine MACHINE_FILE` override at preview and apply. Only digests of effective
runtime settings enter the plan, never machine settings, paths, credentials or
account data.

Apply checks the plan digest, project identity, the config and work-file
snapshot, runtime identity and fresh target reads under the project write lock.
Any change to a work file, provider identity or target requires a fresh
preview. No command here creates, closes, transitions or otherwise modifies
remote tickets; optional remote creation is the separate reviewed step below.

## Interrupted tracker migration recovery

Before the first target write, ai-dlc durably writes
`.ai-dlc/migrations/OPERATION_ID.json`. It holds the exact plan, provenance, and
base64-encoded original and proposed bytes for each changed local file. A
separate immutable `OPERATION_ID.result.json` records `applied`, `rolled-back`,
or `recovery-required`. Keep both as reviewable migration evidence.

The project lock serializes cooperating ai-dlc writers; arbitrary editors do not
participate in it. Writes and rollback use file descriptors bound to the
original inode and never replace a pathname or roll back over a detected
authored replacement. Because writes are in place, a crash can leave partial
bytes; this is not an atomic transaction. Unknown bytes are retained for human
reconciliation.

A failed second write restores earlier writes only while both their identity and
complete contents remain known. A partial write, authored replacement,
interruption, or missing result event leaves recovery evidence and blocks
further migrations. Apply exits unsuccessfully for a rolled-back or
recovery-required result.

1. Inspect without writing target files:
   ```sh
   ai-dlc project tracker-migrate --inspect-recovery OPERATION_ID
   ```
   The report classifies each current file as `before`, `after`, or `changed`
   using the checked recovery digests.
2. Preserve external edits separately, decode the receipt's before and after
   bytes into review files, and reconcile each affected file by hand. Choose a
   complete original batch or a complete proposed batch; mixed contents cannot be
   acknowledged. Do not blindly copy a backup over an authored replacement.
3. Record the reviewed reconciliation:
   ```sh
   ai-dlc project tracker-migrate --resolve-recovery OPERATION_ID
   ```

Resolve verifies that every affected file matches the same known side and
records `OPERATION_ID.recovered.json`; it does not modify project or work files.
An all-original restoration records `rolled-back`; an all-proposed restoration
records `applied`. A corrupt initial receipt cannot drive automated recovery;
reconcile the project from reviewed copies first.

Plane existing targets must satisfy its exact ai-dlc correlation and scoped
external identity contract. Ordinary native-created Plane items without that
identity are refused; do not add identity markers blindly or infer ownership
from a URL.

## Optional reviewed target creation

Use this only when the selected work needs a new destination issue. Configure the
target alias first. The source is explicitly local records: current title,
scope, acceptance and traceability are rendered from reviewed work files. No
source service is read, so remote status, history, comments, attachments and
unrecorded issues are not imported. This is not a Jira migration or a
full-history importer.

1. Preview and save an exact creation intent:
   ```sh
   ai-dlc project tracker-create-plan new-tickets --work work-one --create work-one --source local-records --save-plan .ai-dlc/local/create-targets.json
   ```
   Every `--work` needs either `--create` for the same ID or an existing tracker
   reference from `--mappings`. The sets must be disjoint and complete, with at
   least one `--create`. Preview performs no service calls or writes.
2. Inspect the saved payloads, source omissions and destination, then authorize
   reconciliation. This step may create the reviewed target issues; it never
   changes local work bindings:
   ```sh
   ai-dlc project tracker-reconcile --plan .ai-dlc/local/create-targets.json --save-plan .ai-dlc/local/resolved-move.json
   ```
3. Review the resolved migration plan and apply it separately:
   ```sh
   ai-dlc project tracker-migrate --apply-plan .ai-dlc/local/resolved-move.json
   ```

Use the same `--root` and, if selected, `--machine` override for all steps.
Saved files are exclusive: choose a new output filename to retain a prior plan.
A failure saving the resolved output still reports known retained targets and
the complete proposed local plan.

Reconciliation binds the saved intent fingerprint before reusing any remote
result. The journal stores per-operation intent in the private XDG state
directory under `ai-dlc/tracker-migrations/ROOT_DIGEST/operations.sqlite3`. Keep
the saved intent and local journal; deleting state, changing roots or accounts,
or starting a new creation intent is not a safe retry.

Pending or uncertain operations only search and read on retry. Invisible
correlation after an interruption never authorizes another create. The result
separates freshly verified targets from `retained_targets`: known references
that may currently fail read-back and are recovery evidence, not completion
proof. Created issues are retained after local rollback; a closed or cancelled
target does not waive any specification, merge or CI gate.

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
init`/`adopt` and `project sync`. `doctor` reports it as a configuration gap:

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
[ADR 0001](decisions/0001-refocus-ai-dlc.md), because cloud sandboxes are rendered
by hangar at claim time. They refuse with a message that names the supported
targets. The dev container and the `scripts/cloud/` shims now bootstrap with the
local target.

Python callers of `render_agents` or `render_windows` must drop the unused
`target=` argument; there is no published API contract for it.

Required hooks now check a minimum client version instead of an exact fixture
version. Set `[agents.clients.<client>] version` to the installed CLI version. Any
version at or above the floor (`claude-code` 2.1.0, `codex` 0.151.0) renders. A lower
one refuses with `requires <client> >= <floor>`; an unset version renders with a
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

The last ai-dlc version of all of it is tag `eval-handoff-2026-10`, whose
`docs/verification/end-to-end-evaluation.md#handoff-to-flightdeck` lists every
moved file. Provider conformance keeps `verification/test_proxy.py`.
