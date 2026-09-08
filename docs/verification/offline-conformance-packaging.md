# Packaged offline conformance coverage

This bounded repair belongs to issue #17 and the active portable-development-v4
specification's execution-limitations requirement. It updates the existing isolated
runner's fixture selection, not provider lifecycle behavior or live authorization.

Plan: add Jira Cloud and Plane adapter/shared-workflow suites, include GitHub Projects
in GitHub tracker coverage, and package the exact test/helper closure. Preserve Linear,
SCM and OpenSpec scopes, credential scrubbing, missing-fixture refusal, and explicit
unavailable live scopes. Aggregates include each selected file once. Trusted packaged
sibling test helpers must remain importable without restoring repository source imports
through pytest configuration. Verify actual subprocess execution from a copied kit.

Validation on 2026-09-08, native macOS arm64 / Python 3.12.11:

- The corrected baseline regression run produced 10 failures and one existing pass
  (seven prior tests deselected), exposing missing targets, missing lifecycle coverage,
  and package refusal gaps. Its copied GitHub legacy suite already passed, correctly.
- With targets/files added but the original import mode restored, both copied Jira and
  Plane suites failed to import their sibling helpers. The selected trusted-test import
  mode fixes this without restoring pytest's repository `src` path.
- A hostile repository `src/ai_dlc` sentinel and pytest source-path setting exposed an
  older GitHub fixture's own `PYTHONPATH` override. Removing that fixture-only override
  lets its executable use the prepared installed package, as the container requires.
- `pytest tests/test_conformance.py tests/test_sandbox.py -q`: **22 passed in 20.51s**.
  This includes real subprocess runs of the Dockerfile-copied Jira, Plane, GitHub and
  `all` fixture selections, source-import refusal, helper imports, missing-fixture
  refusal, existing read-only health semantics and fail-closed sandbox checks.
- Repository-wide Ruff format and lint passed; Pyright reported zero errors/warnings;
  generated guidance and generated-file checks passed; strict validation of the active
  `portable-development-v4` change passed.

The worker reused its existing prepared runtime under disk constraints. The coordinator
approved avoiding environment creation/downloads; `sh scripts/bootstrap.sh --source
--plan` inspected source bootstrap pins only. Candidate conformance code and copied test
files ran against the existing prepared Python environment; adapter implementation was
unchanged. This is not a fresh bootstrap or wheel-install qualification.

No full required suite, new container build/image, live service call, release publication,
or native-client qualification was performed. Independent review and integrated required
checks remain pending. The prior 56-test image result in `containers/README.md` describes
the older package; a new digest-addressed image/isolation run remains outstanding.
