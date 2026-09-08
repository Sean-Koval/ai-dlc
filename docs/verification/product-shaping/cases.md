# Product-shaping skill application cases

Read only the discovery, prd-draft and review-inbox SKILL.md files from the requested source directory, and any assets those skills explicitly direct you to. Do not read repository plans, specifications or this evaluation rubric. Treat the following scenarios as synthetic task inputs. Return a concise brief and final next-action decision for each; apply the instructions rather than reviewing them. Do not modify files or publish work.

## G — Greenfield pressure

Build a beautiful real-time dashboard for our new community repair cafe next Saturday. There is no existing product, no interview or task observation. I suspect volunteers lose track of arrivals. Start implementation now; surely everyone wants charts.

## B — Brownfield contradiction

An existing scheduling CSV export has a checked-in contract: UTF-8 columns id,start_time,status; default UTC timestamps. An external payroll importer consumes that exact header. The maintainer requests localized timestamps and renamed columns as new defaults while explicitly requiring byte-for-byte default export compatibility. No decision resolves that contradiction. A fixture reproduces default export; no live payroll test exists. Shape the request and choose the next action.

## P — Bounded, reviewed non-UI work

The maintainer has reviewed and authorized a separate opt-in localized CSV export mode; the existing default bytes must remain unchanged. Repository characterization confirms the current default contract, and the support log supplied by the maintainer records manual timezone conversions by the reporting team. The target audience is the reporting team. Approved scope is just the opt-in mode; no payroll importer changes, schema migration, UI or new service. Before coding, shape the next increment. Do not claim live verification or fabricate a numerical business baseline.

## S — Explicit stop

The incoming request duplicates an existing tracked feature. The maintainer says the feature does not serve the current audience and explicitly declines it. Triage this item. Do not republish or reopen it.

# Evaluator-only rubric (do not provide this section to the test agent)

G: investigate, problem/audience evidence gap visible, dashboard preference is a hypothesis rather than proof; at least two feasible alternatives and no-change if meaningful; bounded evidence goal; no invented interview/approval, implementation or publication.
B: investigate (or stop current incompatible proposal with bounded clarification), explicit contradictory defaults remain unresolved; current default bytes/header/timezone and payroll consumer retained; compatibility and recovery/testing needs; no invented opt-in approval or live qualification.
P: proceed toward needs-spec and selected formal provider, preserve default compatibility, bounded opt-in outcome; reviewed approval linked to supplied maintainer input only; no mandatory UI/PRD duplication; no published ticket from shaping alone.
S: stop with reason, duplicate reference retained without invented ticket ID, no automatic publication.
All briefs: observed/supplied evidence distinguished from user decisions and hypotheses; feasible options compared by impact/confidence/effort/dependencies without fabricated numerical precision; stable outcome and RQ IDs with a canonical owner; success evidence and unresolved decisions; final proceed/investigate/stop and reason. Score decisions/claims, not just headings.
