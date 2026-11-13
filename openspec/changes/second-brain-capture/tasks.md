# Tasks

## 1. Decision and schema

- [x] 1.1 Write ADR 0003 amending the freeze for the second-brain module
- [x] 1.2 Add capture kinds and `origin`, `lane`, `source`, `publish` to `KnowledgeNote`; regenerate the schema (KC-01)

## 2. Guard and contract

- [x] 2.1 Add `knowledge_publish` with source dedupe, the origin/site wall, plan and record (KC-02, KC-03, KC-04)
- [x] 2.2 Add `ai-dlc knowledge captured`, `publish-plan` and `publish-record`
- [x] 2.3 Add the optional `publish` knowledge operation to the provider contract

## 3. Skills and plugin

- [x] 3.1 Add `daily-note`, `capture` and `kb-publish`; remove `day-start`, `day-end`, `review-inbox` and `needs-spec`; move the specification decision into `spec-from-prd`
- [x] 3.2 Relock the skills and rebuild the workflow plugin (WP-02)

## 4. Documentation and checks

- [x] 4.1 Update the knowledge design, tool maps, plugin README and playbook
- [x] 4.2 Add tests for the schema, dedupe, the wall, the version guard and the contract
- [ ] 4.3 Use phase A for two weeks on both machines before any phase B work (Sean)
- [x] 4.4 Superseded: KAN-430 retires note publishing; `knowledge render` writes the wiki, and its live qualification is tracked there
