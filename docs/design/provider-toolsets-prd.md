# Selectable provider toolsets

Implementation authorized: GitHub Issues **and Projects** are the selected first
personal toolset. Plane remains an optional later provider; no Plane installation
is needed to use GitHub. Earlier undecided-destination and Projects-exclusion
notes below are historical and superseded by this selection.
See [the executing child](../superpowers/plans/2026-09-07-github-ticket-workflows.md).

Owner: AI-DLC maintainer.
Status: draft updated with maintainer context, September 7, 2026. Planning requested;
implementation, hosting, account changes, and ticket migration are not performed.
Current priority: task/ticket management with GitHub Issues, Plane and Jira.
Confluence/custom-MCP integration and optional publication are deferred; the server
is on the work laptop and will be shared later. Its availability is not a tracker
implementation prerequisite.

## Problem and audience

AI-DLC prepares a development environment, scaffolds or adopts repositories, and
equips the selected harness to work consistently with the user's tools. A user
should select integrations and authenticate, not edit adapter code or look up
opaque IDs to use a supported toolset. Adding a supported integration is an
implementation task once; selecting it in another repository is configuration.

The immediate user has reached Linear's free limit. Personal projects are choosing between GitHub Issues and
locally self-hosted Plane, which is not installed yet; work projects use Jira
Cloud and Confluence Cloud. Obsidian holds the private journal, daily work log,
scratch notes and accumulated knowledge used by personal assistant agents, as
well as local document viewing. Confluence holds existing product knowledge,
team documents and guides; only a relevant subset belongs in local context. OpenSpec and
repository-owned architecture/runbooks remain as currently configured.

Obsidian can view or edit those repository documents directly. Eligibility for
explicit publication follows the selected document roots and private-note
exclusions, not which editor opens the file.

The [source audit](../planning/provider-toolset-code-audit.md) distinguishes
shipped support from SAN-12's unmerged bundle work. It identifies real gaps in
scaffolding, onboarding, capability handling, and migration UX. Existing upstream
MCP tools, including the maintainer's existing custom Confluence server, should
supply general-purpose service access; AI-DLC only needs narrow
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
3. GitHub Issues, Plane and Jira run the same publish/start/status/finish lifecycle
   and gates, with explicit differences in supported remote states.
   Provider-specific state models, requests, and retries remain behind adapters.
4. Switching defaults for new work and migrating selected retained work are
   separate reviewable actions. Neither silently redirects existing records.
5. Optional Confluence publication shares selected documents and preserves remote
   edits. It does not replace the knowledge role or mirror the Obsidian vault.
6. Tests and live evidence identify exactly which service edition, transport,
   client, and environment have been exercised. Tool installation, sign-in,
   API health, and a complete workflow are distinct evidence levels.

## Scope and exclusions

Three active planning areas are toolset setup/onboarding, tracker adapters and
selective tracker migration. The fourth draft, document publication, is deferred.
Document-only setup tasks may also remain deferred; they do not gate ticket work. Native MCP access
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

The maintainer prefers local drafting with the ability to publish selected shared
documents. Existing Confluence pages remain team-owned sources; this does not
make every page repository-authored. The publication spec proposes explicit
repository Markdown sources and remote edits as conflicts, not consent to
overwrite pages. The maintainer already uses a custom MCP server with a document graph, page
descriptions, LLM-derived semantics and document/space/page quality grading, plus
Claude and Antigravity for writing and pushing pages. Review and reuse that server
before proposing a separate Confluence implementation; its API and update safety
have not yet been inspected.

## Selective relationship between local and shared knowledge

See [the relationship design](local-and-shared-knowledge.md). Default to links and
on-demand reads of relevant Confluence pages. Deliberate local extracts or
summaries retain source URL, page version when available, and retrieval time;
refresh is explicit and preserves personal annotations. Do not mirror spaces,
automatically index the entire site into the vault, or publish daily notes.

An agent can help turn private working material into a separately reviewed shared
draft. Only that selected draft is eligible for publication. Existing page tools
remain usable; no new retrieval database, background sync process or general
personal-assistant platform is included in these changes. Generated guidance is
not a security boundary around independently connected tools.

## Open questions and user inputs

| Needed when | User supplies | AI-DLC/integration discovers or handles |
| --- | --- | --- |
| Before local Plane deployment | Confirm local runtime availability and storage/backup location; local hosting is selected, not installed | Review upstream deployment, startup/recovery instructions and actual supported version |
| Before live Plane connection | Workspace/project URL or friendly name | IDs, states, available projects, account identity |
| Before migration apply | Review active/planned Linear items and select GitHub Issues or local Plane as destination; latest direction supersedes the earlier Plane-only selection | Candidate inventory, target mappings and conflicts; completed history remains outside initial scope |
| Before work integration | Cloud site URLs, project/space names, whether approved AI/API access exists | IDs, create fields, transitions, permissions, live account match |
| Before publication implementation | Custom MCP server repository path/URL or interface documentation; later one representative shared document and source page | Reuse assessment; local-draft preview and any remaining publication gap |
| Before using private notes | Existing vault and intended daily-note convention, set locally | Attach/readiness instructions; no vault upload |
| Before live qualification | Disposable destination or permission to create named test items/pages | Test steps, evidence, and explicit cleanup plan |

No password, token, arbitrary project UUID, or status UUID is needed in chat.
The user signs in through the chosen native client or configures a local
environment reference at connection time. Plane hosting is the local computer;
persistence/backups, startup behavior and maintenance still need an operational
runbook. Propose local-only exposure initially; remote access is a separate choice.
The computer must be running for other clients to reach this instance. Deployment
is a machine-level setup step, not something repeated by project bootstrap.

## Links

- [Product direction](../product-direction.md)
- [Code audit and alternatives](../planning/provider-toolset-code-audit.md)
- [Implementation sequence](../superpowers/plans/2026-09-06-provider-toolsets.md)
- [Toolset setup spec](../../openspec/changes/provider-toolset-onboarding/specs/provider-toolset-onboarding/spec.md)
- [Tracker adapter spec](../../openspec/changes/portable-tracker-adapters/specs/portable-tracker-adapters/spec.md)
- [Migration spec](../../openspec/changes/selective-tracker-migration/specs/selective-tracker-migration/spec.md)
- [Publication spec](../../openspec/changes/team-document-publication/specs/team-document-publication/spec.md)
