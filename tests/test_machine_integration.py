import json
import os
import shutil
import stat
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_dlc.config import digest, resolve_files
from ai_dlc.enrollment import EnrollmentPaths, read_lock
from ai_dlc.machine import MachineManager
from ai_dlc.profile_source import verify_cached_profile

PROFILE = """\
schema = 4
profile_id = "portable-development"

[modules]
include = ["python"]

[credentials.linear-sandbox]
description = "Linear sandbox access"
required_by = ["provider.linear-sandbox"]

[[agents.servers]]
id = "notes"
command = "notes-mcp"
args = ["serve"]
env = ["NOTES_ACCESS_TOKEN"]
"""

UPDATED_PROFILE = PROFILE.replace('include = ["python"]', 'include = ["node"]')
LEGACY_PROFILE = PROFILE.replace('profile_id = "portable-development"\n\n', "")
SENTINEL_A = "synthetic-machine-a-value-never-persist"
SENTINEL_B = "synthetic-machine-b-value-never-persist"


def _machine(
    tmp_path: Path,
    name: str,
    git_environment: dict[str, str],
    credentials: dict[str, str] | None = None,
):
    root = tmp_path / name
    home = root / "home"
    tools = root / "tools"
    home.mkdir(parents=True)
    tools.mkdir(parents=True)
    for tool in ["brew", "mise", "notes-mcp"]:
        path = tools / tool
        path.write_text("test executable; execution is replaced at the process boundary\n")
        path.chmod(0o700)
    environment = {
        **git_environment,
        "PATH": f"{git_environment['PATH']}:{tools}",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(root / "xdg" / "config"),
        "XDG_CACHE_HOME": str(root / "xdg" / "cache"),
        "XDG_STATE_HOME": str(root / "xdg" / "state"),
        "XDG_DATA_HOME": str(root / "xdg" / "data"),
        "AI_DLC_BOOTSTRAP_HOME": str(root / "bootstrap"),
        "SHELL": "/bin/zsh",
        **(credentials or {}),
    }
    paths = EnrollmentPaths.from_environment(home=home, environ=environment)
    return root, MachineManager(home=home, environ=environment, paths=paths), paths


def _bind(paths: EnrollmentPaths, machine_id: str, variable: str) -> None:
    paths.machine_file(machine_id).write_text(
        "schema = 4\n"
        "[credentials.linear-sandbox]\n"
        'source = "environment"\n'
        f'variable = "{variable}"\n'
    )


def _replace_external_execution(monkeypatch: pytest.MonkeyPatch, *, fail: bool = False) -> None:
    import ai_dlc.provision

    def execute(*args, **kwargs):
        del args, kwargs
        if fail:
            raise RuntimeError("synthetic package manager failure")

    monkeypatch.setattr(ai_dlc.provision, "subprocess", SimpleNamespace(run=execute))


def _returned_without_sentinels(results: list[object]) -> None:
    serialized = json.dumps(results, sort_keys=True, default=str)
    assert SENTINEL_A not in serialized
    assert SENTINEL_B not in serialized


def _trees_without_sentinels(*roots: Path) -> None:
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file():
                content = path.read_bytes()
                assert SENTINEL_A.encode() not in content, path
                assert SENTINEL_B.encode() not in content, path


def _tree_snapshot(root: Path) -> dict[str, tuple[object, ...]]:
    snapshot: dict[str, tuple[object, ...]] = {}
    for path in [root, *sorted(root.rglob("*"))]:
        relative = "." if path == root else path.relative_to(root).as_posix()
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            snapshot[relative] = ("symlink", mode, os.readlink(path))
        elif stat.S_ISDIR(metadata.st_mode):
            snapshot[relative] = ("directory", mode)
        elif stat.S_ISREG(metadata.st_mode):
            snapshot[relative] = ("file", mode, path.read_bytes())
        else:
            snapshot[relative] = ("other", mode, metadata.st_rdev)
    return snapshot


def test_two_isolated_machines_share_a_profile_but_not_bindings_or_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, local_git_profile
):
    """Would fail on shared XDG state, lost provenance, online planning, or secret persistence."""
    source = local_git_profile(PROFILE)
    root_a, machine_a, paths_a = _machine(
        tmp_path,
        "machine-a",
        source.environment,
        {"LINEAR_A_TOKEN": SENTINEL_A, "NOTES_ACCESS_TOKEN": SENTINEL_A},
    )
    root_b, machine_b, paths_b = _machine(
        tmp_path,
        "machine-b",
        source.environment,
        {"LINEAR_B_TOKEN": SENTINEL_B, "NOTES_ACCESS_TOKEN": SENTINEL_B},
    )
    results: list[object] = []

    results.append(machine_a.enroll(source.source, "portable-development", "machine-a", apply=True))
    results.append(machine_b.enroll(source.source, "portable-development", "machine-b", apply=True))
    _bind(paths_a, "machine-a", "LINEAR_A_TOKEN")
    _bind(paths_b, "machine-b", "LINEAR_B_TOKEN")

    lock_a = read_lock(paths_a)
    lock_b = read_lock(paths_b)
    assert lock_a is not None and lock_b is not None
    assert lock_a.resolved_commit == lock_b.resolved_commit == source.commit
    assert lock_a.content_sha256 == lock_b.content_sha256
    assert results[0]["profile"]["portable"] is True
    assert results[1]["profile"]["portable"] is True
    profile_a = verify_cached_profile(lock_a, paths_a)
    profile_b = verify_cached_profile(lock_b, paths_b)
    resolved_a = resolve_files(personal=profile_a, machine=paths_a.machine_file("machine-a"))
    resolved_b = resolve_files(personal=profile_b, machine=paths_b.machine_file("machine-b"))
    assert digest(tomllib.loads(profile_a.read_text())) == digest(
        tomllib.loads(profile_b.read_text())
    )
    assert resolved_a.sources["profile_id"] == resolved_b.sources["profile_id"] == "personal"
    assert resolved_a.sources["credentials.linear-sandbox.variable"] == "machine"
    assert resolved_b.sources["credentials.linear-sandbox.variable"] == "machine"
    assert resolved_a.values["credentials"]["linear-sandbox"]["variable"] == "LINEAR_A_TOKEN"
    assert resolved_b.values["credentials"]["linear-sandbox"]["variable"] == "LINEAR_B_TOKEN"

    before_a = _tree_snapshot(root_a)
    plan_a = machine_a.plan()
    assert _tree_snapshot(root_a) == before_a
    before_b = _tree_snapshot(root_b)
    plan_b = machine_b.plan()
    assert _tree_snapshot(root_b) == before_b
    results.extend([plan_a, plan_b])

    _replace_external_execution(monkeypatch)
    results.extend([machine_a.apply(), machine_b.apply()])
    for machine, variable in [(machine_a, "LINEAR_A_TOKEN"), (machine_b, "LINEAR_B_TOKEN")]:
        claude = json.loads((machine.home / ".claude.json").read_text())
        codex = tomllib.loads((machine.home / ".codex/config.toml").read_text())
        assert claude["mcpServers"]["notes"]["env"] == {
            "NOTES_ACCESS_TOKEN": "${NOTES_ACCESS_TOKEN}"
        }
        assert codex["mcp_servers"]["notes"]["env_vars"] == ["NOTES_ACCESS_TOKEN"]
        status = machine.status()
        results.append(status)
        assert status["credentials"][0]["variable"] == variable

    shutil.rmtree(source.repository)
    results.extend([machine_a.status(), machine_b.status(), machine_a.plan(), machine_b.plan()])
    assert results[-4]["cache"] == results[-3]["cache"] == "healthy"
    _returned_without_sentinels(results)
    _trees_without_sentinels(root_a, root_b)


def test_failed_sync_keeps_the_old_lock_and_retry_activates_the_cached_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, local_git_profile
):
    """Would fail if reconciliation activated early or a cached candidate could not be retried."""
    source = local_git_profile(PROFILE)
    _, machine, paths = _machine(
        tmp_path,
        "transaction-machine",
        source.environment,
        {"LINEAR_A_TOKEN": SENTINEL_A},
    )
    machine.enroll(source.source, "portable-development", "machine-a", apply=True)
    _bind(paths, "machine-a", "LINEAR_A_TOKEN")
    old_lock = paths.lock_file.read_bytes()
    new_commit = source.advance(UPDATED_PROFILE)

    _replace_external_execution(monkeypatch)
    preview = machine.sync()
    assert preview["lock"]["resolved_commit"] == new_commit
    assert paths.lock_file.read_bytes() == old_lock

    _replace_external_execution(monkeypatch, fail=True)
    with pytest.raises(RuntimeError, match="reconciliation.*active lock preserved") as failure:
        machine.sync(apply=True)
    assert paths.lock_file.read_bytes() == old_lock

    _replace_external_execution(monkeypatch)
    applied = machine.sync(apply=True)
    assert read_lock(paths).resolved_commit == new_commit
    assert applied["reconciliation"]["agent_configuration"]["applied"] is True
    _returned_without_sentinels([preview, str(failure.value), applied])


def test_cache_tampering_is_scoped_to_one_machine(tmp_path: Path, local_git_profile):
    """Would fail if cache integrity were skipped or machine caches were shared."""
    source = local_git_profile(PROFILE)
    _, machine_a, paths_a = _machine(tmp_path, "cache-machine-a", source.environment)
    _, machine_b, _ = _machine(tmp_path, "cache-machine-b", source.environment)
    machine_a.enroll(source.source, "portable-development", "machine-a", apply=True)
    machine_b.enroll(source.source, "portable-development", "machine-b", apply=True)
    lock_a = read_lock(paths_a)
    assert lock_a is not None
    verify_cached_profile(lock_a, paths_a).write_text("tampered\n")

    status_a = machine_a.status()
    status_b = machine_b.status()

    assert status_a["cache"] == "corrupt"
    assert status_a["ready"] is False
    assert status_b["cache"] == "healthy"


def test_authored_mcp_collision_blocks_sync_before_lock_change_and_preserves_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, local_git_profile
):
    """Would fail if sync overwrote an authored MCP server or changed its lock first."""
    source = local_git_profile(PROFILE)
    _, machine, paths = _machine(tmp_path, "ownership-machine", source.environment)
    machine.enroll(source.source, "portable-development", "machine-a", apply=True)
    _bind(paths, "machine-a", "LINEAR_A_TOKEN")
    authored_path = machine.home / ".claude.json"
    authored_path.write_text(json.dumps({"mcpServers": {"notes": {"command": "authored"}}}))
    authored = authored_path.read_bytes()
    old_lock = paths.lock_file.read_bytes()
    source.advance(UPDATED_PROFILE)
    _replace_external_execution(monkeypatch)

    with pytest.raises(RuntimeError, match="candidate planning.*active lock preserved"):
        machine.sync(apply=True)

    assert paths.lock_file.read_bytes() == old_lock
    assert authored_path.read_bytes() == authored


def test_fetch_failure_keeps_offline_status_healthy_and_reports_the_sync_step(
    tmp_path: Path, local_git_profile
):
    """Would fail if sync invalidated the active cache or hid the failed source step."""
    source = local_git_profile(PROFILE)
    _, machine, paths = _machine(
        tmp_path,
        "offline-machine",
        source.environment,
        {"LINEAR_A_TOKEN": SENTINEL_A},
    )
    machine.enroll(source.source, "portable-development", "machine-a", apply=True)
    _bind(paths, "machine-a", "LINEAR_A_TOKEN")
    old_lock = paths.lock_file.read_bytes()
    shutil.rmtree(source.repository)

    status = machine.status()
    with pytest.raises(
        RuntimeError, match="candidate resolution.*active lock preserved"
    ) as failure:
        machine.sync()

    assert status["cache"] == "healthy"
    assert status["ready"] is True
    assert paths.lock_file.read_bytes() == old_lock
    _returned_without_sentinels([status, str(failure.value)])


def test_legacy_profile_file_migrates_and_syncs_for_the_compatibility_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, local_git_profile
):
    """Would fail if sync forgot an explicitly selected legacy profile path or identity mode."""
    source = local_git_profile(LEGACY_PROFILE, profile_file="profiles/personal.toml")
    _, machine, paths = _machine(tmp_path, "legacy-machine", source.environment)
    enrolled = machine.migrate(
        source.source,
        "profiles/personal.toml",
        "portable-development",
        "legacy-machine",
        apply=True,
    )
    _bind(paths, "legacy-machine", "LINEAR_A_TOKEN")
    second_commit = source.advance(
        LEGACY_PROFILE.replace('include = ["python"]', 'include = ["node"]')
    )
    _replace_external_execution(monkeypatch)

    synced = machine.sync(apply=True)

    assert enrolled["lock"]["profile_file"] == "profiles/personal.toml"
    assert synced["lock"]["profile_file"] == "profiles/personal.toml"
    assert read_lock(paths).resolved_commit == second_commit
