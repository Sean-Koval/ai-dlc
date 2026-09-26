# Repository workflow

The repository owns durable architecture, product rationale, decisions, and runbooks. When selected, the specification role owns formal behavior specifications and the tracker owns priority and lifecycle status. Local setup and verification work without those roles. Personal knowledge notes remain personal and link durable repository material.

Start with the [Development workflow](docs/development-workflow.md). It links the greenfield and brownfield paths, the design-to-implementation contract, and the current role-to-tool map.

Portable personal profiles belong in a separate private Git repository and are
enrolled at a pinned revision. Each machine maintains its own binding for local
paths, account selection, and credential environment-variable names. Keep
credential values in a password manager, keychain, or process environment;
never commit `.env` files or values to AI-DLC Git files. Local CLI and MCP
execution are current; hosted or cloud execution remains a later qualification
target. MCP exposes reviewed work, doctor, and selected knowledge services;
machine enrollment mutation remains CLI-only.

Select scm.repository and provider account/environment references before external operations. Every preset checks generated agent files. New-project initialization also creates a minimal language app and requires its syntax/compiler check. Python additionally runs a standard-library behavior test of its greeting output; empty or entirely skipped suites fail. First setup creates its lockfile and later setup is locked. Adoption leaves existing application manifests/source untouched and requires existing language lockfiles. Add acceptance tests and further required check IDs as behavior develops.

During edits, use `ai-dlc project check --check ID`, repeating `--check` to run
other configured commands in the requested order. A selected optional command is
allowed; combining selection with `--no-required` is refused. Partial receipts
retain the full required list and cannot replace missing completion evidence.
After integrating the target branch, run `ai-dlc project check --required` before
merge. Keep the team's existing tools and commands in `checks.commands` and
select required acceptance checks in `checks.required`; generated tests are a
starting point, not coverage of the developed application.

This project's `scripts/bootstrap.sh` runs in release mode: it installs the AI-DLC engine named by `bootstrap/release.sh`, a hash-bound manifest from a published AI-DLC release. An engine that was itself installed from a release writes that file when it generates a project; an engine running from an AI-DLC source checkout cannot, and reports `"release_manifest": "absent"`. In that case add `bootstrap/release.sh` from a published release before enabling CI, verify it against the release's `SHA256SUMS`, and never download an unpinned latest script.

## Documentation upkeep

Read [documentation guidance](docs/documentation-guide.md). Search the project map, catalog and canonical specifications before creating a document. Update existing authoritative docs, record owners and sources, and review affected docs with code changes. Keep private notes separate from shared drafts.

For documentation changes, use the [documentation ownership and review workflow](docs/documentation-guide.md). Review affected sources and canonical documents before adding another explanation; record an evidence-bound disposition when the project enables documentation checks.

## Optional frontend capability

The node `frontend` capability adds Playwright smoke and screenshot evidence.
Use `--capability frontend` alongside any desired provider roles. Set `BASE_URL`
for a running app; missing or empty configuration fails with a setup remedy before
package or browser tools run. Direct Playwright execution also requires this URL. Install the exact
`@playwright/test@1.58.2` development dependency during setup (initialization
already declares it; adoption preserves your package manifest), then run
`npx --no-install playwright install chromium`. Required checks install neither
packages nor browsers. `ai-dlc design capture --url URL` records viewport PNGs
and a manifest under ignored `.ai-dlc/local/design/`; see the
[design handoff](docs/workflows/design-to-implementation.md) for selectors and evidence limits.
