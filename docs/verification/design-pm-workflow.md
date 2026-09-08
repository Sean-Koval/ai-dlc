# Optional Design PM workflow verification

Scope: GitHub #13, DP-01–06. This candidate provides optional portable guidance,
four Markdown templates, original instructional cases and a calibration protocol.
No UI was executed or generated, no human supplied labels, no paid experiment
ran, and no client/platform or quality-improvement claim is made. Calibration
#16 and remote specification/archive/PR/CI/finish remain coordinator-owned.

## Design and source boundary

The coordinator reviewed and approved the concrete four-artifact design before
implementation: brief, rubric, evaluation and selection; two skills; criterion
IDs linked to PS/TR requirement sources; criterion-specific anchors; separate
behavior results, subjective ratings and unverified evidence; bounded iteration
and earlier-candidate selection. Proposed 0–4/minimum 3 and two-revision/plateau
starters are not task-budget approval or a mandatory project gate.

This isolated branch starts at accepted local PS/TR revision `4058b24`. The
September 5 plan now explicitly records coordinator authorization for parallel
local implementation while remote dependency finish remains pending. Existing
runtime dependency checks and finish policy were not bypassed or changed.

The source skills reference installed-project templates and explain the source
repository/older-project fallback. Assets and examples ship in their existing
locations, with lock hashes, both supported-harness copies and project-template
copies updated together. Guidance remains readable without a new tool service.

## Scenario-first checks

[Pressure inputs and evaluator-only checks](design-pm/cases.md) were fixed before
new skill bodies. They cover draft rubric/budget decisions, an attractive required
failure, static/self-review limits, and earlier candidate/rubric/budget decisions.
All observations in that packet are synthetic supplied inputs. Agent pressure
replays are **pending**, not passing: all reviewer slots were occupied, and the
coordinator explicitly authorized retaining cases for independent review rather
than spawning uncontrolled nested sessions. No failing or successful agent baseline
is fabricated. Existing general design/handoff assets at `4058b24` remain available
for the no-guidance arm; give either arm only its assigned assets and scenario
packet, withholding evaluator checks. Record exact outputs and settings before
making any claim about judgment. Human calibration remains a separate experiment.

Delivery TDD observations:

- Six new init/adoption cases failed because the new templates/examples were
  absent and adoption did not yet recognize those authored paths as conflicts.
- The first two renderer cases had a missing local test import. After correcting
  that test defect, both failed for absent Design PM skills in the chosen harness.
- After asset and hash/render integration, all eight new cases passed in 12.53s.
  An intermediate test assumption that `docs/design` was absent was corrected:
  the existing scaffold already has its README. The final assertion preserves
  that directory/index while verifying no task artifacts are instantiated.
- These tests inspect actual adopted/rendered files, unchanged finish gates,
  source equality and authored conflict behavior. They do not judge agent decisions
  by checking headings. Existing three-way Copier conflict tests remain applicable.
- Wheel/source-distribution byte comparisons now include all four templates and
  both instructional/protocol files from both asset locations.

The broader template/render run reported 345 passed and 2 failures in 157.16s. Both
failures reported `No space left on device`: source-distribution staging while
copying an inherited tracked Rust build artifact, and a later Copier temporary
Git initialization. These failures are environmental evidence, not a passing run.
No shared files or unknown caches were deleted and no expensive retry was started
while the coordinator coordinated disk pressure.

## Preparation and remaining validation

Actual source bootstrap succeeded with a task-specific bootstrap home on the
existing Darwin arm64 host, installing the pinned interpreter and preparing the
source/project environments; both manifest setup steps completed. This is local
development preparation, not clean-machine qualification. Both new skills passed
the installed structural skill validator. Strict validation of the child OpenSpec
change, targeted lint and `git diff --check` passed.

After the broader run, a small source/older-project lookup refinement was added
to both skills and their hashes/generated copies refreshed. The coordinator's independently reviewed packaging fix `8551b09` was cherry-picked
as `e3c2bcf`, excluding tracked compiler outputs from Python source distributions
while preserving Cargo.toml and Rust source. The Design PM edits were preserved.
The final focused template/rendering run then passed **347 tests in 160.28s**,
including archive source-byte comparisons and all eight new delivery cases.
All **15** OpenSpec items passed strict validation.

The final `ai-dlc project check --required` passed all five checks: generated,
format, lint, types and test. The full suite reported **1,218 passed in 235.03s**.
Its receipt identifies `e3c2bcf61adc840b7bb48f64a2bd10cbdbf66a68`, `dirty=true`,
target local and engine 0.4.0. This is a pre-commit local candidate result, not clean
merged-CI, human calibration or platform qualification. Only verification and task
metadata were finalized afterward; tested skills/templates/examples remain frozen.

Independent pressure/source review remains pending with the coordinator. It must
preserve A–D as separate synthetic runs: repeated illustrative candidate labels
are not cross-case evidence identities. No archive, PR, remote mutation or finish
was performed from this branch.
