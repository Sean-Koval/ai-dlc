# Provider Toolset Onboarding Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans after design review. Do not start later tasks by guessing an earlier interface.

**Goal:** Make provider selection, connection and native harness setup reusable.
**Architecture:** Add a small built-in definition registry and common connection service; compose existing configuration and owned assets.
**Tech Stack:** Existing Python, Copier, Typer and native client renderers.
**Spec:** [provider-toolset-onboarding](../../../openspec/changes/provider-toolset-onboarding/specs/provider-toolset-onboarding/spec.md).

Status: draft. Global constraints from [master plan](2026-09-06-provider-toolsets.md) apply.

## Task 1: Explicit scaffold choices and toolset composition

**Files:** modify `copier.yml`, `project-templates/project/ai-dlc.toml.jinja`,
`src/ai_dlc/templates.py`, `src/ai_dlc/cli.py`; create `src/ai_dlc/toolsets.py`;
test `tests/test_templates.py`, `tests/test_toolsets.py`, `tests/test_cli.py`.
**Interface:** extend `adopt(..., providers: dict[str, str] | None = None)` as an
optional keyword. `plan_toolset(config: dict, selections: dict[str, str]) -> dict`
returns proposed role/provider/server changes plus unsupported capabilities; it
does not write, install or authenticate. Persist provider choices in Copier answers.

- [ ] Add a failing real scaffold regression, retaining existing legacy-default tests:

```python
def test_selected_tracker_survives_scaffold_and_update(tmp_path):
    adopt(tmp_path, apply=True, providers={"tracker": "github-issues"})
    config = load_project(tmp_path)
    assert config["roles"]["tracker"] == "github-issues"
    assert "linear" not in config.get("providers", {})
```

- [ ] Run this case first; expected failure is unsupported provider-selection input.
- [ ] Implement explicit choices and pure composition. Reject incompatible role/provider choices; leave unknown integration capabilities visibly unsupported.
- [ ] Admit the optional documents selection for native Confluence setup without WorkService defaults or publication claims; the later publication change owns its executable contract.
- [ ] Test sync preserving selected providers, omitted options, capability exclusion, project-over-personal precedence, and authored conflicts; run focused tests and commit.

## Task 2: Common discovery, plan and apply

**Files:** create `src/ai_dlc/provider_definitions.py`,
`src/ai_dlc/connections.py`; adapt `src/ai_dlc/provider_onboarding.py`, `cli.py`;
test `tests/test_connections.py` and existing `tests/test_provider_onboarding.py`.
**Interfaces:** `discover_connection(root: Path, provider_id: str, *, environ) -> dict`;
`plan_connection(config: dict, provider_id: str, discovery: dict, selection: dict) -> dict`;
`apply_connection(root: Path, plan: dict, *, environ) -> dict`.
Definitions provide discovery/selection handlers; common code alone owns writes.

- [ ] Add a new-ID test handler with authorized named resources and assert preview/apply works without a Linear branch. Fixture responses must include stable account/resource IDs and complete pagination indicators.
- [ ] Verify red, then extract common freshness, plan persistence, alias identity and locking from Linear's existing flow. Preserve compatibility functions and CLI options.
- [ ] Re-run stale-plan, changed membership, incomplete discovery, authored TOML, concurrent work-binding, no-write refusal and secret-sentinel tests against the common path.
- [ ] Add handler-declared `--select KEY=VALUE` selection, named choices, ambiguous-name refusal and unsupported-handler guidance. Run focused checks and commit.

## Task 3: Native tools and honest readiness

**Files:** modify `agents.py`, `readiness.py`, `provision.py`, `credentials.py`,
`modules/components.json`, `modules/catalog.toml`; add provider instructions under
`agents/providers/`; test rendering, components, readiness, credentials, provision.
**Interface:** consume the toolset plan and existing `agents.servers`; report
capabilities through additional structured results without changing existing check meanings.

- [ ] Add red fixtures for remote HTTP transport mapping, local stdio environment names, account-scoped server deduplication, and configured Obsidian with no GUI.
- [ ] Implement only required client schema fields; preserve shared files free of secrets and machine paths. Pin local connector packages at reviewed versions.
- [ ] Separate optional desktop viewing from local notes storage and tracker API requirements. Missing lifecycle adapter stays blocked even when native connector instructions render.
- [ ] Run offline render twice with network disabled and assert idempotence/authored preservation; run current client recognition and OAuth/stdio smoke checks only in a named live environment.
- [ ] Update source guidance and packaged assets together; run required project checks, strict spec validation, review, and commit. Record unsupported clients/editions explicitly.

Requirement coverage: Task 1 PT-01; Task 2 PT-02; Task 3 PT-03/PT-04.
