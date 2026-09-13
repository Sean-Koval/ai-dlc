# Publish a versioned AI-DLC release with bootstrap artifacts

## Context
`scripts/release_manifest.py` hashes one captured byte sequence of the wheel and constraints and writes shell assignments that release-mode bootstrap sources. The manifest therefore cannot live inside the wheel it describes. The template ships `bootstrap/versions.sh` and `bootstrap/download.sh` but not `release.sh`, and `scripts/check_generated.py` keeps those packaged copies identical to the repository's.

## Goals / Non-Goals
Make a tag produce published, verifiable assets; make a generated project bootstrap from them without hand-copying files; keep the maintainer in control of publication; record honestly what was proven. Do not publish to a package index, do not change how bootstrap verifies downloads, and do not claim clean-machine qualification beyond what actually ran.

## Decisions
- Tag is the publish trigger. The workflow's `workflow_dispatch` path stays a candidate build that publishes nothing; a `v*` tag runs the same build and verification, then creates the GitHub Release with the wheel, the locked hashed constraints, the manifest and a checksum file. The manifest's base URL is the release download directory, so the published bytes are the hashed bytes. The tag version must equal `pyproject.toml`'s version or the job fails before any upload.
- The manifest travels beside the engine, not inside it. Release-mode bootstrap copies `bootstrap/release.sh` into the engine's virtual environment directory. The running engine finds it at `sys.prefix/release.sh`, which is exact for a release-installed engine and absent for a source environment. Project generation reads that file and includes it as `bootstrap/release.sh` in the rendered set, so conflict detection, authored-file protection and the `files` result apply to it like any template file.
- Absence is reported, not papered over. A source-installed engine returns `release_manifest = "absent"` and the generated project keeps refusing release-mode bootstrap with the existing message until a manifest is added from a published release.
- Verification after publication uses the published assets. The workflow's final job bootstraps a throwaway project in release mode from the real release URL on Linux and macOS and runs a python preset project's required checks. Local evidence in this cycle uses a fresh bootstrap home and a local HTTPS server standing in for the release host, and is recorded as such.
- Rejected: fetching the manifest over the network during `project init`, which would make generation depend on connectivity and on the release host. Rejected: embedding a self-referential manifest in the wheel, which is impossible to hash consistently.

## Risks / Trade-offs
A release-installed engine that is later upgraded by hand without re-running bootstrap keeps the old manifest; generated projects would pin the old version, which is still a verified one. The workflow can only be proven end to end by pushing a tag; the maintainer decides when.

## Migration Plan
No configuration changes for existing projects. A project generated before this change adds `bootstrap/release.sh` from a published release by hand, as its guidance already says.
