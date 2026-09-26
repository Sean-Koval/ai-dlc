## Why

Teams already own their check commands in `ai-dlc.toml`, but the edit loop can
only run all required commands or all declared commands through the shared check
service. A small explicit selector makes focused verification convenient without
changing what qualifies as completion. Two generated defaults also need more
honest evidence: frontend smoke currently exits successfully without a server,
and a new Python application receives only a syntax check.

## What Changes

- Add repeatable `ai-dlc project check --check ID` selection using existing
  `[checks.commands]`; retain the full configured required list in every receipt.
- Require configured frontend smoke to execute successfully; missing `BASE_URL`
  becomes an actionable failure, including direct execution of the generated test.
- Give newly initialized Python projects a dependency-free behavioral starter
  test and a small standard-library runner that rejects empty/all-skipped suites.
  Keep the separately named syntax check and preserve adopted project content.
- Document focused checks during edits and the complete required run before
  merge; teams keep their chosen tools and replace/extend starter checks as their
  application grows.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `portable-development`: explicit focused selection and meaningful Python
  starter checks, with unchanged full-evidence completion requirements.
- `frontend-capability-pack`: missing server configuration no longer counts as a
  successful required smoke check.

## Impact

Existing check service and CLI, generated Python/frontend assets and their tests.
No new MCP surface: MCP does not currently expose project check. No schema,
workflow DSL, automatic affected-file inference, result cache or finish relaxation.

Canonical documentation owners are [README](../../../../README.md) for check usage,
[portable project guidance](../../../../project-templates/project/AI-DLC.md), and
[frontend workflow](../../../../project-templates/project/docs/workflows/design-to-implementation.md)
with its repository counterpart. Review existing greenfield/brownfield workflow
instructions and catalog mappings; update existing explanations and record
content-bound dispositions instead of introducing another guide.
