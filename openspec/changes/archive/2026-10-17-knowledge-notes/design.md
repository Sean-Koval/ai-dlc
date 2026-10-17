# Design

## Observed implementation

`store_learning` journaled the supplied body under the learning operation ID and
wrote it unchanged; recall returned `{path, first_line}` after skipping a leading
`---` block. `docs check` never read `docs/decisions/`. The ADR template was plain
text. No JSON Schema validator is a dependency; contract schemas are generated
from Pydantic models.

## Decisions

- **One model, generated schema.** `KnowledgeNote` (Pydantic) validates and
  generates the JSON Schema, with the kind rules (`learning` needs a source,
  `decision` needs `status`, other kinds refuse `status`/`checks`) both in the
  validator and as `allOf` conditions in the schema. Extra keys are allowed so
  neighbouring tools can add fields additively; the schema itself adds nothing
  beyond the plan's list and `work`/`repository`.
- **Checks use flightdeck's grammar** (owner decision on #207). Each entry is a
  `flightdeck.spec/v1` spec without its header: `id`, `assert` with one operator,
  optional `scope`, `harness`, `applies_when` and `severity`. AI-DLC checks shape
  only and never evaluates; the issue's example `predicate:` string is not used.
- **Idempotency.** The operation fingerprint stays the supplied body, so a
  different body still conflicts. The generated note is journaled with the path
  in the existing `:path` record, so a retry on another day, or with a different
  `AI_DLC_AUTHOR`, writes byte-identical content.
- **Filling, not rewriting.** Missing keys are appended inside the supplied
  frontmatter block; supplied lines, comments and values are kept verbatim.
- **Author.** `AI_DLC_AUTHOR` wins (normalized to `agent:` when it has no
  prefix); the CLI asks `gh api user` for `human:<login>`; MCP without the variable
  records `agent:unknown`. Nothing is read from other sessions.
- **Hash prefix.** A merge commit is a Git object ID, not a SHA-256 content hash,
  so sources record `git:<sha>`. The schema accepts any `<algorithm>:<value>`.
- **Accepted-record rule.** The working-tree body is compared with
  `git show HEAD:<path>` when the committed version has frontmatter with
  `status: accepted`. Frontmatter edits are allowed; body edits need
  `status: superseded`, which in turn needs `valid_to`. Records without
  frontmatter are reported as `info`. Decision errors make `docs check` exit 2
  without `--strict`, and the documentation gate sees them as error findings.

## Documentation impact

`local-and-shared-knowledge.md` owns the learning format and replaces the old
four-field description; `project-documentation.md` owns the decision checks; the
template's decisions README owns the adopted-project convention.
