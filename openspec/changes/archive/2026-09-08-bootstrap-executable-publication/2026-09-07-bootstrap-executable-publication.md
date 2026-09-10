> Historical record. Retained for provenance, not current implementation guidance.
> Consult docs/index.md, canonical OpenSpec requirements and the tracker.

# Bootstrap executable publication repair

Authorized bounded discovered-behavior child of GitHub #14. Base: root `64cb09f`.
Spec: [bootstrap-executable-publication](specs/bootstrap-executable-publication/spec.md).

1. Demonstrate red real-script old-descriptor regressions for uv/uvx/mise and a synchronized overlapping-download regression. Use isolated local fixtures, no network or shared tools.
2. Publish staged executable bytes and mode by same-filesystem rename. Use independent download files. Preserve previous installed files on failures; retain/report staging instead of deleting mutable pathnames.
3. Exercise copy/mode/rename failures, replaced failed stages and unexpected destination types. Preserve source/template equality.
4. Run required checks using an isolated prepared environment. Record actual source bootstrap separately and do not claim a cause or cure for the observed macOS stall without evidence.
5. Hand a clean commit to independent review. Root owns integration/archive/CI/work finish; this does not complete parent #14.

Shared venv installation, cross-version toolset atomicity and global CLI symlink
selection remain outside this repair. No shared runtime mutations or process cleanup.
