# Provider toolset source audit

Reviewed September 6, 2026, against main `9b6ca29`. Planning branch:
`codex/provider-toolset-plan`. Provider-related implementation is also present on
SAN-12's `codex/portable-workflow-bundles` at `04c65cb`; that branch's bundle work
and stage-retention repair are not assumed merged. Its successful-backup cleanup
finding still blocks SAN-12 closeout. This planning work does not resolve it.

## Findings

| Boundary | Evidence in current source | Implication and bounded correction |
| --- | --- | --- |
| Scaffolding | `copier.yml` chooses capabilities, while `project-templates/project/ai-dlc.toml.jinja` unconditionally selects Linear whenever tracker is included; `templates.adopt` accepts capabilities but no provider selections | Add explicit provider choices, persisted through Copier answers and updates; keep legacy defaults for callers omitting choices |
| Runtime adapters | `providers.Registry.get` ships Linear/GitHub Issues and integrity-verified executable/Python extension boundaries | Thin new adapters fit the existing model; general service interaction need not be reimplemented |
| Guided connection | `cli.provider_connect` rejects names other than Linear; `provider_onboarding.py` mixes Linear discovery with saved plans and comment-preserving edits | Separate provider discovery/selection from common preview, freshness, locking and apply; preserve Linear's existing public wrappers |
| Capability leakage | `workflow.WorkService.start` special-cases GitHub Issues to skip in-progress; provider/config conditionals also appear in `provision.doctor` and credential defaults | Declare supported lifecycle intents and connection requirements; stop growing provider-name branches in workflow services |
| Component coverage | `modules/components.json` has OpenSpec, Linear and GitHub Issues only; resolver rejects unknown component IDs | Plane/Jira/Confluence need descriptors; Obsidian's working local adapter also needs metadata appropriate to local notes versus optional GUI |
| Native harness access | `agents.render_agents` already writes command/args/url/environment-name MCP definitions to Claude and Codex project config | Reuse this. Current renderer omits explicit transport/auth-header metadata; qualify client-specific HTTP output and add only required fields, never raw credentials |
| Readiness | `readiness.inspect_readiness` joins modules/config/credentials/guidance; `provision.doctor` separately performs provider-specific health checks | Compose the same requirements for all providers; distinguish harness access, lifecycle access and live qualification; no claimed readiness from presence of Markdown alone |
| Existing work | `rebind._rebind` inventories all retained records and demands mappings for each; preview does not test the proposed provider | Implement explicit default-only and selected-record paths, verify target mappings, and retain source provenance |
| Identity binding | `WorkService._load` fingerprints provider configuration and account references | Retain old aliases/config when switching defaults; edits to operational config can currently require rebind, so do not silently normalize old fingerprints |
| Knowledge | `knowledge.Knowledge` supports local find/note/append; registry role contract only exposes append; CLI/MCP helpers directly access the vault | Keep private notes local. Shared publishing is a different optional capability; do not point the existing knowledge role at Confluence |
| Extending roles | `components._ROLES`, work binding roles, contract operation vocabulary, and template capabilities are closed lists | A document-publishing role needs one deliberate additive contract change; component metadata alone cannot invent executable operations |
| Qualification | `conformance.py` fixtures and live targets list known providers; live scope is read-only health, not mutation conformance | Add adapter tests and separate disposable live workflow evidence; do not label health probes as full conformance |

## Observed local checks

Source bootstrap completed in the planning worktree. The focused source-audit
suite passed 148 tests across components, readiness, onboarding, rebind, and
providers. A read-only resolver call with explicit Plane/Obsidian selections
reported both as missing components. Registry discovery listed no Plane, Jira,
or Confluence adapter. A read-only Plane rebind preview inventoried 13 retained
records before adding the new draft planning record. None of these checks used
live service credentials or changed active project selections.

Final required project verification on this main-based planning checkout passed
all five outcomes (generated, format, lint, types, test), with 963 full tests.
All four new draft changes passed strict OpenSpec validation; local planning/spec
links and the draft work record were checked. This validates the planning artifact
structure and existing implementation baseline, not the proposed integrations.

The prior SAN-12 cycle's 746 focused / 1,141 full tests apply to its different
branch; they must not be presented as this branch's qualification evidence.

## Product-level alternatives

1. **Reuse native tools plus thin lifecycle adapters (recommended).** MCP supplies
   service search/edit/context; adapters supply AI-DLC's small typed operations,
   reconciliation and evidence boundary. Moderate one-time integration work;
   normal per-project setup becomes choices and authentication.
2. **Native connectors only.** Fastest way to give a harness Plane/Jira/Confluence
   access, and useful as an early milestone. Does not make current `work` commands
   compatible or migrate pinned records. Clearly report this partial support.
3. **General plugin platform or new sync engine.** Larger ongoing maintenance and
   another configuration language before proving the use case. Not justified for
   these tools; reuse current profiles/components/registry and add only measured
   gaps. Revisit only after actual third-party distribution demands it.

The recommended design starts with native access and Plane as a vertical slice,
then uses Jira to prove that no new workflow-service special case is necessary.
The reference adapters may initially ship with AI-DLC; existing verified extension
providers remain supported. No new packaging ecosystem is required.

## Upstream services to reuse

Plane provides an official MCP server. Hosted OAuth and local stdio with a custom
base URL support different deployments. Local stdio uses Python/uv and local
environment configuration. Select a reviewed exact package version for portable
setup rather than copying floating installation examples.
[Plane MCP documentation](https://developers.plane.so/dev-tools/mcp-server).

Atlassian's official Rovo MCP service exposes Jira and Confluence operations for
Atlassian Cloud. Client access and permissions are governed by the organization's
authentication and access controls. Data Center is a separate integration target;
do not configure the Cloud service against it by assumption.
[Atlassian MCP overview](https://developer.atlassian.com/cloud/rovo-mcp/),
[access controls](https://support.atlassian.com/security-and-access-policies/docs/understand-atlassian-rovo-mcp-server/).

REST remains a suitable narrow backend for noninteractive AI-DLC lifecycle calls:
[Plane API](https://developers.plane.so/api-reference/introduction),
[Jira issues and transitions](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/),
[Confluence pages and versions](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/).
An interactive MCP login is not evidence of headless REST authentication.

## What should be easy, and what remains real work

Already-supported provider selection should be configuration, authentication and
named resource selection. Adding another tool requires its descriptor/guidance
and any narrow adapter required by the application's contracts. Different APIs
do not become compatible merely because they are both ticket trackers. Existing
issue migration and two-way document synchronization are separate data problems.

The current framework is a usable foundation but does not yet deliver the promised
low-effort switch end to end. The proposed improvements target those boundaries,
without rebuilding the framework or implementing general remote tool catalogs.
