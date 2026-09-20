- [ ] 0. Maintainer confirms the client, credential variable, caps and base image.
- [ ] 1. Driver contract; move `deterministic` behind it with no behavior change.
- [ ] 2. Base image recipe with Git and the pinned client; `eval image` accepts it.
- [ ] 3. Egress proxy, per-attempt internal network, retained proxy log; real-Docker
  tests that an unlisted host is refused and a listed one connects.
- [ ] 4. `claude-code` driver: headless run, retained stream, usage, fail closed on
  malformed or truncated streams (tested with recorded streams, no network).
- [ ] 5. Budget enforcement across a run.
- [ ] 6. Git observer and the three assertion kinds, with negative tests.
- [ ] 7. Treatment install stage runs `project adopt --apply`; scenario goal prompt.
- [ ] 8. One real run, three attempts per arm; record the report and its limits in
  the runbook. Catalog, dispositions, archive.
