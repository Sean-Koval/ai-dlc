## 1. Rendering freeze (#196)

- [x] 1.1 Remove `target` from `render_agents`, `_render_agents` and `render_windows` and their call sites; add a signature test.
- [x] 1.2 Remove the `devcontainer`, `codex-cloud` and `claude-cloud` targets and their special-casing; refuse removed and unknown targets naming hangar; move the dev container and cloud shims to `local`.
- [x] 1.3 Add the freeze comment above `CLIENT_SKILL_DIRECTORIES` and the ADR 0001 line.

## 2. Hook floor and client pins (#197)

- [x] 2.1 Replace exact fixtures with `min_version` per client and compare dotted integers; warn on unset versions.
- [x] 2.2 Pin `claude-code` 2.1.296 and `codex` 0.162.1 with a source comment; add `scripts/check_client_pins.py`.
- [x] 2.3 Update rendering tests to floor semantics and add refusal tests for removed targets.

## 3. Delivery

- [x] 3.1 Update architecture, tool map, machine-enrollment runbook and migration notes, record documentation dispositions and run `ai-dlc project check --required`.
