# Plane, Jira, Confluence, and Obsidian substitution assessment

Status: maintainer requirements and source assessment, September 6, 2026.
This records the requested direction and remaining work. No provider migration,
remote issue creation, document publication, or live qualification occurred.

## Requested outcome

The maintainer has reached Linear's free limit and wants Plane for personal
projects. Work projects use Jira for ticketing and Confluence for sharing
documents with teammates. Obsidian remains the local document viewer and place
for private daily notes in both contexts. Confluence publishing must not replace
Obsidian or implicitly upload its vault. Notion is not required for this workflow.

| Responsibility | Personal projects | Work projects |
| --- | --- | --- |
| Ticket priority and status | Plane | Jira |
| Local viewing and private notes | Obsidian | Obsidian |
| Shared document publication | Not specified | Confluence |
| Versioned architecture, decisions, runbooks | Repository `docs/` | Repository `docs/` |
| Formal behavior specifications | OpenSpec | OpenSpec unless explicitly changed |

## What the source supports today

The tracker wire contract in [contracts.py](../../src/ai_dlc/contracts.py)
requires `create`, `find`, `read`, and `transition`; `link` is optional. Operation
IDs and correlations support retry reconciliation. The
[registry](../../src/ai_dlc/providers/__init__.py) ships Linear and GitHub Issues
and supports integrity-verified executable and Python extension providers.
Plane and Jira are not built-in adapters. Adding their names to configuration
alone does not make them functional.

[Component metadata](../../modules/components.json) connects installed tools,
required configuration, and harness instructions for OpenSpec, Linear, and GitHub
Issues. Third-party component manifests can add declarative metadata, but do not
implement remote operations. Guided onboarding is currently specific to Linear.
Plane and Jira need adapters, account/project configuration, guidance, and
readiness evidence before the swap is easy in practice.

[Rebind](../../src/ai_dlc/rebind.py) previews affected work and requires explicit
replacement artifact mappings when applied. It retains every work record rather
than trusting a local completion flag. Rebinding is a local mapping operation;
it does not copy Linear issues into Plane or Jira. Active SAN-12 remains bound to
Linear and must not be silently redirected when defaults change.

The September 6 read-only `rebind(..., "tracker", "plane")` preview identified
13 retained work records requiring consideration. It changed no files or remote
state. The 28 existing provider/rebind tests passed. Neither result establishes
a working Plane adapter: the preview describes local mappings without invoking
the proposed service.

The knowledge contract is only `append(path, body, operation_id)`, implemented
for a local vault. It is not a shared document publishing contract. There is no
shipping Confluence or Notion provider. Adding Confluence under the existing
single knowledge selection would conflate private notes with team publication.
The operation vocabulary is validated centrally, so a new publishing capability
requires an explicit contract change, not just external component metadata.

## Smallest useful delivery sequence

1. **Plane tracker:** implement the existing tracker contract, using explicit
   instance URL, workspace, project, state mappings, and an environment credential
   reference. Include bounded pagination, retry reconciliation, visible uncertain
   mutations, secret redaction, and unchanged completion gates. Add component
   metadata, guided configuration, and actionable readiness together.
2. **Personal migration rehearsal:** preview affected records, reconcile target
   issues, produce a reviewed old-to-new reference map, then apply the local
   rebind. Preserve source identifiers and specification/PR links. Re-run the same
   publish/start/read/finish workflow using Plane, with no Plane conditionals in
   the workflow service. Existing Linear bindings must remain valid until mapped.
3. **Jira tracker:** exercise that same contract on the actual work deployment.
   Discover allowed workflow transitions and required create fields; do not
   treat a status name as a universally valid transition. Avoid assuming every
   project uses the same issue types or workflow.
4. **Confluence publication:** specify a separate optional publishing capability
   while retaining `knowledge = obsidian`. Select explicit repository documents,
   preview content and target pages, preserve page IDs and links, handle remote
   versions/conflicts, and refuse overwriting teammate edits. Private daily notes
   and the rest of the vault are excluded by default. Viewing repository Markdown
   in Obsidian does not require turning the vault into a repository mirror.

These are proposed deliverable boundaries, not newly published tickets or an
approved implementation plan. All four require formal specifications for their
observable integration or migration behavior. SAN-12's cleanup remediation does
not implement them. The existing SAN-15 replacement qualification covers
Linear/GitHub Issues; these requested providers need additional explicit cases.

## How this tests replaceability

Pass means the same application services, work format, spec links, and finish
gates operate through each tracker adapter. Differences stay in adapters,
provider configuration, onboarding, and guidance. Adding a third tracker should
not require another copy of the delivery workflow. A successful configuration
parse or mocked response is insufficient evidence.

Use contract tests for request/response behavior, failures, pagination, duplicate
prevention, and state mapping; use disposable live projects for an end-to-end
cycle on each chosen service. Rehearse migration with retained work, uncertain
creates, incomplete mappings, unavailable Linear reads, and rollback of local
configuration. For Confluence, test version conflicts and demonstrate that
unselected documents and private notes never appear in publication requests.

## Missing environment decisions

- Plane instance URL, deployment/version, workspace and project identifiers.
- Whether existing Linear records should be migrated now or new work should
  begin on Plane while the current record is closed through its original binding.
- Jira/Confluence Cloud versus Data Center, target project/space, and allowed
  authentication method. Do not infer work account access from installed tools.
- The intended editable source of shared documents. The proposed first boundary
  is explicit publication from repository documents, with remote edits reported
  as conflicts; bidirectional synchronization is not assumed.

Credentials must remain in the selected local environment, not this document.

## API feasibility evidence

Plane documents API keys and an instance-specific base URL for self-hosted
deployments. This supports a configurable adapter endpoint; the actual deployed
edition and operations still require verification.
[Plane API introduction](https://developers.plane.so/api-reference/introduction).

Jira Cloud exposes issue creation/read and workflow transition operations.
Its adapter must map the shared transition intent to the available Jira workflow.
Data Center must be assessed separately if that is the work deployment.
[Jira Cloud issues API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/).

Confluence Cloud exposes page creation and updates with page identifiers, body
representations, and version numbers. The publishing contract must account for
these rather than model shared document updates as local note appends.
[Confluence Cloud pages API](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/).
