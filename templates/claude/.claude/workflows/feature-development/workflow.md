# Feature development workflow

A feature moves through five phases. Each phase ends with something a reviewer
can read, and no phase writes code that the previous phase did not call for.

## 1. Understand

- Write the problem in one paragraph: who is affected, what they cannot do
  today, and how you will know it is fixed.
- List the constraints you must respect: existing contracts, data formats,
  performance limits, security boundaries.
- Name what is out of scope so the change stays small.

## 2. Design

- Sketch the interfaces first: functions, endpoints, schema changes, CLI flags.
- Identify the risky decision, if there is one, and record why you chose the
  option you did. A short note in the pull request is enough.
- Split the work into slices that can each ship behind the existing tests.

## 3. Implement

- Follow the [test-driven loop](../tdd/workflow.md) for each slice.
- Keep commits focused: one slice, one conventional commit message.
- Update documentation in the same change when behaviour visible to users
  changes.

## 4. Verify

- Run the full test suite, formatting and lint. The `Stop` hook in
  `.claude/settings.json` runs these at the end of every Claude Code turn,
  but run them yourself before opening the pull request.
- Exercise the feature end to end once by hand, or through an integration
  test, and record what you saw.
- Check the security scan output for new findings before you dismiss them.

## 5. Review and release

- Open a pull request that states the behaviour, the verification you did,
  and what remains out of scope.
- Address review comments with follow-up commits rather than force-pushes,
  so reviewers can see what changed.
- After merge, confirm the change on the target branch's CI run before
  closing the tracking item.

## Working with Claude Code

- Give the session the problem statement and constraints from phase 1 before
  asking for code; it will otherwise invent both.
- Ask for the design sketch as a message, not as code, and correct it before
  implementation starts.
- Review generated tests as carefully as generated code; a passing test that
  asserts the wrong thing is worse than no test.
