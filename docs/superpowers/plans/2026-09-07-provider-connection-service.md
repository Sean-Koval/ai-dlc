# Provider connection service implementation plan

> Execute this authorized bounded child sequentially; no helper agents or remote mutations.

Goal: supply reusable named onboarding with real shared exact-plan/apply safeguards while preserving both legacy codecs.
Spec: openspec/changes/archive/2026-09-07-provider-connection-service. Parent: GitHub issue19.

1. Test generic selection parsing, actual third-handler save/apply, drift/account/incomplete discovery refusals, authored comments/collisions and unsupported setup. Run red before implementation.
2. Extract GitHub snapshot/render/exclusive storage/exact apply helpers to connections.py. Add provider_definitions.py and common service, preserve provider_onboarding.connect_provider compatibility and GitHub Project journaling. Run existing GitHub and Linear suites.
3. Add named Linear organization/team/status lookup after complete discovery; preserve canonical plan IDs/state types and legacy same-plan/comment-only semantics. Run focused regression cases.
4. Freeze source, run source-specific shim required checks and strict OpenSpec, commit evidence. Independent review/integration are coordinator-owned; leave archive/remote completion pending.

Owned files: provider_definitions.py, connections.py, provider_onboarding.py, github_onboarding.py, CLI connection route, scoped tests/spec/design/evidence. Do not edit client rendering, readiness, templates, modules or global roadmap.
