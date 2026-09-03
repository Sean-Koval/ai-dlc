import copy

import pytest


@pytest.fixture
def trusted_scm(monkeypatch):
    from ai_dlc import workflow

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
    from ai_dlc.workflow import WorkService

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


def test_publish_reconciles_uncertain_creation(tmp_path):
    from ai_dlc.workflow import WorkService

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
    from ai_dlc.workflow import WorkService

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
    from ai_dlc.workflow import WorkService

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

    from ai_dlc.workflow import WorkService

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

    monkeypatch.setitem(sys.modules, "ai_dlc.knowledge", types.SimpleNamespace(Knowledge=Knowledge))
    service.config["paths"] = {"vault": str(tmp_path / "vault")}
    assert service.finish("one", handoff="Done")["status"] == "completed"
    assert tracker.closed == 1


def test_reopened_remote_cannot_be_completed_from_local_record(tmp_path, trusted_scm):
    from ai_dlc.workflow import WorkService

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


def test_unreviewed_work_cannot_publish(tmp_path):
    from ai_dlc.workflow import WorkService

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
    from ai_dlc.workflow import WorkService

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
    from ai_dlc.workflow import WorkService

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
        (destination / "receipt.json").write_text(json.dumps(receipt))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)
    service = WorkService(
        tmp_path, config, state_path=tmp_path / "state", registry=Registry(tracker)
    )
    service.publish("one")
    service.link("one", "pr", "https://github.com/a/b/pull/12")
    result = service.finish("one")
    assert result["status"] == ("completed" if fault is None else "blocked")
    assert tracker.closed == (1 if fault is None else 0)
    if fault is None:
        assert len(downloads) == 1


def test_work_uses_pinned_specification_provider(tmp_path, trusted_scm):
    from ai_dlc.providers import Registry as ProviderRegistry
    from ai_dlc.workflow import WorkService

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
    from ai_dlc.workflow import WorkService

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
    from ai_dlc.workflow import WorkService

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
    from ai_dlc.workflow import WorkService

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


def test_empty_gates_cannot_bypass_merge_and_ci(tmp_path):
    from ai_dlc.workflow import WorkService

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
    from ai_dlc.workflow import WorkService

    work(tmp_path)
    git = init_git(tmp_path)
    tracker = Tracker()
    service = WorkService(
        tmp_path,
        {"providers": {"fake": {"kind": "github-issues"}}},
        state_path=tmp_path / "state",
        registry=Registry(tracker),
    )
    result = service.start("one")
    assert result["branch"] == "work/one"
    assert git("branch", "--show-current") == "work/one"
    assert result["tracker_transition"]["supported"] is False
    assert service.load("one")["artifacts"]["branch"] == "work/one"
    assert service.start("one")["branch"] == "work/one"


def test_start_preserves_dirty_work_and_linked_branch(tmp_path):
    from ai_dlc.workflow import WorkService

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
    from ai_dlc.workflow import WorkService

    work(tmp_path)
    config = {"paths": {"vault": str(tmp_path / "first-vault")}}
    service = WorkService(
        tmp_path, config, state_path=tmp_path / "state", registry=Registry(Tracker())
    )
    service.publish("one")
    config["paths"]["vault"] = str(tmp_path / "different-vault")
    assert service.load("one")["id"] == "one"


def test_rebound_mapped_tracker_reuses_item_and_gets_new_journal_identity(tmp_path):
    from ai_dlc.workflow import WorkService

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
    from ai_dlc.knowledge import Knowledge
    from ai_dlc.workflow import WorkService

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
