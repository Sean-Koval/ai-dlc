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
| `bootstrap.ps1`, `windows.ps1`, `windows-native.cs`, `windows-select.py`, `windows.json` | `project-templates/project/` | Native installer, guarded storage helper, selection helper and pinned Windows x64 prerequisites; present in native-capable candidates/releases only |
| `SHA256SUMS` | `scripts/prepare_release_assets.py` | Digests of every asset above |

`release.sh` cannot live inside the wheel it hashes. Release-mode bootstrap keeps
a copy beside the installed engine, and `ai-dlc project init` or `adopt` writes
that copy into new projects as `bootstrap/release.sh`, so a generated project's
own bootstrap and CI install the exact assets that generated it.

## Publish

1. On `main`, confirm the version in `pyproject.toml` is the version to publish
   and that `ai-dlc project check --required` passes at that commit.
2. Optional rehearsal: run the `Release` workflow manually with any HTTPS
   directory as `artifact_base_url`, leaving `verify_published_tag` empty. It
   uploads a `release-candidate` artifact to the run and publishes nothing, even
   when the workflow is dispatched at a tag.
3. Tag the commit and push the tag:

   ```sh
   git tag -a v0.4.0 -m "AI-DLC 0.4.0" <commit>
   git push origin v0.4.0
   ```

4. Watch the `Release` workflow. `package` refuses a tag whose version differs
   from `pyproject.toml`, runs the required checks, builds, verifies the wheel
   against the constraints and scaffolds with it, then writes `release.sh`
   against `https://github.com/<owner>/<repo>/releases/download/<tag>`.
   The Windows candidate consumer job must succeed before `publish` creates the
   GitHub Release with exactly those files.
   `verify-published` then installs from the published assets on Linux x64,
   Linux ARM64 and macOS, generates a python project with the released engine,
   confirms the generated `bootstrap/release.sh` is byte-identical, bootstraps
   that project in release mode and runs its required checks. A separate Windows
   Server consumer job exercises the original native assets and generic/Python
   project journeys; record its outcome independently of the Unix matrix.
5. If `verify-published` fails, inspect the exact failed step. A verification
   harness or transient download failure does not justify replacing verified
   package bytes. Fix the harness and replay the existing release as below. If
   the artifacts themselves are defective, a maintainer must explicitly withdraw
   the affected release and tag before repairing and publishing a replacement.
   Consumers pin digests; never silently replace bytes under the same name.
6. Record the outcome in [release verification](../release-verification.md):
   tag, commit, which workflow jobs passed on which runners, and which
   outstanding obligations the release satisfies or leaves open.

## Verify an existing release without publishing

After a verification harness fix is merged, a maintainer can run:

```sh
gh workflow run release.yml --ref main \
  -f artifact_base_url=https://github.com/Sean-Koval/ai-dlc/releases/download/v0.4.0 \
  -f verify_published_tag=v0.4.0
```

`artifact_base_url` remains required for candidate-dispatch compatibility but is
ignored in replay mode. The nonempty `verify_published_tag` skips `package` and
`publish` and runs the configured Unix and native Windows consumer jobs using
existing published assets. Replaying historical v0.4.0 cannot establish native
compatibility: its original assets lack the native installer. The native job
reports that limitation instead of substituting current source assets.
Manual dispatch cannot publish, including a dispatch whose workflow ref is a tag.
Normal tag-push consumers still require successful package and publish jobs.
The selected tag enters quoted download arguments through `RELEASE_TAG`.

The consumer seed uses local first-use setup so generated files can be created.
The released engine generates a Python demo; its included manifest is compared
byte for byte with the seed's manifest. The demo then runs its own release-mode
bootstrap with local first-use setup, initializes and commits its own Git
repository with repository-local fixture identity, then runs explicit
`github-actions` required checks. This preserves the production CI freshness policy for initialized
projects. `GITHUB_PATH` still carries the installed tools to subsequent steps.

Record both the original publication tag/commit/run and the replay workflow
commit/run/platforms. A successful replay qualifies those unchanged published
assets with the corrected harness; it does not turn the failed original run green
or prove factory-clean, container, cloud-client, provider or human evaluation.

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

## Native Windows assets and compatibility

Native installation requires the complete assets from a compatible release or
candidate: `bootstrap.ps1`, `windows.ps1`, `windows-native.cs`, `windows-select.py`,
`windows.json`, `release.sh`, the named wheel and hashed requirements, and
`SHA256SUMS`. Keep the entry point at `scripts/bootstrap.ps1` and its helper files
and `release.sh` under `bootstrap/`, as in a generated project. Verify the original
asset hashes before running the downloaded installer. The release manifest is
parsed as inert data by the native installer; it is not executed as a shell script.

On Windows x64/local NTFS, a compatible generated project can preview release-mode
setup with `.\scripts\bootstrap.ps1 -Root $PWD.Path -Plan` in 64-bit Windows
PowerShell 5.1, then omit `-Plan` to apply. The installer prints direct executable
paths and process-local PATH activation. Persistent PowerShell activation is a
separate [preview/apply action](machine-enrollment.md#native-windows-setup-and-activation).
It does not need WSL, elevate, or change execution policy or machine PATH.

The historical published **v0.4.0 assets are not native-compatible**. Adding a
current PowerShell script beside that old wheel does not qualify or upgrade the
release. The package version alone cannot distinguish a newer source checkout
from those original assets; retain exact source revision or release asset hashes
in evidence. Until a compatible release is explicitly published, use a reviewed
source checkout for native development. Source bootstrap prepares the engine
checkout; consumer qualification must separately install the original candidate
or published wheel and use it in target projects.

The native verification driver records the artifact hashes separately from its
controller revision. It exercises a bare seed, generated generic/Python projects,
required receipts, deliberate check failure/recovery, and authored-edit refusal.
Candidate evidence does not qualify an already-published tag, and replay never
replaces its bytes. Hosted Windows Server runs do not establish the pending clean
Windows 11, native client instruction/skill/MCP recognition, or authentication
walkthroughs. Minimal Git/GH installation may still require manual recovery under
an approved installer policy; no-elevation behavior is not inferred from winget
manifest labels.

## What this does not prove

The workflow proves installation from the published assets on its runners. It
does not prove a factory-clean machine walkthrough, hosted-client sessions or
live provider qualification; those remain in the outstanding list in
[release verification](../release-verification.md).
