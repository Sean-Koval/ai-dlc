import copy

import pytest


@pytest.fixture
def trusted_scm(monkeypatch):
    from ai_dlc.work import workflow

    class SCM:
        def __init__(self, root, config):
            pass

        def merged(self, reference):
            return {"sha": "trusted-merge", "pr": {"merged": True}}

        def ci(self, sha):
            return {"sha": sha, "run_id": 7, "receipt": {"trusted_fixture": True}}

    monkeypatch.setattr(workflow, "GitHubSCM", SCM)


def test_receipt_binds_manifests_and_required_checks():
    from ai_dlc.providers.scm import digest, validate_receipt

    config = {"checks": {"required": ["test"], "commands": {"test": "pytest"}}, "setup": {}}
    receipt = {
        "schema": 1,
        "commit": "abc",
        "checks_digest": digest(config["checks"]),
        "environment_digest": digest({"mise": {}, "setup": {}}),
        "engine_version": "0.4.0",
        "target": "github-actions",
        "required": ["test"],
        "outcomes": [{"id": "test", "status": "passed", "exit_code": 0, "duration_seconds": 1.0}],
        "dirty": False,
    }
    assert validate_receipt(receipt, "abc", config, {})
    for key, value in [
        ("commit", "wrong"),
        ("checks_digest", "bad"),
        ("required", []),
        ("dirty", True),
        ("outcomes", []),
    ]:
        broken = copy.deepcopy(receipt)
        broken[key] = value
        with pytest.raises(ValueError):
            validate_receipt(broken, "abc", config, {})


class Tracker:
    def __init__(self):
        self.created = 0
        self.closed = 0
        self.items = []
        self.fail = False

    def invoke(self, op, data):
        if op == "find":
            return {"items": self.items}
        if op == "create":
            self.created += 1
            self.items = [{"id": "1", "url": "https://issues/1", "state": "open"}]
            if self.fail:
                raise TimeoutError("uncertain")
            return self.items[0]
        if op == "read":
            return self.items[0]
        if op == "transition":
            self.closed += 1
            self.items[0]["state"] = "closed"
            return self.items[0]
        return self.items[0]


def test_uncertain_close_reconciles_without_repeating_remote_mutation(tmp_path, trusted_scm):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)

    class LostResponse(Tracker):
        def invoke(self, op, data):
            result = super().invoke(op, data)
            if op == "transition" and self.closed == 1:
                raise TimeoutError("response lost after remote close")
            return result

    tracker = LostResponse()
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Registry(tracker))
    service.publish("one")
    with pytest.raises(TimeoutError):
        service.finish("one")
    assert service.finish("one")["status"] == "completed"
    assert tracker.closed == 1


class Registry:
    def __init__(self, p):
        self.p = p

    def get(self, id):
        return self.p


def work(tmp_path):
    folder = tmp_path / ".ai-dlc/work"
    folder.mkdir(parents=True)
    (folder / "one.toml").write_text(
        'schema=1\nid="one"\ntitle="One"\nscope="small"\nrequires_spec=false\nspec_reason="No behavior change"\nacceptance=["Tests pass"]\nreviewed=true\n[providers]\ntracker="fake"\n'
    )


def account_lock_cache(tmp_path, monkeypatch):
    """Point account-derived lock storage at an isolated private test home."""
    from types import SimpleNamespace

    from ai_dlc import locking

    account_home = tmp_path / "account-home"
    account_home.mkdir(mode=0o700)
    monkeypatch.setattr(
        locking,
        "pwd",
        SimpleNamespace(
            getpwuid=lambda uid: SimpleNamespace(pw_dir=str(account_home)),
        ),
        raising=False,
    )
    return account_home / ".cache"


def test_project_write_lock_rejects_untrusted_namespace_entries(tmp_path, monkeypatch):
    """A hostile anchor or leaf must not redirect writers onto attacker-controlled inodes."""
    import hashlib

    from ai_dlc.locking import project_write_lock

    project = tmp_path / "project"
    project.mkdir()
    cache = account_lock_cache(tmp_path, monkeypatch)
    cache.mkdir(mode=0o700)
    controlled = tmp_path / "controlled"
    controlled.mkdir()
    (cache / "ai-dlc").symlink_to(controlled, target_is_directory=True)

    with pytest.raises(ValueError, match="lock namespace"), project_write_lock(project):
        pass

    (cache / "ai-dlc").unlink()
    lock_root = cache / "ai-dlc/locks"
    lock_root.mkdir(parents=True, mode=0o700)
    target = tmp_path / "attacker.lock"
    target.write_text("")
    leaf = lock_root / f"{hashlib.sha256(str(project.resolve()).encode()).hexdigest()}.lock"
    leaf.symlink_to(target)

    with pytest.raises(ValueError, match="lock namespace"), project_write_lock(project):
        pass


def test_project_write_lock_rejects_unsafe_anchor_mode(tmp_path, monkeypatch):
    """An anchor writable by other users cannot define a serialization namespace."""
    from ai_dlc.locking import project_write_lock

    cache = account_lock_cache(tmp_path, monkeypatch)
    cache.mkdir(mode=0o777)
    cache.chmod(0o777)

    with (
        pytest.raises(ValueError, match="lock namespace"),
        project_write_lock(tmp_path / "project"),
    ):
        pass


def test_project_write_lock_rejects_unsafe_account_home_with_existing_cache(tmp_path, monkeypatch):
    """A private cache cannot make its writable account-home authority trustworthy."""
    from ai_dlc.locking import project_write_lock

    cache = account_lock_cache(tmp_path, monkeypatch)
    cache.mkdir(mode=0o700)
    account_home = cache.parent
    project = tmp_path / "project"
    project.mkdir()

    with project_write_lock(project):
        pass

    try:
        account_home.chmod(0o777)
        with pytest.raises(ValueError, match="lock namespace"), project_write_lock(project):
            pass
    finally:
        account_home.chmod(0o700)


def test_project_write_lock_uses_a_private_stable_namespace(tmp_path, monkeypatch):
    """A valid existing private anchor supports nesting and a private regular lock leaf."""
    import stat

    from ai_dlc.locking import project_write_lock

    cache = account_lock_cache(tmp_path, monkeypatch)
    lock_root = cache / "ai-dlc/locks"
    lock_root.mkdir(parents=True, mode=0o700)
    cache.chmod(0o700)
    (cache / "ai-dlc").chmod(0o700)
    lock_root.chmod(0o700)
    project = tmp_path / "project"
    project.mkdir()

    with project_write_lock(project), project_write_lock(project):
        leaves = list(lock_root.glob("*.lock"))
        assert len(leaves) == 1
        metadata = leaves[0].stat()
        assert stat.S_ISREG(metadata.st_mode)
        assert stat.S_IMODE(metadata.st_mode) == 0o600


def test_project_write_lock_rejects_leaf_replacement_while_acquiring(tmp_path, monkeypatch):
    """Replacing the directory entry cannot let acquisition bless a different lock inode."""
    import hashlib

    from ai_dlc import locking

    cache = account_lock_cache(tmp_path, monkeypatch)
    lock_root = cache / "ai-dlc/locks"
    lock_root.mkdir(parents=True, mode=0o700)
    for directory in (cache, cache / "ai-dlc", lock_root):
        directory.chmod(0o700)
    project = tmp_path / "project"
    project.mkdir()
    leaf = lock_root / f"{hashlib.sha256(str(project.resolve()).encode()).hexdigest()}.lock"
    leaf.touch(mode=0o600)
    real_flock = locking.fcntl.flock
    replaced = []

    def replace_after_lock(descriptor, operation):
        real_flock(descriptor, operation)
        if operation == locking.fcntl.LOCK_EX and not replaced:
            leaf.rename(leaf.with_suffix(".held"))
            leaf.touch(mode=0o600)
            replaced.append(True)

    monkeypatch.setattr(locking.fcntl, "flock", replace_after_lock)

    with pytest.raises(ValueError, match="lock namespace"), locking.project_write_lock(project):
        pass


def test_project_write_lock_serializes_an_independent_process(tmp_path, monkeypatch):
    """A second process must retain the same project lock identity until release."""
    import os
    import subprocess
    import sys

    from ai_dlc import locking

    cache = account_lock_cache(tmp_path, monkeypatch)
    cache.mkdir(mode=0o700)
    project = tmp_path / "project"
    project.mkdir()
    script = (
        "import sys, types\n"
        "from pathlib import Path\n"
        "from ai_dlc import locking\n"
        "locking.pwd = types.SimpleNamespace(\n"
        "    getpwuid=lambda uid: types.SimpleNamespace(pw_dir=sys.argv[2])\n"
        ")\n"
        "print('ready', flush=True)\n"
        "with locking.project_write_lock(Path(sys.argv[1])):\n"
        "    print('acquired', flush=True)\n"
    )

    with locking.project_write_lock(project):
        child = subprocess.Popen(
            [sys.executable, "-c", script, str(project), str(cache.parent)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ),
        )
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "ready"
        with pytest.raises(subprocess.TimeoutExpired):
            child.wait(timeout=0.2)

    stdout, stderr = child.communicate(timeout=5)
    assert child.returncode == 0, stderr
    assert stdout.strip() == "acquired"


def test_project_write_lock_identity_ignores_process_environment(tmp_path, monkeypatch):
    """One account and project must serialize even when launch environments differ."""
    import os
    import subprocess
    import sys

    from ai_dlc import locking

    account_home = account_lock_cache(tmp_path, monkeypatch).parent
    parent_cache = tmp_path / "parent-cache"
    child_cache = tmp_path / "child-cache"
    child_runtime = tmp_path / "child-runtime"
    parent_home = tmp_path / "parent-home"
    child_home = tmp_path / "child-home"
    parent_tmp = tmp_path / "parent-tmp"
    child_tmp = tmp_path / "child-tmp"
    for directory in (
        parent_cache,
        child_cache,
        child_runtime,
        parent_home,
        child_home,
        parent_tmp,
        child_tmp,
    ):
        directory.mkdir(mode=0o700)
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(parent_cache))
    monkeypatch.setenv("HOME", str(parent_home))
    monkeypatch.setenv("TMPDIR", str(parent_tmp))
    project = tmp_path / "project"
    project.mkdir()
    script = (
        "import sys, types\n"
        "from pathlib import Path\n"
        "from ai_dlc import locking\n"
        "locking.pwd = types.SimpleNamespace(\n"
        "    getpwuid=lambda uid: types.SimpleNamespace(pw_dir=sys.argv[2])\n"
        ")\n"
        "print('ready', flush=True)\n"
        "with locking.project_write_lock(Path(sys.argv[1])):\n"
        "    print('acquired', flush=True)\n"
    )
    child_environment = dict(os.environ)
    child_environment.update(
        {
            "XDG_RUNTIME_DIR": str(child_runtime),
            "XDG_CACHE_HOME": str(child_cache),
            "HOME": str(child_home),
            "TMPDIR": str(child_tmp),
        }
    )

    with locking.project_write_lock(project):
        child = subprocess.Popen(
            [sys.executable, "-c", script, str(project), str(account_home)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=child_environment,
        )
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "ready"
        with pytest.raises(subprocess.TimeoutExpired):
            child.wait(timeout=0.2)

    stdout, stderr = child.communicate(timeout=5)
    assert child.returncode == 0, stderr
    assert stdout.strip() == "acquired"
    lock_root = account_home / ".cache/ai-dlc/locks"
    assert len(list(lock_root.glob("*.lock"))) == 1
    assert not list(parent_cache.rglob("*.lock"))
    assert not list(child_cache.rglob("*.lock"))
    assert not list(child_runtime.rglob("*.lock"))


def test_work_service_from_project_preserves_machine_overlay(tmp_path):
    """Coherent project resolution must retain explicitly selected machine settings."""
    import tomllib

    from ai_dlc.work.workflow import WorkService

    (tmp_path / "ai-dlc.toml").write_text(
        'schema = 4\n[roles]\ntracker = "linear"\n'
        '[providers.linear]\nteam_id = "team-a"\n'
        '[providers.linear.statuses]\nin_progress = "doing-a"\nclosed = "done-a"\n'
    )
    directory = tmp_path / ".ai-dlc/work"
    directory.mkdir(parents=True)
    (directory / "one.toml").write_text(
        'schema=1\nid="one"\ntitle="One"\nscope="small"\nrequires_spec=false\n'
        'spec_reason="Regression"\nacceptance=["Bound"]\nreviewed=true\n'
        '[providers]\ntracker="linear"\n'
    )
    machine = tmp_path / "machine.toml"
    machine.write_text('schema = 4\n[providers.linear]\ntoken_env = "LINEAR_MACHINE_TOKEN"\n')

    service = WorkService.from_project(
        tmp_path,
        machine=machine,
        state_path=tmp_path / "state",
    )
    service.load("one", mutation=True)

    binding = tomllib.loads((directory / "one.toml").read_text())["bindings"]["tracker"]
    assert (
        binding
        == WorkService.from_project(
            tmp_path,
            machine=machine,
            state_path=tmp_path / "fresh-state",
        ).load("one")["bindings"]["tracker"]
    )


def test_publish_reconciles_uncertain_creation(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    tracker = Tracker()
    tracker.fail = True
    service = WorkService(
        tmp_path,
        {"scm": {"repository": "a/b"}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    with pytest.raises(TimeoutError):
        service.publish("one")
    assert service.publish("one")["tracker"]["id"] == "1"
    assert tracker.created == 1


def test_unknown_gate_never_closes(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    tracker = Tracker()
    service = WorkService(
        tmp_path,
        {"gates": {"finish": ["unknown"]}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    service.publish("one")
    assert service.finish("one")["status"] == "blocked"
    assert tracker.closed == 0


def test_handoff_pending_retry_does_not_repeat_close(tmp_path, trusted_scm):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    tracker = Tracker()
    service = WorkService(
        tmp_path,
        {"gates": {"finish": []}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    service.publish("one")
    assert service.finish("one", handoff="Done")["status"] == "completed,handoff_pending"
    assert service.finish("one", handoff="Done")["status"] == "completed,handoff_pending"
    assert tracker.closed == 1


def test_handoff_can_recover_after_vault_configuration(tmp_path, monkeypatch, trusted_scm):
    import sys
    import types

    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    tracker = Tracker()
    service = WorkService(
        tmp_path,
        {"gates": {"finish": []}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    service.publish("one")
    service.finish("one", handoff="Done")

    class Knowledge:
        def __init__(self, vault):
            pass

        def append(self, path, body, operation_id):
            return {"path": path}

    monkeypatch.setitem(
        sys.modules, "ai_dlc.documentation.knowledge", types.SimpleNamespace(Knowledge=Knowledge)
    )
    service.config["paths"] = {"vault": str(tmp_path / "vault")}
    assert service.finish("one", handoff="Done")["status"] == "completed"
    assert tracker.closed == 1


def test_reopened_remote_cannot_be_completed_from_local_record(tmp_path, trusted_scm):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    tracker = Tracker()
    service = WorkService(
        tmp_path,
        {"gates": {"finish": []}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    service.publish("one")
    service.finish("one")
    tracker.items[0]["state"] = "open"
    assert service.finish("one")["status"] == "blocked"


def test_github_scm_rejects_wrong_workflow_and_sha(tmp_path):
    from ai_dlc.providers.scm import GitHubSCM

    scm = GitHubSCM(tmp_path, {"scm": {"repository": "a/b"}})
    scm.api = lambda path: {
        "workflow_runs": [
            {
                "id": 1,
                "head_sha": "wrong",
                "head_branch": "main",
                "event": "push",
                "conclusion": "success",
                "status": "completed",
                "path": ".github/workflows/verify.yml",
                "repository": {"full_name": "a/b"},
            }
        ]
    }
    with pytest.raises(ValueError, match="trusted"):
        scm.ci("correct")


def matrix_receipt_scm(tmp_path, *, tamper_second=False, missing_second=False):
    import base64
    import json
    from pathlib import Path

    import tomli_w

    from ai_dlc.providers.scm import GitHubSCM, digest

    names = ["ai-dlc-receipt-linux", "ai-dlc-receipt-macos"]
    config = {
        "scm": {
            "repository": "a/b",
            "workflow": "verify.yml",
            "target_branch": "main",
            "receipt_artifacts": names,
        },
        "checks": {"required": ["test"], "commands": {"test": "pytest"}},
    }
    receipt = {
        "schema": 1,
        "commit": "merge-sha",
        "checks_digest": digest(config["checks"]),
        "environment_digest": digest({"mise": {}, "setup": {}}),
        "engine_version": "0.4.0",
        "target": "github-actions",
        "required": ["test"],
        "outcomes": [{"id": "test", "status": "passed", "exit_code": 0, "duration_seconds": 1.0}],
        "dirty": False,
    }
    scm = GitHubSCM(tmp_path, config)

    def api(path):
        if "/actions/workflows/" in path:
            return {
                "workflow_runs": [
                    {
                        "id": 7,
                        "head_sha": "merge-sha",
                        "head_branch": "main",
                        "event": "push",
                        "status": "completed",
                        "conclusion": "success",
                        "repository": {"full_name": "a/b"},
                        "path": ".github/workflows/verify.yml",
                    }
                ]
            }
        if path.endswith("/actions/runs/7/artifacts?per_page=100"):
            available = names[:1] if missing_second else names
            return {
                "total_count": len(available),
                "artifacts": [
                    {"id": index, "name": name, "expired": False}
                    for index, name in enumerate(available, 1)
                ],
            }
        if "/contents/" in path:
            value = config if "/ai-dlc.toml?" in path else {}
            return {"content": base64.b64encode(tomli_w.dumps(value).encode()).decode()}
        raise AssertionError(f"unexpected API path: {path}")

    def run(*args):
        assert args[:3] == ("run", "download", "7")
        name = args[args.index("--name") + 1]
        assert name in names
        destination = Path(args[args.index("--dir") + 1])
        destination.mkdir(parents=True)
        value = copy.deepcopy(receipt)
        if tamper_second and name == names[1]:
            value["commit"] = "wrong"
        (destination / "receipt.json").write_text(json.dumps(value))
        return ""

    scm.api = api
    scm.run = run
    return scm


def test_github_scm_downloads_each_matrix_receipt(tmp_path):
    result = matrix_receipt_scm(tmp_path).ci("merge-sha")

    assert result["receipt_count"] == 2
    assert len(result["receipts"]) == 2


def test_github_scm_rejects_tampered_receipt_in_matrix(tmp_path):
    with pytest.raises(ValueError, match="commit mismatch"):
        matrix_receipt_scm(tmp_path, tamper_second=True).ci("merge-sha")


def test_github_scm_rejects_missing_receipt_in_matrix(tmp_path):
    with pytest.raises(ValueError, match="Missing expected"):
        matrix_receipt_scm(tmp_path, missing_second=True).ci("merge-sha")


def test_unreviewed_work_cannot_publish(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    path = tmp_path / ".ai-dlc/work/one.toml"
    path.write_text(path.read_text().replace("reviewed=true", "reviewed=false"))
    tracker = Tracker()
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Registry(tracker))
    with pytest.raises(ValueError, match="reviewed"):
        service.publish("one")
    assert tracker.created == 0


def test_receipt_matches_root_check_manifest():
    from ai_dlc.providers.scm import digest, validate_receipt

    config = {"checks": {"required": ["test"], "commands": {"test": "pytest"}}}
    receipt = {
        "schema": 1,
        "commit": "abc",
        "checks_digest": digest(config["checks"]),
        "environment_digest": digest({"mise": {}, "setup": {}}),
        "engine_version": "0.4.0",
        "target": "github-actions",
        "required": ["test"],
        "outcomes": [{"id": "test", "status": "passed", "exit_code": 0, "duration_seconds": 1.0}],
        "dirty": False,
    }
    assert validate_receipt(receipt, "abc", config, {})
    config["checks"]["required"] = []
    receipt["required"] = []
    receipt["checks_digest"] = digest(config["checks"])
    with pytest.raises(ValueError, match="required"):
        validate_receipt(receipt, "abc", config, {})


def test_publish_pending_crash_does_not_create_again(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    tracker = Tracker()
    service = WorkService(
        tmp_path,
        {"scm": {"repository": "a/b"}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    loaded = service.load("one")
    operation_id = service.op_id(loaded, "publish")
    payload = {
        "provider": "fake",
        "title": loaded["title"],
        "body": "\n".join(loaded["acceptance"]),
        "correlation": f"<!-- ai-dlc:{service.op_id(loaded, 'work')} -->",
        "operation_id": operation_id,
    }
    service.journal.begin(operation_id, payload)
    with pytest.raises(RuntimeError, match="uncertain"):
        service.publish("one")
    assert tracker.created == 0


def test_openspec_uses_installed_cli_capabilities(tmp_path, monkeypatch):
    import subprocess

    from ai_dlc.providers.openspec import OpenSpecProvider

    archive = tmp_path / "openspec/changes/archive/2026-01-01-one"
    archive.mkdir(parents=True)
    (archive / "tasks.md").write_text("- [x] Done\n")
    (archive / "proposal.md").write_text("# One\n")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            1 if "--archived" in command else 0,
            stdout="--all --strict --no-interactive",
            stderr="unsupported archived",
        )

    monkeypatch.setattr(subprocess, "run", run)
    assert OpenSpecProvider(tmp_path).current(
        {"id": "one", "artifacts": {"spec": str(archive.relative_to(tmp_path))}}
    )["current"]
    assert ["openspec", "validate", "--help"] in calls


@pytest.mark.parametrize(
    "fault",
    [None, "pr_repo", "pr_branch", "run_sha", "run_workflow", "receipt_digest", "missing_check"],
)
def test_finish_trusts_only_matching_authenticated_run(tmp_path, monkeypatch, fault):
    import base64
    import json
    import subprocess
    from pathlib import Path

    import tomli_w

    from ai_dlc.providers.scm import digest
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    tracker = Tracker()
    config = {
        "scm": {"repository": "a/b", "workflow": "verify.yml", "target_branch": "main"},
        "checks": {"required": ["test"], "commands": {"test": "pytest"}},
    }
    receipt = {
        "schema": 1,
        "commit": "merge-sha",
        "checks_digest": digest(config["checks"]),
        "environment_digest": digest({"mise": {}, "setup": {}}),
        "engine_version": "0.4.0",
        "target": "github-actions",
        "required": ["test"],
        "outcomes": [{"id": "test", "status": "passed", "exit_code": 0, "duration_seconds": 1.0}],
        "dirty": False,
    }
    if fault == "receipt_digest":
        receipt["checks_digest"] = "bad"
    if fault == "missing_check":
        receipt["outcomes"] = []
    downloads = []

    def run(command, **kwargs):
        assert command[0] == "gh"
        if command[1] == "api":
            endpoint = command[2]
            if "/pulls/" in endpoint:
                value = {
                    "merged": True,
                    "merge_commit_sha": "merge-sha",
                    "base": {
                        "ref": "wrong" if fault == "pr_branch" else "main",
                        "repo": {"full_name": "evil/repo" if fault == "pr_repo" else "a/b"},
                    },
                }
            elif "/runs?" in endpoint:
                value = {
                    "workflow_runs": [
                        {
                            "id": 7,
                            "head_sha": "wrong" if fault == "run_sha" else "merge-sha",
                            "head_branch": "main",
                            "event": "push",
                            "status": "completed",
                            "conclusion": "success",
                            "repository": {"full_name": "a/b"},
                            "path": ".github/workflows/evil.yml"
                            if fault == "run_workflow"
                            else ".github/workflows/verify.yml",
                        }
                    ]
                }
            elif endpoint.endswith("/actions/runs/7/artifacts?per_page=100"):
                value = {
                    "total_count": 1,
                    "artifacts": [{"id": 1, "name": "ai-dlc-receipt", "expired": False}],
                }
            else:
                assert "?ref=merge-sha" in endpoint
                value = {
                    "content": base64.b64encode(
                        tomli_w.dumps(config if "/ai-dlc.toml?" in endpoint else {}).encode()
                    ).decode()
                }
            return subprocess.CompletedProcess(command, 0, json.dumps(value), "")
        assert command[1:4] == ["run", "download", "7"]
        assert command[command.index("--repo") + 1] == "a/b"
        downloads.append(command)
        destination = Path(command[command.index("--dir") + 1])
        destination.mkdir(parents=True)
        (destination / "receipt.json").write_text(json.dumps(receipt))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)
    service = WorkService(
        tmp_path, config, state_path=tmp_path / "state", registry=Registry(tracker)
    )
    service.publish("one")
    service.link("one", "pr", "https://github.com/a/b/pull/12", commit=False)
    result = service.finish("one")
    assert result["status"] == ("completed" if fault is None else "blocked")
    assert tracker.closed == (1 if fault is None else 0)
    if fault is None:
        assert len(downloads) == 1


def test_work_uses_pinned_specification_provider(tmp_path, trusted_scm):
    from ai_dlc.providers import Registry as ProviderRegistry
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    path = tmp_path / ".ai-dlc/work/one.toml"
    path.write_text(
        path.read_text()
        .replace("requires_spec=false", "requires_spec=true")
        .replace('tracker="fake"', 'tracker="fake"\nspecification="custom-spec"')
    )
    tracker = Tracker()
    called = []

    class Specification:
        def current(self, work, revision=None):
            called.append(work["id"])
            return {"current": True, "archive": "custom", "revision": revision}

    registry = ProviderRegistry()
    registry.register("fake", tracker)
    registry.register("custom-spec", Specification())
    service = WorkService(
        tmp_path,
        {"gates": {"finish": ["specification-current"]}},
        state_path=tmp_path / "state",
        registry=registry,
    )
    service.publish("one")
    assert service.finish("one")["status"] == "completed"
    assert called == ["one"]


def test_false_specification_evidence_cannot_close(tmp_path, trusted_scm):
    from ai_dlc.providers import Registry as ProviderRegistry
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    path = tmp_path / ".ai-dlc/work/one.toml"
    path.write_text(
        path.read_text()
        .replace("requires_spec=false", "requires_spec=true")
        .replace('tracker="fake"', 'tracker="fake"\nspecification="custom-spec"')
    )
    tracker = Tracker()

    class Specification:
        def current(self, work, revision=None):
            return {"current": False, "archive": "custom", "revision": revision}

    registry = ProviderRegistry()
    registry.register("fake", tracker)
    registry.register("custom-spec", Specification())
    service = WorkService(
        tmp_path,
        {"gates": {"finish": ["specification-current"]}},
        state_path=tmp_path / "state",
        registry=registry,
    )
    service.publish("one")
    assert service.finish("one")["status"] == "blocked"
    assert tracker.closed == 0


@pytest.mark.parametrize(
    "fault", ["extra_outcome", "missing_engine", "boolean_exit", "nan_duration"]
)
def test_receipt_rejects_malformed_outcomes(fault):
    from ai_dlc.providers.scm import digest, validate_receipt

    config = {"checks": {"required": ["test"], "commands": {"test": "pytest"}}}
    receipt = {
        "schema": 1,
        "commit": "abc",
        "checks_digest": digest(config["checks"]),
        "environment_digest": digest({"mise": {}, "setup": {}}),
        "engine_version": "0.4.0",
        "target": "github-actions",
        "required": ["test"],
        "outcomes": [{"id": "test", "status": "passed", "exit_code": 0, "duration_seconds": 1.0}],
        "dirty": False,
    }
    if fault == "extra_outcome":
        receipt["outcomes"].append({"id": "other", "status": "skipped"})
    if fault == "missing_engine":
        receipt.pop("engine_version")
    if fault == "boolean_exit":
        receipt["outcomes"][0]["exit_code"] = False
    if fault == "nan_duration":
        receipt["outcomes"][0]["duration_seconds"] = float("nan")
    with pytest.raises(ValueError):
        validate_receipt(receipt, "abc", config, {})


def test_work_filters_agent_roles_and_normalizes_workflow_roles(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    path = tmp_path / ".ai-dlc/work/one.toml"
    path.write_text(path.read_text().replace('tracker="fake"', ""))
    service = WorkService(
        tmp_path,
        {
            "roles": {
                "agent-client": ["codex", "claude"],
                "tracker": "fake",
                "specs": "openspec",
                "deploy": "github-deployment",
            }
        },
        state_path=tmp_path / "state",
        registry=Registry(Tracker()),
    )
    service.publish("one")
    assert service.load("one")["providers"] == {
        "tracker": "fake",
        "specs": "openspec",
        "deploy": "github-deployment",
    }


def test_provider_workspace_drift_is_blocked(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    tracker = Tracker()
    config = {"providers": {"fake": {"kind": "linear", "team_id": "original"}}}
    service = WorkService(
        tmp_path, config, state_path=tmp_path / "state", registry=Registry(tracker)
    )
    service.publish("one")
    config["providers"]["fake"]["team_id"] = "changed"
    with pytest.raises(ValueError, match="binding.*drift"):
        service.status("one")


def identity_record(bindings=None):
    return {
        "schema": 1,
        "id": "one",
        "title": "One",
        "scope": "small",
        "requires_spec": False,
        "spec_reason": "No behavior change",
        "acceptance": ["Tests pass"],
        "reviewed": True,
        "providers": {"scm": "github", "tracker": "github-issues", "deploy": "none"},
        "bindings": bindings or {},
    }


def identity_config(**scm):
    settings = {
        "repository": "owner/repo",
        "target_branch": "main",
        "workflow": "verify.yml",
        "receipt_artifacts": ["ai-dlc-receipt-linux"],
    }
    settings.update(scm)
    return {
        "roles": {"scm": "github", "tracker": "github-issues", "deploy": "none"},
        "providers": {"github-issues": {"kind": "github-issues"}},
        "scm": settings,
    }


def test_receipt_artifact_policy_does_not_drift_bindings():
    """The finish gate reads receipt names from the merged manifest, so policy is not identity."""
    from ai_dlc.work.workflow import resolve_work

    bound = resolve_work(identity_record(), identity_config(), "one")["bindings"]
    assert {"scm", "deploy", "tracker"} <= set(bound)

    for replacement in (
        {"receipt_artifacts": ["ai-dlc-receipt-linux", "ai-dlc-receipt-macos"]},
        {"receipt_artifacts": ["ai-dlc-receipt-renamed"]},
        {"receipt_artifact": "ai-dlc-receipt", "receipt_artifacts": None},
    ):
        settings = {k: v for k, v in replacement.items() if v is not None}
        config = identity_config(**settings)
        if "receipt_artifacts" not in settings:
            config["scm"].pop("receipt_artifacts")
        resolved = resolve_work(identity_record(bound), config, "one")
        assert resolved["bindings"] == bound


@pytest.mark.parametrize(
    "change",
    [
        {"repository": "owner/other"},
        {"target_branch": "release"},
        {"workflow": "other.yml"},
        {"host": "github.example.com"},
    ],
)
def test_trusted_scm_settings_still_drift_bindings(change):
    """Identity settings, including an unrecognised one, must still force an explicit review."""
    from ai_dlc.work.workflow import resolve_work

    bound = resolve_work(identity_record(), identity_config(), "one")["bindings"]
    with pytest.raises(ValueError, match="binding drift"):
        resolve_work(identity_record(bound), identity_config(**change), "one")


def test_deployment_identity_covers_configured_deployment_evidence():
    """Both deployment settings decide which run is trusted, so neither leaves the identity."""
    from ai_dlc.work.workflow import resolve_work

    config = identity_config()
    config["deploy"] = {"workflow": "deploy.yml", "environment": "production"}
    bound = resolve_work(identity_record(), config, "one")["bindings"]
    for change in ({"workflow": "other.yml"}, {"environment": "staging"}):
        moved = copy.deepcopy(config)
        moved["deploy"].update(change)
        with pytest.raises(ValueError, match="binding drift"):
            resolve_work(identity_record(bound), moved, "one")


def test_empty_gates_cannot_bypass_merge_and_ci(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    tracker = Tracker()
    service = WorkService(
        tmp_path,
        {"gates": {"finish": []}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    service.publish("one")
    assert service.finish("one")["status"] == "blocked"
    assert tracker.closed == 0


def init_git(tmp_path):
    import subprocess

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, text=True, capture_output=True, check=True
        ).stdout.strip()

    git("init", "-b", "main")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Test")
    (tmp_path / "source.txt").write_text("initial")
    (tmp_path / ".gitignore").write_text("state/\n")
    git("add", ".")
    git("commit", "-m", "initial")
    return git


def test_start_creates_branch_for_github_without_intermediate_state(tmp_path):
    from ai_dlc.providers import Registry as ProviderRegistry
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    git = init_git(tmp_path)

    class GitHubTracker(Tracker):
        def invoke(self, op, data):
            if op == "capabilities":
                return {
                    "schema": 1,
                    "lifecycle": {"in_progress": False, "closed": True},
                    "optional_operations": ["link"],
                }
            return super().invoke(op, data)

    tracker = GitHubTracker()
    registry = ProviderRegistry()
    registry.register("fake", tracker, operations=["capabilities"])
    service = WorkService(
        tmp_path,
        {"providers": {"fake": {"kind": "github-issues"}}},
        state_path=tmp_path / "state",
        registry=registry,
    )
    result = service.start("one")
    assert result["branch"] == "work/one"
    assert git("branch", "--show-current") == "work/one"
    assert result["tracker_transition"]["supported"] is False
    assert result["tracker_transition"]["reason"] == (
        "Tracker does not support the in_progress lifecycle state"
    )
    assert service.load("one")["artifacts"]["branch"] == "work/one"
    assert service.start("one")["branch"] == "work/one"


def test_start_uses_declared_capability_without_provider_name_dispatch(tmp_path):
    from ai_dlc.providers import Registry
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    init_git(tmp_path)

    class CapableTracker(Tracker):
        def invoke(self, op, data):
            if op == "capabilities":
                return {
                    "schema": 1,
                    "lifecycle": {"in_progress": False, "closed": True},
                    "optional_operations": [],
                }
            return super().invoke(op, data)

    tracker = CapableTracker()
    registry = Registry()
    registry.register("fake", tracker, operations=["capabilities"])
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=registry)

    result = service.start("one")

    assert result["tracker_transition"] == {
        "supported": False,
        "reason": "Tracker does not support the in_progress lifecycle state",
    }
    assert result["tracker"]["state"] == "open"
    assert tracker.closed == 0


def test_start_refuses_failed_declared_capability_without_legacy_fallback(tmp_path):
    from ai_dlc.providers import Registry
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    init_git(tmp_path)

    class BrokenCapabilityTracker(Tracker):
        def invoke(self, op, data):
            if op == "capabilities":
                raise RuntimeError("capability transport failed")
            return super().invoke(op, data)

    tracker = BrokenCapabilityTracker()
    registry = Registry()
    registry.register("fake", tracker, operations=["capabilities"])
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=registry)

    with pytest.raises(RuntimeError, match="capability transport failed"):
        service.start("one")
    assert tracker.closed == 0


def test_start_rejects_malformed_declared_capability_before_mutation(tmp_path):
    from ai_dlc.providers import Registry
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    git = init_git(tmp_path)

    class MalformedCapabilityTracker(Tracker):
        def invoke(self, op, data):
            if op == "capabilities":
                return {
                    "lifecycle": {"in_progress": 1, "closed": 0},
                    "optional_operations": [],
                }
            return super().invoke(op, data)

    tracker = MalformedCapabilityTracker()
    registry = Registry()
    registry.register("fake", tracker, operations=["capabilities"])
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=registry)

    with pytest.raises(ValueError):
        service.start("one")
    assert git("branch", "--show-current") == "main"
    assert tracker.created == 0
    assert "tracker" not in service.load("one")["artifacts"]


def test_start_marks_absent_capability_declaration_as_unverified(tmp_path):
    from ai_dlc.providers import Registry
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    init_git(tmp_path)
    tracker = Tracker()
    registry = Registry()
    registry.register("fake", tracker)
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=registry)

    result = service.start("one")

    assert result["tracker_transition"] == {
        "supported": True,
        "state": "in_progress",
        "verified": False,
    }


def test_start_preserves_dirty_work_and_linked_branch(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    git = init_git(tmp_path)
    tracker = Tracker()
    git("branch", "existing")
    path = tmp_path / ".ai-dlc/work/one.toml"
    path.write_text(path.read_text() + '\n[artifacts]\nbranch="existing"\n')
    (tmp_path / "source.txt").write_text("user changes")
    service = WorkService(
        tmp_path,
        {"providers": {"fake": {"kind": "github-issues"}}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    with pytest.raises(ValueError, match="dirty"):
        service.start("one")
    assert git("branch", "--show-current") == "main"
    assert (tmp_path / "source.txt").read_text() == "user changes"
    assert tracker.created == 0


def test_openspec_rejects_archive_not_at_merged_revision(tmp_path):
    from ai_dlc.providers.openspec import OpenSpecProvider

    init_git(tmp_path)
    archive = tmp_path / "openspec/changes/archive/2026-01-01-one"
    archive.mkdir(parents=True)
    (archive / "tasks.md").write_text("- [x] Done")
    (archive / "proposal.md").write_text("# Proposal")
    with pytest.raises(ValueError, match="revision|dirty"):
        OpenSpecProvider(tmp_path).current(
            {"id": "one", "artifacts": {"spec": str(archive.relative_to(tmp_path))}},
            revision="different-merge",
        )


def test_revision_mismatch_names_both_revisions_and_the_remedy(tmp_path):
    from ai_dlc.providers.openspec import OpenSpecProvider

    git = init_git(tmp_path)
    archive = tmp_path / "openspec/changes/archive/2026-01-01-one"
    archive.mkdir(parents=True)
    (archive / "tasks.md").write_text("- [x] Done")
    (archive / "proposal.md").write_text("# Proposal")
    git("add", "openspec")
    git("commit", "-m", "archive spec")
    head = git("rev-parse", "HEAD")
    merged = "0" * 40
    with pytest.raises(ValueError) as failure:
        OpenSpecProvider(tmp_path).current(
            {"id": "one", "artifacts": {"spec": str(archive.relative_to(tmp_path))}},
            revision=merged,
        )
    reason = str(failure.value)
    assert merged in reason and head in reason
    assert "git worktree add --detach" in reason


def test_dirty_tree_at_the_merged_revision_is_a_distinct_reason(tmp_path, monkeypatch):
    import subprocess

    from ai_dlc.providers.openspec import OpenSpecProvider

    git = init_git(tmp_path)
    archive = tmp_path / "openspec/changes/archive/2026-01-01-one"
    archive.mkdir(parents=True)
    (archive / "tasks.md").write_text("- [x] Done")
    (archive / "proposal.md").write_text("# Proposal")
    git("add", "openspec")
    git("commit", "-m", "archive spec")
    sha = git("rev-parse", "HEAD")
    (archive / "extra.md").write_text("# Untracked")
    real_run = subprocess.run

    def run(command, **kwargs):
        if command[0] == "openspec":
            return subprocess.CompletedProcess(command, 0, "--all --strict --no-interactive", "")
        return real_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ValueError) as failure:
        OpenSpecProvider(tmp_path).current(
            {"id": "one", "artifacts": {"spec": str(archive.relative_to(tmp_path))}}, revision=sha
        )
    reason = str(failure.value)
    assert "dirty" in reason and sha in reason
    assert "worktree" not in reason


def test_unknown_merged_revision_is_reported_without_a_comparison(tmp_path):
    from ai_dlc.providers.openspec import OpenSpecProvider

    init_git(tmp_path)
    archive = tmp_path / "openspec/changes/archive/2026-01-01-one"
    archive.mkdir(parents=True)
    (archive / "tasks.md").write_text("- [x] Done")
    (archive / "proposal.md").write_text("# Proposal")
    with pytest.raises(ValueError, match="merged revision is unknown"):
        OpenSpecProvider(tmp_path).current(
            {"id": "one", "artifacts": {"spec": str(archive.relative_to(tmp_path))}}, revision=""
        )


def test_ignored_local_archive_is_not_merged_evidence(tmp_path, monkeypatch):
    import subprocess

    from ai_dlc.providers.openspec import OpenSpecProvider

    git = init_git(tmp_path)
    (tmp_path / ".gitignore").write_text("state/\nopenspec/\n")
    git("add", ".gitignore")
    git("commit", "-m", "ignore local spec")
    sha = git("rev-parse", "HEAD")
    archive = tmp_path / "openspec/changes/archive/2026-01-01-one"
    archive.mkdir(parents=True)
    (archive / "tasks.md").write_text("- [x] Done")
    (archive / "proposal.md").write_text("# Proposal")
    real_run = subprocess.run

    def run(command, **kwargs):
        if command[0] == "openspec":
            return subprocess.CompletedProcess(command, 0, "--all --strict --no-interactive", "")
        return real_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ValueError, match="dirty|tracked"):
        OpenSpecProvider(tmp_path).current(
            {"id": "one", "artifacts": {"spec": str(archive.relative_to(tmp_path))}}, revision=sha
        )


def test_clean_archived_spec_is_bound_to_merged_sha(tmp_path, monkeypatch):
    import subprocess

    from ai_dlc.providers.openspec import OpenSpecProvider

    git = init_git(tmp_path)
    archive = tmp_path / "openspec/changes/archive/2026-01-01-one"
    archive.mkdir(parents=True)
    (archive / "tasks.md").write_text("- [x] Done")
    (archive / "proposal.md").write_text("# Proposal")
    git("add", "openspec")
    git("commit", "-m", "archive spec")
    sha = git("rev-parse", "HEAD")
    real_run = subprocess.run

    def run(command, **kwargs):
        if command[0] == "openspec":
            return subprocess.CompletedProcess(command, 0, "--all --strict --no-interactive", "")
        return real_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    work_item = {"id": "one", "artifacts": {"spec": str(archive.relative_to(tmp_path))}}
    assert OpenSpecProvider(tmp_path).current(work_item, revision=sha)["revision"] == sha
    (archive / "proposal.md").write_text("# Uncommitted")
    with pytest.raises(ValueError, match="dirty"):
        OpenSpecProvider(tmp_path).current(work_item, revision=sha)


def test_machine_vault_relocation_does_not_rebind_work(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    config = {"paths": {"vault": str(tmp_path / "first-vault")}}
    service = WorkService(
        tmp_path, config, state_path=tmp_path / "state", registry=Registry(Tracker())
    )
    service.publish("one")
    config["paths"]["vault"] = str(tmp_path / "different-vault")
    assert service.load("one")["id"] == "one"


def test_rebound_mapped_tracker_reuses_item_and_gets_new_journal_identity(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    original = Tracker()

    class Replacement(Tracker):
        def invoke(self, op, data):
            if op == "find":
                return {"items": []}
            if op == "read":
                assert data["reference"] == "mapped"
                return {"id": "mapped", "url": "https://issues/mapped", "state": "open"}
            if op == "create":
                raise AssertionError("mapped tracker must not be recreated")
            return super().invoke(op, data)

    replacement = Replacement()

    class Providers:
        def get(self, name):
            return original if name == "fake" else replacement

    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Providers())
    service.publish("one")
    updated = service.load("one")
    updated["providers"]["tracker"] = "replacement"
    updated["bindings"].pop("tracker")
    updated["artifacts"]["tracker"] = "mapped"
    service.save(updated)
    assert service.publish("one")["tracker"]["id"] == "mapped"


def test_handoff_rebind_uses_mapped_note_and_new_operation(tmp_path, trusted_scm):
    from ai_dlc.documentation.knowledge import Knowledge
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    tracker = Tracker()
    vault = tmp_path / "vault"
    vault.mkdir()

    class Providers:
        def get(self, name):
            return Knowledge(vault) if name == "notes" else tracker

    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Providers())
    record = service.load("one")
    record["providers"]["knowledge"] = "notes"
    record["bindings"].pop("knowledge", None)
    service.save(record)
    service.publish("one")
    assert service.finish("one", "Outcome")["status"] == "completed"
    record = service.load("one")
    record["artifacts"]["knowledge"] = "replacement.md"
    service.save(record)
    assert service.finish("one", "Outcome")["status"] == "completed"
    assert "Outcome" in (vault / "replacement.md").read_text()
    assert tracker.closed == 1


def traceability_record(root, work_id="target", **changes):
    import tomli_w

    record = {
        "schema": 1,
        "id": work_id,
        "title": work_id,
        "scope": "An independently finishable increment",
        "requires_spec": False,
        "spec_reason": "Existing behavior verification",
        "acceptance": ["Observe the required result"],
        "reviewed": True,
        "providers": {"tracker": "fake"},
    }
    record.update(changes)
    path = root / ".ai-dlc/work" / f"{work_id}.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(record))
    return path


class TraceabilityTracker:
    def __init__(self):
        self.items = {}
        self.calls = []

    def invoke(self, operation, payload):
        self.calls.append((operation, copy.deepcopy(payload)))
        if operation == "read":
            return dict(self.items[payload["reference"]])
        if operation == "find":
            return {
                "items": [
                    dict(item)
                    for item in self.items.values()
                    if payload["correlation"] in item.get("body", "")
                ]
            }
        if operation == "create":
            item = {
                "id": "created",
                "url": "https://tracker.invalid/created",
                "state": "open",
                "body": payload["body"] + payload["correlation"],
            }
            self.items[item["id"]] = item
            return dict(item)
        if operation == "transition":
            self.items[payload["reference"]]["state"] = payload["state"]
            return dict(self.items[payload["reference"]])
        raise AssertionError(operation)


@pytest.mark.parametrize("invalid", ["missing", "cycle", "artifact", "escape", "symlink"])
def test_traceability_refusal_precedes_publication_and_binding_writes(tmp_path, invalid):
    from ai_dlc.work.workflow import WorkService

    root = tmp_path / "project"
    artifacts = {}
    depends_on = []
    if invalid == "missing":
        depends_on = ["absent"]
    if invalid == "cycle":
        depends_on = ["parent"]
        traceability_record(root, "parent", depends_on=["target"])
    if invalid == "artifact":
        artifacts["brief"] = "docs/absent.md"
    if invalid == "escape":
        artifacts["brief"] = "../outside.md"
        (tmp_path / "outside.md").write_text("outside")
    if invalid == "symlink":
        root.mkdir(exist_ok=True)
        outside = tmp_path / "outside.md"
        outside.write_text("outside")
        (root / "brief.md").symlink_to(outside)
        artifacts["brief"] = "brief.md"
    path = traceability_record(root, depends_on=depends_on, artifacts=artifacts)
    before = path.read_bytes()
    tracker = TraceabilityTracker()
    service = WorkService(root, {}, state_path=tmp_path / "state", registry=Registry(tracker))

    with pytest.raises(ValueError):
        service.publish("target")

    assert path.read_bytes() == before
    assert tracker.calls == []
    assert service.journal.db.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 0


def test_traceability_defaults_and_rich_create_preserve_correlation_identity(tmp_path):
    from ai_dlc.work.workflow import WorkService

    root = tmp_path / "project"
    path = traceability_record(root)
    tracker = TraceabilityTracker()
    service = WorkService(root, {}, state_path=tmp_path / "state", registry=Registry(tracker))
    old = service.load("target")
    correlation = service.op_id(old, "work")
    operation = service.op_id(old, "publish")
    assert old["depends_on"] == old["requirements"] == []
    (root / "brief.md").write_text("# RQ-001")
    traceability_record(root, requirements=["brief#RQ-001"], artifacts={"brief": "brief.md#RQ-001"})
    result = service.publish("target")
    created = tracker.items[result["tracker"]["id"]]
    assert "## Scope" in created["body"]
    assert "brief#RQ-001" in created["body"]
    assert "brief.md#RQ-001" in created["body"]
    assert f"<!-- ai-dlc:{correlation} -->" in created["body"]
    assert service.op_id(service.load("target"), "publish") == operation
    assert path.exists()


@pytest.mark.parametrize("mapped", [True, False])
def test_rich_republication_reconciles_legacy_journal_and_preserves_authored_body(tmp_path, mapped):
    import tomli_w

    from ai_dlc.work.workflow import WorkService

    root = tmp_path / "project"
    path = traceability_record(root)
    tracker = TraceabilityTracker()
    service = WorkService(root, {}, state_path=tmp_path / "state", registry=Registry(tracker))
    old = service.load("target")
    old_payload = {
        "provider": "fake",
        "title": old["title"],
        "body": "\n".join(old["acceptance"]),
        "correlation": f"<!-- ai-dlc:{service.op_id(old, 'work')} -->",
        "operation_id": service.op_id(old, "publish"),
    }
    service.journal.begin(old_payload["operation_id"], old_payload)
    item = {
        "id": "original",
        "url": "https://tracker.invalid/original",
        "state": "open",
        "body": "Owner edited this description.\n" + old_payload["correlation"],
    }
    tracker.items[item["id"]] = item
    service.journal.succeed(old_payload["operation_id"], item)
    fingerprint = service.journal.db.execute("SELECT fingerprint FROM operations").fetchone()[0]
    old["requirements"] = ["brief#RQ-001"]
    old["scope"] = "Updated reviewed scope"
    if mapped:
        old["artifacts"]["tracker"] = "original"
    path.write_text(tomli_w.dumps(old))

    result = service.publish("target")

    assert result["tracker"]["id"] == "original"
    assert tracker.items["original"]["body"] == item["body"]
    assert all(op not in {"create", "link", "transition"} for op, _ in tracker.calls)
    assert (
        service.journal.db.execute("SELECT fingerprint FROM operations").fetchone()[0]
        == fingerprint
    )


@pytest.mark.parametrize(
    "state", ["open", "in_progress", "cancelled", "duplicate", "unknown", None]
)
def test_dependency_refusal_precedes_branch_and_local_mutation(tmp_path, state):
    import subprocess

    from ai_dlc.work.workflow import WorkService

    root = tmp_path / "project"
    traceability_record(root, "parent", artifacts={"tracker": "parent-ref"})
    path = traceability_record(root, depends_on=["parent"])
    before = path.read_bytes()
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
    tracker = TraceabilityTracker()
    if state is not None:
        tracker.items["parent-ref"] = {
            "id": "parent-ref",
            "url": "https://tracker.invalid/parent",
            "state": state,
        }
    service = WorkService(root, {}, state_path=tmp_path / "state", registry=Registry(tracker))

    with pytest.raises(ValueError, match="[Dd]ependency"):
        service.start("target")

    assert path.read_bytes() == before
    branch = subprocess.check_output(
        ["git", "-C", str(root), "branch", "--show-current"], text=True
    ).strip()
    assert branch == "main"
    assert all(op == "read" for op, _ in tracker.calls)


def test_completed_dependencies_allow_start_with_their_pinned_provider(tmp_path):
    import subprocess

    from ai_dlc.work.workflow import WorkService

    root = tmp_path / "project"
    traceability_record(
        root, "parent", artifacts={"tracker": "parent-ref"}, providers={"tracker": "other"}
    )
    traceability_record(root, depends_on=["parent"])
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "fixture",
        ],
        check=True,
        capture_output=True,
    )
    current = TraceabilityTracker()
    parent = TraceabilityTracker()
    parent.items["parent-ref"] = {
        "id": "parent-ref",
        "url": "https://tracker.invalid/parent",
        "state": "closed",
    }

    class SelectedRegistry:
        def get(self, provider_id):
            return {"fake": current, "other": parent}[provider_id]

    service = WorkService(root, {}, state_path=tmp_path / "state", registry=SelectedRegistry())
    assert service.start("target")["status"] == "started"
    assert parent.calls == [("read", {"reference": "parent-ref"})]
    assert current.items["created"]["state"] == "in_progress"


@pytest.mark.parametrize("status", ["pending", "uncertain", "succeeded"])
def test_legacy_publication_journal_recovery_survives_richer_payload(tmp_path, status):
    from ai_dlc.work.workflow import WorkService

    root = tmp_path / "project"
    traceability_record(root)

    class DelayedIndex(TraceabilityTracker):
        def invoke(self, operation, payload):
            if operation == "find":
                self.calls.append((operation, payload))
                return {"items": []}
            return super().invoke(operation, payload)

    tracker = DelayedIndex()
    service = WorkService(root, {}, state_path=tmp_path / "state", registry=Registry(tracker))
    item = service.load("target")
    operation_id = service.op_id(item, "publish")
    payload = {
        "provider": "fake",
        "title": item["title"],
        "body": "\n".join(item["acceptance"]),
        "correlation": f"<!-- ai-dlc:{service.op_id(item, 'work')} -->",
        "operation_id": operation_id,
    }
    service.journal.begin(operation_id, payload)
    if status == "uncertain":
        service.journal.uncertain(operation_id)
    if status == "succeeded":
        remote = {
            "id": "existing",
            "url": "https://tracker.invalid/existing",
            "state": "open",
            "body": "Authored body",
        }
        tracker.items["existing"] = remote
        service.journal.succeed(operation_id, remote)
        assert service.publish("target")["tracker"] == remote
    else:
        with pytest.raises(RuntimeError, match="uncertain"):
            service.publish("target")
    assert not any(op == "create" for op, _ in tracker.calls)
    assert service.journal.db.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == 1


@pytest.mark.parametrize("requirements", [[""], [" "], ["RQ-001\ninvented requirement"]])
def test_work_references_are_identifiers_not_blank_or_multiline_prose(tmp_path, requirements):
    from ai_dlc.work.workflow import WorkService

    root = tmp_path / "project"
    traceability_record(root, requirements=requirements)
    service = WorkService(
        root, {}, state_path=tmp_path / "state", registry=Registry(TraceabilityTracker())
    )
    with pytest.raises(ValueError, match="[Rr]equirement"):
        service.load("target")


def test_validation_keeps_provider_artifacts_and_external_documents_unprobed(tmp_path):
    from ai_dlc.work.workflow import validate_work

    root = tmp_path / "project"
    traceability_record(
        root,
        artifacts={
            "tracker": "remote-item",
            "pr": "remote-pr",
            "branch": "work/target",
            "deployment": "deployment-opaque-id",
            "knowledge": "private-vault-note.md",
            "spec": "https://specs.invalid/change#RQ-001",
        },
    )
    assert validate_work(root, {}, "target")["valid"]


def test_start_requires_every_transitive_dependency_and_refreshes_each_read(tmp_path):
    from ai_dlc.work.workflow import WorkService

    root = tmp_path / "project"
    traceability_record(root, "base", artifacts={"tracker": "base-ref"})
    traceability_record(root, "parent", depends_on=["base"], artifacts={"tracker": "parent-ref"})
    path = traceability_record(root, depends_on=["parent"])
    tracker = TraceabilityTracker()
    for name in ["base", "parent"]:
        tracker.items[f"{name}-ref"] = {
            "id": f"{name}-ref",
            "url": f"https://tracker.invalid/{name}",
            "state": "closed",
        }
    tracker.items["base-ref"]["state"] = "open"
    service = WorkService(root, {}, state_path=tmp_path / "state", registry=Registry(tracker))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="Dependency base"):
        service.start("target")
    tracker.items["base-ref"]["state"] = "closed"
    tracker.items["parent-ref"]["state"] = "cancelled"
    with pytest.raises(ValueError, match="Dependency parent"):
        service.start("target")
    assert path.read_bytes() == before
    assert [payload["reference"] for op, payload in tracker.calls if op == "read"] == [
        "base-ref",
        "base-ref",
        "parent-ref",
    ]


def test_start_rejects_stale_project_configuration_before_branch_or_dependency_reads(tmp_path):
    import subprocess

    from ai_dlc.work.workflow import WorkService

    root = tmp_path / "project"
    traceability_record(root)
    manifest = root / "ai-dlc.toml"
    manifest.write_text('schema=4\n[roles]\ntracker="fake"\n')
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)

    def commit():
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "fixture",
            ],
            check=True,
            capture_output=True,
        )

    commit()
    tracker = TraceabilityTracker()
    service = WorkService(
        root,
        {"roles": {"tracker": "fake"}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    manifest.write_text('schema=4\n[roles]\ntracker="replacement"\n')
    commit()
    with pytest.raises(ValueError, match="Project configuration changed"):
        service.start("target")
    assert (
        subprocess.check_output(
            ["git", "-C", str(root), "branch", "--show-current"], text=True
        ).strip()
        == "main"
    )
    assert tracker.calls == []


@pytest.mark.parametrize(
    "reference",
    [
        "github-ticket-workflows",
        "github-project-defaults",
        "organization/spec-id",
        "spec-provider://organization/change",
    ],
)
def test_legacy_native_spec_reference_validates_and_preserves_mapped_issue(tmp_path, reference):
    from ai_dlc.work.workflow import WorkService, validate_work

    traceability_record(
        tmp_path,
        requires_spec=True,
        spec_reason="Existing provider specification",
        artifacts={"spec": reference, "tracker": "mapped"},
    )
    tracker = TraceabilityTracker()
    tracker.items["mapped"] = {
        "id": "mapped",
        "state": "open",
        "body": "Authored issue remains intact",
    }
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Registry(tracker))
    assert validate_work(tmp_path, {}, "target")["valid"]
    for _ in range(2):
        result = service.publish("target")
        assert result["tracker"]["body"] == "Authored issue remains intact"
    assert not any(operation == "create" for operation, _ in tracker.calls)
    assert service.load("target")["artifacts"]["spec"] == reference


@pytest.mark.parametrize(
    "reference", ["./missing-change", "docs/missing.md", "spec.md", "../outside"]
)
def test_explicit_local_spec_reference_still_refuses_before_publication(tmp_path, reference):
    from ai_dlc.work.workflow import WorkService

    path = traceability_record(tmp_path, artifacts={"spec": reference, "tracker": "mapped"})
    before = path.read_bytes()
    tracker = TraceabilityTracker()
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Registry(tracker))
    with pytest.raises(ValueError, match="Work validation failed"):
        service.publish("target")
    assert tracker.calls == []
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "reference",
    [
        "file:docs/missing.md",
        "file:./missing-change",
        "file:///outside/missing-change",
        "file:../outside",
        "FILE://localhost/missing-change",
    ],
)
def test_filesystem_uri_is_reserved_and_refused_before_publication(tmp_path, reference):
    from ai_dlc.work.workflow import WorkService

    path = traceability_record(tmp_path, artifacts={"spec": reference, "tracker": "mapped"})
    before = path.read_bytes()
    tracker = TraceabilityTracker()
    tracker.items["mapped"] = {"id": "mapped", "state": "open", "body": "Authored"}
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Registry(tracker))
    with pytest.raises(ValueError, match="Work validation failed"):
        service.publish("target")
    assert tracker.calls == []
    assert path.read_bytes() == before


def test_moved_bare_spec_directory_is_reported_absent_rather_than_reclassified(tmp_path):
    from ai_dlc.work.workflow import validate_work

    change = tmp_path / "openspec/changes/target"
    change.mkdir(parents=True)
    traceability_record(tmp_path, artifacts={"spec": "openspec/changes/target"})
    assert validate_work(tmp_path, {}, "target")["valid"]

    # Archiving moves the directory; the reference keeps pointing at the old location.
    (tmp_path / "openspec/changes/archive").mkdir()
    change.rename(tmp_path / "openspec/changes/archive/2026-09-12-target")

    result = validate_work(tmp_path, {}, "target")
    assert result["errors"] == [
        "Work target: artifact spec (openspec/changes/target): Referenced local artifact is absent"
    ]
    assert not result["valid"]


def test_anchored_spec_path_that_never_existed_is_reported_absent(tmp_path):
    from ai_dlc.work.workflow import validate_work

    (tmp_path / "docs").mkdir()
    traceability_record(tmp_path, artifacts={"spec": "docs/never-written"})
    result = validate_work(tmp_path, {}, "target")
    assert result["errors"] == [
        "Work target: artifact spec (docs/never-written): Referenced local artifact is absent"
    ]


@pytest.mark.parametrize("reference", ["organization/spec-id", "provider://organization/spec-id"])
def test_unanchored_provider_native_spec_id_is_not_validated_as_a_path(tmp_path, reference):
    from ai_dlc.work.workflow import validate_work

    (tmp_path / "openspec/changes").mkdir(parents=True)
    traceability_record(tmp_path, artifacts={"spec": reference})
    assert validate_work(tmp_path, {}, "target") == {
        "valid": True,
        "work_id": "target",
        "dependencies": [],
        "errors": [],
    }


def test_validate_work_records_reports_dangling_artifacts_without_resolving_bindings(tmp_path):
    from ai_dlc.work.workflow import validate_work_records

    (tmp_path / "openspec/changes/kept").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/plan.md").write_text("plan")
    traceability_record(
        tmp_path,
        "kept",
        artifacts={"spec": "openspec/changes/kept", "plan": "docs/plan.md"},
        # A finished record keeps its historical fingerprint; drift is not a repository invariant.
        bindings={"scm": "0" * 64, "tracker": "1" * 64},
    )
    traceability_record(tmp_path, "moved", artifacts={"spec": "openspec/changes/moved"})
    traceability_record(
        tmp_path, "planless", artifacts={"plan": "docs/absent.md"}, depends_on=["kept"]
    )
    traceability_record(
        tmp_path,
        "native",
        artifacts={
            "spec": "organization/spec-id",
            "tracker": "42",
            "pr": "https://example.test/pull/1",
        },
    )

    result = validate_work_records(tmp_path)

    assert result == {
        "valid": False,
        "records": ["kept", "moved", "native", "planless"],
        "errors": [
            "Work moved: artifact spec (openspec/changes/moved): Referenced local artifact is absent",
            "Work planless: artifact plan (docs/absent.md): Referenced local artifact is absent",
        ],
    }


def test_validate_work_records_reports_unreadable_records_and_graph_errors(tmp_path):
    from ai_dlc.work.workflow import validate_work_records

    assert validate_work_records(tmp_path) == {"valid": True, "records": [], "errors": []}
    folder = tmp_path / ".ai-dlc/work"
    folder.mkdir(parents=True)
    (folder / "broken.toml").write_text("invalid TOML")
    (folder / "bad id.toml").write_text("")
    traceability_record(tmp_path, "renamed", id="other")
    traceability_record(tmp_path, "cyclic", depends_on=["cyclic"])
    traceability_record(tmp_path, "orphan", depends_on=["missing"])

    result = validate_work_records(tmp_path)

    assert result["records"] == ["cyclic", "orphan"]
    assert not result["valid"]
    assert "Work renamed: Work ID does not match filename" in result["errors"]
    assert "Work cyclic: self dependency cycle" in result["errors"]
    assert "Work orphan: missing dependency missing" in result["errors"]
    assert any(error.startswith("Work broken: ") for error in result["errors"])
    assert any(error.startswith("Work bad id: ") for error in result["errors"])


@pytest.mark.parametrize("dangling_ancestor", [False, True])
def test_suffixless_dangling_spec_symlink_cannot_masquerade_as_native_id(
    tmp_path, dangling_ancestor
):
    from ai_dlc.work.workflow import WorkService

    directory = tmp_path / "spec-links"
    directory.mkdir()
    link = directory / "dangling"
    link.symlink_to(tmp_path.parent / "missing-outside-target", target_is_directory=True)
    reference = "spec-links/dangling/child" if dangling_ancestor else "spec-links/dangling"
    path = traceability_record(tmp_path, artifacts={"spec": reference, "tracker": "mapped"})
    before = path.read_bytes()
    tracker = TraceabilityTracker()
    tracker.items["mapped"] = {"id": "mapped", "state": "open", "body": "Authored"}
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Registry(tracker))
    with pytest.raises(ValueError, match="Work validation failed"):
        service.publish("target")
    assert tracker.calls == []
    assert path.read_bytes() == before


def test_build_context_reads_records_as_written_and_cli_prints_the_same_json(tmp_path):
    """Would fail if the CLI context command diverged from the work service it now delegates to."""
    import json

    from typer.testing import CliRunner

    from ai_dlc.cli import app
    from ai_dlc.work.workflow import build_context

    (tmp_path / "ai-dlc.toml").write_text(
        'schema = 4\n[project]\nname = "demo"\n[checks]\nrequired = ["lint", "test"]\n'
    )
    work_dir = tmp_path / ".ai-dlc/work"
    work_dir.mkdir(parents=True)
    for index in range(4):
        (work_dir / f"item-{index}.toml").write_text(
            f'schema = 1\nid = "item-{index}"\ntitle = "Item {index}"\n[artifacts]\nbranch = "b{index}"\n'
        )
    (work_dir / "malformed.toml").write_text("only_a_title = true\n")

    full = build_context(tmp_path)
    assert [record["id"] for record in full["work"]] == [
        "item-0",
        "item-1",
        "item-2",
        "item-3",
        None,
    ]
    assert full["work"][0]["artifacts"] == {"branch": "b0"}
    assert full["required"] == ["lint", "test"]
    assert full["next"].startswith("Select work;")
    brief = build_context(tmp_path, brief=True)
    assert [record["id"] for record in brief["work"]] == ["item-2", "item-3", None]

    result = CliRunner().invoke(app, ["context", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert result.output == json.dumps(full, indent=2) + "\n"
    result = CliRunner().invoke(app, ["context", "--root", str(tmp_path), "--brief"])
    assert result.output == json.dumps(brief, indent=2)[:2000] + "\n"


def _git_output(tmp_path, *args):
    import subprocess

    return subprocess.run(
        ["git", *args], cwd=tmp_path, text=True, capture_output=True, check=True
    ).stdout.strip()


def test_start_commits_only_its_record_and_stays_idempotent(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    git = init_git(tmp_path)
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Registry(Tracker()))

    result = service.start("one")

    assert git("status", "--porcelain") == ""
    assert git("log", "-1", "--format=%s") == "chore(work): start one"
    assert git("show", "--name-only", "--format=", "HEAD") == ".ai-dlc/work/one.toml"
    assert result["commit"] == git("rev-parse", "HEAD")
    head = git("rev-parse", "HEAD")
    again = service.start("one")
    assert git("rev-parse", "HEAD") == head
    assert again["commit"] is None


def test_start_without_commit_keeps_the_record_dirty(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    git = init_git(tmp_path)
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Registry(Tracker()))

    result = service.start("one", commit=False)

    assert result["commit"] is None
    assert git("status", "--porcelain") == "M .ai-dlc/work/one.toml"
    assert git("log", "-1", "--format=%s") == "initial"


def test_link_commits_only_its_record_and_leaves_other_staged_files_alone(tmp_path):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    git = init_git(tmp_path)
    (tmp_path / "source.txt").write_text("staged elsewhere")
    git("add", "source.txt")
    (tmp_path / "notes.txt").write_text("untracked")
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Registry(Tracker()))

    result = service.link("one", "spec", "openspec/changes/kept")

    assert git("log", "-1", "--format=%s") == "chore(work): link spec for one"
    assert git("show", "--name-only", "--format=", "HEAD") == ".ai-dlc/work/one.toml"
    assert git("diff", "--cached", "--name-only") == "source.txt"
    assert (tmp_path / "notes.txt").read_text() == "untracked"
    assert result["commit"] == git("rev-parse", "HEAD")
    assert service.link("one", "spec", "openspec/changes/kept", commit=False)["commit"] is None


class FakeSCM(Tracker):
    """One registered provider serving both the tracker and the SCM role of a record."""

    def __init__(self, url="https://github.com/a/b/pull/7"):
        super().__init__()
        self.url = url
        self.pull_requests = []
        self.refuse = None

    def pull_request_create(self, title, body, base, head):
        if self.refuse:
            raise self.refuse
        self.pull_requests.append({"title": title, "body": body, "base": base, "head": head})
        return {"url": self.url, "number": 7}


def started_service(tmp_path, config=None):
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    git = init_git(tmp_path)
    record_path = tmp_path / ".ai-dlc/work/one.toml"
    record_path.write_text(
        record_path.read_text().replace('tracker="fake"', 'tracker="fake"\nscm="fake"')
    )
    scm = FakeSCM()
    service = WorkService(
        tmp_path, config or {}, state_path=tmp_path / "state", registry=Registry(scm)
    )
    service.start("one")
    return service, scm, git


def test_pr_opens_once_links_the_url_and_commits_the_record(tmp_path):
    service, scm, git = started_service(tmp_path)

    result = service.pr("one")

    assert result["status"] == "created"
    assert result["created"] is True
    assert result["pr"] == {"url": "https://github.com/a/b/pull/7", "number": 7}
    assert scm.pull_requests == [
        {
            "title": "One",
            "body": "## Scope\n\nsmall\n\n## Acceptance\n\n- Tests pass\n",
            "base": "main",
            "head": "work/one",
        }
    ]
    assert service.load("one")["artifacts"]["pr"] == "https://github.com/a/b/pull/7"
    assert git("status", "--porcelain") == ""
    assert git("log", "-1", "--format=%s") == "chore(work): link pr for one"
    assert git("show", "--name-only", "--format=", "HEAD") == ".ai-dlc/work/one.toml"
    head = git("rev-parse", "HEAD")

    again = service.pr("one")

    assert again["status"] == "linked"
    assert again["created"] is False
    assert again["pr"]["url"] == "https://github.com/a/b/pull/7"
    assert len(scm.pull_requests) == 1
    assert git("rev-parse", "HEAD") == head


def test_pr_closes_the_issue_only_for_a_bare_github_issue_number(tmp_path):
    config = {
        "providers": {"fake": {"kind": "github-issues"}},
        "scm": {"repository": "a/b", "target_branch": "trunk"},
    }
    service, scm, _ = started_service(tmp_path, config)

    service.pr("one")

    assert scm.pull_requests[0]["base"] == "trunk"
    assert scm.pull_requests[0]["body"].endswith("- Tests pass\n\nCloses #1\n")


def test_pr_retry_after_a_lost_response_reuses_the_journaled_pull_request(tmp_path):
    service, scm, _ = started_service(tmp_path)
    original = scm.pull_request_create

    def lose_response(*args, **kwargs):
        original(*args, **kwargs)
        raise TimeoutError("response lost after creation")

    scm.pull_request_create = lose_response
    with pytest.raises(TimeoutError):
        service.pr("one")
    assert "pr" not in service.load("one")["artifacts"]
    scm.pull_request_create = original

    with pytest.raises(RuntimeError, match="uncertain") as caught:
        service.pr("one")

    assert "work link one pr" in str(caught.value)
    assert len(scm.pull_requests) == 1
    assert "pr" not in service.load("one")["artifacts"]


def test_pr_refusal_from_the_scm_has_no_side_effects(tmp_path):
    from ai_dlc.errors import RefusedError

    service, scm, git = started_service(tmp_path)
    scm.refuse = RefusedError("Branch work/one has no upstream; push the branch first")
    head = git("rev-parse", "HEAD")
    before = (tmp_path / ".ai-dlc/work/one.toml").read_bytes()

    with pytest.raises(RefusedError, match="push the branch first"):
        service.pr("one")

    assert scm.pull_requests == []
    assert git("rev-parse", "HEAD") == head
    assert git("status", "--porcelain") == ""
    assert (tmp_path / ".ai-dlc/work/one.toml").read_bytes() == before
    scm.refuse = None
    assert service.pr("one")["created"] is True
    assert len(scm.pull_requests) == 1


def test_pr_requires_a_started_record(tmp_path):
    from ai_dlc.errors import RefusedError
    from ai_dlc.work.workflow import WorkService

    work(tmp_path)
    init_git(tmp_path)
    record_path = tmp_path / ".ai-dlc/work/one.toml"
    record_path.write_text(
        record_path.read_text().replace('tracker="fake"', 'tracker="fake"\nscm="fake"')
    )
    scm = FakeSCM()
    service = WorkService(tmp_path, {}, state_path=tmp_path / "state", registry=Registry(scm))

    with pytest.raises(RefusedError, match="work start"):
        service.pr("one")
    assert scm.pull_requests == []


def fake_gh(tmp_path, monkeypatch):
    """Install a gh stand-in that records its arguments and prints a pull request URL."""
    import os

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh.log"
    script = bin_dir / "gh"
    script.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" > "{log}"\n'
        'while [ "$#" -gt 0 ]; do\n'
        '  if [ "$1" = "--body-file" ]; then cat "$2" > "$(dirname "$0")/body.md"; fi\n'
        "  shift\n"
        "done\n"
        'echo "Creating pull request"\n'
        'echo "https://github.com/a/b/pull/12"\n'
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return log, bin_dir / "body.md"


def test_github_scm_creates_the_pull_request_through_gh_for_a_pushed_branch(tmp_path, monkeypatch):
    from ai_dlc.providers.scm import GitHubSCM

    log, body_file = fake_gh(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    git = init_git(repo)
    git("switch", "-c", "work/one")
    remote = tmp_path / "remote.git"
    _git_output(tmp_path, "init", "--bare", str(remote))
    git("remote", "add", "origin", str(remote))
    git("push", "-u", "origin", "work/one")
    scm = GitHubSCM(repo, {"scm": {"repository": "a/b"}})

    result = scm.pull_request_create("Title", "## Scope\n\nbody\n", "main", "work/one")

    assert result == {"url": "https://github.com/a/b/pull/12", "number": 12}
    arguments = log.read_text().splitlines()
    assert arguments[:8] == [
        "pr",
        "create",
        "--repo",
        "a/b",
        "--base",
        "main",
        "--head",
        "work/one",
    ]
    assert arguments[8:10] == ["--title", "Title"]
    assert arguments[10] == "--body-file"
    assert body_file.read_text() == "## Scope\n\nbody\n"


def test_github_scm_refuses_a_branch_without_upstream_before_calling_gh(tmp_path, monkeypatch):
    from ai_dlc.errors import RefusedError
    from ai_dlc.providers.scm import GitHubSCM

    log, _ = fake_gh(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    git = init_git(repo)
    git("switch", "-c", "work/one")
    scm = GitHubSCM(repo, {"scm": {"repository": "a/b"}})

    with pytest.raises(RefusedError, match="push the branch first") as caught:
        scm.pull_request_create("Title", "body", "main", "work/one")

    assert "git push -u origin work/one" in str(caught.value)
    assert not log.exists()


def test_github_scm_rejects_a_pull_request_url_from_another_repository(tmp_path, monkeypatch):
    from ai_dlc.providers.scm import GitHubSCM

    fake_gh(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    repo.mkdir()
    git = init_git(repo)
    git("switch", "-c", "work/one")
    remote = tmp_path / "remote.git"
    _git_output(tmp_path, "init", "--bare", str(remote))
    git("remote", "add", "origin", str(remote))
    git("push", "-u", "origin", "work/one")
    scm = GitHubSCM(repo, {"scm": {"repository": "other/repo"}})

    with pytest.raises(ValueError, match="configured repository"):
        scm.pull_request_create("Title", "body", "main", "work/one")


def test_pr_pending_journal_never_repeats_creation(tmp_path):
    service, scm, _ = started_service(tmp_path)
    record = service.load("one")
    service.journal.begin(
        service.op_id(record, "pr"),
        {"provider": record["providers"].get("scm"), "base": "main", "head": "work/one"},
    )
    with pytest.raises(RuntimeError, match="uncertain"):
        service.pr("one")
    assert scm.pull_requests == []


def test_pr_refuses_an_unrelated_checkout_without_writing(tmp_path):
    service, scm, git = started_service(tmp_path)
    git("switch", "-c", "unrelated")
    before = (tmp_path / ".ai-dlc/work/one.toml").read_bytes()
    with pytest.raises(ValueError, match="bound branch"):
        service.pr("one")
    assert scm.pull_requests == []
    assert (tmp_path / ".ai-dlc/work/one.toml").read_bytes() == before


def test_pr_recovers_success_before_record_link(tmp_path, monkeypatch):
    service, scm, _ = started_service(tmp_path)
    original = service.link
    monkeypatch.setattr(service, "link", lambda *args: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError, match="disk"):
        service.pr("one")
    monkeypatch.setattr(service, "link", original)
    assert service.pr("one")["pr"]["url"] == scm.url
    assert len(scm.pull_requests) == 1


def test_new_work_offline_is_unreviewed_valid_and_creates_no_state(tmp_path):
    from ai_dlc.work.workflow import WorkService, validate_work

    state = tmp_path / "state"
    service = WorkService(
        tmp_path, {"roles": {"tracker": "fake", "agent-client": ["codex"]}}, state_path=state
    )
    result = service.new("demo", title="T", scope="S", acceptance=["A"])
    assert result["reviewed"] is False
    assert result["providers"] == {"tracker": "fake"}
    assert result["requirements"] == result["depends_on"] == []
    assert validate_work(tmp_path, service.config, "demo")["valid"]
    assert not state.exists()
    with pytest.raises(ValueError, match="reviewed"):
        service.load("demo", mutation=True)


@pytest.mark.parametrize(
    "body, acceptance",
    [
        (
            "## Why\n\nFirst paragraph.\nStill first.\n\nSecond.\n\n## Acceptance criteria\n- A\n* B\n\n## Other\n- C",
            ["A", "B"],
        ),
        ("Scope only.", ["TODO: state acceptance"]),
        ("## Acceptance\n- One\n+ Two", ["One", "Two"]),
    ],
)
def test_new_work_from_issue_preserves_source_fields(tmp_path, body, acceptance):
    from ai_dlc.work.workflow import WorkService

    tracker = Tracker()
    tracker.items = [{"id": "68", "title": "Issue title", "body": body, "state": "open"}]
    service = WorkService(
        tmp_path,
        {"roles": {"tracker": "fake"}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    result = service.new("demo", tracker_reference="68")
    assert result["title"] == "Issue title"
    assert result["acceptance"] == acceptance
    assert result["artifacts"] == {"tracker": "68"}
    assert result["requires_spec"] is True
    assert result["spec_reason"] == "TODO: record the specification decision"
    assert result["reviewed"] is False
    if body.startswith("## Why"):
        assert result["scope"] == "First paragraph.\nStill first."


def test_new_work_overrides_and_refusals_do_not_overwrite(tmp_path):
    from ai_dlc.work.workflow import WorkService

    tracker = Tracker()
    tracker.items = [{"title": "Issue", "body": "Issue scope."}]
    service = WorkService(
        tmp_path,
        {"roles": {"tracker": "fake"}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    result = service.new(
        "demo",
        tracker_reference="68",
        title="Override",
        scope="Explicit",
        acceptance=["A"],
        requires_spec=False,
        spec_reason="Configuration only",
    )
    assert result["title"] == "Override" and result["scope"] == "Explicit"
    assert result["requires_spec"] is False and result["acceptance"] == ["A"]
    path = tmp_path / ".ai-dlc/work/demo.toml"
    before = path.read_bytes()
    for work_id in ["demo", "../escape", ""]:
        with pytest.raises(ValueError):
            service.new(work_id, tracker_reference="68")
    assert path.read_bytes() == before
    with pytest.raises(ValueError):
        service.new("invalid", title="", scope="S", acceptance=[])
    assert not (path.parent / "invalid.toml").exists()


def test_new_work_refuses_symlink_and_configuration_change_during_read(tmp_path):
    from ai_dlc.work.workflow import WorkService

    project = tmp_path / "ai-dlc.toml"
    project.write_text('schema=4\n[roles]\ntracker="fake"\n')
    tracker = Tracker()
    service = WorkService(
        tmp_path,
        {"schema": 4, "roles": {"tracker": "fake"}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    directory = tmp_path / ".ai-dlc/work"
    directory.mkdir(parents=True)
    (directory / "linked.toml").symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="symlink"):
        service.new("linked", title="T", scope="S", acceptance=["A"])

    def read_with_drift(operation, payload):
        project.write_text('schema=4\n[roles]\ntracker="other"\n')
        return {"title": "Issue", "body": "Scope"}

    tracker.invoke = read_with_drift
    with pytest.raises(ValueError, match="configuration changed"):
        service.new("drift", tracker_reference="68")
    assert not (directory / "drift.toml").exists()


def archive_service(tmp_path):
    service, scm, git = started_service(tmp_path)
    change = tmp_path / "openspec/changes/one"
    (change / "specs/demo").mkdir(parents=True)
    (change / "proposal.md").write_text("Proposal")
    (change / "tasks.md").write_text("- [x] Implement")
    (change / "specs/demo/spec.md").write_text("Delta")
    canonical = tmp_path / "openspec/specs/demo/spec.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("Original")
    record = service.load("one")
    record["requires_spec"] = True
    record["artifacts"].update(spec="openspec/changes/one", plan="openspec/changes/one/tasks.md")
    service.save(record)
    git("add", "openspec", ".ai-dlc/work/one.toml")
    git("commit", "-m", "specification")
    return service, scm, git


def fake_archive_cli(tmp_path, monkeypatch):
    import json
    import shutil
    import subprocess

    run = subprocess.run
    calls = []

    def execute(args, **kwargs):
        if args[0] != "openspec":
            return run(args, **kwargs)
        calls.append(args)
        source = tmp_path / "openspec/changes/one"
        target = tmp_path / "openspec/changes/archive/2026-09-14-one"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, target)
        (tmp_path / "openspec/specs/demo/spec.md").write_text("Promoted")
        return subprocess.CompletedProcess(
            args,
            0,
            json.dumps(
                {
                    "archive": {
                        "change": "one",
                        "archivedAs": target.name,
                        "path": str(target),
                        "specsUpdated": True,
                    }
                }
            ),
            "",
        )

    monkeypatch.setattr(subprocess, "run", execute)
    return calls


def test_archive_repoints_and_commits_only_its_files(tmp_path, monkeypatch):
    from ai_dlc.work.workflow import validate_work_records

    service, _, git = archive_service(tmp_path)
    (tmp_path / "other.txt").write_text("Unrelated staged content")
    git("add", "other.txt")
    calls = fake_archive_cli(tmp_path, monkeypatch)
    result = service.archive("one")
    assert calls == [["openspec", "archive", "one", "--yes", "--json"]]
    assert result["promoted_specs"] == ["openspec/specs/demo/spec.md"]
    record = service.load("one")
    assert record["artifacts"]["spec"] == "openspec/changes/archive/2026-09-14-one"
    assert record["artifacts"]["plan"] == "openspec/changes/archive/2026-09-14-one/tasks.md"
    assert git("log", "-1", "--format=%s") == "docs(specs): archive one"
    assert git("diff", "--cached", "--name-only") == "other.txt"
    assert "other.txt" not in git("show", "--name-only", "--format=", "HEAD")
    assert validate_work_records(tmp_path)["valid"]


def test_archive_refuses_dirty_promoted_spec_or_foreign_change(tmp_path, monkeypatch):
    service, _, _ = archive_service(tmp_path)
    calls = fake_archive_cli(tmp_path, monkeypatch)
    (tmp_path / "openspec/specs/demo/spec.md").write_text("Unrelated local change")
    with pytest.raises(ValueError, match="dirty"):
        service.archive("one")
    assert not calls
    record = service.load("one")
    record["artifacts"]["spec"] = "openspec/changes/someone-else"
    service.save(record)
    with pytest.raises(ValueError, match="own active"):
        service.archive("one")
    assert not calls


def test_specification_status_is_local_and_pr_warns(tmp_path):
    service, scm, _ = archive_service(tmp_path)

    def no_tracker(*args):
        raise AssertionError("Status cannot call the network")

    original = scm.invoke
    scm.invoke = no_tracker
    assert service.status("one")["specification"] == "active change, archive before merge"
    record = service.load("one")
    record["artifacts"]["spec"] = "openspec/changes/archive/2026-09-14-one"
    service.save(record)
    assert service.status("one")["specification"] == "archived"
    record["artifacts"]["spec"] = "openspec/changes/one"
    service.save(record)
    scm.invoke = original
    assert "archive before merge" in service.pr("one")["specification"]


def test_unarchived_specification_gate_names_the_remedy(tmp_path):
    from ai_dlc.providers.openspec import OpenSpecProvider

    service, _, _ = archive_service(tmp_path)
    with pytest.raises(ValueError, match="Run `ai-dlc work archive one`") as caught:
        OpenSpecProvider(tmp_path).current(service.load("one"))
    assert "work link one pr <url>" in str(caught.value)


def test_archive_invalid_json_does_not_repoint_record(tmp_path, monkeypatch):
    import subprocess

    service, _, _ = archive_service(tmp_path)
    before = (tmp_path / ".ai-dlc/work/one.toml").read_bytes()
    original = subprocess.run

    def invalid(args, **kwargs):
        if args[0] == "openspec":
            return subprocess.CompletedProcess(args, 0, "invalid JSON", "")
        return original(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", invalid)
    with pytest.raises(RuntimeError, match="inspect the active change"):
        service.archive("one")
    assert (tmp_path / ".ai-dlc/work/one.toml").read_bytes() == before


def test_archive_refuses_symlinked_source_before_invocation(tmp_path, monkeypatch):
    service, _, _ = archive_service(tmp_path)
    source = tmp_path / "openspec/changes/one"
    (source / "external").symlink_to(tmp_path / "elsewhere")
    calls = fake_archive_cli(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="symlink"):
        service.archive("one")
    assert calls == []


def test_work_status_cli_is_offline_and_shows_archive_warning(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from ai_dlc.cli import app
    from ai_dlc.work.workflow import WorkService

    service, _, _ = archive_service(tmp_path)
    monkeypatch.setattr(WorkService, "from_project", lambda *args, **kwargs: service)
    result = CliRunner().invoke(app, ["work", "status", "one", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "active change, archive before merge" in result.output
