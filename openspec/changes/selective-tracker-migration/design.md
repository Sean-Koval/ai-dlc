## Current decisions

PR23 delivered default-only binding preservation, explicit verified selected mappings and immutable local transaction receipts. Keep legacy schema1 plans usable. The existing descriptor-based local transaction preserves detected authored replacements but is not crash atomic: partial bytes require explicit recovery. No remote rollback or source deletion is introduced.

### Evidence and substitution
New previews use schema2. They record local-record-only source provenance, unknown remote state/history and explicit omitted information, together with freshly observed target logical state and declared capabilities when available. No source provider call is implicit. Existing-target mapping preserves remote state; closed/cancelled/unknown never imply local completion, and unsupported transitions remain reported rather than performed. Schema1 revalidation retains its original exact shape. Real Registry GitHub/Plane transport fixtures cover substitution; Plane targets must retain the adapter's existing exact correlation/external identity requirements.

### Reviewed optional creation
A separate saved creation-intent format binds root/config/work snapshots, explicit local-record-only source choice, exact reviewed per-work title/body, target alias/fingerprint, existing mappings and stable correlation/operation IDs. Saving does not mutate a service. An explicit reconciliation action validates the immutable identity before reusing any find/read result, journals durable intent, and honors Journal.begin sender election. Pending/uncertain absence never authorizes another send. Each selected target is reconciled independently, and all targets remain reported if local files change or another target remains uncertain.

Reconciliation never saves work bindings. Once every target is known and current local freshness holds, it produces the ordinary reviewed migration plan for a separate save/apply step. A stale local snapshot allows read-only reconciliation of prior intents, never new creation. Retained targets can be reused in fresh existing-target mappings without generating a new creation identity. Local and remote transactions are separate. Provider-specific identity, authentication and mutation safeguards stay behind Registry; no WorkService vendor branch or forced retry API is added.

### Evidence boundary
Personal GitHub migration is already delivered and is not repeated. No Jira migration, full-history importer, source cleanup or new completion evidence is included. Local fixture qualification does not establish a real Plane deployment/account/version or a live substitution rehearsal. Parent issue21 remains open until those explicit gates are satisfied.
