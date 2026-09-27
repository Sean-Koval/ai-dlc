# Proportionate push policy design

## Authority and observed disagreement

The [product direction](../../../docs/product-direction.md) allows selected team workflows and small artifacts. `docs/development-workflow.md` permits a PR-only path without a tracker or specification decision. However `harness/hooks.py` denies recognized direct pushes and `gh pr create` when no reviewed record with a tracker reference matches the branch. This is an optional hook; projects not requesting it are unaffected. Canonical native-harness requirements do not currently define an alternate push policy, so PPP requirements are additive rather than silently rewriting the existing default.

## Configuration contract

Use one scalar: `[agents] bound_push_policy = "all-branches" | "tracked-branches"`. Omission means `all-branches`. Only the project layer may supply this field. Personal, machine and team-source values are rejected even though some other agents settings support those layers. Unknown values or invalid types are errors before managed rendering or hook allowance. Do not infer an opt-in from absence of tracker configuration.

This setting affects only the existing optional `bound-push` feature. It neither enables hooks nor changes their supported client/version/target matrix. The ordinary classification and destructive denial remain prior constraints.

## Decision flow

Resolve the current branch and inspect local work records using existing offline validation helpers, without initializing provider clients or operation journals. A matching record means the branch is tracked regardless of reviewed status or missing fields. Invalid matching records, an unreadable record whose association cannot be determined, unavailable branch identity, or malformed policy produce a clear denial. A branch is unbound only after a complete readable inventory establishes no matching record.

For `all-branches`, an unbound branch still receives the existing reviewed-work remedy. For `tracked-branches`, a truly unbound branch is allowed by this hook; regular checks, native approvals and repository review rules still apply. For either mode, a tracked branch is allowed only if one or more records belong to it and every matching record is valid, reviewed, has a tracker reference and has valid local bindings. Do not query remote tracker state in a pre-tool hook. A local provider-identity drift is not waived by lightweight mode.

No path-, size- or branch-name classifier is involved. A team can intentionally choose a lower-friction mode, but the implementation cannot guess that a change is safe because it appears to be documentation. The setting does not enforce arbitrary wrappers or terminal operations outside current coverage.

## Compatibility and results

Retain the native hook response shape and existing destructive-operation behavior. Reasons distinguish strict unbound denial, invalid tracked state, unsupported payload coverage and explicit lightweight allowance. Generated guidance names the policy only when the bound-push feature applies and explains that all-branches requires a record even for a PR-only change. Unknown policy must fail visibly rather than fall back to permissive behavior.

The authorization boundary is shared checked-in policy, not an agent's runtime decision. No new work record schema, local waiver storage or tracked-change heuristic is needed.

## Verification and documentation

Test the two modes against valid, unreviewed, malformed, missing-tracker, provider-drifted, multiple-valid-record and unbound branches; test non-project configuration rejection and unchanged destructive denials. Use temporary repositories and invoke the real hook service. Native fixture results remain fixture evidence. Review development workflow, relevant client setup guidance and config examples together, record their content-bound dispositions and maintain catalog mappings.

## Dependencies and open inputs

No hard dependency on another proposed slice. Existing config ownership, work validation and hook renderer services are the interfaces. Team owners choose whether to opt in; default behavior remains strict. Actual native version qualification remains a separate platform task and is not a precondition for testing this policy's offline behavior.
