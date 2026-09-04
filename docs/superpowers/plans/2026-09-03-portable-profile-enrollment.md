# Portable Profile and Machine Enrollment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AI-DLC able to enroll a secret-free personal profile from an exact Git revision, bind that profile to one machine without copying secrets, resolve it automatically with project configuration, and safely plan, apply, synchronize, inspect, and diagnose the resulting machine.

**Architecture:** Keep the portable profile, project configuration, machine binding, credential values, and generated client files as separate ownership layers. A Git-backed profile store materializes an immutable, digest-verified cache; a small enrollment store owns the active lock and machine file; the existing configuration and provisioning services consume those resolved paths; and a thin `machine` CLI exposes preview-first lifecycle operations. Existing schema-4 files and `setup`, `profile show`, `doctor`, and `--machine` entry points remain compatible.

**Tech Stack:** Python 3.12, Typer, Pydantic 2, `tomllib`, `tomli-w`, Git CLI, pytest, Ruff, Pyright, existing atomic-write and agent-rendering utilities.

**Spec:** [Portable Profile and Machine Enrollment Design](../specs/2026-09-03-portable-profile-enrollment-design.md)

## Global Constraints

- Preserve the unrelated worktree files `.DS_Store`, `.ai-dlc/.DS_Store`, and `target/.rustc_info.json`; never stage, edit, or delete them.
- Never read, print, copy, stage, or serialize values from `.ai-dlc/local/linear.env` or `.ai-dlc/local/.linear.env.swp`.
- Never put a credential value in a profile, lock, machine binding, cache receipt, plan, error, journal, generated client file, or test snapshot. Tests must use unmistakably fake sentinel values and assert their absence from persisted files and returned structures.
- Keep schema 4 for base, personal, project, and machine configuration. Enrollment locks use schema 1.
- Add no runtime dependency. Invoke Git with argument arrays and `shell=False` behavior through `subprocess.run`.
- Treat the checked-out public repository as product source, not as the user's portable personal-profile repository. Tests create disposable Git repositories; documentation explains how to create the separate private repository.
- Make every state-changing lifecycle action preview-first. `enroll`, `migrate`, and `sync` change active state only with `--apply`; `machine plan` never writes; `machine apply` is the explicit workstation/client mutation.
- Write AI-DLC-owned metadata atomically. Activate a new lock last. A failed candidate validation or reconciliation must leave the prior lock byte-for-byte unchanged.
- Resolve configuration in the fixed order base → personal → project → machine. An explicit personal or machine file replaces the enrolled file in that scope; it is not a fifth precedence layer.
- Preserve user-authored Codex, Claude, shell, and MCP configuration through the existing ownership checks.
- Do not perform a live Linear mutation as part of the automated tests. The final dogfood step may use only the already-designated `sandbox-aidlc` workspace and only when its team/status configuration is complete.

## Spec Coverage Map

| Approved design area | Implemented and verified in |
|---|---|
| Secret-free profile identity and credentials | Tasks 1, 3, and 9 |
| XDG enrollment lock, cache, and machine binding | Tasks 2, 3, and 5 |
| Fixed configuration precedence and explicit overrides | Task 4 |
| Preview-first enroll, migrate, status, plan, apply, sync, and doctor | Tasks 5, 6, and 7 |
| Exact Git revisions, offline cache, integrity, and transaction failures | Tasks 3, 6, and 8 |
| Current CLI/schema compatibility | Tasks 1, 4, 6, and 7 |
| Two-machine proof, client ownership, and secret redaction | Task 8 |
| Public examples, handbook, migration, and honest follow-on gaps | Tasks 9 and 10 |
| Dogfood record, formal specification, review, CI, PR, and merge | Tasks 0 and 10 |

---

### Task 0: Bind the approved design to AI-DLC's own work and specification records

**Files:**

- Create: `.ai-dlc/work/portable-profile-enrollment.toml`
- Create: `openspec/changes/portable-profile-enrollment/proposal.md`
- Create: `openspec/changes/portable-profile-enrollment/design.md`
- Create: `openspec/changes/portable-profile-enrollment/tasks.md`

- [ ] **Step 1: Create the reviewed work record**

Create `.ai-dlc/work/portable-profile-enrollment.toml` with this exact initial content:

```toml
schema = 1
id = "portable-profile-enrollment"
title = "Implement portable profile and machine enrollment"
scope = "Enroll a secret-free personal profile from an exact Git revision, bind it per machine, and safely resolve, reconcile, synchronize, inspect, and diagnose it."
requires_spec = true
spec_reason = "Changes configuration ownership, credential references, machine state, CLI behavior, and synchronization guarantees."
acceptance = [
  "Two isolated machines resolve one pinned profile with distinct local bindings",
  "Preview, apply, sync, status, and doctor preserve active state on failure",
  "Credentials remain external and no secret value is persisted or returned",
  "Existing schema-4 and setup/profile/doctor interfaces remain compatible",
  "Required project checks and independent review pass",
]
reviewed = true

[providers]
specs = "openspec"
tracker = "linear"
scm = "github"
knowledge = "obsidian"
deploy = "none"

[artifacts]
spec = "openspec/changes/portable-profile-enrollment"
branch = "codex/portable-profile-enrollment"
```

- [ ] **Step 2: Translate the approved design into the repository's OpenSpec shape**

Create:

- `proposal.md` with Why, What Changes, Capabilities, and Impact sections;
- `design.md` with the five ownership layers, lock/cache transaction, precedence, credential boundary, command/service boundary, compatibility strategy, and explicit non-goals;
- `tasks.md` with Tasks 1–10 in this plan as unchecked implementation groups and a note that Task 0 is the already-completed bootstrap record.

The OpenSpec documents summarize and link to the approved detailed design. They do not invent requirements or duplicate the full 367-line design verbatim.

- [ ] **Step 3: Validate the work and specification records**

Run:

```sh
ai-dlc work status portable-profile-enrollment
openspec validate portable-profile-enrollment --strict --no-interactive
git diff --check
```

Expected: the work record parses and the active OpenSpec change validates. `work status` may report no tracker artifact because publication is deliberately deferred until non-secret sandbox IDs are available.

- [ ] **Step 4: Commit Task 0**

Run:

```sh
git add .ai-dlc/work/portable-profile-enrollment.toml openspec/changes/portable-profile-enrollment
git commit -m "docs: specify portable profile enrollment"
```

---

### Task 1: Add portable credential declarations and machine bindings

**Files:**

- Create: `src/ai_dlc/credentials.py`
- Modify: `src/ai_dlc/config.py`
- Modify: `tests/test_config.py`
- Create: `tests/test_credentials.py`

- [ ] **Step 1: Write failing scope and merge tests**

Add tests to `tests/test_config.py` that establish the schema contract:

```python
def test_personal_credential_requirement_and_machine_binding_merge():
    from ai_dlc.config import resolve_layers

    result = resolve_layers(
        [
            (
                "personal",
                {
                    "schema": 4,
                    "profile_id": "sean-development",
                    "credentials": {
                        "linear-sandbox": {
                            "description": "Linear sandbox access",
                            "required_by": ["provider.linear-sandbox"],
                        }
                    },
                },
            ),
            (
                "machine",
                {
                    "schema": 4,
                    "credentials": {
                        "linear-sandbox": {
                            "source": "environment",
                            "variable": "LINEAR_SANDBOX_TOKEN",
                        }
                    },
                },
            ),
        ]
    )

    assert result.values["credentials"]["linear-sandbox"] == {
        "description": "Linear sandbox access",
        "required_by": ["provider.linear-sandbox"],
        "source": "environment",
        "variable": "LINEAR_SANDBOX_TOKEN",
    }
    assert result.sources["credentials.linear-sandbox.description"] == "personal"
    assert result.sources["credentials.linear-sandbox.variable"] == "machine"
```

Also test all invalid placements:

- `profile_id` is allowed only in a personal layer;
- personal credentials reject `source` and `variable`;
- machine credentials reject `description` and `required_by`;
- machine credential sources other than `environment` fail;
- credential IDs and environment variable names must be stable slugs/identifiers;
- secret-shaped value fields remain rejected recursively.

- [ ] **Step 2: Run the focused config tests and confirm failure**

Run:

```sh
uv run --locked --no-sync pytest tests/test_config.py -q
```

Expected: the new tests fail because `profile_id` and `credentials` are unknown fields.

- [ ] **Step 3: Implement scope validation**

In `src/ai_dlc/config.py`:

- add `profile_id` to the personal scope only;
- add `credentials` to personal and machine scopes;
- validate credential tables per layer before recursive merging;
- require logical IDs to match `^[a-z0-9][a-z0-9-]*$`;
- require environment variable names to match `^[A-Z_][A-Z0-9_]*$`;
- require personal entries to contain `description` and a string list `required_by`;
- require machine entries to contain only `source = "environment"` and `variable`;
- keep machine providers restricted to the existing account/reference fields.

Use small private helpers such as `_validate_credentials(layer, value)` rather than adding credential-specific branches to the merge algorithm.

- [ ] **Step 4: Write failing redaction and legacy-normalization tests**

Create `tests/test_credentials.py` with these behaviors:

```python
def test_status_reports_presence_without_returning_environment_value(monkeypatch):
    from ai_dlc.credentials import credential_status

    marker = "fake-value-that-must-not-escape"
    monkeypatch.setenv("LINEAR_SANDBOX_TOKEN", marker)
    config = {
        "credentials": {
            "linear-sandbox": {
                "description": "Linear sandbox access",
                "required_by": ["provider.linear-sandbox"],
                "source": "environment",
                "variable": "LINEAR_SANDBOX_TOKEN",
            }
        }
    }

    result = credential_status(config)

    assert result == [
        {
            "id": "linear-sandbox",
            "description": "Linear sandbox access",
            "required_by": ["provider.linear-sandbox"],
            "source": "environment",
            "variable": "LINEAR_SANDBOX_TOKEN",
            "configured": True,
            "present": True,
        }
    ]
    assert marker not in repr(result)
```

Add tests that:

- an unbound requirement is `configured = False` and `present = False`;
- an unset bound variable is configured but not present;
- a legacy provider with `token_env = "LINEAR_API_KEY"` appears as logical ID `provider.<provider-id>` only when no explicit credential covers it;
- supplied `environ: Mapping[str, str]` is honored without mutating `os.environ`;
- results are sorted by logical ID.

- [ ] **Step 5: Run the credential tests and confirm failure**

Run:

```sh
uv run --locked --no-sync pytest tests/test_credentials.py -q
```

Expected: collection fails because `ai_dlc.credentials` does not exist.

- [ ] **Step 6: Implement the credential report**

Create `src/ai_dlc/credentials.py` with the public interface:

```python
from collections.abc import Mapping
from typing import Any


def credential_status(
    config: dict[str, Any],
    environ: Mapping[str, str] | None = None,
) -> list[dict[str, object]]:
    """Return credential readiness metadata without returning credential values."""
```

Normalize legacy `providers.<id>.token_env` references into the same report. Explicit logical requirements win over a synthetic legacy entry when their `required_by` contains `provider.<id>`. Inspect only key presence and nonempty value truthiness; never copy the value into a local returned object.

- [ ] **Step 7: Verify and commit Task 1**

Run:

```sh
uv run --locked --no-sync pytest tests/test_config.py tests/test_credentials.py -q
uv run --locked --no-sync ruff check src/ai_dlc/config.py src/ai_dlc/credentials.py tests/test_config.py tests/test_credentials.py
uv run --locked --no-sync pyright --pythonpath .venv/bin/python
git diff --check
```

Expected: all commands pass.

Commit only the Task 1 files:

```sh
git add src/ai_dlc/config.py src/ai_dlc/credentials.py tests/test_config.py tests/test_credentials.py
git commit -m "feat: model portable credential bindings"
```

---

### Task 2: Model enrollment locks and XDG-owned paths

**Files:**

- Create: `src/ai_dlc/enrollment.py`
- Create: `tests/test_enrollment.py`
- Modify: `src/ai_dlc/files.py`

- [ ] **Step 1: Write failing path, model, and atomicity tests**

Create `tests/test_enrollment.py` covering:

1. Explicit `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `XDG_STATE_HOME` produce:
   - `config/ai-dlc/enrollment.toml`;
   - `config/ai-dlc/machines/<machine-id>.toml`;
   - `cache/ai-dlc/profiles/<profile-id>/<commit>/`;
   - `state/ai-dlc/`.
2. With no XDG variables, a supplied home uses `.config`, `.cache`, and `.local/state` fallbacks.
3. `EnrollmentLock` accepts exactly schema 1, a stable profile ID, a stable machine ID, a 40-character lowercase Git commit, a 64-character lowercase SHA-256 digest, a relative subdirectory, and a relative profile file.
4. Absolute paths, `..`, empty IDs, uppercase IDs, unknown lock fields, malformed commits, and malformed digests fail before a write.
5. `write_lock` produces parseable TOML, mode `0600`, and an atomic final file.
6. `ensure_machine_file` creates only `schema = 4`, uses mode `0600`, and never replaces an existing file.
7. Replacing a lock through a deliberately failing writer leaves its prior bytes intact. Extend `atomic_write` only if the current helper cannot support this test.

Use the exact model shape:

```python
class EnrollmentLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[1] = 1
    profile_id: str
    source: str
    requested_ref: str
    resolved_commit: str
    content_sha256: str
    machine_id: str
    subdirectory: str = ""
    profile_file: str = "ai-dlc-profile.toml"
```

- [ ] **Step 2: Run the enrollment tests and confirm failure**

Run:

```sh
uv run --locked --no-sync pytest tests/test_enrollment.py -q
```

Expected: collection fails because `ai_dlc.enrollment` does not exist.

- [ ] **Step 3: Implement paths and validated persistence**

Create `src/ai_dlc/enrollment.py` with this public surface:

- immutable `EnrollmentPaths(config_root: Path, cache_root: Path, state_root: Path)`;
- `EnrollmentPaths.from_environment(home: Path | None = None, environ: Mapping[str, str] | None = None) -> EnrollmentPaths`;
- `EnrollmentPaths.lock_file -> Path`;
- `EnrollmentPaths.machine_file(machine_id: str) -> Path`;
- `EnrollmentPaths.profile_root(profile_id: str, resolved_commit: str) -> Path`;
- `read_lock(paths: EnrollmentPaths) -> EnrollmentLock | None`;
- `write_lock(paths: EnrollmentPaths, lock: EnrollmentLock) -> Path`;
- `ensure_machine_file(paths: EnrollmentPaths, machine_id: str) -> Path`;
- `active_profile_file(paths: EnrollmentPaths, lock: EnrollmentLock) -> Path`.

Validate relative paths using `PurePosixPath`; reject absolute paths, empty components, `.` and `..`. Serialize with `tomli_w`. If `atomic_write` cannot set a private final mode safely, add an optional `mode: int | None = None` argument and preserve all existing callers' behavior when it is omitted.

- [ ] **Step 4: Verify and commit Task 2**

Run:

```sh
uv run --locked --no-sync pytest tests/test_enrollment.py tests/test_user_agents.py -q
uv run --locked --no-sync ruff check src/ai_dlc/enrollment.py src/ai_dlc/files.py tests/test_enrollment.py
uv run --locked --no-sync pyright --pythonpath .venv/bin/python
git diff --check
```

Expected: all commands pass, including existing ownership-file behavior.

Commit only the Task 2 files:

```sh
git add src/ai_dlc/enrollment.py src/ai_dlc/files.py tests/test_enrollment.py
git commit -m "feat: persist machine enrollment state"
```

---

### Task 3: Resolve Git sources into an immutable verified cache

**Files:**

- Create: `src/ai_dlc/profile_source.py`
- Create: `tests/test_profile_source.py`

- [ ] **Step 1: Write a reusable disposable-Git fixture**

In `tests/test_profile_source.py`, add a helper that initializes a temporary Git repository, configures a local test identity, writes `ai-dlc-profile.toml`, commits it, and returns the repository path and exact commit. Keep the fixture local; no network access is required.

The normal manifest should be:

```toml
schema = 4
profile_id = "test-development"

[modules]
include = ["core"]

[credentials.linear-sandbox]
description = "Linear sandbox access"
required_by = ["provider.linear-sandbox"]
```

- [ ] **Step 2: Write failing resolution and cache tests**

Test these behaviors:

- resolving `main` yields the exact 40-character commit and a deterministic 64-character bundle digest;
- the materialized cache contains only the declared profile file without `.git` metadata;
- unrelated files in the selected repository/subdirectory are not copied into the cache;
- a relative `subdirectory` works and cannot escape the repository;
- `profile_id` must match the normal manifest;
- normal enrollment rejects a missing `profile_id`;
- legacy resolution accepts an explicit relative `profile_file` that omits `profile_id`;
- a manifest containing a secret-shaped field is rejected before cache activation;
- a profile path that is a symlink or non-regular file is rejected;
- a second resolution reuses a byte-identical cache;
- an existing cache with changed bytes is reported as corrupt, never silently replaced;
- resolving a moved branch produces a new candidate commit while the old cache remains valid;
- an invalid or ambiguous ref fails without changing any existing cache;
- `verify_cached_profile(lock, paths)` works with the source repository unavailable;
- local repository sources are marked `portable = False`.

The public result type is:

```python
@dataclass(frozen=True)
class ProfileCandidate:
    profile_id: str
    source: str
    requested_ref: str
    resolved_commit: str
    content_sha256: str
    subdirectory: str
    profile_file: str
    cache_root: Path
    portable: bool
```

- [ ] **Step 3: Run the profile-source tests and confirm failure**

Run:

```sh
uv run --locked --no-sync pytest tests/test_profile_source.py -q
```

Expected: collection fails because `ai_dlc.profile_source` does not exist.

- [ ] **Step 4: Implement deterministic Git resolution**

Create `src/ai_dlc/profile_source.py` with these public call signatures:

- `resolve_profile_source(source: str, profile_id: str, requested_ref: str, paths: EnrollmentPaths, *, subdirectory: str = "", profile_file: str = "ai-dlc-profile.toml", allow_legacy_identity: bool = False) -> ProfileCandidate`;
- `verify_cached_profile(lock: EnrollmentLock, paths: EnrollmentPaths) -> Path`.

Implementation requirements:

1. Clone to a temporary directory under the AI-DLC cache parent with no checkout, fetch only the requested ref, resolve `FETCH_HEAD^{commit}`, then check out that exact detached commit.
2. Pass every subprocess argument separately and include bounded timeout/error handling. Never interpolate source/ref text into a shell command.
3. Resolve and validate only the selected relative profile file. Reject symlinks, non-regular files, and path escapes. Do not copy unrelated repository or subdirectory content.
4. Validate the profile by passing it through the personal-layer schema validator. Normal manifests require matching `profile_id`; legacy files may omit it but must match if present.
5. Calculate the digest from the profile's POSIX relative path, byte length, and contents. Do not include mtimes, ownership, absolute paths, unrelated files, or Git metadata.
6. Copy to a temporary sibling and rename it into `<profile-id>/<commit>` only after validation. If the destination exists, verify its digest and reuse it or fail as corrupt.
7. Clean up temporary clones on success and failure.
8. Treat existing local paths and `file://` Git sources as nonportable; HTTPS, SSH URL, and SCP-style Git remotes are portable metadata.

- [ ] **Step 5: Verify and commit Task 3**

Run:

```sh
uv run --locked --no-sync pytest tests/test_profile_source.py tests/test_config.py -q
uv run --locked --no-sync ruff check src/ai_dlc/profile_source.py tests/test_profile_source.py
uv run --locked --no-sync pyright --pythonpath .venv/bin/python
git diff --check
```

Expected: all commands pass.

Commit only the Task 3 files:

```sh
git add src/ai_dlc/profile_source.py tests/test_profile_source.py
git commit -m "feat: materialize pinned profile sources"
```

---

### Task 4: Resolve enrolled configuration automatically and preserve precedence

**Files:**

- Modify: `src/ai_dlc/config.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_enrollment.py`

- [ ] **Step 1: Write failing runtime-resolution tests**

Add tests for a new high-level resolver while preserving `resolve_files` as an explicit, side-effect-free primitive:

```python
def test_runtime_resolution_uses_enrolled_files_and_fixed_precedence(tmp_path):
    from ai_dlc.config import resolve_runtime

    # Build XDG roots, a valid lock/cache, personal/project/machine files,
    # then assert base → personal → project → machine values and provenance.
```

Cover these exact cases:

- packaged `profiles/base.toml` is the default base layer;
- a verified active cache supplies the personal layer;
- `<root>/ai-dlc.toml` supplies the project layer only when it exists;
- the lock's machine ID selects exactly one machine file;
- `personal=` replaces the enrolled personal path but still precedes project;
- `machine=` replaces the enrolled machine path but cannot weaken project checks;
- no active enrollment is valid and simply omits personal/machine layers;
- a present lock with a missing, changed, or malformed cache is an error rather than a silent fallback;
- two different homes/XDG roots cannot see each other's enrollment;
- returned provenance stays `base`, `personal`, `project`, or `machine`.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```sh
uv run --locked --no-sync pytest tests/test_config.py tests/test_enrollment.py -q
```

Expected: the new tests fail because `resolve_runtime` does not exist.

- [ ] **Step 3: Implement the high-level resolver**

Add this public call signature to `src/ai_dlc/config.py`: `resolve_runtime(root: Path | None = None, *, base: Path | None = None, personal: Path | None = None, machine: Path | None = None, home: Path | None = None, environ: Mapping[str, str] | None = None, enrollment_paths: EnrollmentPaths | None = None) -> Resolved`.

Use local imports for enrollment/profile-cache helpers if needed to avoid an import cycle. If either explicit scope is absent, consult the active lock; explicit files replace only their matching enrolled scope. Include the project file only when `root` is supplied and `root / "ai-dlc.toml"` exists. Keep `resolve_layers`, `resolve_files`, and `load_project` deterministic and enrollment-independent for unit tests and project-only operations.

- [ ] **Step 4: Verify and commit Task 4**

Run:

```sh
uv run --locked --no-sync pytest tests/test_config.py tests/test_enrollment.py tests/test_project.py -q
uv run --locked --no-sync ruff check src/ai_dlc/config.py tests/test_config.py tests/test_enrollment.py
uv run --locked --no-sync pyright --pythonpath .venv/bin/python
git diff --check
```

Expected: all commands pass.

Commit only the Task 4 files:

```sh
git add src/ai_dlc/config.py tests/test_config.py tests/test_enrollment.py
git commit -m "feat: resolve enrolled configuration"
```

---

### Task 5: Add preview-first enrollment, migration, and status services

**Files:**

- Create: `src/ai_dlc/machine.py`
- Create: `tests/test_machine.py`

- [ ] **Step 1: Write failing enrollment-service tests**

Create `tests/test_machine.py` using the disposable Git helper or move that helper to `tests/conftest.py` if both modules need it. Test `MachineManager.enroll`:

- preview resolves and caches a candidate but does not create a lock or machine file;
- the preview reports source, requested ref, exact commit, digest, portability, proposed lock, required bindings, missing credential variable names, selected modules, user-level MCP changes, and ownership conflicts;
- preview and error output never contain environment values;
- `apply=True` creates a schema-4 machine skeleton if absent and activates the lock last;
- enrollment performs no package-manager command and no client-config write;
- reenrolling the same candidate is idempotent;
- explicit enrollment may replace a different profile ID, and the preview clearly reports that change;
- a profile-ID mismatch fails before any active-state write.

Test `MachineManager.migrate`:

- it requires an explicit relative `profile_file`;
- it accepts a pinned schema-4 personal file with no `profile_id`;
- the compatibility lock records that exact file path;
- it has the same preview/apply behavior as enrollment;
- it never rewrites the source file.

- [ ] **Step 2: Write failing status tests**

Test status for:

- no enrollment: `enrolled = False`, no exception, and an actionable next step;
- healthy enrollment: identity, commit, source portability, machine file, cache health, credential readiness, and drift all reported without secret values;
- missing machine binding: reported as configuration drift;
- missing credential variable: reported by logical ID and variable name;
- corrupt cache: `cache = "corrupt"` and `ready = False` without fetching;
- source repository removed: healthy cached status remains available offline.

- [ ] **Step 3: Run the machine tests and confirm failure**

Run:

```sh
uv run --locked --no-sync pytest tests/test_machine.py -q
```

Expected: collection fails because `ai_dlc.machine` does not exist.

- [ ] **Step 4: Implement `MachineManager` enrollment and status**

Create `src/ai_dlc/machine.py` with dependency-injectable construction and these public call signatures:

- `MachineManager(*, home: Path | None = None, environ: Mapping[str, str] | None = None, paths: EnrollmentPaths | None = None)`;
- `enroll(source: str, profile_id: str, machine_id: str, *, requested_ref: str = "main", subdirectory: str = "", apply: bool = False) -> dict[str, object]`;
- `migrate(source: str, profile_file: str, profile_id: str, machine_id: str, *, requested_ref: str = "main", subdirectory: str = "", apply: bool = False) -> dict[str, object]`;
- `status(root: Path | None = None) -> dict[str, object]`.

Factor normal/legacy candidate handling into one private method. Generate previews from the candidate personal configuration plus the proposed/current machine binding. Use `credential_status` and `render_user_agents(candidate_config, apply=False)` for readiness and client changes. On enrollment apply, create or preserve the machine file first and write the validated lock last. Do not call `provision.machine_apply` here.

- [ ] **Step 5: Verify and commit Task 5**

Run:

```sh
uv run --locked --no-sync pytest tests/test_machine.py tests/test_profile_source.py tests/test_user_agents.py -q
uv run --locked --no-sync ruff check src/ai_dlc/machine.py tests/test_machine.py
uv run --locked --no-sync pyright --pythonpath .venv/bin/python
git diff --check
```

Expected: all commands pass.

Commit only the Task 5 files:

```sh
git add src/ai_dlc/machine.py tests/test_machine.py
git commit -m "feat: enroll portable machine profiles"
```

---

### Task 6: Reconcile, synchronize, and diagnose the enrolled machine

**Files:**

- Modify: `src/ai_dlc/provision.py`
- Modify: `src/ai_dlc/machine.py`
- Modify: `tests/test_provision.py`
- Modify: `tests/test_machine.py`

- [ ] **Step 1: Write failing provisioning-layer tests**

Update `tests/test_provision.py` to require:

- `machine_plan(profile, machine=machine_path)` merges personal then machine scope;
- machine credential bindings and path/account choices are visible to readiness logic but do not alter executable provider behavior;
- `machine_apply(profile, machine=machine_path)` renders the merged agent configuration;
- existing callers that provide only `profile` remain valid;
- no secret environment value enters the returned plan or generated files.

Change signatures compatibly to `machine_plan(profile: Path, headless: bool = False, system: str | None = None, architecture: str | None = None, home: Path | None = None, machine: Path | None = None) -> dict` and `machine_apply(profile: Path, headless: bool = False, home: Path | None = None, machine: Path | None = None) -> dict`.

- [ ] **Step 2: Run provisioning tests and confirm failure**

Run:

```sh
uv run --locked --no-sync pytest tests/test_provision.py -q
```

Expected: new calls fail because `machine` is not accepted or merged.

- [ ] **Step 3: Implement merged provisioning**

Change both provisioning functions to call `resolve_files(personal=profile, machine=machine)`. Preserve current platform checks, package-manager delegation, setup journal behavior, runtime activation, preview behavior, and user-agent ownership safeguards.

- [ ] **Step 4: Write failing manager plan/apply/sync/doctor tests**

Extend `tests/test_machine.py` for:

- `plan()` loads only the active verified cache and active machine binding, then delegates to `machine_plan` without writing;
- `apply()` delegates to `machine_apply` and returns lock identity plus the existing reconciliation result;
- `sync(apply=False)` fetches a moved requested ref and previews commit/config differences without changing lock bytes or client files;
- `sync(apply=True)` reconciles against the candidate and writes the new lock only after success;
- a failed candidate reconciliation leaves the prior lock bytes unchanged and labels any package-side effects as potentially partial;
- invalid candidate content, corrupt cache, and fetch failure leave the active lock unchanged;
- sync to the already-active commit is idempotent;
- `doctor(root)` combines machine status, project runtime checks, agent-client rendering, native sign-ins, credentials, and provider health;
- doctor never returns an environment value.

Patch `ai_dlc.provision.machine_plan`, `machine_apply`, and `doctor` in unit tests. Use real Git only for source/ref behavior.

- [ ] **Step 5: Run manager tests and confirm failure**

Run:

```sh
uv run --locked --no-sync pytest tests/test_machine.py -q
```

Expected: new tests fail because the lifecycle methods do not exist.

- [ ] **Step 6: Implement the remaining manager lifecycle**

Add these calls to `MachineManager`: `plan(*, headless: bool = False) -> dict[str, object]`, `apply(*, headless: bool = False) -> dict[str, object]`, `sync(*, apply: bool = False, headless: bool = False) -> dict[str, object]`, and `doctor(root: Path, *, target: str = "local") -> dict[str, object]`.

Implementation order for `sync(apply=True)` is mandatory:

1. read and retain the prior lock bytes;
2. fetch, materialize, and validate a candidate without changing the lock;
3. calculate the candidate diff and readiness report;
4. call `machine_apply(candidate_profile, machine=active_machine_file)`;
5. only after success, atomically write the candidate lock;
6. on failure, report the failed step, retain candidate cache for safe reuse, and assert the active lock bytes are unchanged.

Refactor `provision.doctor` to accept optional personal/home/environment inputs or add a compatible helper so both the root `doctor` command and `MachineManager.doctor` use the same checks. Credential readiness must come from `credentials.credential_status`, not duplicated environment logic.

- [ ] **Step 7: Verify and commit Task 6**

Run:

```sh
uv run --locked --no-sync pytest tests/test_provision.py tests/test_machine.py tests/test_user_agents.py tests/test_workstation.py -q
uv run --locked --no-sync ruff check src/ai_dlc/provision.py src/ai_dlc/machine.py tests/test_provision.py tests/test_machine.py
uv run --locked --no-sync pyright --pythonpath .venv/bin/python
git diff --check
```

Expected: all commands pass.

Commit only the Task 6 files:

```sh
git add src/ai_dlc/provision.py src/ai_dlc/machine.py tests/test_provision.py tests/test_machine.py
git commit -m "feat: reconcile and sync enrolled machines"
```

---

### Task 7: Expose the machine lifecycle and retain compatibility aliases

**Files:**

- Modify: `src/ai_dlc/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing help and command-routing tests**

Extend `tests/test_cli.py` to assert the root help includes `machine`, and machine help includes:

- `enroll`;
- `migrate`;
- `plan`;
- `apply`;
- `sync`;
- `status`;
- `doctor`.

Using monkeypatched `MachineManager` methods, assert routing and defaults for:

```text
ai-dlc machine enroll /tmp/profile-repo --profile-id test-development --machine-id test-mac
ai-dlc machine enroll /tmp/profile-repo --profile-id test-development --machine-id test-mac --ref stable --subdirectory config --apply
ai-dlc machine migrate /tmp/profile-repo --profile-file profiles/sean.toml --profile-id sean-development --machine-id personal-macbook
ai-dlc machine plan
ai-dlc machine apply
ai-dlc machine sync
ai-dlc machine sync --apply
ai-dlc machine status
ai-dlc machine doctor --root /tmp/project
```

Add compatibility tests proving:

- `setup plan --profile <path>` and `setup apply --profile <path>` still call the existing provision functions;
- `setup plan` and `setup apply` without `--profile` call the enrolled manager;
- `profile show` without explicit files uses `resolve_runtime`;
- an explicit `--machine` replaces enrolled machine scope for workflow and doctor calls;
- root `doctor` and `machine doctor` share readiness semantics.

- [ ] **Step 2: Run CLI tests and confirm failure**

Run:

```sh
uv run --locked --no-sync pytest tests/test_cli.py -q
```

Expected: help assertions and manager command calls fail because the group is absent.

- [ ] **Step 3: Implement thin Typer commands**

In `src/ai_dlc/cli.py`:

- create and register `machine = typer.Typer(no_args_is_help=True)`;
- make each command instantiate `MachineManager` and emit its JSON-safe result;
- keep `--apply` false by default for enroll, migrate, and sync;
- make `setup --profile` optional and route based on whether it was supplied;
- change `config_for` to use `resolve_runtime(root, machine=machine)`;
- change default `profile show` and root `doctor` to use enrolled resolution;
- preserve explicit paths and all existing JSON/nonzero-exit behavior.

Do not put Git, filesystem, credential, or provisioning logic in CLI functions.

- [ ] **Step 4: Verify and commit Task 7**

Run:

```sh
uv run --locked --no-sync pytest tests/test_cli.py tests/test_workflow.py tests/test_provision.py -q
uv run --locked --no-sync ruff check src/ai_dlc/cli.py tests/test_cli.py
uv run --locked --no-sync pyright --pythonpath .venv/bin/python
git diff --check
```

Expected: all commands pass.

Commit only the Task 7 files:

```sh
git add src/ai_dlc/cli.py tests/test_cli.py
git commit -m "feat: expose machine enrollment commands"
```

---

### Task 8: Prove two-machine portability, offline behavior, and secret containment

**Files:**

- Create: `tests/test_machine_integration.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_user_agents.py`

- [ ] **Step 1: Extract a shared local-Git fixture if needed**

Move only the disposable profile-repository setup needed by multiple test modules into `tests/conftest.py`. The fixture must return explicit paths/commits and must not rely on the user's Git config, home directory, network, or credential environment.

- [ ] **Step 2: Write the two-machine end-to-end test**

Create `tests/test_machine_integration.py` with one high-value flow:

1. Create one secret-free Git profile with a credential requirement and one MCP server using an environment variable reference.
2. Create `machine-a` and `machine-b` with entirely separate home/config/cache/state directories.
3. Enroll both against the same exact commit.
4. Write distinct machine bindings mapping the same logical credential to `LINEAR_A_TOKEN` and `LINEAR_B_TOKEN`.
5. Supply different fake sentinel environment values in memory.
6. Assert both machines resolve the same personal/profile digest and different machine provenance.
7. Preview reconciliation for both without writes.
8. Apply only agent rendering through a patched package/runtime boundary and assert generated Codex/Claude configuration contains environment variable names, never values.
9. Remove the source Git repository and prove status/plan still work from verified caches.
10. Scan every regular file in both temporary XDG/home trees and every returned JSON structure; neither sentinel value may appear.

- [ ] **Step 3: Add adversarial transaction and ownership integration cases**

Add tests for:

- moving `main`, previewing sync, then failing reconciliation: old lock remains active;
- retrying the same cached candidate successfully: new lock activates;
- tampering with one machine's cache: that machine fails integrity while the other remains healthy;
- a user-authored MCP ID collision: apply fails before lock change and authored bytes survive;
- source fetch failure: active offline status remains healthy and sync reports an actionable failure;
- legacy `profile_file` enrollment and sync for one compatibility window.

- [ ] **Step 4: Run integration tests and fix only evidenced defects**

Run:

```sh
uv run --locked --no-sync pytest tests/test_machine_integration.py tests/test_user_agents.py -q
```

Expected: tests initially expose any integration defects. For each failure, use `superpowers:systematic-debugging`, add or tighten the smallest regression assertion, then change the responsible implementation module. Do not weaken integrity, atomicity, ownership, or redaction assertions.

- [ ] **Step 5: Verify and commit Task 8**

Run:

```sh
uv run --locked --no-sync pytest tests/test_machine_integration.py tests/test_machine.py tests/test_user_agents.py -q
uv run --locked --no-sync ruff format --check src tests
uv run --locked --no-sync ruff check src tests
uv run --locked --no-sync pyright --pythonpath .venv/bin/python
git diff --check
```

Expected: all commands pass.

Commit the integration tests plus only implementation fixes directly required by those tests:

```sh
git add tests/conftest.py tests/test_machine_integration.py tests/test_user_agents.py src/ai_dlc/config.py src/ai_dlc/credentials.py src/ai_dlc/enrollment.py src/ai_dlc/profile_source.py src/ai_dlc/machine.py src/ai_dlc/provision.py src/ai_dlc/user_agents.py
git commit -m "test: prove portable enrollment end to end"
```

Before committing, inspect `git diff --cached --name-only` and unstage any unrelated source file.

---

### Task 9: Ship a nonpersonal profile example and update durable guidance

**Files:**

- Create: `profiles/example/ai-dlc-profile.toml`
- Modify: `profiles/machines/example.toml`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/development-workflow.md`
- Modify: `docs/workflows/tool-map.md`
- Modify: `docs/migration.md`
- Modify: `project-templates/project/AI-DLC.md`
- Modify: `project-templates/project/docs/development-workflow.md.jinja`
- Modify: `project-templates/project/docs/workflows/tool-map.md`
- Modify: `tests/test_templates.py`

- [ ] **Step 1: Write failing packaged-example and generated-handbook tests**

In `tests/test_templates.py`, assert:

- the wheel asset path contains `profiles/example/ai-dlc-profile.toml`;
- the example validates as a personal layer and contains no personal account, organization, vault, repository, or credential value;
- the machine example validates as a machine layer and demonstrates `LINEAR_SANDBOX_TOKEN` as a variable name only;
- generated handbook pages mention portable profile, machine enrollment, secret ownership, local/cloud boundary, and the design→implementation workflow;
- no template tells users to commit `.env` files or credential values.

- [ ] **Step 2: Run template tests and confirm failure**

Run:

```sh
uv run --locked --no-sync pytest tests/test_templates.py -q
```

Expected: tests fail because the profile example and new handbook language are absent.

- [ ] **Step 3: Add the public profile and machine examples**

Create `profiles/example/ai-dlc-profile.toml` with profile ID `example-development`, conservative `core` and `python` modules, provider-neutral roles, an empty agent server collection, and a demonstrative `linear-sandbox` credential requirement. Do not include Sean's profile, workspace IDs, team IDs, account names, paths, remotes, or secret values.

Extend `profiles/machines/example.toml` with a commented or inert credential binding using `source = "environment"` and `variable = "LINEAR_SANDBOX_TOKEN"`. Ensure the parsed file remains valid schema 4.

- [ ] **Step 4: Update product and generated handbook documentation**

Document:

- the five ownership layers and their Git/sync policy;
- creating a separate private profile repository with `ai-dlc-profile.toml`;
- enrolling the same pinned profile on a second machine;
- editing the machine binding independently on each machine;
- using `machine status`, `plan`, `apply`, `sync`, and `doctor`;
- storing Linear and future provider credentials in a password manager/keychain that injects the configured environment variable, never in AI-DLC Git files;
- local execution as today's primary control plane and hosted/cloud execution as a later qualification target;
- normal migration from `profiles/sean.toml`, including `machine migrate` and eventual reenrollment with the canonical filename;
- provider-neutral knowledge ownership, with Obsidian create/attach and provider discovery explicitly identified as the next cycle rather than falsely documented as complete;
- brownfield and greenfield design→implementation stages and which CLI/MCP/skill surface owns each stage.

Update both source handbook pages and their project-template copies so generated repositories do not drift from the product guidance.

- [ ] **Step 5: Verify and commit Task 9**

Run:

```sh
uv run --locked --no-sync pytest tests/test_templates.py tests/test_config.py -q
uv run --locked --no-sync python scripts/check_generated.py
uv run --locked --no-sync ruff check tests/test_templates.py
git diff --check
```

Expected: all commands pass.

Commit only the example, documentation, template, and test files:

```sh
git add profiles/example/ai-dlc-profile.toml profiles/machines/example.toml README.md docs/architecture.md docs/development-workflow.md docs/workflows/tool-map.md docs/migration.md project-templates/project/AI-DLC.md project-templates/project/docs/development-workflow.md.jinja project-templates/project/docs/workflows/tool-map.md tests/test_templates.py
git commit -m "docs: document portable machine enrollment"
```

---

### Task 10: Dogfood the lifecycle, run release-grade verification, and prepare review

**Files:**

- Modify: `docs/release-verification.md`
- Modify: `.ai-dlc/work/portable-profile-enrollment.toml`
- Move: `openspec/changes/portable-profile-enrollment/` → `openspec/changes/archive/2026-09-03-portable-profile-enrollment/`
- Create: `docs/reviews/2026-09-03-portable-profile-enrollment.md`

- [ ] **Step 1: Validate and optionally publish the dogfood work record**

Validate the reviewed work record created in Task 0. It is already bound to the active OpenSpec change, current `codex/portable-profile-enrollment` branch, and repository tracker/SCM providers. Do not add provider credentials or guessed Linear IDs.

Run the existing record/status commands locally. If the already-designated `sandbox-aidlc` team and native status IDs are configured in ignored machine-local configuration, publish/start/link this record using the normal AI-DLC work commands. If those non-secret IDs are still absent, leave the record locally valid and state that provider publication is the one operator action deferred to the provider-onboarding cycle; do not access another Linear workspace and do not guess IDs.

- [ ] **Step 2: Exercise the new lifecycle against a clean disposable profile repo**

Create a temporary Git repository outside the checkout containing the public example as `ai-dlc-profile.toml`. Use temporary XDG roots and execute the installed source checkout:

```sh
AI_DLC_TEST_HOME="$(mktemp -d)"
XDG_CONFIG_HOME="$AI_DLC_TEST_HOME/config" XDG_CACHE_HOME="$AI_DLC_TEST_HOME/cache" XDG_STATE_HOME="$AI_DLC_TEST_HOME/state" ai-dlc machine enroll "$AI_DLC_TEST_HOME/profile-repo" --profile-id example-development --machine-id verification-machine
XDG_CONFIG_HOME="$AI_DLC_TEST_HOME/config" XDG_CACHE_HOME="$AI_DLC_TEST_HOME/cache" XDG_STATE_HOME="$AI_DLC_TEST_HOME/state" ai-dlc machine enroll "$AI_DLC_TEST_HOME/profile-repo" --profile-id example-development --machine-id verification-machine --apply
XDG_CONFIG_HOME="$AI_DLC_TEST_HOME/config" XDG_CACHE_HOME="$AI_DLC_TEST_HOME/cache" XDG_STATE_HOME="$AI_DLC_TEST_HOME/state" ai-dlc machine status
XDG_CONFIG_HOME="$AI_DLC_TEST_HOME/config" XDG_CACHE_HOME="$AI_DLC_TEST_HOME/cache" XDG_STATE_HOME="$AI_DLC_TEST_HOME/state" ai-dlc machine plan
```

Use a task-specific variable exactly as shown; do not use or overwrite `HOME`. Remove the temporary directory only after capturing the non-secret results. Do not run `machine apply` against the real user home during this verification.

- [ ] **Step 3: Run focused security and packaging checks**

Run:

```sh
uv build
uv run --locked --no-sync pytest tests/test_credentials.py tests/test_enrollment.py tests/test_profile_source.py tests/test_machine.py tests/test_machine_integration.py -q
uv run --locked --no-sync python scripts/check_generated.py
```

Inspect the built wheel and assert the example profile is included while `.ai-dlc/local`, enrollment locks, machine files, environment files, Git metadata, and user-specific paths are absent.

- [ ] **Step 4: Run the repository's full required gate**

Run:

```sh
ai-dlc project check --required --receipt .ai-dlc/local/portable-profile-enrollment-receipt.json
```

Expected: `generated`, `format`, `lint`, `types`, and `test` all pass. The receipt remains ignored under `.ai-dlc/local/` and must not be staged.

If any check fails, invoke `superpowers:systematic-debugging`, reproduce the smallest failing command, add a regression test where appropriate, fix the root cause, and rerun the entire required gate.

- [ ] **Step 5: Finalize the formal specification, record evidence, and perform an independent code review**

Mark every completed item in `openspec/changes/portable-profile-enrollment/tasks.md`, validate the active change strictly, then move the complete directory to `openspec/changes/archive/2026-09-03-portable-profile-enrollment/`. Update the work record's `artifacts.spec` value to that exact archive path and validate the archive strictly.

Update `docs/release-verification.md` with dated, factual evidence from the disposable enrollment and the full required gate. Do not claim clean-machine hosted/cloud qualification, provider onboarding, Obsidian attach/create, full Linear discovery, behavioral skill evaluation, or published release assets.

Use `superpowers:requesting-code-review` to review the complete branch against the approved design and this plan. Save the resulting findings and resolutions in `docs/reviews/2026-09-03-portable-profile-enrollment.md`. Address every correctness, security, compatibility, or test-gap finding before continuing.

- [ ] **Step 6: Verify no secret or unrelated file is staged**

Run:

```sh
git status --short
git diff --cached --name-only
git grep -n "fake-value-that-must-not-escape" -- . ':!docs/superpowers/plans/2026-09-03-portable-profile-enrollment.md' ':!tests/test_credentials.py' ':!tests/test_machine_integration.py'
git diff --check
```

Expected:

- `.ai-dlc/local/linear.env` and `.ai-dlc/local/.linear.env.swp` are not staged or displayed;
- `.DS_Store`, `.ai-dlc/.DS_Store`, and `target/.rustc_info.json` remain unrelated and unstaged;
- no sentinel credential value appears outside the redaction test sources and this plan;
- only the Task 10 work record, archived specification, verification doc, review report, and any review-driven source/test fixes are staged.

- [ ] **Step 7: Commit verification evidence**

Run:

```sh
git add .ai-dlc/work/portable-profile-enrollment.toml openspec/changes/portable-profile-enrollment openspec/changes/archive/2026-09-03-portable-profile-enrollment docs/release-verification.md docs/reviews/2026-09-03-portable-profile-enrollment.md
git commit -m "test: verify portable profile enrollment"
```

If review-driven code changed after the previous commit, include only those reviewed source/test files after rerunning the full required gate.

- [ ] **Step 8: Finish the branch using the integration workflow**

Invoke `superpowers:verification-before-completion`, rerun its required evidence checks, then invoke `superpowers:finishing-a-development-branch`. The expected integration path is:

1. push `codex/portable-profile-enrollment`;
2. create a pull request describing motivation, functional changes, schema/template migration, before/after CLI surface, and remaining provider-onboarding/cloud/release work;
3. wait for required CI;
4. merge only when checks pass and review findings are resolved;
5. update the main checkout with a fast-forward pull;
6. verify the merged revision locally with `ai-dlc project check --required`;
7. use `work finish` only if the sandbox work record was successfully published and its exact merged-revision CI evidence is available.

Do not mark Linear work complete before the PR is merged and merged-revision CI receipts pass.
