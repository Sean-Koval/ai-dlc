# Selectable provider toolsets

Owner: AI-DLC maintainer.
Status: draft for maintainer review, September 6, 2026. Planning requested;
implementation, hosting, account changes, and ticket migration are not performed.

## Problem and audience

AI-DLC prepares a development environment, scaffolds or adopts repositories, and
equips the selected harness to work consistently with the user's tools. A user
should select integrations and authenticate, not edit adapter code or look up
opaque IDs to use a supported toolset. Adding a supported integration is an
implementation task once; selecting it in another repository is configuration.

The immediate user has reached Linear's free limit. Personal projects should use
Plane; work projects use Jira and Confluence. Obsidian remains available for
local document viewing and private daily notes in both contexts. OpenSpec and
repository-owned architecture/runbooks remain as currently configured.

Obsidian can view or edit those repository documents directly. Eligibility for
explicit publication follows the selected document roots and private-note
exclusions, not which editor opens the file.

The [source audit](../planning/provider-toolset-code-audit.md) distinguishes
shipped support from SAN-12's unmerged bundle work. It identifies real gaps in
scaffolding, onboarding, capability handling, and migration UX. Existing upstream
MCP tools should supply general-purpose service access; AI-DLC only needs narrow
adapters for its own deterministic lifecycle and publication contracts.

## Outcomes and acceptance

1. A prepared user can choose a supported tracker and optional team publishing
   provider while scaffolding or adopting, sign in locally, select named remote
   resources, preview the resulting configuration, and render usable harness
   guidance. No manual UUID lookup or changes to AI-DLC source are required.
2. Personal and work projects coexist on one machine with explicit, separate
   account/provider aliases. Opening a work project does not redirect personal
   tickets or publish private notes. A second machine repeats authentication and
   chooses its local vault path without editing shared provider choices.
3. Plane and Jira run the same publish/start/status/finish lifecycle and gates.
   Provider-specific state models, requests, and retries remain behind adapters.
4. Switching defaults for new work and migrating selected retained work are
   separate reviewable actions. Neither silently redirects existing records.
5. Optional Confluence publication shares selected documents and preserves remote
   edits. It does not replace the knowledge role or mirror the Obsidian vault.
6. Tests and live evidence identify exactly which service edition, transport,
   client, and environment have been exercised. Tool installation, sign-in,
   API health, and a complete workflow are distinct evidence levels.

## Scope and exclusions

Four independently reviewable changes: toolset setup/onboarding, tracker adapters,
selective tracker migration, and optional document publication. Native MCP access
can be useful before the AI-DLC lifecycle adapter is available; that distinction
must be explicit in guidance/readiness. A connector login never proves that the
separate CLI/API credential works.

Reuse the Python services, role configuration, component metadata, module recipes,
Copier, native client renderers, provider registry, journals, and finish gates.
No new daemon, marketplace, universal integration language, or replacement for
Jira/Plane/Confluence UI. No automatic provisioning of a Plane server from every
project's bootstrap. No complete ticket-history importer, identity migration,
attachment migration, or bidirectional document sync in the first delivery.

Native Confluence tools already cover ordinary page access and editing. The
separate publication service is an optional stronger guarantee, not a prerequisite
for adding Confluence to the toolset. Implement it only if the maintainer wants
AI-DLC to own repeatable, version-aware publication; native tool use plus guidance
may satisfy the immediate team-document need without that service.

## Constraints and risks

Existing schemas and installed clients remain compatible. New options are
additive and explicit. Unselected providers add no installation or login burden.
Secrets and vault paths stay local; shared files contain references and portable
choices only. A provider change preserves work/spec/PR references and configured
completion gates. Native service tools remain available; AI-DLC cannot prevent
independent edits in the external service and must reconcile them honestly.

Readiness must separate API integration from optional desktop viewing. Missing
Obsidian GUI on a headless machine does not by itself invalidate tracker work;
missing notes storage matters only to requested note operations.

The Confluence spec proposes repository Markdown as the publication source and
remote edits as conflicts. This is a draft choice, not inferred consent to
overwrite pages. If Confluence is the main authoring location, prioritize native
read/search/link access and revise the publishing scope before implementation.

## Open questions and user inputs

| Needed when | User supplies | AI-DLC/integration discovers or handles |
| --- | --- | --- |
| Before choosing Plane transport | Already hosted, Plane Cloud, or not installed; URL if known | Supported edition/version and available authentication paths |
| Before live Plane connection | Workspace/project URL or friendly name | IDs, states, available projects, account identity |
| Before migration apply | New-work-only or selected backlog migration; scope | Candidate records, target reference map, conflicts, uncertain operations |
| Before work integration | Jira/Confluence URLs, Cloud or Data Center, project/space names, whether approved AI/API access exists | IDs, create fields, transitions, permissions, live account match |
| Before publication implementation | Repository-first, Confluence-first, or two-way authoring intent | A bounded compatible workflow and content conversion preview |
| Before using private notes | Existing vault and intended daily-note convention, set locally | Attach/readiness instructions; no vault upload |
| Before live qualification | Disposable destination or permission to create named test items/pages | Test steps, evidence, and explicit cleanup plan |

No password, token, arbitrary project UUID, or status UUID is needed in chat.
The user signs in through the chosen native client or configures a local
environment reference at connection time. If Plane is not installed, hosting
placement, persistence/backups, domain/TLS, and maintenance ownership need a
separate operational decision; this is not provider-adapter complexity.

## Links

- [Product direction](../product-direction.md)
- [Code audit and alternatives](../planning/provider-toolset-code-audit.md)
- [Implementation sequence](../superpowers/plans/2026-09-06-provider-toolsets.md)
- [Toolset setup spec](../../openspec/changes/provider-toolset-onboarding/specs/provider-toolset-onboarding/spec.md)
- [Tracker adapter spec](../../openspec/changes/portable-tracker-adapters/specs/portable-tracker-adapters/spec.md)
- [Migration spec](../../openspec/changes/selective-tracker-migration/specs/selective-tracker-migration/spec.md)
- [Publication spec](../../openspec/changes/team-document-publication/specs/team-document-publication/spec.md)
