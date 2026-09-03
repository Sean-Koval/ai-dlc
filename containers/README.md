# Provider conformance container

This image supplies `ai-dlc-conformance`, its installed AI-DLC package, and the real
provider/workflow fixture tests under `/kit`. Default targets run those tests with fake
credentials and no live API calls. The sandbox runner supplies a digest-pinned image,
`--network=none`, a read-only root filesystem, an unprivileged UID, resource limits,
read-only fixtures, and a dedicated executable `/work` scratch tmpfs. `/tmp` remains
non-executable. Executable provider fixtures need `/work`; no host fallback is allowed.

The conformance program itself is **normal trusted-user execution**, not an isolation
boundary. Running it directly on a host runs Python and pytest with that user's
permissions. Only the Docker runner provides the documented container controls.

## Build with a reviewed digest

Supply a reviewed Linux base image that includes uv, Python >=3.12, Git, and CA roots.
A uv-derived Python image is suitable only if it has those tools. Git is required by
real temporary-repository workflow tests. The Dockerfile deliberately fails if Git or
uv is missing; it does not silently install unpinned operating-system packages. A live
GitHub health check additionally needs `gh` in the reviewed base image.

Follow the [official uv container documentation](https://docs.astral.sh/uv/guides/integration/docker/)
when preparing that base. Resolve and review its actual registry digest. No image or
image digest is supplied or published by this repository.

Validate the supplied reference **before** Docker resolves `FROM`:

```sh
: "${CONFORMANCE_BASE_IMAGE:?Set a reviewed name@sha256:digest reference}"
python -c 'import re,sys; assert re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}",sys.argv[1]), "digest-pinned base required"' "$CONFORMANCE_BASE_IMAGE"
docker build --build-arg "BASE_IMAGE=$CONFORMANCE_BASE_IMAGE" \
  --file containers/provider-tests.Dockerfile --tag ai-dlc-provider-tests:local .
```

`BASE_IMAGE` has no default; the Dockerfile also validates the digest reference and
Python version. It copies only declared source/assets/tests, not the host home, `.git`,
`.venv`, or credential folders. `uv sync --locked --no-editable --group dev` installs
the lock-defined dependencies and a non-editable package. Network access is needed at
build time to fetch locked dependencies, but not for default test execution.

After publishing the result to a registry you control, record its actual immutable
`name@sha256:digest` in the provider-test manifest. A local tag or arbitrary image ID is
not a substitute for the runner's required repository digest reference. No publish step
is performed automatically.

## Test scopes

`ai-dlc-conformance --list` prints implemented scopes. Default fixture targets:

- `linear`: HTTP transport read/error fixtures.
- `github-issues`: production executable adapter wrapping a fake GitHub CLI.
- `openspec`: native archive/provenance fixtures.
- `github` or `scm`: receipt and authenticated workflow-evidence fixtures.
- `providers`, `workflow`, or `all`: their complete packaged fixture suites.

The result identifies `scope=offline-fixtures`; it does not claim live API correctness.
Missing packaged tests, unknown targets, and unimplemented targets fail explicitly.
Cloudflare deployment and knowledge live conformance are unavailable, rather than
reported as passing without tests.

## Explicit live read-only health scope

Only `linear --live` and `github-issues --live` exist. Neither performs mutation
conformance. Both require a read-only mounted `/fixtures/provider.toml`, an exact
`AI_DLC_SANDBOX_WORKSPACE` match, an explicit credential environment reference, and an
existing `health_reference`. Successful results say `scope=read-only-health`, with
`mutation_conformance=unavailable` and `full_conformance=unavailable`.

Linear fixture example (use real sandbox IDs, never credential values):

```toml
sandbox_workspace = "sandbox-team-id"
[provider]
kind = "linear"
team_id = "sandbox-team-id"
token_env = "LINEAR_SANDBOX_TOKEN"
health_reference = "existing-issue-uuid"
```

Linear reads the selected issue and verifies its returned team ID. GitHub example:

```toml
sandbox_workspace = "sandbox-owner/sandbox-repository"
[provider]
kind = "github-issues"
repository = "sandbox-owner/sandbox-repository"
token_env = "GH_TOKEN"
health_reference = "12"
```

GitHub accepts only an issue number in that repository and checks the returned issue
identity/URL. `GH_TOKEN` or `GITHUB_TOKEN` must be explicitly forwarded by the live test
manifest. The sandbox runner separately requires pinned proxy/enforcement images,
explicit allowed hosts, and a namespace firewall. Merely setting proxy environment
variables is not sufficient egress enforcement.

## Verification limits

The container build/run, direct-egress rejection, and live API health calls have not
been executed in the current development environment because the Docker daemon is unavailable (the client is installed).
Host unit tests verify command selection and health-check behavior with transport
fixtures. Run the actual image through the sandbox runner on a Docker-capable host
before treating isolation or live compatibility as verified.
