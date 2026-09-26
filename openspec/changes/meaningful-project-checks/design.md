## Observed implementation

`src/ai_dlc/setup/project.py:check_project` executes the configured required list
by default or all command keys with `required_only=False`. There is no focused
selector. The CLI has `--required/--no-required`, `--receipt` and `--json`. Its exit
status currently checks whether all required IDs passed, which must be separated
from the success of an explicitly requested subset. MCP exposes no check service.

Receipts already carry the full required list and configuration digests;
`src/ai_dlc/providers/scm.py:validate_receipt` requires outcomes to match all required
IDs exactly, at the trusted merged revision. Keep that validator and schema.

The frontend manifest explicitly returns zero when `BASE_URL` is unset, and the
Playwright test also skips. Reproducing the generated command without Node on PATH
returns exit 0, “Skipping frontend smoke: BASE_URL is unset”, without dependencies.
This behavior matches the old FE-01 requirement but conflicts with the general
portable-development requirement that skipped required checks cannot qualify.
The change intentionally replaces FE-01's successful skip; do not rewrite the
historical archived evidence or claim it had previously required failure.

Python initialization generates `src/main.py` printing `Hello, world!`; its
`language-check` only runs compileall. Existing project adoption omits the starter
source and preserves authored manifests. Standard-library tests need no new
package, lockfile dependency, or mandatory test framework for existing teams.

## Decisions

### Explicit selection, unchanged required truth

Add an optional keyword selection argument to `check_project` and a repeatable
`--check ID` CLI option. Omission retains current `--required/--no-required`
selection and exit behavior. A supplied nonempty list selects exactly those IDs,
in requested order, whether required or optional. Combining explicit selection
with `--no-required` (service `required_only=False`) is rejected as ambiguous; the
default/explicit `--required` remains compatible with selected optional IDs because
that flag filters only when no IDs are supplied.

Before resolving runtimes or executing anything, reject an explicitly supplied
empty list, selection combined with all-command mode, blank/unknown/duplicate IDs,
and selected commands that are not
nonempty strings. Use the existing concise CLI validation-error convention.
No selected command runs after any selection validation error and no new receipt
is written for invalid selection.

For explicit selection, CLI success means every selected command passed with
exit zero. Failure/cancellation yields nonzero even for optional selected checks.
Keep existing runtime-unavailable handling and command timeout/cancellation logic.
Every receipt retains the entire manifest `required` list, full checks/environment
digests, and normal dirty/commit binding; only outcomes are selected. A partial
successful run is useful local feedback but is rejected by existing completion
validation. Running exactly every required ID may qualify if all other existing
trust conditions hold; extra optional outcomes still fail exact required matching.
Do not invent a new receipt kind or merge receipts across runs.

### Honest frontend required smoke

Replace the shell's successful skip with nonzero failure explaining that a
running app and `BASE_URL` are required. Check this before launching package tools;
do not install packages or browsers. Replace the generated Playwright skip with
an explicit configuration failure as well, so direct test execution cannot silently
skip the generated smoke. Keep the opt-in frontend capability, pinned dependency,
root visit, nonempty title assertion and ignored screenshot destination. A team
choosing another browser tool supplies its own configured command; the framework
does not inspect arbitrary command internals or mandate Playwright for adoption.

### Small Python behavior test only for new Python starters

Retain `language-check` as syntax validation. Add `application-tests` to required
checks only when `initialize` and `preset == "python"`, with command
`uv run --locked --no-sync python scripts/check_tests.py`. Generate
`tests/test_main.py` using `unittest` and assert the starter's observable
`Hello, world!\n` output, executing its actual entry point (subprocess or captured
main output) rather than reproducing the implementation. A syntax-valid change
in output must fail.

The generated runner discovers `test*.py` below `tests`, reports ordinary unittest
results and exits nonzero on test/import failures, missing/empty discovery, or
when every discovered test is skipped. This is a small project-owned helper, not
an engine-level test abstraction; use normal unittest discovery and result counts.
New test files are discovered without editing the helper. The runner/check installs
nothing and writes no tracked artifacts. Copier excludes both helper and starter
test for non-Python presets and non-initializing adoption. Existing authored check
commands, required IDs, manifests and test files remain under existing adoption/
update preservation rules; do not migrate them automatically.

## Documentation and delivery

Update existing README and portable AI-DLC guidance for explicit check selection,
its partial-evidence limit, and one full required run after integrating the target
branch immediately before merge. Update both frontend workflow copies to replace
skip guidance with setup remedies. Describe syntax versus behavioral starter
coverage accurately and tell teams to retain their existing tools/commands during
adoption; a hello-world assertion is not acceptance coverage for a developed app.
Review existing workflow docs and update catalog code/test mappings for new assets
where needed. Record documentation-impact dispositions against actual content.

Use focused regression tests while editing. Delivery still runs every required
project check; existing archive, merged-revision receipts and finish rules remain.
No paid client comparisons, remote provider qualification or live browser claims
follow from shell tests/mocks. A real local browser smoke run is the integration
check when the prepared browser is available; record absence honestly otherwise.
