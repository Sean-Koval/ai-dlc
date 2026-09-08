# Conditional credential readiness repair

This bug repair implements the existing PT-04 local-credential readiness contract
in the provider-toolset-onboarding change. The integrated Jira Basic path could
report offline readiness with a populated token and a missing required email
reference/value. Jira correctly refused authentication construction, but shared
readiness inspected only the token.

Trusted provider definitions now declare bounded environment requirements: a
provider configuration field, optional default environment name, and optional
exact configuration condition. Jira requires token_env for both supported modes
and email_env for personal_scoped_token_basic. OAuth remains token-only. Linear's
existing default and logical credential ID are retained through the definition.
Unknown/custom providers retain their explicit token_env compatibility behavior.
No project data loads callbacks or code, and no Jira branch was added to the
credential service, CLI or WorkService.

Missing/invalid references remain visible as unconfigured requirements; absent or
whitespace-only environment values are not present. Reports expose variable names
and presence metadata, never values. Explicit declarations covering the same
provider alias and variable deduplicate. Generated IDs retain provider.<alias> for
tokens and use provider.<alias>.<field> for additional inputs; deterministic numeric
suffixes avoid overwriting any explicit logical credential, including collisions
with the old token ID. This is local presence checking, not validation of account
identity, token scopes, email syntax or successful authentication.

## Evidence

The first test run reproduced 25 failures with 13 passing compatibility cases.
The new cases cover both Jira aliases, missing/empty/invalid references, absent and
blank values, actual offline false-readiness, Basic/OAuth selection, explicit
coverage, generated-ID collisions and a synthetic third trusted definition.
After the repair, 50 credential/readiness cases passed. The wider affected suite
passed **179 tests in 2.24 seconds**, including common connection, Jira provider,
onboarding, WorkService and component boundaries. Repository-wide format and lint
checks passed; the prepared interpreter type check reported zero errors, warnings
or information messages. `git diff --check` passed. These checks used frozen source
and tests based on 03d5cbe before the final evidence/commit metadata was written.

The existing prepared environment was reused on a new branch from 03d5cbe; no
bootstrap, download, package build or full suite was run because host disk space
was constrained. Exact integrated required checks, independent review and delivery
remain coordinator-owned. The immutable Jira implementation/repair references and
Plane candidate were not modified. These fixtures do not establish native-client,
company Jira, platform or live-service qualification.
