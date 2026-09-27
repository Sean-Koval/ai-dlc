"""Exact-merge finish orchestration with real Git and fake remote transports."""

from __future__ import annotations

import shutil
import subprocess
import threading
import tomllib
from contextlib import contextmanager
from pathlib import Path

import pytest
import tomli_w

from ai_dlc.config import resolve_runtime
from ai_dlc.providers import Registry
from ai_dlc.work.workflow import WorkService, resolve_work


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    if check and result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class RemoteSCM:
    def __init__(
        self,
        merge: str,
        *,
        merge_error: str | None = None,
        ci_error: str | None = None,
    ):
        self.merge = merge
        self.merge_error = merge_error
        self.ci_error = ci_error
        self.merged_calls = 0
        self.ci_calls = 0
        self.deployment_calls = 0

    def merged(self, reference: str) -> dict:
        self.merged_calls += 1
        if self.merge_error:
            raise ValueError(self.merge_error)
        assert reference in {"7", "8"}
        return {
            "sha": self.merge,
            "pr": {
                "merged": True,
                "base": {"ref": "main", "repo": {"full_name": "owner/repo"}},
            },
        }

    def ci(self, sha: str) -> dict:
        self.ci_calls += 1
        if self.ci_error:
            raise RuntimeError(self.ci_error)
        return {"sha": sha, "run_id": 17, "receipt": {"fixture": True}}

    def deployment(self, sha: str) -> dict:
        self.deployment_calls += 1
        raise AssertionError("current target policy must not replace historical policy")


class RemoteTracker:
    def __init__(self, *, lose_first_transition: bool = False):
        self.state = "open"
        self.transition_calls = 0
        self.lose_first_transition = lose_first_transition

    def invoke(self, operation: str, payload: dict) -> dict:
        if operation == "read":
            return {"id": "ISSUE-1", "state": self.state, "url": "https://issues/1"}
        if operation == "transition":
            self.transition_calls += 1
            self.state = payload["state"]
            if self.lose_first_transition and self.transition_calls == 1:
                raise TimeoutError("response lost after remote close")
            return {"id": "ISSUE-1", "state": self.state, "url": "https://issues/1"}
        raise AssertionError(operation)


class ProcessRemoteSCM:
    def __init__(self, merge: str, shared, guard):
        self.merge = merge
        self.shared = shared
        self.guard = guard

    def _increment(self, key: str) -> None:
        with self.guard:
            self.shared[key] = self.shared[key] + 1

    def merged(self, reference: str) -> dict:
        self._increment("merged_calls")
        return {
            "sha": self.merge,
            "pr": {
                "merged": True,
                "base": {"ref": "main", "repo": {"full_name": "owner/repo"}},
            },
        }

    def ci(self, sha: str) -> dict:
        self._increment("ci_calls")
        return {"sha": sha, "run_id": 21, "receipt": {"fixture": True}}


class ProcessRemoteTracker:
    def __init__(self, shared, guard, read_barrier, *, strict_barrier: bool):
        self.shared = shared
        self.guard = guard
        self.read_barrier = read_barrier
        self.strict_barrier = strict_barrier

    def invoke(self, operation: str, payload: dict) -> dict:
        if operation == "read":
            with self.guard:
                state = self.shared["state"]
            if state == "open":
                try:
                    if self.strict_barrier:
                        self.read_barrier.wait()
                    else:
                        self.read_barrier.wait(timeout=3)
                except threading.BrokenBarrierError:
                    pass
            return {"id": "ISSUE-1", "state": state, "url": "https://issues/1"}
        if operation == "transition":
            with self.guard:
                self.shared["transition_calls"] = self.shared["transition_calls"] + 1
                self.shared["state"] = payload["state"]
                state = self.shared["state"]
            return {"id": "ISSUE-1", "state": state, "url": "https://issues/1"}
        raise AssertionError(operation)


def finish_process(
    root: str,
    state: str,
    merge: str,
    shared,
    guard,
    start_barrier,
    common_acquired,
    read_barrier,
    output,
    break_common_lock: bool,
    leader: bool,
):
    """Spawn-safe helper using real WorkService locks and shared fake remote state."""
    from ai_dlc.work import workflow

    root_path = Path(root)
    scm = ProcessRemoteSCM(merge, shared, guard)
    tracker = ProcessRemoteTracker(shared, guard, read_barrier, strict_barrier=break_common_lock)
    caller_registry = Registry()
    caller_registry.register("fixture-scm", scm)
    caller_registry.register("fixture-tracker", tracker)
    service = WorkService.from_project(root_path, state_path=Path(state), registry=caller_registry)
    historical_roots: list[str] = []

    def merge_service(historical_root: Path) -> WorkService:
        historical_roots.append(str(historical_root))
        historical = WorkService.from_project(
            historical_root,
            machine=service._selected_machine(),
            state_path=service._journal_path.parent,
        )
        fresh = Registry(historical.config, root=historical_root)
        fresh.register("fixture-scm", scm)
        fresh.register("fixture-tracker", tracker)
        historical.registry = fresh
        return historical

    service.__dict__["_merge_service"] = merge_service
    common = workflow.repository_common_dir(root_path)
    real_lock = workflow.project_write_lock

    @contextmanager
    def coordinated_lock(lock_root: Path):
        target = root_path if break_common_lock and Path(lock_root) == common else lock_root
        with real_lock(target):
            if leader and Path(lock_root) == common:
                common_acquired.set()
            yield

    workflow.project_write_lock = coordinated_lock
    try:
        start_barrier.wait()
        if not leader and not common_acquired.wait(timeout=10):
            raise TimeoutError("leader did not acquire the common-directory lock")
        result = service.finish_at_merge("one")
        output.put({"status": result["status"], "root": historical_roots[0]})
    except BaseException as error:  # noqa: BLE001 -- child must report failures to the parent
        import traceback

        output.put(
            {
                "error": repr(error),
                "notes": list(getattr(error, "__notes__", ())),
                "roots": historical_roots,
                "traceback": traceback.format_exc(),
            }
        )


def project_source(
    *,
    deployed: bool = False,
    tracker: str = "fixture-tracker",
    tracker_identity: str | None = None,
) -> str:
    gates = '["pr-merged", "ci-green", "deployed"]' if deployed else '["pr-merged", "ci-green"]'
    tracker_setting = f'identity = "{tracker_identity}"\n' if tracker_identity is not None else ""
    return (
        "schema = 4\n"
        '[project]\nname = "fixture"\n'
        f'[roles]\nscm = "fixture-scm"\ntracker = "{tracker}"\n'
        'specs = "openspec"\ndeploy = "none"\nknowledge = "obsidian"\n'
        '[providers.fixture-scm]\nkind = "github"\n'
        f'[providers.{tracker}]\nkind = "github-issues"\n'
        f'{tracker_setting}[scm]\nrepository = "owner/repo"\ntarget_branch = "main"\n'
        "[gates]\nfinish = " + gates + "\n"
    )


def authored_record(config: dict, *, pr: str = "7", requires_spec: bool = False) -> dict:
    raw = {
        "schema": 1,
        "id": "one",
        "title": "One",
        "scope": "Finish at its merge",
        "requires_spec": requires_spec,
        "spec_reason": (
            "Specification required"
            if requires_spec
            else "No specification required for this fixture"
        ),
        "acceptance": ["Completion is exact"],
        "reviewed": True,
        "providers": {
            "scm": "fixture-scm",
            "tracker": "fixture-tracker",
            "specs": "openspec",
            "deploy": "none",
            "knowledge": "obsidian",
        },
        "artifacts": {"pr": pr, "tracker": "ISSUE-1"},
    }
    return resolve_work(raw, config, "one", require_review=True)


def legacy_record(*, providers: dict | str | None = None) -> dict:
    raw = {
        "schema": 1,
        "id": "one",
        "title": "One",
        "scope": "Finish at its merge",
        "requires_spec": False,
        "spec_reason": "No specification required for this fixture",
        "acceptance": ["Completion is exact"],
        "reviewed": True,
        "artifacts": {"pr": "7", "tracker": "ISSUE-1"},
    }
    if providers is not None:
        raw["providers"] = providers
    return raw


def commit_legacy_identity_drift(tmp_path: Path, *, drift: str) -> tuple[Path, str]:
    root = tmp_path / "legacy identity project"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "AI-DLC Test")
    git(root, "config", "user.email", "ai-dlc@example.test")
    explicit = {
        "scm": "fixture-scm",
        "tracker": "fixture-tracker",
        "specs": "openspec",
        "deploy": "none",
        "knowledge": "obsidian",
    }
    historical_source = project_source(
        tracker_identity="historical" if drift == "binding" else None
    )
    (root / "ai-dlc.toml").write_text(historical_source)
    work_dir = root / ".ai-dlc/work"
    work_dir.mkdir(parents=True)
    record = legacy_record(providers=explicit if drift == "binding" else None)
    (work_dir / "one.toml").write_text(tomli_w.dumps(record))
    git(root, "add", ".")
    git(root, "commit", "-m", "merged legacy delivery")
    merge = git(root, "rev-parse", "HEAD")
    if drift == "provider":
        current_source = project_source(tracker="other-tracker")
    elif drift == "binding":
        current_source = project_source(tracker_identity="current")
    else:
        current_source = historical_source
    (root / "ai-dlc.toml").write_text(current_source)
    (root / "advanced.txt").write_text("target advanced\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "advance target policy")
    return root, merge


def commit_project(
    tmp_path: Path,
    *,
    commented_record: bool = False,
    crlf_record: bool = False,
    historical_deployed: bool = False,
    merge_has_config: bool = True,
    requires_spec: bool = False,
) -> tuple[Path, str]:
    root = tmp_path / "caller project ü"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "AI-DLC Test")
    git(root, "config", "user.email", "ai-dlc@example.test")
    git(root, "config", "core.autocrlf", "false")
    if merge_has_config:
        (root / "ai-dlc.toml").write_text(project_source(deployed=historical_deployed))
        config = resolve_runtime(root).values
    else:
        config = resolve_runtime().values
    work_dir = root / ".ai-dlc/work"
    work_dir.mkdir(parents=True)
    record = authored_record(config, requires_spec=requires_spec)
    prefix = "# historical formatting\n" if commented_record else ""
    record_bytes = (prefix + tomli_w.dumps(record)).encode("utf-8")
    if crlf_record:
        record_bytes = record_bytes.replace(b"\n", b"\r\n")
    (work_dir / "one.toml").write_bytes(record_bytes)
    git(root, "add", ".")
    git(root, "commit", "-m", "merged delivery")
    merge = git(root, "rev-parse", "HEAD")
    (root / "ai-dlc.toml").write_text(project_source(deployed=True))
    (root / "advanced.txt").write_text("target advanced\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "advance target")
    return root, merge


def commit_absolute_policy_symlink(tmp_path: Path) -> tuple[Path, Path, str]:
    external = tmp_path / "external current policy.toml"
    external.write_text(project_source(deployed=True))
    root = tmp_path / "symlink policy project"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "AI-DLC Test")
    git(root, "config", "user.email", "ai-dlc@example.test")
    try:
        (root / "ai-dlc.toml").symlink_to(external)
    except OSError as error:
        pytest.skip(f"file symlinks are unavailable on this host: {error}")
    if not (root / "ai-dlc.toml").is_symlink():
        pytest.skip("file symlinks are unavailable on this host")
    config = resolve_runtime(root).values
    work_dir = root / ".ai-dlc/work"
    work_dir.mkdir(parents=True)
    (work_dir / "one.toml").write_text(tomli_w.dumps(authored_record(config)))
    git(root, "add", ".")
    git(root, "commit", "-m", "merged delivery with external policy link")
    merge = git(root, "rev-parse", "HEAD")
    (root / "advanced.txt").write_text("target advanced\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "advance target")
    external.write_text(project_source(deployed=False))
    return root, external, merge


def configured_service(
    root: Path,
    merge: str,
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    scm: RemoteSCM | None = None,
    tracker: RemoteTracker | None = None,
    machine: Path | None = None,
) -> tuple[WorkService, RemoteSCM, RemoteTracker, list[Path]]:
    scm = scm or RemoteSCM(merge)
    tracker = tracker or RemoteTracker()
    caller_registry = Registry()
    caller_registry.register("fixture-scm", scm)
    caller_registry.register("fixture-tracker", tracker)
    service = WorkService.from_project(
        root, machine=machine, state_path=state, registry=caller_registry
    )
    historical_roots: list[Path] = []

    def merge_service(historical_root: Path) -> WorkService:
        historical_roots.append(historical_root)
        historical = WorkService.from_project(
            historical_root,
            machine=service._selected_machine(),
            state_path=service._journal_path.parent,
        )
        remote_registry = Registry(historical.config, root=historical_root)
        remote_registry.register("fixture-scm", scm)
        remote_registry.register("fixture-tracker", tracker)
        historical.registry = remote_registry
        return historical

    monkeypatch.setattr(service, "_merge_service", merge_service)
    return service, scm, tracker, historical_roots


def configured_legacy_service(
    root: Path,
    merge: str,
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    scm = RemoteSCM(merge)
    current_tracker = RemoteTracker()
    historical_tracker = RemoteTracker()
    current_tracker_id = resolve_runtime(root).values["roles"]["tracker"]
    caller_registry = Registry()
    caller_registry.register("fixture-scm", scm)
    caller_registry.register(current_tracker_id, current_tracker)
    service = WorkService.from_project(root, state_path=state, registry=caller_registry)
    historical_roots: list[Path] = []

    def merge_service(historical_root: Path) -> WorkService:
        historical_roots.append(historical_root)
        historical = WorkService.from_project(
            historical_root,
            machine=service._selected_machine(),
            state_path=service._journal_path.parent,
        )
        fresh = Registry(historical.config, root=historical_root)
        fresh.register("fixture-scm", scm)
        fresh.register("fixture-tracker", historical_tracker)
        historical.registry = fresh
        return historical

    monkeypatch.setattr(service, "_merge_service", merge_service)
    return service, scm, current_tracker, historical_tracker, historical_roots


def caller_snapshot(root: Path) -> dict:
    return {
        "head": git(root, "rev-parse", "HEAD"),
        "index": git(root, "diff", "--cached", "--binary"),
        "worktree": git(root, "status", "--porcelain=v1", "--untracked-files=all"),
        "record": (root / ".ai-dlc/work/one.toml").read_bytes(),
    }


def test_finish_at_merge_uses_historical_policy_and_preserves_dirty_caller(tmp_path, monkeypatch):
    """Fails if orchestration uses target HEAD/policy or mutates caller files/index/HEAD."""
    root, merge = commit_project(tmp_path)
    record = root / ".ai-dlc/work/one.toml"
    record.write_text("# caller formatting stays byte-for-byte\n" + record.read_text())
    (root / "untracked caller.txt").write_text("keep me\n")
    state = tmp_path / "state location"
    service, scm, tracker, historical_roots = configured_service(root, merge, state, monkeypatch)
    before = caller_snapshot(root)

    result = service.finish_at_merge("one")

    assert result["status"] == "completed"
    assert result["cleanup"] == {
        "status": "removed",
        "locator": None,
        "reason": None,
        "remedy": None,
    }
    assert result["evidence"]["pr-merged"]["sha"] == merge
    assert result["evidence"]["ci-green"]["sha"] == merge
    assert scm.merged_calls == 2  # read-only preflight plus fresh ordinary-finish gate
    assert scm.ci_calls == 1
    assert scm.deployment_calls == 0
    assert tracker.transition_calls == 1
    assert caller_snapshot(root) == before
    assert len(historical_roots) == 1
    assert not historical_roots[0].exists()
    assert service._journal_path == (state / "operations.sqlite3").absolute()


def test_finish_at_merge_refuses_raw_historical_identity_conflict_before_completion(
    tmp_path, monkeypatch
):
    """Fails if historical PR/provider identity is silently rewritten or ignored."""
    root, merge = commit_project(tmp_path)
    record = root / ".ai-dlc/work/one.toml"
    record.write_text(record.read_text().replace('pr = "7"', 'pr = "8"'))
    service, _, tracker, _ = configured_service(root, merge, tmp_path / "state", monkeypatch)
    before = record.read_bytes()

    with pytest.raises(ValueError, match="historical.*identity") as failure:
        service.finish_at_merge("one")

    assert failure.value.__dict__["cleanup"]["status"] == "removed"
    assert tracker.transition_calls == 0
    assert record.read_bytes() == before


@pytest.mark.parametrize("drift", ["provider", "binding"])
def test_finish_at_merge_refuses_resolved_legacy_identity_drift_before_completion(
    tmp_path, monkeypatch, drift
):
    """Fails if matching raw legacy records can resolve to different completion identities."""
    from ai_dlc.errors import RefusedError

    root, merge = commit_legacy_identity_drift(tmp_path, drift=drift)
    state = tmp_path / "legacy state"
    service, scm, current_tracker, historical_tracker, historical_roots = configured_legacy_service(
        root, merge, state, monkeypatch
    )

    with pytest.raises(RefusedError, match="historical.*identity") as failure:
        service.finish_at_merge("one")

    assert failure.value.__dict__["cleanup"]["status"] == "removed"
    assert scm.merged_calls == 1
    assert current_tracker.transition_calls == 0
    assert historical_tracker.transition_calls == 0
    assert not (state / "operations.sqlite3").exists()
    assert len(historical_roots) == 1
    assert not historical_roots[0].exists()


def test_finish_at_merge_accepts_unchanged_inferred_legacy_identity(tmp_path, monkeypatch):
    """Fails if comparing effective identities rejects equal default-shaped records."""
    root, merge = commit_legacy_identity_drift(tmp_path, drift="none")
    service, _, current_tracker, historical_tracker, _ = configured_legacy_service(
        root, merge, tmp_path / "legacy state", monkeypatch
    )

    result = service.finish_at_merge("one")

    assert result["status"] == "completed"
    assert current_tracker.transition_calls == 0
    assert historical_tracker.transition_calls == 1
    assert result["cleanup"]["status"] == "recovery-required"
    assert Path(result["cleanup"]["locator"]).exists()


def test_finish_at_merge_refuses_malformed_provider_shape_before_remote_lookup(
    tmp_path, monkeypatch
):
    """Fails if invalid reviewed TOML escapes as AttributeError or reaches external state."""
    from ai_dlc.errors import RefusedError

    root, merge = commit_project(tmp_path)
    record = root / ".ai-dlc/work/one.toml"
    record.write_text(tomli_w.dumps(legacy_record(providers="broken")))
    state = tmp_path / "malformed state"
    service, scm, tracker, historical_roots = configured_service(root, merge, state, monkeypatch)

    with pytest.raises(RefusedError, match=r"Work record.*one\.toml.*correct"):
        service.finish_at_merge("one")

    assert scm.merged_calls == 0
    assert tracker.transition_calls == 0
    assert historical_roots == []
    assert not (state / "operations.sqlite3").exists()


def test_finish_at_merge_refuses_current_binding_drift_before_remote_lookup(tmp_path, monkeypatch):
    """Fails if current reviewed bindings are not independently validated in read-only preflight."""
    root, merge = commit_project(tmp_path)
    config_path = root / "ai-dlc.toml"
    config_path.write_text(config_path.read_text().replace("owner/repo", "owner/other"))
    scm = RemoteSCM(merge)
    service, _, tracker, roots = configured_service(
        root, merge, tmp_path / "state", monkeypatch, scm=scm
    )

    with pytest.raises(ValueError, match="binding drift"):
        service.finish_at_merge("one")

    assert scm.merged_calls == 0
    assert tracker.transition_calls == 0
    assert roots == []


def test_finish_at_merge_keeps_blocked_outcome_separate_from_cleanup(tmp_path, monkeypatch):
    """Fails if a gate block becomes a cleanup failure or skips safe removal."""
    root, merge = commit_project(tmp_path)
    scm = RemoteSCM(merge, ci_error="receipt unavailable")
    service, _, tracker, roots = configured_service(
        root, merge, tmp_path / "state", monkeypatch, scm=scm
    )

    result = service.finish_at_merge("one")

    assert result["status"] == "blocked"
    assert result["blocked"] == [{"gate": "ci-green", "reason": "receipt unavailable"}]
    assert result["cleanup"]["status"] == "removed"
    assert tracker.transition_calls == 0
    assert not roots[0].exists()


@pytest.mark.parametrize("gate", ["specification-current", "deployed"])
def test_finish_at_merge_retains_historical_spec_and_deployment_blocks(tmp_path, monkeypatch, gate):
    """Fails if isolated preparation bypasses configured ordinary finish gates."""
    root, merge = commit_project(
        tmp_path,
        historical_deployed=gate == "deployed",
        requires_spec=gate == "specification-current",
    )
    service, _, tracker, _ = configured_service(root, merge, tmp_path / "state", monkeypatch)

    result = service.finish_at_merge("one")

    assert result["status"] == "blocked"
    assert gate in {item["gate"] for item in result["blocked"]}
    assert result["cleanup"]["status"] == "removed"
    assert tracker.transition_calls == 0


@pytest.mark.parametrize(
    "merge, error",
    [
        ("f" * 40, None),
        ("unused", "PR must be merged into configured repository and target branch"),
    ],
)
def test_finish_at_merge_preflight_refusals_never_mutate_tracker(
    tmp_path, monkeypatch, merge, error
):
    """Fails if missing objects or untrusted PR identity create resources or mutate remote state."""
    root, actual_merge = commit_project(tmp_path)
    scm = RemoteSCM(merge, merge_error=error)
    tracker = RemoteTracker()
    service, _, _, roots = configured_service(
        root,
        actual_merge,
        tmp_path / "state",
        monkeypatch,
        scm=scm,
        tracker=tracker,
    )

    with pytest.raises(ValueError, match="merged|commit|revision|object|PR"):
        service.finish_at_merge("one")

    assert tracker.transition_calls == 0
    assert roots == []


def test_finish_at_merge_reconciles_lost_transition_with_same_journal(tmp_path, monkeypatch):
    """Fails if retry changes correlation, trusts a local success, or repeats transition."""
    root, merge = commit_project(tmp_path)
    tracker = RemoteTracker(lose_first_transition=True)
    service, scm, _, _ = configured_service(
        root, merge, tmp_path / "state", monkeypatch, tracker=tracker
    )

    with pytest.raises(TimeoutError, match="response lost") as failure:
        service.finish_at_merge("one")
    assert failure.value.__dict__["cleanup"]["status"] == "removed"

    result = service.finish_at_merge("one")

    assert result["status"] == "completed"
    assert result["cleanup"]["status"] == "removed"
    assert tracker.transition_calls == 1
    assert scm.ci_calls == 2  # fresh evidence is mandatory on the retry


def test_finish_at_merge_cleans_up_when_historical_lock_entry_is_interrupted(tmp_path, monkeypatch):
    """Fails if lock __enter__ sits outside the cleanup-covered orchestration scope."""
    from ai_dlc.work import workflow

    root, merge = commit_project(tmp_path)
    service, _, tracker, historical_roots = configured_service(
        root, merge, tmp_path / "state", monkeypatch
    )
    common = workflow.repository_common_dir(root)
    real_lock = workflow.project_write_lock
    historical_entries = 0

    @contextmanager
    def interrupted_lock(lock_root: Path):
        nonlocal historical_entries
        if Path(lock_root) not in {common, root}:
            historical_entries += 1
            # from_project and WorkService.__init__ take the first two reentrant entries.
            if historical_entries == 3:
                raise KeyboardInterrupt("interrupted while acquiring historical lock")
        with real_lock(lock_root):
            yield

    monkeypatch.setattr(workflow, "project_write_lock", interrupted_lock)

    with pytest.raises(KeyboardInterrupt, match="historical lock") as failure:
        service.finish_at_merge("one")

    assert failure.value.__dict__["cleanup"]["status"] == "removed"
    assert len(historical_roots) == 1
    assert not historical_roots[0].exists()
    assert tracker.transition_calls == 0


def test_finish_at_merge_releases_historical_lock_before_cleanup(tmp_path, monkeypatch):
    """Fails if Windows directory sharing can block non-forced Git worktree removal."""
    from ai_dlc.work import workflow

    root, merge = commit_project(tmp_path)
    service, _, _, _ = configured_service(root, merge, tmp_path / "state", monkeypatch)
    common = workflow.repository_common_dir(root)
    real_lock = workflow.project_write_lock
    real_allocate = workflow.allocate_checkout
    historical_lock_depth = 0
    cleanup_observations: list[int] = []

    @contextmanager
    def observed_lock(lock_root: Path):
        nonlocal historical_lock_depth
        historical = Path(lock_root) not in {common, root}
        with real_lock(lock_root):
            if historical:
                historical_lock_depth += 1
            try:
                yield
            finally:
                if historical:
                    historical_lock_depth -= 1

    def observed_checkout(**kwargs):
        owned = real_allocate(**kwargs)

        class Observed:
            root = owned.root
            revision = owned.revision
            marker = owned.marker

            def create(self):
                return owned.create()

            def cleanup(self):
                cleanup_observations.append(historical_lock_depth)
                return owned.cleanup()

        return Observed()

    monkeypatch.setattr(workflow, "project_write_lock", observed_lock)
    monkeypatch.setattr(workflow, "allocate_checkout", observed_checkout)

    result = service.finish_at_merge("one")

    assert result["status"] == "completed"
    assert cleanup_observations == [0]


def run_linked_processes(tmp_path: Path, *, break_common_lock: bool):
    import multiprocessing

    root, merge = commit_project(tmp_path)
    caller_one = tmp_path / "linked caller one"
    caller_two = tmp_path / "linked caller two"
    git(root, "worktree", "add", "--detach", str(caller_one), "HEAD")
    git(root, "worktree", "add", "--detach", str(caller_two), "HEAD")
    context = multiprocessing.get_context("spawn")
    with context.Manager() as manager:
        shared = manager.dict(state="open", transition_calls=0, merged_calls=0, ci_calls=0)
        guard = manager.RLock()
        start_barrier = manager.Barrier(2)
        common_acquired = manager.Event()
        read_barrier = manager.Barrier(2)
        output = manager.Queue()
        processes = [
            context.Process(
                target=finish_process,
                args=(
                    str(caller),
                    str(tmp_path / f"process state {index}"),
                    merge,
                    shared,
                    guard,
                    start_barrier,
                    common_acquired,
                    read_barrier,
                    output,
                    break_common_lock,
                    index == 1,
                ),
            )
            for index, caller in enumerate((caller_one, caller_two), start=1)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=30)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                pytest.fail("concurrent finish helper did not complete")
            assert process.exitcode == 0
        results = [output.get(timeout=5) for _ in processes]
        observed = dict(shared)
    return results, observed


def test_linked_worktree_helpers_share_process_lock_with_distinct_state_paths(tmp_path):
    """Fails if helpers lock caller roots instead of the linked repository common directory."""
    results, observed = run_linked_processes(tmp_path, break_common_lock=False)

    errors = [result["traceback"] for result in results if "traceback" in result]
    assert not errors, "\n".join(errors)
    assert all(result.get("status") == "completed" for result in results), results
    assert len({result["root"] for result in results}) == 2
    assert observed == {
        "state": "closed",
        "transition_calls": 1,
        "merged_calls": 4,
        "ci_calls": 2,
    }
    assert (tmp_path / "process state 1/operations.sqlite3").is_file()
    assert (tmp_path / "process state 2/operations.sqlite3").is_file()


def test_process_fixture_exposes_a_caller_root_only_lock_regression(tmp_path):
    """Proves the controlled remote barrier detects the pending-transition race."""
    results, observed = run_linked_processes(tmp_path, break_common_lock=True)

    assert all(result.get("status") == "completed" for result in results), results
    assert observed["transition_calls"] == 2


def test_finish_at_merge_retains_normalized_historical_checkout(tmp_path, monkeypatch):
    """Fails if orchestration hides ordinary finish normalization or force-cleans evidence."""
    root, merge = commit_project(tmp_path, commented_record=True)
    service, _, tracker, _ = configured_service(root, merge, tmp_path / "state", monkeypatch)

    result = service.finish_at_merge("one")

    assert result["status"] == "completed"
    assert result["cleanup"]["status"] == "recovery-required"
    assert Path(result["cleanup"]["locator"]).exists()
    assert tracker.transition_calls == 1


def test_finish_at_merge_retains_crlf_normalized_historical_checkout(tmp_path, monkeypatch):
    """Fails if ordinary LF normalization is hidden or its dirty checkout is force-cleaned."""
    root, merge = commit_project(tmp_path, crlf_record=True)
    committed = subprocess.run(
        ["git", "show", f"{merge}:.ai-dlc/work/one.toml"],
        cwd=root,
        capture_output=True,
        check=True,
        text=False,
        timeout=10,
    ).stdout
    assert b"\r\n" in committed
    service, _, tracker, _ = configured_service(root, merge, tmp_path / "state", monkeypatch)

    result = service.finish_at_merge("one")

    assert result["status"] == "completed"
    assert result["cleanup"]["status"] == "recovery-required"
    marker = Path(result["cleanup"]["locator"])
    retained_record = marker.parent / "checkout/.ai-dlc/work/one.toml"
    assert marker.exists()
    assert retained_record.exists()
    assert b"\r\n" not in retained_record.read_bytes()
    dirty = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--", retained_record.name],
        cwd=retained_record.parent,
        capture_output=True,
        check=True,
        text=False,
        timeout=10,
    ).stdout
    assert dirty == b" M .ai-dlc/work/one.toml\0"
    assert tracker.transition_calls == 1


@pytest.mark.parametrize("blocked", [False, True])
def test_finish_at_merge_keeps_finish_outcome_when_cleanup_refuses(tmp_path, monkeypatch, blocked):
    """Fails if retained-resource recovery overwrites completed or blocked finish truth."""
    from ai_dlc.work import workflow

    root, merge = commit_project(tmp_path)
    scm = RemoteSCM(merge, ci_error="CI blocked" if blocked else None)
    service, _, tracker, _ = configured_service(
        root, merge, tmp_path / "state", monkeypatch, scm=scm
    )
    real_allocate = workflow.allocate_checkout

    def retain_checkout(**kwargs):
        owned = real_allocate(**kwargs)

        class Retained:
            root = owned.root
            revision = owned.revision
            marker = owned.marker

            def create(self):
                return owned.create()

            def cleanup(self):
                return workflow.CleanupResult(
                    status="recovery-required",
                    locator=str(owned.marker),
                    reason="fixture removal refusal",
                    remedy="inspect retained fixture",
                )

        return Retained()

    monkeypatch.setattr(workflow, "allocate_checkout", retain_checkout)

    result = service.finish_at_merge("one")

    assert result["status"] == ("blocked" if blocked else "completed")
    assert result["cleanup"]["status"] == "recovery-required"
    assert result["cleanup"]["reason"] == "fixture removal refusal"
    assert tracker.transition_calls == (0 if blocked else 1)


def test_finish_at_merge_rechecks_relative_machine_configuration_before_mutation(
    tmp_path, monkeypatch
):
    """Fails if relative provenance is rooted at the project or drift after preparation is missed."""
    root, merge = commit_project(tmp_path)
    caller_cwd = tmp_path / "caller cwd"
    caller_cwd.mkdir()
    machine = caller_cwd / "config/machine.toml"
    machine.parent.mkdir()
    machine.write_text('schema = 4\n[paths]\nvault = "/first"\n')
    monkeypatch.chdir(caller_cwd)
    service, _, tracker, _ = configured_service(
        root,
        merge,
        Path("relative state"),
        monkeypatch,
        machine=Path("config/machine.toml"),
    )
    original_factory = service._merge_service

    def drift_after_preparation(historical_root: Path) -> WorkService:
        historical = original_factory(historical_root)
        machine.write_text('schema = 4\n[paths]\nvault = "/changed"\n')
        return historical

    monkeypatch.setattr(service, "_merge_service", drift_after_preparation)

    with pytest.raises(ValueError, match="configuration changed") as failure:
        service.finish_at_merge("one")

    assert service._machine == machine.absolute()
    assert service._journal_path == (caller_cwd / "relative state/operations.sqlite3")
    assert failure.value.__dict__["cleanup"]["status"] == "removed"
    assert tracker.transition_calls == 0


def test_finish_at_merge_refuses_nonreproducible_direct_configuration(tmp_path):
    """Fails if injected runtime values are treated as reproducible layer provenance."""
    root, _ = commit_project(tmp_path)
    injected = resolve_runtime(root).values
    injected["runtime-only"] = {"injected": True}
    service = WorkService(root, injected, state_path=tmp_path / "state", registry=Registry())

    with pytest.raises(ValueError, match="from_project"):
        service.finish_at_merge("one")


def test_reviewed_source_reads_utf8_without_platform_default_or_write(tmp_path, monkeypatch):
    """Fails if finish preflight decodes a valid work record with the host text default."""
    root, _ = commit_project(tmp_path)
    record_path = root / ".ai-dlc/work/one.toml"
    record = tomllib.loads(record_path.read_text(encoding="utf-8"))
    record["title"] = "One Ё"
    record_path.write_text(tomli_w.dumps(record), encoding="utf-8", newline="\n")
    before = record_path.read_bytes()
    service = WorkService.from_project(root, state_path=tmp_path / "state", registry=Registry())
    original = Path.read_text

    def legacy_default(path, encoding=None, errors=None):
        return original(path, encoding=encoding or "cp1252", errors=errors)

    monkeypatch.setattr(Path, "read_text", legacy_default)

    assert service.load("one")["title"] == "One Ё"
    raw, reviewed = service._reviewed_source("one")
    assert raw["title"] == reviewed["title"] == "One Ё"
    assert record_path.read_bytes() == before


def test_merge_service_uses_fresh_registry_at_historical_root(tmp_path, monkeypatch):
    """Fails if root-sensitive providers or caller adapter caches leak into historical evidence."""
    from ai_dlc.work import workflow

    root, merge = commit_project(tmp_path)
    caller_registry = Registry()
    caller_registry.register("fixture-scm", RemoteSCM(merge))
    service = WorkService.from_project(
        root, state_path=tmp_path / "state", registry=caller_registry
    )
    historical_root = tmp_path / "historical"
    historical_root.mkdir()
    shutil.copy2(root / "ai-dlc.toml", historical_root / "ai-dlc.toml")
    shutil.copytree(root / ".ai-dlc", historical_root / ".ai-dlc")
    created: list[Path] = []
    real_registry = workflow.Registry

    class RecordingRegistry(real_registry):
        def __init__(self, config=None, *, root=None, environ=None):
            if root is None:
                raise AssertionError("historical registry must receive its checkout root")
            created.append(Path(root))
            super().__init__(config, root=root, environ=environ)

    monkeypatch.setattr(workflow, "Registry", RecordingRegistry)

    historical = service._merge_service(historical_root)

    assert created == [historical_root]
    assert historical.registry is not caller_registry
    assert historical.registry.root == historical_root
    assert historical._journal_path == service._journal_path


def test_finish_at_merge_requires_historical_project_policy(tmp_path, monkeypatch):
    """Fails if a missing historical ai-dlc.toml falls back to current/default policy."""
    root, merge = commit_project(tmp_path, merge_has_config=False)
    # The current record was authored against defaults before current project policy appeared;
    # align only its raw identity with the current reviewed record for preflight.
    config = resolve_runtime(root).values
    record = authored_record(config)
    (root / ".ai-dlc/work/one.toml").write_text(tomli_w.dumps(record))
    service, _, tracker, _ = configured_service(root, merge, tmp_path / "state", monkeypatch)
    monkeypatch.setattr(service, "_merge_service", WorkService._merge_service.__get__(service))

    with pytest.raises(ValueError, match="historical.*ai-dlc.toml") as failure:
        service.finish_at_merge("one")

    assert failure.value.__dict__["cleanup"]["status"] == "removed"
    assert tracker.transition_calls == 0


def test_finish_at_merge_refuses_historical_policy_symlink_before_gate_bypass(
    tmp_path, monkeypatch
):
    """Fails if a committed absolute symlink can substitute external current policy."""
    from ai_dlc.errors import RefusedError
    from ai_dlc.work import workflow

    root, external, merge = commit_absolute_policy_symlink(tmp_path)
    external_before = external.read_bytes()
    scm = RemoteSCM(merge)
    tracker = RemoteTracker()
    caller_registry = Registry()
    caller_registry.register("fixture-scm", scm)
    caller_registry.register("fixture-tracker", tracker)
    state = tmp_path / "symlink state"
    service = WorkService.from_project(root, state_path=state, registry=caller_registry)
    real_registry = workflow.Registry

    class HistoricalRegistry(real_registry):
        def __init__(self, config=None, *, root=None, environ=None):
            super().__init__(config, root=root, environ=environ)
            self.register("fixture-scm", scm)
            self.register("fixture-tracker", tracker)

    monkeypatch.setattr(workflow, "Registry", HistoricalRegistry)

    with pytest.raises(RefusedError, match="historical.*ai-dlc.toml.*regular") as failure:
        service.finish_at_merge("one")

    assert failure.value.__dict__["cleanup"]["status"] == "removed"
    assert scm.merged_calls == 1
    assert scm.ci_calls == 0
    assert scm.deployment_calls == 0
    assert tracker.transition_calls == 0
    assert external.read_bytes() == external_before
    assert not (state / "operations.sqlite3").exists()


def test_finish_at_merge_preserves_handoff_pending_status(tmp_path, monkeypatch):
    """Fails if helper rewrites the existing completion/handoff result envelope."""
    root, merge = commit_project(tmp_path)
    service, _, _, _ = configured_service(root, merge, tmp_path / "state", monkeypatch)

    result = service.finish_at_merge("one", handoff="Continue from the merge")

    assert result["status"] == "completed,handoff_pending"
    assert "handoff_error" in result
    assert result["cleanup"]["status"] == "removed"
