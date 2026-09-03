# AI-DLC provider contract v1

`manifest.json` and operation schemas are generated from `ai_dlc.contracts` Pydantic models.
They describe tracker, specs, SCM, deploy, and knowledge role capabilities.
Completion is intentionally absent: callers must use `WorkService.finish`.
The public `Registry.invoke` also refuses terminal tracker transitions.

Executable providers consume one JSON object on stdin and return one JSON object on
stdout. The request envelope contains `schema_version: 1`, `operation`, `payload`, and
`operation_id` (null for reads). Diagnostics belong on stderr; nonzero exit is failure.
Every mutation payload includes its stable operation ID. Executables have a configured
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
provided) and wraps authenticated `gh`. Linear uses HTTPS GraphQL and a `token_env`
reference. Its `statuses` map canonical `open`, `in_progress`, and `closed` to native
state IDs. GitHub Issues has only `open` and `closed`; work start still creates/reuses its Git branch
and reads the issue, returning an explicit unsupported in_progress capability.

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
