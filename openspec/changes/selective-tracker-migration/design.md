## Decisions

Separate three user-visible paths: keep the current provider; switch the default
for future work; migrate an explicit subset. Retain the existing all-work rebind
command for compatibility. Add explicit mode and selected work IDs to the new
migration service, not a silent change to legacy rebind semantics.

Default-only planning inventories every retained record, including records lacking
explicit providers/bindings. Apply first pins each such record to its effective
old provider without changing its artifact references, then selects the new
default atomically in shared configuration. Preserve every old provider alias,
account reference, spec, branch, PR and gate. Do not rehash already bound records
to hide drift. New work uses the new default; old work still resolves old settings.

Selected migration plan schema 1 records source config/work digests, selected work
IDs, old provider/binding/reference, target provider/account/project identity,
verified target references or proposed creation payloads, correlation/operation
IDs, state mapping and limitations. Store it under ignored `.ai-dlc/local/` without
secrets. Display unselected records explicitly. A local completed flag does not
exclude a record automatically.

Mapping to existing target issues requires fresh authorized reads and identity
checks. Optional creation uses an explicitly reviewed plan and durable correlation
reconciliation; complete every selected mapping before local apply. An uncertain
remote create leaves local bindings unchanged and is resumed through its journal.
Remote writes and local files cannot form one atomic transaction. Do not delete
new target issues to imitate rollback; report retained targets and resume safely.

After mapping, recheck plan/work/config/account identities under the project lock,
then apply only selected tracker bindings/references. Append a non-secret immutable
mapping receipt under `.ai-dlc/migrations/<operation-id>.json` for cross-machine
provenance; it includes source reference, destination reference, work ID and
operation ID. Do not edit the Work schema to add history fields in this change.
Snapshot and update receipts with the same safe local transaction.

If Linear is unreadable, the tool can still preview known local records and accept
verified target mappings; it must label remote source status/history unknown.
Creating target issues from local acceptance text requires choosing that limited
source explicitly. It cannot claim a full import or copy missing comments,
attachments, assignees or remote edits. No live source completion claims are made.

Finish gates remain unchanged. A target marked closed is not evidence that local
work passed CI or merged. Changing defaults never authorizes publication or starts
work. The first live rehearsal uses disposable records before any real backlog.
