# Publish a versioned AI-DLC release with bootstrap artifacts

## Why
Nothing AI-DLC promises for other repositories is usable yet. `project-templates/project/AI-DLC.md` says the template needs release bootstrap artifacts before CI can run and that no public release location is assumed; `README.md` says there is no published v4 bootstrap release. The template's `scripts/bootstrap.sh` runs in release mode by default and refuses without `bootstrap/release.sh`, and nothing generates that file. Until a release exists, `ai-dlc project init` and `ai-dlc project adopt` only work from this source checkout, so every downstream feature is theoretical. Issue #71 records the gap.

The pieces exist separately: `uv build` produces the wheel, `scripts/release_manifest.py` produces a hash-bound manifest from real artifact bytes, release-mode bootstrap installs a verified wheel and constraints, and the release workflow builds a candidate artifact from a manual base URL. Nothing connects a tag to published assets, and nothing carries the manifest into generated projects.

## What Changes
- A release SHALL be published only from a Git tag whose version equals the engine version, through the release workflow, which builds, verifies and publishes exactly the verified assets with their digests; a manual run still produces only a candidate artifact.
- Release-mode bootstrap SHALL retain the manifest beside the installed engine, and project generation SHALL include `bootstrap/release.sh` from the running engine's retained manifest so a generated project's bootstrap and CI can run.
- A source-installed engine SHALL report that no manifest is available instead of generating a project that claims one.
- Documentation SHALL describe the publication procedure and record what the release evidence proves and what remains unqualified.

## Capabilities
### New Capabilities
- release-publication: Tag-driven publication of hash-bound assets, manifest propagation into generated projects, and honest evidence boundaries.

## Impact
The release workflow, `scripts/bootstrap.sh` and its packaged template copy, project generation in `ai_dlc.setup.templates`, the README, the template guidance, a new release runbook and the release verification record. No provider adapter, work lifecycle or finish gate changes. Publishing remains the maintainer's action: pushing the tag.
