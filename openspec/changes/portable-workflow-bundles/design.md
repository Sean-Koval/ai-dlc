## Context

Make a replaceable workflow bundle reproducible in the project repository and discoverable to the harness using existing managed rendering.
Read [product direction](../../../docs/product-direction.md) and the [delivery architecture](../../../docs/design/framework-delivery.md).

## Goals / Non-Goals

Goal: Make a replaceable workflow bundle reproducible in the project repository and discoverable to the harness using existing managed rendering.

Excluded: No arbitrary installer/scripts, marketplace, dependency solver, new client adapter, remote auto-update, or changes to personal profile enrollment semantics.

## Decisions

The first bundle format is a duplicate-key-free UTF-8 `bundle.json` object with
exact fields `schema`, `id`, `skills`, `templates`, and `files`. `schema` is 1;
`id` and every export name are lowercase ASCII slugs. `skills` maps export names
to normalized relative paths ending in `SKILL.md`; `templates` maps export names
to normalized relative `.md` paths; and `files` maps every payload path to its
lowercase SHA-256 digest. Paths contain only ASCII letters, digits, `.`, `_`, `-`,
and `/`, in addition to satisfying the structural rules below; Markdown-sensitive
path characters therefore never require link escaping. The two export maps form one namespace, and one payload
path can have only one export name. In schema 1, the `files` keys equal exactly
the union of skill and template target paths: supporting files that are not
direct exports are deferred rather than copied to an undefined destination.
`bundle.json` is not a payload entry because its own byte digest is recorded
separately in the import lock.

Each skill export is valid for both supported harnesses only when its Markdown
starts with a four-line constrained frontmatter block: `---`, `name: NAME`,
`description: DESCRIPTION`, `---`, in that exact order. `NAME` equals the export
slug. `DESCRIPTION` is a single non-empty UTF-8 line of at most 1,024 characters
with no leading/trailing whitespace or control characters. This is deliberately
not general YAML, accepts no comments or additional keys, and needs no parser
dependency. The Markdown body after frontmatter is non-empty. Templates require
non-empty Markdown but no frontmatter. Schema 1 defers client-specific metadata
rather than silently accepting fields one client may ignore.

The first delivery permits at most 1 MiB for `bundle.json`, 1,024 payload files,
16 path segments, 2 MiB per payload file, and 10 MiB total payload. All payload
is regular UTF-8 Markdown. Symlinks at any path component, non-regular files,
absolute or non-normalized paths, traversal, Windows drive paths, scripts,
missing or undeclared files, and digest mismatches are rejected. Git metadata is
excluded from bundle-tree comparison only for the checkout root's `.git` entry;
a nested `.git` path is ordinary undeclared content and is rejected. At least one
skill or template export is required. The existing Git timeout bounds source
resolution; M1 does not claim a hard network-transfer byte limit, so the source
and exact revision remain an explicit review boundary.

Add `ai-dlc agents bundle import SOURCE --ref REF --id ID [--apply
--expected-commit SHA]`. Only portable Git transports accepted by the existing
profile-source grammar (`https`, `ssh`, or SCP form) are accepted; local and
`file:` sources are refused so committed provenance never contains a machine
path. Preview may fetch into temporary storage but changes no project, client,
profile, or remote state. It returns the source, ref, exact commit, manifest
digest, complete export maps, payload hashes, and planned vendored paths so a
reviewer can inspect the exact source revision. Resolution parses `bundle.json`
with duplicate-key rejection, requires its `id` to equal `--id`, validates the
complete checkout tree, and returns a context-managed `BundleCandidate`.

Apply freshly resolves and validates the same ref. The service boundary is
`import_bundle(root, candidate, *, apply=False, expected_commit=None)`; apply
requires a 40-character `expected_commit` equal to the freshly resolved commit.
It revalidates manifest and payload bytes immediately before copying. Apply
vendors only `bundle.json`, the declared payload, and deterministic
`bundle.lock.json` under `.ai-dlc/bundles/ID`. The lock has exact fields
`schema=1`, `id`, `source`, `ref`, `resolved_commit`, `manifest_sha256`, and the
complete sorted `files` digest map. A staged tree and project write lock make the
replacement transactional; any failure restores the previous bundle byte for
byte and changes no active rendered file. An existing bundle may update only
when its lock, manifest, and every previously owned byte still validate. An
authored directory, extra file, invalid lock, or local edit is a conflict.

Import does not select or render a bundle and never edits `ai-dlc.toml`.
Activation is the separate, reviewable project configuration
`agents.bundles = ["ID"]`, followed by `ai-dlc agents render --apply`. The field
is a duplicate-free list of bundle-ID slugs, is valid only in the project layer,
and is rejected in base, personal, and machine layers. Missing and empty both
select no imported bundles. Existing `agents.skills` continues to select shipped
skills only.

Rendering validates every selected vendored lock, manifest, payload, export, and
collision before planning any write. Bundle export names are globally unique
across selected bundles and across their skill/template maps; bundle skill names
also cannot collide with shipped skills. Skills render to
`.agents/skills/NAME/SKILL.md` and `.claude/skills/NAME/SKILL.md` for the selected
supported clients. Templates render once to `docs/templates/NAME.md`, and the
managed `AGENTS.md` provider/workflow index links every rendered bundle skill and
template; `CLAUDE.md` continues to reference `AGENTS.md`. These destinations make
templates directly readable by either harness without inventing a client-specific
template convention.

Bundle-owned outputs carry both owner ID and digest in the existing project
ownership document. A render involving selected or previously owned bundle
outputs writes ownership schema 3: the existing `files[path] = sha256` map
remains the authoritative digest map for provider copies, shipped skills, and
bundle outputs already tracked by file path, and its value shape stays unchanged
for compatibility. Additive `bundle_files[path] = {"owner": ID, "sha256":
DIGEST}` entries identify a subset of those same paths as bundle outputs. Every
`bundle_files` path must exist in `files` with the same digest; missing or
disagreeing cross-map entries are invalid and block writes. Schema-2 ownership
loads as having no prior bundle owners. Once schema 3 is written it is retained
with an empty `bundle_files` map after the last bundle output is removed; it never
downgrades. Existing managed-section, MCP, and hook ownership representations
remain unchanged; they do not move into either bundle map.

A pre-existing unowned destination is a collision even when its bytes match. A
same-owner update is allowed only when the current digest still matches prior
ownership; an authored/local edit is preserved and blocks the whole render. If
an updated selected bundle removes or renames an export, the obsolete same-owner
output is removed only when intact and blocks the render when edited. Deselecting
a bundle follows the same rule. All bundle validation and collision failures
write nothing. When selected or previously owned bundle outputs participate,
every changed or removed file in that entire `render_agents(..., apply=True)`
invocation—including managed guidance, provider copies, MCP/hooks/config files,
bundle outputs, and ownership—is one project-locked transaction; an operational
failure restores every affected file.

The managed workflow-bundle index is deterministic: sort by bundle ID, then
`skill` before `template`, then export name. Each skill links to its canonical
vendored path `.ai-dlc/bundles/ID/PAYLOAD_PATH`, avoiding a client-specific link
in shared `AGENTS.md`; each template links to its rendered
`docs/templates/NAME.md`. Native skill copies remain the actual discovery path
for each selected client.

Project readiness consumes a shared structured inspection boundary rather than
parsing renderer exceptions: `inspect_bundle_guidance(root, config, clients) ->
list[dict]`. It returns exactly one sorted result per selected bundle with keys
`bundle_id`, `status`, `reason`, and `next_action`. Readiness maps it to the
existing five-field check using `component = "bundle:" + bundle_id` and
`dimension = "guidance"`. A missing vendored path or expected rendered output is
`missing`; any present-but-invalid lock/manifest/payload or edited owned output
is `blocked`; an intact vendored and rendered bundle is `ready`. An output that
still matches prior ownership but is stale or obsolete for the current bundle is
`missing` with a full-render next action. A collision blocks every selected
bundle participating in that export or destination claim. Inspection evaluates
all configured clients even after a client-specific render, so intact but stale
non-target-client outputs remain `missing`; bytes diverging from recorded
ownership are `blocked`. When multiple conditions apply, precedence is
`blocked`, then `missing`, then `ready`, and reasons are deterministic. Each
result has an actionable next step and participates in the existing blocking
guidance dimension, so readiness cannot be true while selected bundle guidance
is unavailable.

Guidance remains untrusted input for the receiving harness. Import and rendering
never execute Markdown, referenced commands, or linked content. There is no
remote registry, automatic startup fetch, marketplace, or implicit update.

### Interface contract

`validate_bundle(root: Path, manifest: dict) -> dict` returns a validated
schema-1 manifest. Raw duplicate JSON keys are rejected by the resolver before
this already-parsed-dictionary boundary. `resolve_bundle(source: str, ref: str,
bundle_id: str, *, environ) -> BundleCandidate` returns the exact temporary
candidate and does not activate files. The context-managed `BundleCandidate`
contains `source`, `ref`, `bundle_id`, `resolved_commit`, `root`, `manifest`,
`manifest_sha256`, and `file_hashes`; context exit removes its temporary tree.
`import_bundle(root: Path, candidate, *, apply: bool = False,
expected_commit: str | None = None) -> dict` returns exactly `applied: bool`,
`changed: list[str]`, `conflicts: list[str]`, `source: str`, `ref: str`,
`bundle_id: str`, `resolved_commit: str`, `manifest_sha256: str`, `skills:
dict[str, str]`, `templates: dict[str, str]`, and `files: dict[str, str]`.
Lists and maps are deterministically sorted. Invalid or unsafe input, stale
commit, or candidate tampering raises a credential-redacted `ValueError` and
writes nothing. Existing-destination or ownership conflicts return the same
result with `applied=false`, `changed=[]`, and non-empty `conflicts`, even when
apply was requested. Each conflict is a credential-redacted, deterministic
`PROJECT_RELATIVE_PATH: reason` string sorted by path and reason. On a successful
preview, `changed` is the sorted project-relative list of vendored files whose
desired bytes differ, including `bundle.json`, every changed payload, and
`bundle.lock.json`; apply success returns that same planned list. A successful
idempotent apply returns `applied=true` and `changed=[]`. No active profile lock
is mutated.

### Dependency contract

- component-capability-contract: consume its committed documented interfaces; do not implement an incompatible local substitute.
- connected-project-readiness: consume its committed documented interfaces; do not implement an incompatible local substitute.
- linear-provider-onboarding: consume its project write-lock interface for
  transaction coordination; do not create an independent competing lock.

## Risks / Trade-offs

- Existing configuration or content is changed accidentally → validate all
  sources/destinations before writes and use rollback/refusal-path tests.
- An agent implements a neighboring ticket's responsibilities → use the explicit file/interface boundaries and dependency gate.
- Generated assets drift from source → update source, integrity metadata and generated copies together and run required checks.
- A reviewed Markdown bundle contains harmful instructions → retain explicit
  source/revision review, never execute bundle content, and require a separate
  checked-in selection before the harness sees it as active guidance.

## Migration Plan

Use additive defaults for existing configurations. The exact sequence is:

1. Preview the portable Git source/ref and inspect the returned exact commit,
   mappings, paths, and hashes.
2. Repeat the import with `--apply --expected-commit COMMIT` to vendor bytes only.
3. Add the bundle ID to project-level `agents.bundles` in a reviewed change.
4. Run `ai-dlc agents render --apply`, inspect the managed index and outputs, and
   commit the config, vendored bundle/lock, and intended managed artifacts.
5. In a fresh checkout, bootstrap and rerun `ai-dlc agents render --check`; this
   path reads only committed files and does not contact the original source.

Preserve original files on validation, collision, or publication failures.
Deliver changes on an independently reviewed branch. Reverting owned assets must
preserve authored project content and prior provider bindings.

## Verification

- WB-01: exercise a source ref moves before apply and the corresponding expected result in the formal spec.
- WB-02: exercise an imported skill has a local edit and the corresponding expected result in the formal spec.
- WB-03: exercise a fresh checkout has no network and the corresponding expected result in the formal spec.
- Exercise duplicate JSON keys, manifest-ID mismatch, size/count/path/type limits,
  portable-source refusal, complete lock integrity, same-owner update, cross-bundle
  and authored collisions, config-layer rejection, rollback, generated index, and
  readiness blocking with real files wherever practical.

[Task-level instructions and acceptance example](../../../docs/superpowers/plans/2026-09-05-portable-workflow-bundles.md).
