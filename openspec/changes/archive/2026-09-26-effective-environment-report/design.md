## Reviewed implementation disposition — September 26, 2026

The user authorized implementation of the specified issues one by one, including
push and merge. This independent slice follows completed #173. The product goal
is a useful, private comparison of selected team setup facts, with honest missing
evidence. It does not add build provenance infrastructure, a native evidence
runner, a probe plugin framework, or a new environment manager.

Read-only service review found that compound doctor/workspace diagnostics execute
commands or inspect unrelated personal state. Reuse their narrow local readers,
not those entry points. Existing profile/source/ownership hashes cover excluded
content and are not safe export provenance. They remain null with reasons unless
a narrowly defined safe projection establishes the field. Known pins, selections,
missing tools and guidance conflicts remain useful even when overall comparison
is incomplete. Default exports from current installations will normally be
incomplete because trusted engine/source identity and native client observations
are unavailable. Do not relax completeness to make these reports exit 0.

Both CLI doctor entry points receive the opt-in mode; the existing MCP doctor
contract remains unchanged. `--probe-versions` without report/export mode is an
input error. Explicit doctor `--target` (even local) or `--machine` is incompatible
with report mode; use parameter provenance or nullable defaults to preserve
ordinary invocation behavior. Status comparison is also incompatible with
`--probe-versions`. Compare accepts exactly two explicit files, never local state.

### Closed record details

All nested records reject extra keys and coercion. Use the existing Pydantic
dependency or equally small strict validation; no configurable schema framework.
The top-level fields below remain the complete export allowlist. Where a record
has `reasons`, it is a fixed-key mapping from its nullable fields to closed reason
codes, rather than freeform messages. Required unavailable observations cannot be
made optional by an input flag or limitation. Empty successfully inspected sets
and an unenrolled profile are distinct from failed collection.

- Engine current-process and PATH-selected observations have package_version,
  installation_kind, source_revision, source_dirty, artifact_sha256, state and
  reasons. The engine's existing top-level scalar fields mirror current_process
  exactly. Known source identity needs revision and dirty=false; a release needs
  an artifact digest. The source-root marker is attribution, not provenance. No
  Git probes, source-byte hashing or inferred revisions are introduced.
- Platform has os, architecture, shell_family and reasons. Use normalized fixed
  enums. Unknown active shell stays unknown; login-shell configuration alone
  does not prove the invoking shell.
- Profile and sources have id, commit, content_sha256, state and reasons. Profile
  state permits not-applicable for absent enrollment. Missing/corrupt source sets
  carry a required scoped limitation, never an apparently complete empty list.
- Runtimes have id, required and version. Version retains intended, observed,
  state and reason. A null intended version is an unconstrained declaration only
  in an otherwise successfully resolved scope; malformed declarations also carry
  a required limitation. IDs denote executable observations, not module names.
- Clients have id, edition, version, configured, rendered, recognized,
  authenticated and reasons. All selected clients require edition/version and
  configured/rendered assessment for complete observation; native recognition
  and authentication remain independent evidence dimensions.
- Project has engine_constraint, roles, components, client_ids,
  configuration_sha256, guidance, state and reasons. Roles contain role, provider
  and component. Components contain id and platform_support; support contains os,
  architecture and shell_family, each a bounded enum array or null. Today's
  component contracts have no support matrix, so collection emits null. Explicit
  synthetic support fixtures test comparison, not live platform qualification.
- Guidance contains id, kind, expected_sha256, observed_sha256, state, reasons
  and native_server. Kinds are instruction, skill, provider or native-server.
  Only native-server entries contain the latter record: alias, provider,
  transport, recipe_identity and reasons. Unestablished safe recipe identity
  remains null. An intact ownership checksum does not prove fresh desired output.
- Auth contains kind (provider/client), id, credential_presence, verification,
  verified_at, evidence_identity and reasons. Evidence identity, when present,
  contains configuration_identity and observation_identity. No evidence store is
  added here: collection leaves verification not-assessed and evidence null.
- Limitations contain field, reason_code and required; fields follow a bounded
  logical-field grammar and reasons a closed enum. Completeness is derived from
  actual validated fields and collection status, not trusted input declarations.

Bounds: identifiers 64 ASCII characters; versions/constraints 64; logical fields
256; sources 16; roles 5; clients 16; components/runtimes/auth 128; guidance 512;
limitations 1024; nesting depth 12; serialized input/output 1 MiB. IDs use a
portable lowercase alphanumeric/dot/underscore/hyphen grammar, no path syntax.
Unknown IDs aggregate into at most one null identifier-redacted record per
collection; do not derive a hash or ordinal identity from excluded values.
Reject duplicate JSON keys, duplicate logical IDs, nonfinite numbers,
bool-as-integer schema values, contradictory mirrors and inconsistent identities.
The schema module owns the closed reason/state vocabularies and safe errors.

### Identity, drift and safe observation decisions

The project configuration digest binds its desired safe fields; overall
configuration identity adds profile/source pins and desired runtime/client
context without observation state, timestamps, auth or self-reference. The
observation identity includes that identity and actual engine/platform/runtime,
client edition/version/configured/rendered and guidance state/digest. Both are
recomputed on import. Arrays sort by logical ID before canonical UTF-8 JSON.

Profile/source raw content hashes remain unavailable. For guidance, use a narrow
semantic projection with a fixed reviewed generator contract and only allowed
IDs/selections when its actual owned content can be checked against desired
content without executing a renderer or reading unrelated home state. Otherwise
retain null digests and an unknown reason. Known missing/modified owned guidance
still yields missing/mismatch and blocking drift, without exporting a digest of
the edited bytes. Never turn an intact but unverified marker into a match.

EER-05 invalidation concerns represented safe fields. Different excluded or
unknowable bytes may have the same incomplete identity; such reports are always
ineligible for exact-context native evidence reuse. This reconciles invalidation
with EER-03's prohibition on secret-derived hashes.

Compare each known field even when another is unknown. Check each side's own
missing required runtime, incompatible constraint, dirty source and guidance
mismatch before comparing sides; matching broken/unknown states cannot pass.
Unknown precedes equality. Auth differences are informational and do not change
configuration identity. Equal known platform values need no compatibility guess;
different values require explicit support by every selected component on both
sides or remain unknown. Explicit unsupported metadata is blocking on either side.
Client version differences remain unknown without a registered compatible
adapter contract; no current hook fixtures supply such a contract.

Version grammar is bounded numeric dotted versions, exact pins and comma-separated
numeric comparisons using ==, >=, >, <=, <. No wildcard/caret/prerelease guessing.
Project .mise.toml pins override module defaults; explicit agents.clients client
version overrides its default, but conflicting explicit declarations are unknown
with a conflict reason. Unsupported syntax is never echoed. Runtime differences
are informational only under the same declared constraint satisfied on both sides.

Comparison returns schema_version, configuration_complete, observation_complete
and findings with the already specified safe fields. Exit 1 follows blocking
findings or required incompleteness; optional unknowns remain visible. No parity,
readiness or qualification claim follows digest equality alone. Next actions are
closed route identifiers, never input-derived commands.

Optional probes use a fixed built-in executable/argv/parser table, no shell or
configured recipes, sequential execution, stdin disabled, a minimal child
environment, a five-second deadline and an actual combined 16 KiB capture bound.
Discard raw output/errors. Explicit permission to invoke a PATH executable is
not a sandbox against an arbitrary local wrapper; document that trust boundary.
Export itself initiates no network/client/provider session.

File comparison uses no-follow bounded reads. File export validates fully before
publishing a new private file atomically and refuses existing destinations and
unsafe parent traversal. Reuse Windows guarded publication and descriptor-pinned
POSIX primitives; strengthen only the small required filesystem operation.
Real host exports requiring privacy review remain separate from fixture
verification and are not necessary to claim this feature implemented.

## Existing implementation and gap

`environment/machine.py:status` reads local enrollment, verifies caches and checks credential presence; it discards its root. `doctor` combines this with project readiness and separately performs existing explicit health inspection. `project workspace-check` distinguishes PATH-selected and current-process versions and source alias attribution. Reuse these local collectors behind a shared report projection; do not serialize their raw output because it contains machine paths and potentially private identifiers. Package version alone is insufficient when release and source identify as 0.4.0. No existing canonical contract promises the proposed export or compare interface.

## Reviewed bounded CLI

- Existing `ai-dlc machine status` remains unchanged.
- `ai-dlc machine status --root PATH --export FILE` writes the safe schema-1 report; `--export -` emits it to stdout. Optional `--probe-versions` explicitly enables the bounded executable version probes below; by default only already available trusted metadata is read and unavailable observations are unknown. Existing files are refused, avoiding accidental destruction; atomic new-file publication uses existing filesystem protections. Export implies read-only local inspection except the requested output artifact.
- `ai-dlc machine status --compare LEFT RIGHT` reads two exports, emits a JSON comparison, and never resolves the local environment. It is mutually exclusive with root/export.
- Add `--effective-environment` to both existing doctor entry points. It emits the same report projection in an offline mode, with the same optional `--probe-versions` flag and no executable probes by default, without invoking existing provider-health probes; ordinary doctor invocations retain their current behavior. It is mutually exclusive with target/machine overrides until such identities have an explicit schema contract. Document the opt-in mode clearly rather than changing default doctor semantics.

Export exit 0 means a valid report was produced (unknowns and drift may exist); 2 means malformed input/unsafe destination/schema failure and no output file. Compare exit 0 means no blocking difference and complete identity coverage, 1 means blocking drift or unknown required comparability, and 2 means invalid exports/unsupported schema. Expected differences can exit 0 but must remain in findings. No comparison result is named ready or qualified.

## Schema 1 and identity

The serialized allowlist is JSON object `schema_version: 1`, `observed_at` (UTC), `engine`, `platform`, `profile`, `sources[]`, `runtimes[]`, `clients[]`, `project`, `auth[]`, `limitations[]`, `configuration_identity` and `observation_identity`. Unknown values are null accompanied by a fixed reason code, never silently omitted. Each version observation is `{intended: string|null, observed: string|null, state: observed|missing|unknown|unsupported, reason: code|null}`. No arbitrary adapter text is admitted.

- `engine`: `package_version`, `installation_kind` (`release|source|unknown`), `source_revision`, `source_dirty` (`true|false|null`), `artifact_sha256`, and separate `path_selected`/`current_process` version/provenance objects. Missing build provenance stays unknown; never infer a commit from package version or an environment directory name. Dirty sources carry dirty=true and cannot count as equal reproducible code even at the same commit.
- `platform`: normalized `os`, `architecture`, `shell_family`; hostnames, usernames and shell rc content excluded.
- `profile`: logical `id`, `commit`, `content_sha256`, `state`; `sources[]`: declared portable `id`, `commit`, `content_sha256`, `state`. No repository URL, machine ID, local cache location or source credentials. Logical IDs must pass a bounded identifier grammar; malformed/private-path IDs are redacted to null with `identifier-redacted`, not hashed into a covert identifier.
- `runtimes[]`: logical component ID plus version observation. `clients[]`: adapter ID, `edition`, version observation and separate `configured`, `rendered`, `recognized`, `authenticated` states (`yes|no|unknown|not-applicable`). Observation of one dimension never fills another.
- `project`: declared engine constraint; portable role/client selections; digest of the strictly allowlisted portable effective configuration; `guidance[]` entries with portable managed instruction/skill/native-server artifact ID, expected/observed SHA-256 and state. Native-server comparison includes only declared portable alias, provider/adapter ID, transport kind and verified safe recipe identity. Opaque/private endpoint, command or environment details are excluded and their unavailable transport identity is explicit; evidence requiring that unknown identity cannot establish exact-context MCP qualification. Arbitrary TOML, command bodies, profile content, authored client config and source files are not copied. The configuration digest covers selected component IDs, selected client IDs, engine/runtime version constraints, verified profile/source identities and managed guidance expectations, not secret values, machine bindings, endpoints, arbitrary check commands or private paths. It is intentionally a scoped configuration identity, not proof that all project bytes match; limitations say excluded fields are not compared.
- `auth[]`: selected logical provider/client ID, `credential_presence` (`present|missing|unknown`), `verification` (`verified|failed|not-assessed|stale`), optional `verified_at` and evidence identity. Presence does not verify account identity; exports omit accounts and token/environment-variable values. Verification is copied only from valid scoped evidence, never triggered during export.

Profile/source content digests may be carried only as verified nonsecret source-provenance metadata. Guidance expected/observed digests cover validated safe owned generated content or a defined nonsecret projection; never hash arbitrary authored files, private paths, credentials or raw command content. If safe projection/provenance cannot be established, emit null plus `safe-digest-unavailable` and mark comparison incomplete rather than hashing excluded bytes. This report does not prove identical arbitrary check commands or an identical whole software environment.

All text identifiers/enumerations are allowlisted and bounded, all digests are SHA-256, revisions are validated hexadecimal commit IDs, arrays sort by stable logical ID, duplicate IDs reject, and unknown schema versions reject. Comparison inputs have a 1 MiB limit each and reject unknown fields or invalid types rather than preserving arbitrary strings. Only with explicit `--probe-versions`, built-in bounded probe adapters may run allowlisted version commands without a shell, with a 5-second timeout and 16 KiB capture cap; raw stdout/stderr is discarded after parsing and never exported. Local export makes no network request, launches no native model session and reads no general home/client configuration directories.

`configuration_identity` is SHA-256 of canonical JSON (UTF-8, lexicographically sorted keys, sorted logical-ID arrays, no insignificant whitespace) of desired portable project/profile/source/runtime/client/guidance fields described above. Nulls are included but mark identity completeness false in limitations. `observation_identity` uses the same rules over configuration identity plus actual engine provenance, platform, observed runtime versions/states, client adapter/edition/version/configured/rendered states, and managed-guidance observations. It excludes timestamps, auth observations, client recognized/authenticated evidence-derived statuses and limitations. Excluding evidence-derived statuses prevents accepted native evidence from changing its own binding identity. Neither digest certifies authenticity; evidence must retain the schema payload and completeness checks. Native smoke evidence binds both identities plus explicit client/version/platform fields; observation changes invalidate that exact-context evidence even where comparison calls the difference expected.

## Drift classification

Return schema 1 `findings[]` entries with logical `field`, safe `left`/`right` values, `class`, `reason_code` and `next_action`; never quote raw file input in errors. Classes are `blocking`, `expected-platform`, `informational`, `unknown`; no difference is suppressed. Evaluate unknown before equality: unknown engine/source/profile/guidance identity, unobserved required runtime/client or dirty source means comparison cannot prove parity. Blocking includes known different engine artifact/source identity, selected profile/source commits/digests, desired configuration/guidance hashes, observed guidance failing its desired digest, selected client edition mismatch, or required runtime version violating its declared constraint on either side. Mere version equality never masks source identity mismatch.

OS/architecture/shell differences are `expected-platform` only when both are explicitly supported by the selected component contract; unsupported selection is blocking and absent support metadata is unknown. A runtime version difference within the same declared compatible constraint is informational, retaining both versions. Client version differences are unknown unless an adapter explicitly declares both compatible for the selected edition/schema; then informational. Credential-presence differences are informational local setup differences and verification remains separate; failed authentication is a scoped authentication finding, never evidence that shared configuration differs. Unknown optional observations remain visible but do not block complete required identity comparisons. Findings explain the existing repair/enrollment/render/check route; comparison never repairs automatically.

## Privacy, recovery, invalidation and evidence

Use a positive projection before file emission, never redact a dump by token substitution. Tests include sentinel secrets in profile URLs, project commands, env values, version output, client config and errors; private paths and values must be absent. Missing caches, malformed configuration and probe timeout yield scoped unknown/error codes and preserve independent observations. A malformed root may still produce an explicitly incomplete report; invalid serialized schema cannot be exported. Comparison never opens paths or URLs embedded in payloads.

Evidence covers same portable identity on two independent fixture homes, release-versus-source 0.4.0, dirty source, missing provenance, changed guidance, compatible/unsupported OS, unknown client edition, timeout, credential-presence differences and malformed/oversized exports. Record real supported-host exports only after user review for privacy; native/cross-machine observation remains #53. No paid model call or remote provider health probe is needed. Do not manufacture source provenance for old release artifacts; it stays unknown until a separately qualified build supplies it.

## Documentation and review

Machine enrollment owns how to export/compare; architecture owns collection/projection boundaries; tool map owns command usage; work-computer setup owns independent credentials; release verification owns remaining provenance/qualification gaps. Record content-bound dispositions during implementation, not hypothetical freshness now. The reviewed disposition above authorizes the bounded implementation under the user’s request; default diagnostics remain unchanged.
