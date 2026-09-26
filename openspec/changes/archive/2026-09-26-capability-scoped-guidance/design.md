# Capability-scoped shared guidance

## Observed implementation and intended behavior

`src/ai_dlc/harness/agents.py::_render_agents` loads the project layer, resolves
components for the provider index, then passes only checks into
`_shared_guidance_lines`. Consequently its lifecycle prose cannot distinguish a
local-only project from this repository's full delivery configuration.

`Registry.get` resolves runtime kinds through `kind`, then `type`, then the
selected provider ID, with existing registered aliases. Component selection can
instead use `component`; a custom executable provider may intentionally reuse an
OpenSpec component for instructions. Therefore a component ID alone is not proof
that `ai-dlc work archive` or GitHub-specific lifecycle behavior is supported.

`Workflow.finish` always includes `pr-merged`, `ci-green` and
`specification-current`, even when `gates.finish` is empty. This change preserves
that rule. Removing prose does not relax gates or introduce offline completion.
Existing TR-04 requires generated merged-revision advice without a selection
qualification; its delta narrows only the instruction audience, not its gate.

## Decisions

Keep selection pure and offline inside the harness layer, passing the effective
project configuration or a small derived value into guidance composition. Reuse
existing runtime identity rules; do not instantiate adapters, run provider
commands, query credentials or inspect remote state while rendering. No new
public configuration keys or component metadata are needed.

Generic specification and tracker authority instructions follow nonempty selected
roles other than `none`. They say to use the selected provider's instructions;
they do not invent that provider's commands. Role omission is the supported
minimal/local configuration; this change does not make `none` a newly supported
specification, tracker or SCM provider.

For concrete lifecycle directives, recognize the current built-in tracker kinds
`linear`, `github-issues`, `jira-cloud` and `plane`, and SCM runtime kind `github`
including registered aliases. An external executable/Python provider can retain
generic role guidance and its linked instructions, but component selection alone
does not opt it into the built-in lifecycle sentences. This bounded renderer does
not claim extension lifecycle support is absent; it leaves provider-specific
instructions to the extension's owned guidance.

The instruction rules are:

| Directive | Selection predicate |
| --- | --- |
| Read `ai-dlc.toml`; read an active work record if present | Always |
| Store durable project explanations in `docs/` | Always |
| Specification authority and finalize required specs before review | Selected specification role |
| Tracker owns priority/status | Selected tracker role |
| `ai-dlc work archive` on the bound delivery branch | Runtime specification kind is `openspec`; say before merge only when supported SCM is selected |
| Update from target branch and rerun checks immediately before merge | Selected supported GitHub SCM |
| Rerecord only stale documentation dispositions | Applicable merge advice and a required configured documentation gate; do not introduce this policy when absent |
| Complete through `ai-dlc work finish` | Selected supported built-in tracker and supported GitHub SCM |
| Finish from merge checkout; detached worktree when target moved | Finish predicate plus runtime OpenSpec selection |
| Personal notes in selected knowledge provider | Selected knowledge role |
| Required check list and `ai-dlc project check --required` | Always, preserving declared order, command text and missing-command reporting |

Required documentation-gate recognition must use existing required check
configuration and be covered by a present/absent test; do not add a shell command
parser or infer a gate merely from a document catalog. Generic finish wording
continues to defer to required specifications and configured evidence, not a new
renderer-defined policy.

All selected clients consume the same conditional shared body through existing
AGENTS/CLAUDE/native-rule delivery. Preserve provider-index unresolved entries,
bundle/team guidance, stable ordering, managed markers, hashes and transactional
conflict checks. Never rewrite author-owned text to remove older unconditional
policy: only the owned generated body changes. Re-rendering old intact generated
sections updates them normally; edited managed sections still refuse.

## Required capability matrix

Exercise each row offline using actual project fixtures. Every row preserves
required checks and existing index behavior. `S` means generic specification
instruction, `T` tracker authority, `A` OpenSpec archive, `M` SCM merge advice,
`F` finish command, and `R` OpenSpec merged-checkout recovery.

| Configuration | Expected directives |
| --- | --- |
| No provider roles; one required check | No S/T/A/M/F/R; local config/docs/check guidance remains |
| OpenSpec only | S/A; no T/M/F/R and no before-merge premise |
| Each built-in tracker alone | T; no S/A/M/F/R |
| GitHub SCM only | M; no S/T/A/F/R |
| Each built-in tracker plus GitHub SCM, no specs | T/M/F; no S/A/R |
| OpenSpec plus GitHub SCM, no tracker | S/A/M; no T/F/R |
| OpenSpec, each built-in tracker and GitHub SCM | S/T/A/M/F/R |
| Same complete profile with empty finish-gate list | Same directives; mandatory runtime gates unchanged |
| Custom specification component plus built-in tracker/SCM | S/T/M/F; no A/R |
| Custom runtime specs provider advertising component `openspec` | Same as custom specs; component cannot enable A/R |
| Provider aliases using `kind`, and legacy `type` | Same directives as corresponding actual runtime kinds |
| Custom tracker or SCM component without built-in runtime kind | Generic selected-role guidance and links; no built-in F, and no M for custom SCM |
| Complete profile with/without required documentation gate | Stale-document disposition advice only with the gate |

Add precedence coverage when both `kind` and `type` appear, supported SCM alias
normalization, knowledge selected/omitted, and profile-only provider settings that
must not leak into a project's body. A full Cartesian product is unnecessary;
these rows cover every independent predicate and the important conjunctions.

## Verification and compatibility

NH-06 matrix tests belong in `tests/test_agents_phases.py` and observable render
tests in `tests/test_rendering.py`. Test presence and absence of meaningful
instructions rather than an entire prose snapshot. Retain an end-to-end default
configuration regression and all supported-client, author-preservation,
edited-managed-section refusal and idempotence checks. Switching full selection
to a local configuration removes only inapplicable owned prose, with byte-stable
author text and intact check commands. No live provider qualification is required
or established by these renderer tests.

## Documentation impact and migration

Update the rendering explanation in `docs/runbooks/machine-enrollment.md` with
selection boundaries and the supported local configuration example. Review
`docs/workflows/design-to-implementation.md` to retain the exact merged-revision
procedure and clarify its OpenSpec delivery context if necessary. Inspect actual
documentation impact for `docs/verification/documentation-workflow.md` and record
accurate unchanged/updated dispositions. Maintain existing catalog mappings if
test/source ownership changes. No migration is required; applying render is the
existing explicit update mechanism. Proceed to implementation after specification
validation; no additional product decision or approval gate is introduced.
