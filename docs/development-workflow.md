# Development workflow

Install the pinned runtime and project dependencies through the reviewed bootstrap. Select provider accounts and repository identity explicitly. Keep machine-local paths and environment variables in the machine scope.

Use the day-start skill to reconcile priorities and evidence. Use discovery for unclear problems, prd-draft for product rationale, needs-spec for the reviewed formal specification decision, and spec-from-prd for approved behavior. Review scope and acceptance criteria before publishing work. Implement on the work branch, run project checks, and finish through the service so merged PR, green CI and current specification evidence are checked. Use day-end and handoff to preserve verified continuity; review-inbox helps triage new requests without automatically publishing them.

## Project adoption

`ai-dlc project adopt` previews files; apply only after reviewing conflicts. Existing managed-path files are conflicts, including user-authored configuration or docs. Generic installs no language toolchain. Adoption presets expect existing application manifests and lockfiles, and never create application source. New-project initialization creates a minimal no-dependency language application. Its first setup explicitly creates the lockfile; later setup uses the lock without updating it. Every preset requires the generated-agent-file check; initialized language projects also require a real syntax/compiler check. Extend these baseline checks with acceptance tests as application behavior develops.

The Python adoption API accepts `template_source` and `vcs_ref`. For portable updates, use an accessible Git template URL and immutable release tag. Copier creates its own answers recording source/revision. A bundled local template can bootstrap a project, but cannot provide portable updates until distributed as a versioned Git template. Never hand-edit Copier revision history to manufacture upgrade support.

Sync copies the checkout into a temporary Git repository and lets Copier perform its update there. Conflicts leave the original untouched. Application files are retained; .git metadata is never copied back. File application uses replacement writes and rollback on ordinary errors; a power-loss-safe multi-file transaction is not claimed.

## CI and release

The generated single-job `.github/workflows/verify.yml` runs reviewed bootstrap artifacts and required checks, then uploads its `ai-dlc-receipt` artifact. Repositories with a matrix, including AI-DLC itself, declare every exact expected artifact name in `scm.receipt_artifacts`. Completion reads that declaration from the authenticated merged revision and validates every expected receipt; one missing, malformed, dirty, mismatched, or expired receipt blocks completion. Until a signed/pinned release location exists, supply bootstrap/release.sh and the artifact lock from the published distribution; do not insert a made-up release URL. The release gate must check clean-machine bootstrap and artifact integrity.

Skill release requires no-guidance control and skill-enabled model runs using agents/evaluation.toml and scenarios. Preserve outputs and human scoring. The fixture configuration alone is not a passing behavioral evaluation.

Adoption accepts selected role capabilities (specs, tracker, knowledge, scm, deploy, agent-client); omitted selection enables all defaults. Selection is recorded by Copier and controls provider-role configuration; the GitHub workflow is omitted without SCM. Shared repository docs and bootstrap remain available. Rebind accepts optional machine configuration for validating existing bindings but never writes machine data into the project configuration.

Snapshot and staging skip .git, language dependency folders, common tool caches, .ai-dlc/local, and Git-ignored untracked paths. These runtime files remain untouched in the destination. A checkout edit detected after staging aborts application and asks for a fresh preview/retry.
