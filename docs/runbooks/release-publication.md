# Release publication

This runbook publishes a hash-bound AI-DLC release and describes how a machine
installs from it. Publishing is the maintainer's action: pushing a version tag.
The workflow does the building, verification and upload; nothing is published
from a laptop.

## What a release contains

| Asset | Produced by | Verified how |
| --- | --- | --- |
| `ai_dlc-<version>-py3-none-any.whl` | `uv build` | Installed with `--no-deps` after the constraints in the workflow |
| `ai_dlc-<version>.tar.gz` | `uv build` | Source distribution for inspection |
| `requirements.txt` | `uv export --locked --no-dev` | Hashed constraints; installed with `--require-hashes` |
| `release.sh` | `scripts/release_manifest.py` | Shell assignments naming the wheel and constraints URLs and SHA-256 digests |
| `bootstrap.sh`, `versions.sh`, `download.sh` | `project-templates/project/` | The standalone installer and its pinned uv, Python and mise digests |
| `SHA256SUMS` | `sha256sum` in the workflow | Digests of every asset above |

`release.sh` cannot live inside the wheel it hashes. Release-mode bootstrap keeps
a copy beside the installed engine, and `ai-dlc project init` or `adopt` writes
that copy into new projects as `bootstrap/release.sh`, so a generated project's
own bootstrap and CI install the exact assets that generated it.

## Publish

1. On `main`, confirm the version in `pyproject.toml` is the version to publish
   and that `ai-dlc project check --required` passes at that commit.
2. Optional rehearsal: run the `Release` workflow manually with any HTTPS
   directory as `artifact_base_url`. It uploads a `release-candidate` artifact to
   the run and publishes nothing.
3. Tag the commit and push the tag:

   ```sh
   git tag -a v0.4.0 -m "AI-DLC 0.4.0" <commit>
   git push origin v0.4.0
   ```

4. Watch the `Release` workflow. `package` refuses a tag whose version differs
   from `pyproject.toml`, runs the required checks, builds, verifies the wheel
   against the constraints and scaffolds with it, then writes `release.sh`
   against `https://github.com/<owner>/<repo>/releases/download/<tag>`.
   `publish` creates the GitHub Release with exactly those files.
   `verify-published` then installs from the published assets on Linux x64,
   Linux ARM64 and macOS, generates a python project with the released engine,
   confirms the generated `bootstrap/release.sh` is byte-identical, bootstraps
   that project in release mode and runs its required checks.
5. If `verify-published` fails, delete the release and the tag, fix, and tag
   again. Consumers pin digests, so a withdrawn release cannot be replaced
   silently by different bytes under the same name.
6. Record the outcome in [release verification](../release-verification.md):
   tag, commit, which workflow jobs passed on which runners, and which
   outstanding obligations the release satisfies or leaves open.

## Install from a release

On a machine with a POSIX shell, `curl`, CA certificates and `tar`:

```sh
mkdir -p ai-dlc-install/scripts ai-dlc-install/bootstrap && cd ai-dlc-install
for f in bootstrap.sh versions.sh download.sh release.sh SHA256SUMS; do
  curl --fail --location --proto '=https' --tlsv1.2 -O "https://github.com/Sean-Koval/ai-dlc/releases/download/v0.4.0/$f"
done
grep -E ' (release|bootstrap|versions|download)\.sh$' SHA256SUMS | sha256sum -c -
mv bootstrap.sh scripts/ && mv versions.sh download.sh release.sh bootstrap/
printf 'schema = 4\n' > ai-dlc.toml
sh scripts/bootstrap.sh
```

Use `shasum -a 256 -c -` on macOS. The bootstrap downloads uv, a managed
Python and mise at the pinned digests, installs the wheel with hashed
constraints, and prints the two directories to add to `PATH`. From there
`ai-dlc project init <path> --preset python` creates a project whose
`bootstrap/release.sh` is included automatically.

A source-installed engine (`sh scripts/bootstrap.sh --source` in this
repository) has no manifest. Projects it generates report
`"release_manifest": "absent"` and need `bootstrap/release.sh` from a published
release before their CI can bootstrap.

## What this does not prove

The workflow proves installation from the published assets on its runners. It
does not prove a factory-clean machine walkthrough, hosted-client sessions or
live provider qualification; those remain in the outstanding list in
[release verification](../release-verification.md).
