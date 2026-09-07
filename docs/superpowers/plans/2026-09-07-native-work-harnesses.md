# Native work harness implementation plan

Spec: [native-work-harnesses](../../../openspec/changes/native-work-harnesses/specs/native-work-harnesses/spec.md).
Current authority: [roadmap](../../roadmap.md), GitHub #19 and the maintainer's
Claude/Antigravity work-computer request. This bounded child adds project support;
common provider connections and Jira follow as separate implementation slices.

1. Test the actual Claude renderer's remote definition and ownership upgrade from
   a prior URL-only entry. Add the required HTTP type; run rendering regressions.
2. Test explicit Antigravity selection, native paths, real JSON/rule ownership,
   repeated render, authored conflicts and Codex shared skills. Implement through
   existing managed planning; reconcile with #10's preservation changes on integration.
3. Test readiness file drift and missing client evidence; reject unsupported hooks
   and unqualified env mapping. Report actual native login/recognition separately.
4. Document engine bootstrap versus adopting another repository, project client
   selection, native rule activation, MCP login, Obsidian boundaries and a harmless
   fresh-session qualification. Do not imply Jira adapter or global config exists.
5. Run required project checks and strict OpenSpec validation, independent review,
   then integrate with #10's preservation fixes and record remaining live checks.

Each behavior follows TDD. No machine/global configuration or work-service remote
state is changed by preparing this implementation. Credentials remain local.
