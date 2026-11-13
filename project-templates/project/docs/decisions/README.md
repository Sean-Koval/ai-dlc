# Decisions

Record each consequential choice as one decision record in this directory. Git is
the source of truth for decisions and the pull request is the only way to change
one.

## Files and numbering

Name records `NNNN-slug.md` with a four-digit number one higher than the last, for
example `0007-landing-stays-in-hangar.md`. Start from
[`docs/templates/adr.md`](../templates/adr.md). The body has the sections Context,
Options considered, Decision, Consequences and Links.

## Frontmatter

Each record starts with knowledge-record frontmatter
(`knowledge-record.schema.json` in the ai-dlc contracts):

| Field | Meaning |
| --- | --- |
| `id` | `DEC-NNNN`, the file's number |
| `type` | `decision` |
| `scope`, `label` | who it applies to (`personal`, `project`, `team`) and its sensitivity (`internal`, `confidential`) |
| `status` | `proposed`, `accepted`, `rejected` or `superseded` |
| `date`, `owner` | when it was recorded and who owns it |
| `sources` | evidence as `{resource, hash}` entries, such as the pull request and its merge commit |
| `links` | typed links; `{type: supersedes, target: DEC-NNNN}` names a replaced record |
| `author` | `human:<github-login>`, or `agent:<model>@<digest>` for an agent-drafted record |
| `confidence` | `low`, `medium` or `high` |
| `valid_from`, `valid_to`, `stale_after` | when it took effect, when it stopped and when to look at it again |
| `checks` | optional trace checks, described below |

Older records with `kind: decision` frontmatter are still read, with a deprecation
warning; `ai-dlc knowledge migrate --write` rewrites them.

## Accepted records are superseded, not edited

Once a record is `accepted`, its body does not change. To change a decision, add a
new record with a `supersedes` link to `DEC-NNNN`, and in the same pull
request set the old record to `status: superseded` with a `valid_to` date.
`ai-dlc docs check` validates the frontmatter of every record that has it and fails
when the body of an accepted record differs from the committed version unless its
status changes to `superseded`. Records without frontmatter are reported, not
failed.

Agent-drafted records arrive as pull requests labelled `agent-drafted`; review them
like any other change.

## Checks

A record may carry `checks:`, trace predicates that flightdeck evaluates every
night against recorded agent runs. Each entry uses flightdeck's behavior-spec
grammar (`flightdeck.spec/v1`): an `id` unique within the record, an `assert` with
one operator and optional `scope` (`turn`, `job` or `session`), `harness`,
`applies_when` and `severity` (`warn` or `fail`). ai-dlc checks only that shape;
it never evaluates a predicate.

```yaml
checks:
  - id: landing-stays-in-hangar
    scope: job
    assert: {never: {event: pr.merge, where: {hangar.pr.merged_by: {not: "hangar-landing[bot]"}}}}
```

Loosening or deleting a check needs a reviewer other than its author. Enforce that
with branch protection and a CODEOWNERS entry for this directory, for example:

```text
# .github/CODEOWNERS
/docs/decisions/ @your-org/decision-reviewers
```
