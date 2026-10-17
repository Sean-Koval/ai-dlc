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

Each record starts with knowledge-note frontmatter, the same schema learnings use
(`knowledge-note.schema.json` in the AI-DLC contracts):

| Field | Meaning |
| --- | --- |
| `id` | `decision/<file name without .md>` |
| `kind` | `decision` |
| `scope`, `label` | who it applies to (`personal`, `project`, `team`) and its sensitivity (`internal`, `confidential`) |
| `status` | `proposed`, `accepted`, `superseded` or `rejected` |
| `sources` | evidence as `{uri, hash}` pairs, such as the pull request and its merge commit |
| `author` | `human:<github-login>`, or `agent:<model>@<digest>` for an agent-drafted record |
| `confidence` | `low`, `medium` or `high` |
| `valid_from`, `valid_to`, `review_by` | when it took effect, when it stopped (null while current) and when to look at it again |
| `supersedes` | ids of the records this one replaces |
| `checks` | optional trace checks, described below |

## Accepted records are superseded, not edited

Once a record is `accepted`, its body does not change. To change a decision, add a
new record with `supersedes: [decision/NNNN-old-slug]`, and in the same pull
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
`applies_when` and `severity` (`warn` or `fail`). AI-DLC checks only that shape;
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
