# Framework qualification protocol and report validation

Status: local preparation under GitHub #14. This document provides the protocol
and validator contract; it does not record completed Q-01–03 live qualification.
Root owns actual walkthrough artifacts, review, global release evidence and finish.

## Read-only validator

Run from a prepared checkout:

```sh
QUAL_REPORT_DIR=$(mktemp -d)
python scripts/qualify_framework.py --schema > "$QUAL_REPORT_DIR/schema.json"
python scripts/qualify_framework.py --protocol > "$QUAL_REPORT_DIR/report.json"
python scripts/qualify_framework.py --validate "$QUAL_REPORT_DIR/report.json"
```

The emitted protocol is valid but every case is `not-run`, with unknown revisions,
environment, client and classification. Nothing is auto-detected or upgraded.
These are the only modes. `steps` are data, never shell commands to execute; the
script does not call networks, trackers, Docker, clients or completion services.
It writes only stdout and reads the selected report and its referenced evidence.

Exit 0 means structurally valid evidence records. It never means that live evidence
is authentic, that a platform is qualified or that work is complete. The summary
always says `live_authenticated=false`, `qualification_complete=false` and
`human_review_required=true`. `pending-review` means declared live observations
need review, not passed acceptance. Valid failed/unavailable/not-run observations
retain their result. A fixture pass cannot fill a required live slot.

## Schema and evidence boundary

Schema 1 contains `run_id` and unique scenario/target records. Each keeps full engine
commit, selected profile/bundle revisions, environment, harness name/version,
provider identity when relevant, ordered steps, expected/observed, classification,
result, evidence and limitations. Null profile and empty bundle map mean unselected
or unavailable: explain which in limitations. Never substitute current HEAD for a
missing historical pin. Passed records require an immutable 40-character revision,
observation and evidence; a failed case needs the observed failure. Record actual
capture times in the transcript/method rather than inventing timestamps.

Environment isolation distinguishes existing-host, clean-clone, isolated-runtime,
container, factory-clean, hosted and planned. Record OS version and architecture,
preinstalled tools/caches and other inherited conditions. Container evidence needs
its actual immutable image digest and container identity. The required container
slot uses Ubuntu 24.04 arm64 (`os=Linux` or `Ubuntu`, VERSION_ID beginning 24.04,
architecture arm64/aarch64); the native slot uses Darwin/macOS arm64. These checks
catch contradictory metadata; they do not attest to that metadata's truth.

Artifacts use paths relative to the report directory, SHA-256, producer, method and
`fixture|live-local|live-container|live-hosted`. Every artifact in a record must
match that record's classification; split mixed evidence into separate records
instead of taking the strongest class. Links, path traversal, nonregular files,
changed files, missing files and digest mismatches are refused. Report size is
limited to 2 MiB, each artifact to 20 MiB, and a report to 128 artifact references.
Unknown fields, duplicate JSON keys, duplicate scenario/target rows and unknown
scenario IDs fail validation. The script's semantic and filesystem checks go
beyond its emitted JSON Schema.

A matching hash authenticates bytes against a declaration, not the producer,
environment, timing or meaning of a transcript. A dishonest declaration can still
be structurally valid. A reviewer must inspect provenance, exact revisions,
commands, environment isolation, expected/actual behavior, omitted steps and
contradictions. Do not include credential values, full environment dumps or
unreviewed private work content. Redacted evidence needs an explicit redaction
method and its own digest; never present it as an unchanged raw capture.

## Exact synthetic example

This fixture illustrates format only; its revision is deliberately synthetic.
Create the artifact and save the JSON below as `report.json` in the same directory:

```sh
mkdir -p "$QUAL_REPORT_DIR/evidence"
printf 'synthetic observation\n' > "$QUAL_REPORT_DIR/evidence/synthetic.txt"
```

```json
{
  "schema": 1,
  "run_id": "synthetic-format-example",
  "scenarios": [
    {
      "scenario_id": "Q01-repeat-setup",
      "target_id": "format-example",
      "commit": "1111111111111111111111111111111111111111",
      "profile_revision": null,
      "bundle_revisions": {},
      "environment": {
        "os": null,
        "version": null,
        "architecture": null,
        "isolation": "planned",
        "image_digest": null,
        "container_id": null,
        "inherited_tools": []
      },
      "harness_name": null,
      "harness_version": null,
      "provider": null,
      "steps": [
        "Write the synthetic observation file; no setup was performed."
      ],
      "expected": "Demonstrate a structurally valid fixture record.",
      "observed": "Synthetic example only.",
      "classification": "fixture",
      "result": "passed",
      "evidence": [
        {
          "path": "evidence/synthetic.txt",
          "sha256": "3d543d7dc86145dd0f38cf97cbfa2f1a42877f3b5882238984444df641ddf54a",
          "kind": "fixture",
          "producer": "documented format example",
          "method": "synthetic text file"
        }
      ],
      "limitations": [
        "The revision is synthetic; no live setup or client was tested.",
        "No profile or bundle was selected."
      ]
    }
  ]
}
```

```sh
python scripts/qualify_framework.py --validate "$QUAL_REPORT_DIR/report.json"
```

Expected: structurally valid, fixture classification preserved, live slots unmet,
no authenticated live claim and no qualification completion. Only replace those
values with actual reviewed observations; never rename this example as live proof.

## Q-01: setup continuity

Use separate disposable engine and adopted-project directories. Engine bootstrap
and adoption are different operations; never copy this engine repository's
personal GitHub project/account binding into a work repository. Record exact
source revision, clean/dirty checkout, selected profile and bundle locks, and
independent local binding identities without credential values.

Before starting, root chooses a reviewed revision and disposable location. For
example, with explicitly supplied SOURCE_REPOSITORY and REVIEWED_COMMIT:

```sh
QUAL_RUN_DIR=$(mktemp -d)
git clone --no-local "$SOURCE_REPOSITORY" "$QUAL_RUN_DIR/engine"
git -C "$QUAL_RUN_DIR/engine" checkout --detach "$REVIEWED_COMMIT"
git -C "$QUAL_RUN_DIR/engine" rev-parse HEAD > "$QUAL_RUN_DIR/revision.txt"
git -C "$QUAL_RUN_DIR/engine" status --porcelain > "$QUAL_RUN_DIR/checkout-status.txt"
AI_DLC_BOOTSTRAP_HOME="$QUAL_RUN_DIR/bootstrap" sh "$QUAL_RUN_DIR/engine/scripts/bootstrap.sh" --source
```

Capture stdout/stderr/exit status from the actual invocation into retained files;
use the PATH printed by that invocation. No private runtime is substituted for a
missing clean-machine result. An isolated bootstrap home still runs on the existing
host and may reuse its mise tools/caches. Repeat the same revision and record the
second result separately; snapshot owned assets/bindings before and after.

The local adoption example uses current CLI syntax and does not call a tracker:

```sh
ai-dlc project init "$QUAL_RUN_DIR/disposable-project" --preset generic --tracker github-issues
ai-dlc project readiness --root "$QUAL_RUN_DIR/disposable-project"
ai-dlc agents render --root "$QUAL_RUN_DIR/disposable-project" --check
```

Readiness may correctly report missing account/tool requirements. Preserve that
result. Qualification also needs safe authored-conflict preservation, pinned
bundle availability in a fresh offline process, and failed-update recovery with
retained-path diagnostics. Record the actual preconditions and commands; the
existing unit tests demonstrate fixtures only. Do not add a production failure
injection mode or turn a skipped operational failure into a passed case.

Repeat applicable cases for native-macos-arm64 and container-ubuntu2404-arm64.
For the container, root records the exact image digest, container ID, OS release,
architecture, mounts, inherited dependencies and actual operations. An available
image or running Docker daemon does not qualify setup. No factory-clean or hosted
claim follows from a fresh clone, container image or isolated runtime.

## Q-02: two actual tracker adapters

Use two real, separately scoped tracker adapters for new work through the same
application services. Preserve existing work bindings and authored records. Read
actual capabilities: GitHub issues-only lacks in_progress, while configured
Projects can support it. These are two configurations of one `github-issues`
adapter, and the summary counts them once. Capabilities probes alone do not
replace two complete provider cycles or preserved-binding evidence.

Current direction selects Jira Cloud for new work without migration; Plane is
optional. Actual Jira/Plane destinations, credentials and required field/transition
choices are unavailable here. Their live rows stay unavailable/not-run. No Linear
calls are part of this protocol preparation. The schema can preserve old Linear
records, but a historical artifact is not a current authorized live experiment.
Do not switch this repository's tracker to run qualification.

Root must explicitly select disposable destinations and local credential bindings
before any remote lifecycle operation. Keep native client OAuth separate from
lifecycle adapter authentication. Record publish/start/read/finish behavior,
unsupported operations, duplicate/recovery refusal and unchanged prior bindings.
Finish retains the actual specification/PR/merged-CI gates. Mock adapters and
fabricated merged evidence remain fixtures and cannot satisfy live slots.

## Q-03: fresh-session handoff

Save exact input artifacts, their revisions/hashes and a bounded next-action
expectation before starting a new client session. Provide repository paths and
no prior conversation. A sample initial instruction is: “Read AGENTS.md and the
identified work/spec/plan artifacts. State the next unfinished action and its
evidence. Identify missing prerequisites without inventing credentials, prior
steps or service results. Do not perform remote mutations.”

Record client name/version, startup invocation, exact prompt, transcript, files
consulted, observed next action, unexpected private context and limitations. A
continued chat, a child with inherited conversation or a unit-test subprocess is
not proof of a fresh Claude/Antigravity session. Root reviews the actual consumer
behavior and required target/client coverage; validator success cannot do so.

The coordinator reports Darwin arm64 with Claude Code 2.1.263 and an available
Ubuntu 24.04 arm64 image through Docker Desktop. Antigravity is absent here; work
OS/client versions remain pending. These are planning inputs, not completed
walkthrough records or evidence emitted by this validator.

## Preservation and current evidence

Keep report and evidence until reviewed. The validator performs no cleanup.
Inspect disposable directories, mounts and any retained bootstrap/bundle paths
before explicit removal. Do not bulk-delete shared tools, provider resources or
staging paths. Remote cleanup requires the selected resource identity and prior
authorization; absent credentials do not authorize guessing another account.

Initial TDD cases failed because the validator did not exist. Twenty-three cases
then passed. Four additional tests exposed duplicate-key acceptance, boolean
schema-version acceptance, a native record filling a container-named slot and an
incomplete harness pair; each failed before its corresponding correction.
A subsequent regression caught omission of the run identity from the validated
summary; that test failed before correction. The exact documented JSON fixture
also validates without filling live slots. The final focused qualification,
machine-integration and rebind run passed 42 tests in 12.19 seconds.

The checkout was prepared with the actual source bootstrap using a task-specific
bootstrap home on the existing Darwin arm64 host. All five required manifest
checks passed: generated, format, lint, types and test; the full suite passed
1,437 tests in 279.99 seconds. The receipt identifies base revision
`33d4b5241f81fb1b716820645ddbd2352ad7b7b3` with `dirty=true` for this candidate.
These are local development checks and synthetic fixture evidence, not Q-01–03
live fulfillment or factory-clean qualification. Independent review and actual
walkthrough evidence remain with the coordinator.
