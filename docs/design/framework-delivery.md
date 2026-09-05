# Framework delivery architecture

Status: planned implementation contracts, September 5, 2026.
Authority: [product direction](../product-direction.md). Formal behavior belongs
to the linked OpenSpec changes.

## Baseline and intended change

The current Python implementation has installation modules, scoped configuration,
provider adapters, managed client files, work records, and finish gates. These
primitives need a connected role-to-tool-to-guidance readiness experience.
Product-shaping instructions also need concrete examples and verification.

Keep existing services. Add small boundaries where responsibilities are currently
disconnected: provider role → component → existing modules, guidance, configuration.
Provider code continues to own remote operations and evidence interpretation.

## Ticket boundaries

| Work ID | Owns | Excludes |
| --- | --- | --- |
| component-capability-contract | Pure metadata validation and resolution | Installation, network, remote mutation |
| connected-project-readiness | Provisioning composition, guidance index, scoped readiness | Account selection, platform certification |
| linear-provider-onboarding | Discovery and reviewed local configuration | Issues, keys, automatic account switching |
| portable-workflow-bundles | Pinned Markdown import and owned distribution | Arbitrary installers and orchestration |
| product-shaping-workflow | Evidence, alternatives, scope, requirement IDs | Formal-spec ownership, publication during discovery |
| spec-delivery-traceability | Work graph, references, validation, initial ticket body | Product decisions |
| design-pm-workflow | Optional UI/UX rubric and evaluation | Framework-wide workflow policy |
| framework-qualification | Target, replacement, continuity evidence | New platform support by assertion |
| workflow-quality-calibration | Product/delivery decision evaluations | UI taste calibration |
| design-pm-calibration | UI evaluator's incremental value | General environment qualification |

## Frozen cross-ticket contracts

1. Retain schema 4 with additive nested fields. Component overrides use
   `providers.<id>.component`, `component_manifest`, and
   `component_manifest_sha256`. Machine layers cannot set them. Imported
   `agents.bundles` is project-only initially. Absent fields preserve old behavior.
2. Resolve explicit project/profile choices with provenance. Compatibility-only
   defaults do not authorize installation. Union required modules without rewriting
   the personal profile.
3. Component schema 1 contains `id`, `roles`, `modules`, `guidance`, and
   `required_config`. Recipes remain in `modules/catalog.toml`; built-in guidance
   lives in `agents/providers/`. Custom metadata is checked-in hashed JSON with
   existing recipe references and no executable installation commands.
4. Offline readiness uses tool, configuration, credential, and guidance checks.
   Provider health is informational unless explicitly inspected. Report
   ready/missing/blocked/unverified with a next action and
   `qualification = not-assessed`. Preserve existing doctor enrollment failures.
5. Linear onboarding uses the selected environment reference. Apply consumes the
   saved non-secret preview after fresh membership and source-digest checks.
   Bound work needs explicit rebind. Do not auto-read secret files or guess states.
6. Workflow bundles contain regular Markdown from a reviewed Git source/ref.
   Vendor selected files and a lock with exact commit and hashes. Preview and
   owned updates preserve authored files. Offline use never fetches.
7. Future Work fields `depends_on` and `requirements` have empty-list defaults.
   They are not valid in today's Work schema. Current plans and Linear
   relationships therefore carry dependencies until the traceability ticket lands.
8. Each behavior ticket owns an independently finishable OpenSpec change.
   Verification tickets use `requires_spec = false`; changing a predecessor's
   behavior requires a new specification decision.

Exact service signatures, file ownership, refusal cases, and sample regressions
are in the [execution plans](../superpowers/plans/2026-09-05-framework-delivery.md).
Dependent tickets must consume those interfaces rather than invent alternatives.

Implementation clarifications:

- Component loading owns filesystem/digest checks; pure resolution receives its
  validated catalog. Use `load_component_catalog(root: Path, config: dict) -> dict`
  in components.py, with packaged defaults through the existing assets helper.
  Explicit-role filtering uses `Resolved.sources`: personal/project selections
  count; compatibility-only base defaults do not trigger new installation.

### Third-party component example

A project can add a checked-in schema-1 component manifest without adding an
installer or provider operation. This complete example has three project files:

```text
components/third-party-tracker.json
guidance/third-party-tracker.md
ai-dlc.toml
```

`components/third-party-tracker.json` contains only declarative metadata. Its
`core` module is an existing recipe, and its guidance path is relative to the
same project root:

```json
{
  "schema": 1,
  "components": [
    {
      "id": "third-party-tracker",
      "roles": ["tracker"],
      "modules": ["core"],
      "guidance": ["guidance/third-party-tracker.md"],
      "required_config": ["repository"]
    }
  ]
}
```

For those exact bytes, configure the selected provider in the project-level
`ai-dlc.toml` as follows. The digest must be recalculated when the manifest
changes; machine configuration cannot set any of these component fields.

```toml
schema = 4

[roles]
tracker = "third-party-tracker"

[providers.third-party-tracker]
component = "third-party-tracker"
component_manifest = "components/third-party-tracker.json"
component_manifest_sha256 = "8f3e85c4f63fa73cf6b6a269544ed945d6d4f935fa7c4e2e1084c75da371a087"
```

Finally, `guidance/third-party-tracker.md` is checked-in Markdown with the
provider-specific instructions the selected harness can read:

```md
# Third-party tracker guidance

Use this tracker only for the project's configured repository. Record the
provider's issue reference in the normal work evidence, then run the required
project checks before requesting review.

This manifest declares requirements only; it does not authorize commands,
installers, or provider mutations.
```

Component loading verifies the manifest's path and digest, parses its schema,
confirms the `core` recipe and guidance file exist, and never executes manifest
content.
- Linear plan `config` is the parsed shared ai-dlc.toml, not merged machine state.
  `before_digest` uses the existing canonical `config.digest` on that dictionary.
  Apply re-reads/parses the current file and compares the same digest. Comment-only
  changes survive because editing starts from the current file text, never from a
  reserialization of the old dictionary. Invalid plans write nothing.
- A bundle candidate is a context-managed `BundleCandidate` dataclass in
  workflow_bundles.py with `source: str`, `ref: str`, `bundle_id: str`,
  `resolved_commit: str`, `root: Path`, `manifest: dict`, and
  `file_hashes: dict[str, str]`. `root` is temporary reviewed content. Exiting its
  context cleans temporary content; import copies validated bytes to owned
  project storage before exit. Revalidate file hashes immediately before copying.

## Agent execution and proportional effort

A ticket is the unit of independently reviewed delivery. Its OpenSpec tasks and
plan checkboxes are smaller steps inside it. Use installed tools directly for
development and the current services where repository policy requires them.

Skill delivery includes worked examples and decision cases. A small change can
use one brief or evaluation report if it carries the required evidence. Do not
generate every template or always spawn multiple agents.

## Rollout and evidence

M1/M2 ship additive behavior with focused regressions and required checks. M3
measures their integrated outcomes on explicitly named environments. Unavailable
targets leave qualification unfinished. Human ratings and paid experiments
require actual participation and a declared budget.

A documentation PR, generated fixture, live run, and human evaluation establish
different evidence. Original v4 release gates remain separately tracked.
