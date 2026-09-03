# Brownfield workflow

Use this path when bringing AI-DLC into an existing repository or changing an
existing product. Adoption must preserve application files and observed
behavior while introducing portable workflow controls deliberately.

[Back to the workflow map](../development-workflow.md)

## Flow

```mermaid
flowchart TD
    I[Inventory repository] --> P[Preview adoption]
    P --> A[Apply reviewed files]
    A --> C[Characterize current behavior]
    C --> D[Design incremental change]
    D --> S[Specification decision]
    S --> W[Publish and start work]
    W --> M[Implement and migrate]
    M --> V[Regression checks, review, merge, finish]
```

## 1. Inventory before adopting

Identify the deployable application, manifests and lockfiles, module and data
boundaries, public interfaces, CI rules, operational runbooks, and existing
documentation. Record unknown behavior instead of guessing. Find owner-written
files that overlap AI-DLC managed paths before applying a template.

Establish a clean test baseline. Where important behavior lacks tests, add
characterization tests that describe the current observable contract before
changing it. A characterization test is evidence, not an endorsement of the
current design.

## 2. Preview and apply adoption

Preview first:

```sh
ai-dlc project adopt --root /path/to/project --preset generic
```

Review every proposed file and conflict, then repeat with `--apply`. Existing
managed-path files are conflicts, including user-authored configuration and
documentation. Adoption presets expect existing manifests and lockfiles and do
not create application source. The generic preset installs no language
toolchain.

The bundled template can bootstrap a checkout, but portable updates require an
accessible Git template URL and immutable release tag. Copier owns its answers,
source, revision, and three-way update history; never hand-edit that history to
manufacture upgrade support.

## 3. Establish the managed boundary

After adoption, distinguish four areas:

- application code and owner-authored documents that AI-DLC must preserve;
- template-managed workflow files that can receive reviewed updates;
- provider-owned remote state such as specifications, tracker status, and SCM
  evidence;
- machine-local state such as credentials, paths, caches, and journals.

Snapshot and staging omit `.git`, dependency directories, tool caches,
`.ai-dlc/local/`, and Git-ignored untracked files. Runtime files remain
untouched. If the checkout changes after staging, application aborts and asks
for a fresh preview instead of applying a stale plan. Copier conflicts leave
the original checkout untouched.

## 4. Design the incremental change

Begin from the current journey and interfaces, not the desired implementation.
State what must remain compatible, what may migrate, and how users or dependent
systems cross the transition. Include data migration, rollout, observability,
recovery, and rollback when the change can affect stored or remote state.

Follow the [design-to-implementation contract](design-to-implementation.md).
For a risky change, prefer multiple independently releasable slices over a
single replacement. Record consequential compatibility decisions in an ADR.

## 5. Specify, publish, and implement

Decide whether changed behavior requires a formal specification. Use the
configured provider or a deliberately used local OpenSpec compatibility
fallback when one is required; otherwise record `requires_spec = false` and its
reviewed reason. With tracker and SCM capabilities configured, link the design
and specification from the work record, then publish and start through AI-DLC.
Otherwise, use the local project lifecycle and manual tracking. Implement on
the bound branch when available and preserve unrelated repository behavior.
Add regression tests for old contracts and acceptance tests for new outcomes.

For template updates, run a preview before applying. Sync stages the checkout
in a temporary Git repository and asks Copier to perform the three-way update.
Application files are retained, `.git` metadata is never copied back, ordinary
write errors roll back, and conflicts leave the destination untouched. A
power-loss-safe multi-file transaction is not claimed.

## 6. Review, migrate, and finish

Review compatibility evidence, migrations, rollback, documentation, and the
new behavior—not only the code diff. Always run required checks locally. With
tracker and SCM roles configured, merge through SCM, observe rollout evidence
when configured, and use `ai-dlc work finish <work-id>` to authenticate the
merged revision before completing remote tracker state. Otherwise, close the
manual lifecycle without claiming AI-DLC remote completion.

## Ready and done

Brownfield work is ready when current behavior, compatibility boundaries,
affected owners, incremental design, specification decision, rollback needs,
and test strategy are explicit. Local work is done when required old and new
behavior is verified and migrations and runbooks are current. With tracker and
SCM roles configured, done additionally means the reviewed PR is merged and
AI-DLC accepts every finish gate.
