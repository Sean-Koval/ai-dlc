# Test-driven development workflow

Use this loop for every behaviour change. Each step is small enough to review
on its own, and the test suite stays green between steps.

## 1. Red: write one failing test

- State the behaviour in the test name, not the implementation.
- Run only that test and confirm it fails for the expected reason. A test that
  fails because of a typo or missing import proves nothing yet.
- Do not write production code until the failure is the right one.

## 2. Green: make it pass with the smallest change

- Implement just enough for the new test and the existing suite to pass.
- Prefer the obvious implementation over a general one; generality comes from
  the next test, not from anticipation.
- Run the whole suite before moving on.

## 3. Refactor: improve the design under a green suite

- Remove duplication introduced by the last two steps.
- Rename until the code reads like the test names.
- Keep the suite green after every extraction or rename; if it goes red,
  undo the last change rather than debugging forward.

## Working with Claude Code

- Ask for the failing test first and review it before asking for the
  implementation. The test is the specification.
- When a test is hard to write, treat that as design feedback: the unit is
  probably too large or has a hidden dependency.
- The `Stop` hook in `.claude/settings.json` runs the project's format, lint,
  test and security checks at the end of each turn, so a red suite surfaces
  before the next step starts.

## Definition of done for a change

- New behaviour has at least one test that would fail without it.
- No test was deleted or weakened to get to green.
- Formatting and lint pass with no new suppressions.
