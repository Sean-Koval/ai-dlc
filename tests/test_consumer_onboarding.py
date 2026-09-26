"""Consumer plans recommend explicit target operations without performing them."""

from __future__ import annotations

import builtins
import hashlib
import importlib
import io
import json
import os
import socket
import subprocess
import tempfile
from pathlib import Path

import pytest
from fixtures.enrollment import write_enrollment

from ai_dlc.environment.enrollment import EnrollmentPaths
from ai_dlc.harness.agents import managed_section


@pytest.fixture
def environment(tmp_path, monkeypatch):
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr("platform.machine", lambda: "arm64")
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("ai-dlc", "sh", "python"):
        tool = bin_dir / name
        tool.write_text("#!/bin/sh\nexit 99\n")
        tool.chmod(0o755)
    return {
        "HOME": str(home),
        "PATH": str(bin_dir),
        "SHELL": "/bin/zsh",
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_STATE_HOME": str(home / "state"),
        "TMPDIR": str(home / "tmp"),
    }


@pytest.fixture
def target(tmp_path):
    root = tmp_path / "downstream repo"
    root.mkdir()
    return root


def plan(root, environment, **selection):
    module = importlib.import_module("ai_dlc.setup.onboarding")
    return module.plan_onboarding(root, environ=environment, **selection)


def adopted(root, *, checks=True, client="codex"):
    text = f'schema = 4\n[roles]\nagent-client = ["{client}"]\n'
    if checks:
        text += (
            '[checks]\nrequired = ["acceptance"]\n[checks.commands]\n'
            'acceptance = { argv = ["python", "acceptance.py"] }\n'
        )
    (root / "ai-dlc.toml").write_text(text)


def action(result, name):
    return next(item for item in result["actions"] if item["id"] == name)


def codes(result):
    return {item["code"] for item in result["findings"]}


def test_fresh_target_requires_explicit_clients(target, environment):
    result = plan(target, environment)
    assert result["schema"] == 1
    assert result["state"] == "input-required"
    assert result["clients"] == []
    assert "client-selection-required" in codes(result)
    assert not any(item["available"] for item in result["actions"])


def test_generic_adoption_does_not_infer_python_or_personal_providers(target, environment):
    (target / "pyproject.toml").write_text('[project]\nname = "downstream"\n')
    result = plan(target, environment, agent_clients=["codex"])
    preview = action(result, "adopt-preview")
    assert preview["argv"] == [
        "ai-dlc",
        "project",
        "adopt",
        "--root",
        str(target),
        "--preset",
        "generic",
        "--capability",
        "agent-client",
        "--agent-client",
        "codex",
    ]
    assert preview["available"]
    assert preview["effects"]
    assert action(result, "adopt-apply")["argv"] == [*preview["argv"], "--apply"]
    assert action(result, "adopt-apply")["requires_review"]
    assert "adopt-preview" in action(result, "adopt-apply")["depends_on"]
    assert result["enrollment"]["status"] == "unselected"
    assert not any(item["stage"] == "machine" for item in result["actions"])
    assert result["qualification"] == "not-assessed"
    assert "target-check-required" in codes(result)
    assert action(result, "target-check")["argv"] == []
    assert "linear" not in json.dumps(result)


def test_adopted_project_uses_target_checks_and_ignores_ambient_profile(target, environment):
    adopted(target)
    paths = EnrollmentPaths.from_environment(Path(environment["HOME"]), environment)
    paths.lock_file.parent.mkdir(parents=True)
    paths.lock_file.write_text("invalid ambient enrollment must not be read")
    result = plan(target, environment)
    assert result["state"] == "actionable"
    assert result["clients"] == ["codex"]
    assert not any(item["id"].startswith("adopt") for item in result["actions"])
    check = action(result, "target-check")
    assert check["argv"] == ["ai-dlc", "project", "check", "--root", str(target), "--required"]
    assert "not observed" in " ".join(item["reason"] for item in result["findings"])
    assert "passed" not in result


@pytest.mark.parametrize(
    "selection",
    [
        {"source": "https://example.test/profile.git"},
        {"ref": "main"},
        {"profile_id": "work"},
        {"machine_id": "laptop"},
    ],
)
def test_partial_enrollment_does_not_invent_values(target, environment, selection):
    adopted(target)
    result = plan(target, environment, **selection)
    assert result["state"] == "input-required"
    assert "source-selection-incomplete" in codes(result)
    assert not any(item["available"] for item in result["actions"])


def test_explicit_enrollment_orders_preview_and_reviewed_apply(target, environment):
    adopted(target)
    result = plan(
        target,
        environment,
        source="https://example.test/profiles.git",
        ref="main",
        profile_id="work",
        machine_id="laptop",
    )
    preview = action(result, "enroll-preview")
    assert preview["argv"] == [
        "ai-dlc",
        "machine",
        "enroll",
        "https://example.test/profiles.git",
        "--ref",
        "main",
        "--profile-id",
        "work",
        "--machine-id",
        "laptop",
    ]
    assert action(result, "enroll-apply")["requires_review"]
    assert action(result, "machine-preview")["depends_on"] == ["enroll-apply"]
    assert "cache" in " ".join(preview["effects"])


def test_only_matching_verified_enrollment_satisfies_selection(target, environment):
    adopted(target)
    paths = EnrollmentPaths.from_environment(Path(environment["HOME"]), environment)
    write_enrollment(paths, content=b'schema = 4\nprofile_id = "personal-profile"\n')
    selections = {
        "source": "https://example.test/profiles.git",
        "ref": "main",
        "profile_id": "personal-profile",
        "machine_id": "workstation-01",
    }
    result = plan(target, environment, **selections)
    assert result["enrollment"]["status"] == "verified"
    assert result["enrollment"]["resolved_commit"] == "a" * 40
    assert not any(item["id"].startswith("enroll-") for item in result["actions"])
    cached = paths.profile_root("personal-profile", "a" * 40) / "ai-dlc-profile.toml"
    cached.write_text("tampered")
    result = plan(target, environment, **selections)
    assert result["enrollment"]["status"] != "verified"
    assert "enrollment-unverified" in codes(result)


@pytest.mark.parametrize("selection", [{"agent_clients": ["claude-code"]}, {"preset": "python"}])
def test_explicit_conflict_does_not_rewrite_existing_choices(target, environment, selection):
    adopted(target)
    (target / ".copier-answers.yml").write_text("preset: generic\n")
    result = plan(target, environment, **selection)
    assert result["state"] == "blocked"
    assert "selection-conflict" in codes(result)
    assert not any(item["available"] for item in result["actions"])


@pytest.mark.parametrize(
    "selection",
    [
        {"agent_clients": ["imaginary-client"]},
        {"preset": "rust"},
        {"profile_id": "Invalid ID"},
        {"source": "https://secret@example.test/profile.git"},
        {"source": "https://example.test/profile.git?token=secret"},
        {"ref": "--help"},
    ],
)
def test_malformed_selections_are_safe_input_errors(target, environment, selection):
    with pytest.raises(ValueError) as caught:
        plan(target, environment, **selection)
    assert "secret" not in str(caught.value)


def test_unsupported_host_never_suggests_unix_or_wsl_commands(target, environment, monkeypatch):
    adopted(target)
    monkeypatch.setattr("platform.system", lambda: "Windows")
    result = plan(target, environment)
    assert result["state"] == "unsupported"
    assert "unsupported-platform" in codes(result)
    assert not any(item["available"] for item in result["actions"])
    assert "wsl" not in json.dumps(result).lower()
    assert not any("command" in item for item in result["actions"])


def test_unknown_shell_retains_argv_without_copyable_text(target, environment):
    adopted(target)
    result = plan(target, {**environment, "SHELL": "/usr/bin/unknown-shell"})
    assert result["state"] == "actionable"
    assert "unsupported-shell" in codes(result)
    assert action(result, "target-check")["argv"]
    assert not any("command" in item for item in result["actions"])


def test_missing_engine_is_not_a_version_based_feature_claim(target, environment):
    adopted(target)
    result = plan(target, {**environment, "PATH": ""})
    assert result["state"] == "blocked"
    assert "engine-feature-unavailable" in codes(result)
    assert not any(item["available"] for item in result["actions"])
    assert result["engine"]["source"] == "unknown"


def test_target_must_exist_and_must_not_be_engine_checkout(target, environment):
    missing = target / "missing"
    result = plan(missing, environment, agent_clients=["codex"])
    assert result["state"] == "input-required"
    assert "target-required" in codes(result)
    assert not missing.exists()
    (target / "src/ai_dlc").mkdir(parents=True)
    (target / "src/ai_dlc/__init__.py").write_text("")
    (target / "pyproject.toml").write_text('[project]\nname = "ai-dlc"\n')
    result = plan(target, environment, agent_clients=["codex"])
    assert result["state"] == "blocked"
    assert "engine-checkout-target" in codes(result)


def test_unreadable_target_is_bounded(target, environment, monkeypatch):
    original = os.access
    monkeypatch.setattr(
        os, "access", lambda path, mode: False if Path(path) == target else original(path, mode)
    )
    result = plan(target, environment)
    assert "target-required" in codes(result)
    assert not result["actions"]


def test_stale_intact_guidance_is_not_an_authored_conflict(target, environment):
    adopted(target)
    guidance = target / "AGENTS.md"
    guidance.write_text(managed_section("Authored introduction", "old generated guidance\n"))
    result = plan(target, environment)
    assert "guidance-conflict" not in codes(result)
    assert action(result, "render-preview")["available"]
    guidance.write_text(guidance.read_text().replace("old generated", "authored edited"))
    result = plan(target, environment)
    assert "guidance-conflict" in codes(result)
    assert result["state"] == "blocked"
    assert action(result, "render-preview")["available"]
    assert not action(result, "render-apply")["available"]


def test_owned_file_edits_are_reported_without_reading_outside_target(target, environment):
    adopted(target)
    owned = target / ".ai-dlc/providers/local.md"
    owned.parent.mkdir(parents=True)
    owned.write_text("authored edit")
    (target / ".ai-dlc/agent-ownership.json").write_text(
        json.dumps(
            {
                "schema": 2,
                "files": {".ai-dlc/providers/local.md": hashlib.sha256(b"old").hexdigest()},
            }
        )
    )
    assert "guidance-conflict" in codes(plan(target, environment))


def test_target_runtime_gap_is_explicit_and_never_reports_a_pass(target, environment):
    adopted(target)
    (Path(environment["PATH"]) / "python").unlink()
    result = plan(target, environment)
    assert "target-runtime-unavailable" in codes(result)
    assert not action(result, "target-check")["available"]
    assert action(result, "project-setup")["available"]
    assert result["qualification"] == "not-assessed"


def test_check_selection_is_required_without_required_checks(target, environment):
    adopted(target, checks=False)
    with (target / "ai-dlc.toml").open("a") as handle:
        handle.write('[checks.commands]\nsmoke = "true"\n')
    result = plan(target, environment)
    assert result["state"] == "input-required"
    assert "target-check-required" in codes(result)
    assert not action(result, "target-check")["available"]


def test_repeated_plans_never_write_spawn_fetch_or_read_ambient_configuration(
    target, environment, monkeypatch
):
    adopted(target, client="antigravity")
    paths = EnrollmentPaths.from_environment(Path(environment["HOME"]), environment)
    write_enrollment(paths, content=b'schema = 4\nprofile_id = "personal-profile"\n')
    module = importlib.import_module("ai_dlc.setup.onboarding")
    # Warm imports before the guards so the boundary covers planning rather than Python's loader.
    selections = {
        "source": "https://example.test/profiles.git",
        "ref": "main",
        "profile_id": "personal-profile",
        "machine_id": "workstation-01",
    }
    module.plan_onboarding(target, environ=environment, **selections)
    snapshot = lambda: {
        str(path): (path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode)
        for path in target.parent.rglob("*")
        if path.is_file()
    }
    before = snapshot()

    def forbidden(*args, **kwargs):
        raise AssertionError("planning attempted an effect")

    for name in ("Popen", "run", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(tempfile, "mkstemp", forbidden)
    for name in ("mkdir", "unlink", "rename", "replace"):
        monkeypatch.setattr(os, name, forbidden)
    original_open = builtins.open
    original_io_open = io.open
    original_os_open = os.open

    def checked_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            forbidden()
        return original_open(file, mode, *args, **kwargs)

    def checked_io_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            forbidden()
        return original_io_open(file, mode, *args, **kwargs)

    def checked_os_open(path, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            forbidden()
        return original_os_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", checked_open)
    monkeypatch.setattr(io, "open", checked_io_open)
    monkeypatch.setattr(os, "open", checked_os_open)
    monkeypatch.setattr(tempfile, "TemporaryDirectory", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    for name in ("mkdir", "write_text", "write_bytes", "touch", "unlink", "rename", "replace"):
        monkeypatch.setattr(Path, name, forbidden)
    monkeypatch.setattr("ai_dlc.setup.templates.adopt", forbidden)
    monkeypatch.setattr("ai_dlc.harness.agents.render_agents", forbidden)
    monkeypatch.setattr("ai_dlc.config.resolve_runtime", forbidden)
    first = module.plan_onboarding(target, environ=environment, **selections)
    second = module.plan_onboarding(target, environ=environment, **selections)
    assert first == second
    unselected = module.plan_onboarding(target, environ=environment)
    assert unselected["enrollment"] == {"status": "unselected"}
    assert before == snapshot()
    ids = set()
    for item in first["actions"]:
        assert set(item["depends_on"]) <= ids
        ids.add(item["id"])


def test_generic_scaffold_management_checks_require_application_acceptance(target, environment):
    adopted(target, checks=False)
    with (target / "ai-dlc.toml").open("a") as handle:
        handle.write(
            '[checks]\nrequired = ["generated", "work-records"]\n[checks.commands]\ngenerated = "ai-dlc agents render --check"\nwork-records = "ai-dlc work validate --all"\n'
        )
    result = plan(target, environment)
    assert result["state"] == "input-required"
    assert "target-check-required" in codes(result)
    assert action(result, "target-check")["argv"] == []


def test_invalid_target_configuration_never_echoes_secret_values(target, environment):
    (target / "ai-dlc.toml").write_text(
        'schema = 4\n[providers.custom]\npassword = "secret-value"\n'
    )
    with pytest.raises(ValueError) as caught:
        plan(target, environment)
    assert "configuration-invalid" in str(caught.value)
    assert "secret-value" not in str(caught.value)


def test_conflicting_active_enrollment_is_not_replaced(target, environment):
    adopted(target)
    paths = EnrollmentPaths.from_environment(Path(environment["HOME"]), environment)
    write_enrollment(paths, content=b'schema = 4\nprofile_id = "personal-profile"\n')
    result = plan(
        target,
        environment,
        source="https://example.test/different.git",
        ref="main",
        profile_id="other",
        machine_id="workstation-01",
    )
    assert result["state"] == "blocked"
    assert "selection-conflict" in codes(result)
    assert not action(result, "enroll-apply")["available"]


def test_path_engine_presence_does_not_claim_its_feature_parity(target, environment):
    adopted(target)
    result = plan(target, environment)
    assert result["engine"]["executable_features"] == "not-assessed"
    assert any(
        "conditional" in item["reason"] and "PATH" in item["reason"] for item in result["findings"]
    )


def test_planner_does_not_read_credential_environment_values(target, environment):
    adopted(target)

    class MetadataEnvironment(dict):
        def keys(self):
            raise AssertionError("do not enumerate credential-bearing environment")

        def __iter__(self):
            raise AssertionError("do not enumerate credential-bearing environment")

        def __getitem__(self, key):
            assert key != "PRIVATE_TOKEN"
            return super().__getitem__(key)

    supplied = MetadataEnvironment({**environment, "PRIVATE_TOKEN": "secret"})
    result = plan(target, supplied)
    assert "secret" not in json.dumps(result)
