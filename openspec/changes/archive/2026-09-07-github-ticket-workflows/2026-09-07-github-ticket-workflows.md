> Historical record. Retained for provenance, not current implementation guidance.
> Consult docs/index.md, canonical OpenSpec requirements and the tracker.

# GitHub ticket workflows execution plan

Spec: [github-ticket-workflows](../../../specs/github-ticket-workflows/spec.md).
User authorized implementation, with GitHub Issues and Projects selected. Parent
portability plans remain active; document setup is deferred. Use TDD and independent
review per task. Preserve Linear behavior, provider integrity, hashes and gates.

## Task 1: Capability contract and work start

Add optional capabilities operation to contracts and generated schemas. Schema 1
response: lifecycle {in_progress: bool, closed: bool}, optional_operations list[str].
Declare support before invocation via registry definitions/explicit external opt-in;
registered test providers can explicitly declare support. Built-in Linear/GitHub
report truthful semantics. Work start uses it without provider-name dispatch.
Absence alone enables legacy fallback; opted-in failures refuse. Preserve existing
unsupported-start response and report legacy capability as unverified. Do not
change binding fingerprints. Test first, verify red/green, run focused checks,
commit only owned files. Covers GT-01.

## Task 2: GitHub Issues and Projects

Extend existing gh issue adapter with optional Projects v2 helper. Keep issue-only
working; add configured board field/options; validate ids against remote project,
field/options and issue origin. Paginate membership, recover partial create/attach
without duplicate issue or unsafe blind retries. State includes native issue and
planning metadata; in_progress may map to board state while issue stays open.
Terminal issues must not be silently reopened. Distinguish not-planned closure.
Test mutation sequences, identity and uncertainty before implementation. Covers
GT-02/03. Preserve capability interface from Task 1.

## Task 3: Selection and guided setup

Add explicit tracker input to scaffold/adopt with legacy default preservation.
Reuse existing configuration preview/apply discipline for GitHub host/account,
repo and optional Project discovery. Offer names, validate ambiguity/completeness,
bind exact plan to config/resource identity and revalidate at apply. Keep credentials
local and support gh auth. Preserve Linear compatibility. Avoid agents.py/SAN-12
changes; no new MCP server is required for gh-backed lifecycle. Covers GT-04.

## Task 4: Portable migration

Implement common default-only and selected verified-target mapping from parent
migration plan. No remote create implicitly; exact create intent requires reviewed
plan/reconciliation before local apply. Freeze retained effective bindings and
preserve old aliases, non-tracker refs, unselected bytes, gates. Test with distinct
provider aliases and GitHub/Plane-like fixture capabilities without claiming a
shipped Plane adapter. Covers GT-05.

## Task 5: Qualification and report

Run all required checks and strict specs; independent whole-branch review. Inspect
live destination only when supplied/authorized. Preview active/planned migration
and its missing remote-only information; apply only a concrete reviewed mapping.
Missing live input is a reported release gate, not a reason to invent service
success. Record parent Plane/Jira work as remaining. Covers GT-06.
