from __future__ import annotations

import copy
import tomllib
from pathlib import Path

import pytest
import tomli_w
from fixtures.git import git


def initialize_hook_project(root: Path, policy: str | None) -> str:
    root.mkdir()
    policy_line = "" if policy is None else f'bound_push_policy = "{policy}"\n'
    (root / "ai-dlc.toml").write_text(
        "schema = 4\n"
        '[project]\nname = "Hook fixture"\n'
        '[roles]\nspecs = "openspec"\ntracker = "github-issues"\n'
        'knowledge = "obsidian"\nscm = "github"\ndeploy = "none"\n'
        f"[agents]\n{policy_line}"
        '[scm]\nrepository = "example/project"\ntarget_branch = "main"\n'
        '[providers.github-issues]\nkind = "github-issues"\nhost = "github.com"\n'
    )
    git(root, "init", "--initial-branch=topic", "--template=")
    git(root, "config", "user.name", "Hook Fixture")
    git(root, "config", "user.email", "hook@example.test")
    (root / "tracked.txt").write_text("fixture\n")
    git(root, "add", "--", "tracked.txt", "ai-dlc.toml")
    git(root, "commit", "-m", "initialize hook fixture")
    return "topic"


def write_work_record(root: Path, work_id: str, **changes) -> Path:
    from ai_dlc.config import resolve_runtime
    from ai_dlc.work.workflow import resolve_work

    raw = {
        "schema": 1,
        "id": work_id,
        "title": f"Work {work_id}",
        "scope": "Exercise the bound-operation hook",
        "requires_spec": False,
        "spec_reason": "The fixture does not need a specification",
        "acceptance": ["The hook decision is verified"],
        "reviewed": True,
        "depends_on": [],
        "requirements": [],
        "providers": {},
        "artifacts": {"branch": "topic", "tracker": "177"},
        "bindings": {},
    }
    for key, value in changes.items():
        raw[key] = copy.deepcopy(value)
    raw = resolve_work(raw, resolve_runtime(root).values, work_id)
    path = root / ".ai-dlc/work" / f"{work_id}.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(raw))
    return path


def hook_payload(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _inventory_snapshot(root: Path) -> dict[str, tuple[str, bytes | str]]:
    directory = root / ".ai-dlc/work"
    if not directory.exists() and not directory.is_symlink():
        return {}
    if directory.is_symlink():
        return {".": ("symlink", str(directory.readlink()))}
    if not directory.is_dir():
        return {".": ("non-directory", b"")}
    snapshot = {}
    for entry in sorted(directory.iterdir(), key=lambda item: item.name):
        if entry.is_symlink():
            snapshot[entry.name] = ("symlink", str(entry.readlink()))
        elif entry.is_file():
            snapshot[entry.name] = ("file", entry.read_bytes())
        elif entry.is_dir():
            snapshot[entry.name] = ("directory", b"")
        else:
            snapshot[entry.name] = ("non-regular", b"")
    return snapshot


def invoke_hook(root: Path, command: str) -> dict:
    from ai_dlc.harness.hooks import handle_hook

    before = _inventory_snapshot(root)
    response = handle_hook(root, "pre-tool", hook_payload(command))
    assert _inventory_snapshot(root) == before
    assert not list(root.parent.rglob("operations.sqlite3"))
    return response


@pytest.fixture(autouse=True)
def forbid_provider_and_operation_services(monkeypatch):
    from ai_dlc.work import workflow

    def forbidden(*args, **kwargs):
        raise AssertionError("the offline hook must not construct provider or operation services")

    monkeypatch.setattr(workflow, "Registry", forbidden)
    monkeypatch.setattr(workflow, "WorkService", forbidden)
    monkeypatch.setattr(workflow, "Journal", forbidden)


@pytest.mark.parametrize("command", ["git push origin topic", "gh pr create --title change"])
@pytest.mark.parametrize("policy", [None, "all-branches"])
def test_all_branches_policy_denies_unbound_operations(tmp_path, policy, command):
    root = tmp_path / "project"
    initialize_hook_project(root, policy)

    response = invoke_hook(root, command)

    assert response["decision"] == "deny"
    assert "all-branches" in response["reason"]
    assert "work start" in response["reason"]


@pytest.mark.parametrize("command", ["git push origin topic", "gh pr create --title change"])
def test_tracked_branches_policy_allows_a_proven_unbound_operation(tmp_path, command):
    root = tmp_path / "project"
    initialize_hook_project(root, "tracked-branches")

    response = invoke_hook(root, command)

    assert response["decision"] == "allow"
    assert response["coverage"] == "bound-operation"
    assert "tracked-branches" in response["reason"]
    assert "no local work record" in response["reason"]


@pytest.mark.parametrize("policy", [None, "all-branches", "tracked-branches"])
@pytest.mark.parametrize("record_count", [1, 2])
def test_every_valid_matching_record_allows_the_bound_operation(tmp_path, policy, record_count):
    root = tmp_path / "project"
    initialize_hook_project(root, policy)
    for index in range(record_count):
        write_work_record(root, f"valid-{index}")

    response = invoke_hook(root, "git push origin topic")

    assert response == {"decision": "allow", "coverage": "bound-operation"}


@pytest.mark.parametrize("policy", ["all-branches", "tracked-branches"])
@pytest.mark.parametrize(
    "fault",
    ["unreviewed", "missing-tracker", "blank-tracker", "missing-field", "binding-drift"],
)
def test_any_invalid_matching_record_denies_and_names_the_record(tmp_path, policy, fault):
    root = tmp_path / "project"
    initialize_hook_project(root, policy)
    if fault == "binding-drift":
        write_work_record(root, "z-invalid")
        project = root / "ai-dlc.toml"
        project.write_text(project.read_text().replace("example/project", "example/changed"))
        write_work_record(root, "a-valid")
    else:
        write_work_record(root, "a-valid")
        if fault == "unreviewed":
            write_work_record(root, "z-invalid", reviewed=False)
        elif fault == "missing-tracker":
            write_work_record(root, "z-invalid", artifacts={"branch": "topic"})
        elif fault == "blank-tracker":
            write_work_record(root, "z-invalid", artifacts={"branch": "topic", "tracker": ""})
        else:
            path = write_work_record(root, "z-invalid")
            raw = tomllib.loads(path.read_text())
            del raw["scope"]
            path.write_text(tomli_w.dumps(raw))

    response = invoke_hook(root, "git push origin topic")

    assert response["decision"] == "deny"
    assert "z-invalid" in response["reason"]
    expected = {
        "unreviewed": "reviewed",
        "missing-tracker": "tracker",
        "blank-tracker": "tracker",
        "missing-field": "scope",
        "binding-drift": "binding drift",
    }
    assert expected[fault] in response["reason"].lower()


def test_parseable_record_without_a_branch_is_a_determinate_nonmatch(tmp_path):
    root = tmp_path / "project"
    initialize_hook_project(root, "tracked-branches")
    path = write_work_record(root, "other", artifacts={"tracker": "177"})
    raw = tomllib.loads(path.read_text())
    del raw["scope"]
    path.write_text(tomli_w.dumps(raw))

    response = invoke_hook(root, "git push origin topic")

    assert response["decision"] == "allow"
    assert "tracked-branches" in response["reason"]


@pytest.mark.parametrize("branch", ["", "   ", 7])
def test_malformed_present_branch_denies_lightweight_operation(tmp_path, branch):
    root = tmp_path / "project"
    initialize_hook_project(root, "tracked-branches")
    directory = root / ".ai-dlc/work"
    directory.mkdir(parents=True)
    (directory / "malformed.toml").write_text(tomli_w.dumps({"artifacts": {"branch": branch}}))

    response = invoke_hook(root, "git push origin topic")

    assert response["decision"] == "deny"
    assert "malformed" in response["reason"]
    assert "branch" in response["reason"]


def test_nonregular_toml_inventory_entry_denies_lightweight_operation(tmp_path):
    root = tmp_path / "project"
    initialize_hook_project(root, "tracked-branches")
    (root / ".ai-dlc/work/unreadable.toml").mkdir(parents=True)

    response = invoke_hook(root, "git push origin topic")

    assert response["decision"] == "deny"
    assert "inventory" in response["reason"]
    assert "unreadable.toml" in response["reason"]


def test_path_unsafe_toml_inventory_entry_denies_lightweight_operation(tmp_path):
    root = tmp_path / "project"
    initialize_hook_project(root, "tracked-branches")
    outside = root / "outside.toml"
    outside.write_text('artifacts = { branch = "elsewhere" }\n')
    directory = root / ".ai-dlc/work"
    directory.mkdir(parents=True)
    (directory / "unsafe.toml").symlink_to(outside)

    response = invoke_hook(root, "git push origin topic")

    assert response["decision"] == "deny"
    assert "inventory" in response["reason"]
    assert "unsafe.toml" in response["reason"]


def test_invalid_policy_denies_before_lightweight_allowance(tmp_path):
    root = tmp_path / "project"
    initialize_hook_project(root, "sometimes")

    response = invoke_hook(root, "git push origin topic")

    assert response["decision"] == "deny"
    assert "policy" in response["reason"]
    assert "all-branches or tracked-branches" in response["reason"]


def test_detached_head_denies_before_lightweight_allowance(tmp_path):
    root = tmp_path / "project"
    initialize_hook_project(root, "tracked-branches")
    git(root, "checkout", "--detach")

    response = invoke_hook(root, "git push origin topic")

    assert response["decision"] == "deny"
    assert "current branch" in response["reason"]


def test_destructive_denial_precedes_tracked_branches_policy(tmp_path):
    from ai_dlc.harness.hooks import classify_command

    root = tmp_path / "project"
    initialize_hook_project(root, "tracked-branches")
    for command in [
        "git reset --hard HEAD~1",
        "git clean -dfx",
        "git push --force origin topic",
        "git push -f origin topic",
        "git push --delete origin topic",
    ]:
        assert classify_command(command) == "destructive"
        response = invoke_hook(root, command)
        assert response["decision"] == "deny"
        assert "Destructive operation denied" in response["reason"]


def test_ordinary_hook_operation_and_stop_reminder_do_not_loop(tmp_path):
    from ai_dlc.harness.hooks import handle_hook

    payload = hook_payload("git status")
    assert handle_hook(tmp_path, "pre-tool", payload)["decision"] == "allow"
    payload["session_id"] = "s1"
    assert handle_hook(tmp_path, "stop", payload)["reminder"]
    assert not handle_hook(tmp_path, "stop", payload)["reminder"]


def test_required_unsupported_path_is_reported():
    from ai_dlc.harness.hooks import classify_command

    assert classify_command("git -C elsewhere push") == "unsupported"
    assert classify_command("gh pr create --title 'hi'") == "bound-operation"
    assert classify_command("echo 'git push'") == "ordinary"


def test_specification_edit_warning(tmp_path):
    from ai_dlc.harness.hooks import handle_hook

    response = handle_hook(
        tmp_path,
        "pre-tool",
        {"tool_name": "Edit", "tool_input": {"file_path": str(tmp_path / "docs/specs/feature.md")}},
    )
    assert response["decision"] == "allow"
    assert "warning" in response
