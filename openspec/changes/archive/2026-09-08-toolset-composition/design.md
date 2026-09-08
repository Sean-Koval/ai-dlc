## Context

This child implements remaining PT-01/PT-04 of #19. Root authorized isolated work from 519b199 with connection dependency ab7cecb. Jira owns its own definition and adapter; definition enumeration automatically exposes that tracker after dependency integration. GitHub is recommended for personal projects; omitted old API inputs retain Linear, Claude Code and Codex.

## Decisions

A pure plan validates capabilities, provider role membership and renderer-supported clients. Trusted ProviderDefinition entries own non-secret scaffold defaults. New trackers need a registration, not CLI vendor branching. Jira emits only its kind until explicit connection setup supplies verified identity/auth; no invented IDs or default credentials. Copier answers persist selections and settings so updates reuse them. Template fallback defaults exist solely for historical answers/direct Copier callers.

The existing schema-1 component metadata remains unchanged in structure. Trusted definitions may declare a bounded existing-directory configuration path, optional viewer and lifecycle availability. Obsidian reads only paths.vault, matching Registry and Knowledge; no provider-local alternative is treated as configured. Inspection expands the user path and checks the real existing directory without creating files, reading note contents or claiming write access/live qualification. Optional viewer absence in headless environments does not block note operations. Plane's declared absent lifecycle adapter remains a blocking independent readiness dimension even when its native guidance is delivered.

No native renderer, provider API, WorkService or credential semantics change. Client selection is configuration; render remains the existing explicit owned operation. Preview does not mutate the destination or install/authenticate tools. Preserve existing staged conflict and three-way update behavior.

## Verification

Real Copier adoption and versioned sync regressions cover explicit selections, old answers, authored conflicts and CLI repeats. Definition-registration tests demonstrate extension without vendor branches. Local filesystem readiness cases cover absent/non-directory/present vaults, alias configuration and headless GUI separation. Required manifest checks and strict OpenSpec validation precede independent review. No live provider/client qualification is claimed.
