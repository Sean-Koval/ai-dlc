# Redacted effective-environment export and comparison

Priority: P1. Product owner: Sean Koval. Implementation owner: unassigned. Status: proposed for review; no implementation or qualification performed.

## Problem and outcome

Machine status currently measures enrollment/cache/credential drift; equal 0.4.0 labels can conceal a newer source checkout. Teammates need to compare intended tools and guidance with actual engine/runtime/client state without exchanging secrets or copying global client state.

## Authorization and proposed delivery

The user authorized specifications and detailed issues from the PM review. Recommended technical design extends existing status/doctor with an opt-in schema-1 export and offline compare; it is subject to product/engineering review before implementation. Preserve default CLI behavior and existing services.

## Acceptance contract

- EER-01: Opt-in scoped export/offline doctor reuse local collectors, retain unknowns and perform no provider health/network/native-session work. Executable version probes require explicit `--probe-versions`; default export uses known metadata only.
- EER-02: Report current-process versus PATH-selected engine and release/source provenance, pinned profile/team-source identities, desired/observed runtime and client edition/version, portable config and managed guidance. Equal version alone is insufficient.
- EER-03: Positive privacy projection, bounded schema, safe output publication and deterministic configuration/observation identities. No secrets, private paths, accounts, raw command/config dumps or copied global state, including hashes of excluded secret content. Unestablished safe digest inputs remain unknown. Excluded arbitrary check commands and software state are not proven equivalent. Presence does not prove authentication.
- EER-04: Compare two exports offline with blocking, expected-platform, informational and unknown findings; validate input and never open embedded paths/URLs or run embedded commands.
- EER-05: Bind downstream native evidence to complete identities and invalidate changed contexts, including a changed compatible client version. Mocks do not establish qualification.

## Concrete delivery and dependencies

Proposed commands: `machine status --root PATH --export FILE`, `machine status --compare LEFT RIGHT`, and opt-in doctor `--effective-environment`. Design fixes schema fields, canonical digest inputs, limits, exit codes and drift classifications. No Windows implementation dependency; unsupported observations are explicit. Native harness verification consumes this identity contract. Actual paired machine/client walkthrough remains #53.

## Errors and evidence

Malformed/oversized/unsupported exports and unsafe output destination fail with exit 2 and safe bounded messages. Compare blocking/unknown required state exits 1; expected differences remain visible. Cover release versus source at 0.4.0, dirty/unknown provenance, edited guidance, compatible runtimes, supported/unsupported OS, probe timeout, malformed inputs and secret sentinels. Record real host evidence only when observed and privacy-reviewed. No paid evaluation or remote writes required.

## Documentation and exclusions

Review existing machine-enrollment runbook, architecture, tool map, work-computer setup and release verification; record content-bound dispositions during delivery. Exclude dashboards, new diagnostics services, synchronization, account/login copying, automatic OAuth, publication and broad native parity claims.

## Authoritative scope

[Product direction](../../../docs/product-direction.md), [proposal](proposal.md), [design](design.md), [EER requirements](specs/effective-environment-report/spec.md) and authoritative unchecked [tasks](tasks.md). These planning artifacts do not establish implementation approval, readiness or release qualification.
