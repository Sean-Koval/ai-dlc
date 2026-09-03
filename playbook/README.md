# AI-DLC playbook

AI-DLC is a local CLI/library plus project templates and agent skills. It does not host orchestration. The human and agent decide what work is useful; deterministic services validate, store, and link that work.

Start with one deployable application and explicit module boundaries. Split deployment only when requirements justify it. Repository maintainers own architecture, product rationale, design context, decisions, and runbooks. Update these documents alongside relevant code.

The specification role is the sole formal behavior specification system. The tracker owns priority and lifecycle status. Personal knowledge holds continuity, reflection, and private notes; it links durable repository material. Do not mirror all four stores or resolve contradictory state by overwriting it.

Daily practice: review priorities and current evidence; discover unclear problems; draft and review a PRD when needed; decide whether formal specification is needed; translate approved scope through the specification provider; review a work record before publishing; implement and run required checks; use evidence-gated finish; capture a concise handoff.

Agent skills supply judgment patterns. Provider instructions supply vendor operations. Services own validation, receipts, idempotency and external state reconciliation. No skill bypasses completion gates or extends the user’s authorization.

The eight skills under agents/skills are draft release assets. Scenario fixtures and model/budget configuration are provided under agents/. Behavioral control and treatment runs remain pending. Static packaging validation is not behavioral evaluation.
