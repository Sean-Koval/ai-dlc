- [x] 0. Maintainer confirms the client, credential variable, caps and base image.
- [x] 1. Driver contract; move `deterministic` behind it with no behavior change.
- [x] 2. Base image recipe with Git and the pinned client; `eval image` accepts it.
- [x] 3. Egress proxy, per-attempt internal network, retained proxy log; real-Docker
  tests that an unlisted host is refused and a listed one connects.
- [x] 4. `claude-code` driver: headless run, retained stream, usage, fail closed on
  malformed or truncated streams (tested with recorded streams, no network).
- [x] 5. Budget enforcement across a run.
- [ ] 6. Git observer and the three assertion kinds, with negative tests.
- [ ] 7. Treatment install stage runs `project adopt --apply`; scenario goal prompt.
- [ ] 8. Record implementation evidence and the explicit paid-comparison deferral
  in the runbook; refresh catalog dispositions and archive the delivered code.

## Deferred qualification (original task 8)

The maintainer deferred the paid comparison on September 25, 2026. One real run
with three attempts per arm, its report, costs and limits remain pending under
#138. This is not completed by the implementation archive or code-slice finish.
