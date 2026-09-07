# Provider connection service verification

This is the bounded common-service child of [issue 19](https://github.com/Sean-Koval/ai-dlc/issues/19).
Its [PC-01–PC-04 specification](../../openspec/changes/provider-connection-service/specs/provider-connection-service/spec.md)
and [design](../design/provider-connections.md) cover trusted definitions,
generic named selections, common declarative-handler persistence and compatibility.
They do not close the mixed-scope provider-toolset-onboarding parent.

## Local evidence, 2026-09-07

The source checkout was based on `631d10a034ba319e76c564a43ad34c641695117d`.
`ai-dlc project check --required --receipt .ai-dlc/local/provider-connections-required.json`
passed generated, format, lint, types and test. The full suite reported **1,165
passed in 185.35 seconds**. The ignored receipt identifies target `local`, base
revision `631d10a034ba319e76c564a43ad34c641695117d` and `dirty=true`: this was a
frozen candidate before its delivery commit, not a clean-revision or merged-CI
receipt. Only this evidence document and task completion metadata were changed
after those checks; the tested Python and test files were unchanged.

The explicit source shim was
`/Users/seankoval/.local/share/ai-dlc/bootstrap/source-781071990/bin`, followed by
the bundled bootstrap tool directory in PATH. The imported package was confirmed
to be this worktree's `src/ai_dlc`; a shared convenience symlink was not relied on.
All **16** OpenSpec items passed `openspec validate --all --strict`.

Before implementation the retained Linear/GitHub onboarding suites reported
129 passing cases. The new declarative-provider tests initially failed because
the definition/service did not exist; the actual CLI third-provider case then
failed as unsupported after only adding the definition. Two named Linear cases
failed before name resolution was implemented. A public-facade preservation
case exposed GitHub's Project-specific refusal in the extracted renderer; that
rule is now enabled only by GitHub. The same case exposed a returned string
plan path that needed normalization before apply. The final focused suite
reported **156 passed** across `test_connections.py`,
`test_provider_onboarding.py`, `test_github_onboarding.py` and
`test_github_project_defaults.py`.

## What those tests establish

| Requirement | Evidence |
| --- | --- |
| PC-01 | A synthetic third kind uses the real CLI and common API for discovery, save and apply with no new CLI provider branch. Its callbacks return metadata/patches, not filesystem writes. A definition without a setup handler refuses without altering lifecycle configuration. |
| PC-02 | Real local files exercise canonical name/ID selection, complete discovery, account/resource/source/work drift, exclusive plan collisions, symlink confinement, authored TOML refusal/preservation and changes after acquiring the apply lock. Known credential-shaped metadata is refused without echoing the sentinel. |
| PC-03 | Existing Linear and GitHub suites retain canonical/comment-only versus exact-byte behavior, saved-plan protections, late runtime/stage/work checks and default Project journal coverage. New CLI cases cover Linear names, ambiguous names, GitHub named Project selection, issues-only boolean selection and generic/legacy conflicts. |
| PC-04 | Discovery is fixture-driven; configuration files and local filesystem operations are real. No live account, tenant, client or platform claim follows from those fixtures. |

The common exact writer retains the previous GitHub checks and intentionally
retains failed/replaced stages and empty private directories. Its guarantees
remain bounded against same-user races; extraction does not add crash-atomic
multi-file transactions or a hostile-code sandbox.

## Remaining delivery and qualification

- Independent review and any findings remain pending before integration.
- Linear's canonical persistence/recovery and GitHub's remote Project journal
  remain explicit compatibility boundaries; full parent PT-02 extraction is
  not claimed.
- Native Claude/Antigravity connection rendering, real authentication, work
  laptop tooling, Jira Cloud lifecycle work and tenant/platform qualification
  are separate work. Confluence remains deferred.
- PR, archive, merge, merged-revision CI and work finish are coordinator-owned
  and were not performed by this child. No remote service state was mutated.
