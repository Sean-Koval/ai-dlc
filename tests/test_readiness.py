from __future__ import annotations

from pathlib import Path

import pytest
from test_rendering import _skill, _write_vendored_bundle


def _checks(result: dict, component: str, dimension: str) -> list[dict]:
    return [
        check
        for check in result["checks"]
        if check["component"] == component and check["dimension"] == dimension
    ]


def _linear_config(*, headless: bool = False) -> dict:
    config = {
        "roles": {"tracker": "linear"},
        "providers": {
            "linear": {
                "team_id": "team",
                "token_env": "READINESS_TEST_TOKEN",
                "statuses": {"in_progress": "started", "closed": "completed"},
            }
        },
    }
    if headless:
        config["preferences"] = {"headless": True}
    return config


def test_reports_a_missing_tool_with_an_actionable_next_step(tmp_path: Path):
    """Would fail if an unavailable module executable did not block readiness."""
    from ai_dlc.setup.readiness import inspect_readiness

    result = inspect_readiness(
        tmp_path,
        {"roles": {"specs": "openspec"}},
        environ={},
        probe=lambda argv: {"available": False},
    )

    checks = _checks(result, "openspec", "tool")
    assert checks[0]["status"] == "missing"
    assert checks[0]["reason"]
    assert checks[0]["next_action"]
    assert result["ready"] is False
    assert result["qualification"] == "not-assessed"


def test_reports_missing_component_configuration_separately(tmp_path: Path):
    """Would fail if required provider configuration were mistaken for tool readiness."""
    from ai_dlc.setup.readiness import inspect_readiness

    result = inspect_readiness(
        tmp_path,
        {"roles": {"tracker": "linear"}, "providers": {"linear": {}}},
        environ={"READINESS_TEST_TOKEN": "present"},
        probe=lambda argv: {"available": True},
    )

    checks = _checks(result, "linear", "configuration")
    assert [check["status"] for check in checks] == ["missing", "missing", "missing"]
    assert all(check["next_action"] for check in checks)
    assert result["ready"] is False


def test_reports_an_absent_environment_credential_without_its_value(tmp_path: Path):
    """Would fail if readiness treated an unset credential binding as ready or exposed it."""
    from ai_dlc.setup.readiness import inspect_readiness

    result = inspect_readiness(
        tmp_path,
        _linear_config(),
        environ={},
        probe=lambda argv: {"available": True},
    )

    checks = _checks(result, "linear", "credential")
    assert checks[0]["status"] == "missing"
    assert checks[0]["next_action"]
    assert result["ready"] is False


def test_reports_missing_guidance_without_declaring_the_component_ready(tmp_path: Path):
    """Would fail if a selected component could pass while its guidance was absent."""
    import hashlib
    import json

    from ai_dlc.harness.components import load_component_catalog
    from ai_dlc.setup import readiness

    manifest = tmp_path / "component.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "components": [
                    {
                        "id": "synthetic-specs",
                        "roles": ["specs"],
                        "modules": [],
                        "guidance": ["guidance/missing.md"],
                        "required_config": [],
                    }
                ],
            }
        )
    )
    config = {
        "roles": {"specs": "synthetic-specs"},
        "providers": {
            "synthetic-specs": {
                "component_manifest": "component.json",
                "component_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            }
        },
    }
    with pytest.raises(ValueError, match="existing regular file"):
        load_component_catalog(tmp_path, config)

    result = readiness.inspect_readiness(
        tmp_path,
        config,
        environ={},
        probe=lambda argv: {"available": True},
    )

    checks = _checks(result, "synthetic-specs", "guidance")
    assert checks[0]["status"] == "missing"
    assert checks[0]["next_action"]
    assert result["ready"] is False

    (tmp_path / "guidance").mkdir()
    (tmp_path / "guidance/missing.md").write_text("# Restored instructions\n")
    restored = readiness.inspect_readiness(
        tmp_path, config, environ={}, probe=lambda argv: {"available": True}
    )
    assert restored["ready"] is True


def test_reports_ready_offline_requirements_and_unverified_provider_health(tmp_path: Path):
    """Would fail if offline readiness performed health checks or treated them as blocking."""
    from ai_dlc.setup.readiness import inspect_readiness

    probes: list[list[str]] = []
    result = inspect_readiness(
        tmp_path,
        {"roles": {"specs": "openspec"}},
        environ={},
        probe=lambda argv: probes.append(argv) or {"available": True},
    )

    assert probes == [["openspec"]]
    assert _checks(result, "openspec", "tool")[0]["status"] == "ready"
    assert _checks(result, "openspec", "guidance")[0]["status"] == "ready"
    assert _checks(result, "openspec", "provider-health")[0]["status"] == "unverified"
    assert result["ready"] is True
    assert result["qualification"] == "not-assessed"


def test_reports_headless_desktop_capability_as_blocked(tmp_path: Path):
    """Would fail if headless readiness silently substituted or accepted a desktop module."""
    from ai_dlc.setup.readiness import inspect_readiness

    result = inspect_readiness(
        tmp_path,
        _linear_config(headless=True),
        environ={"READINESS_TEST_TOKEN": "present"},
        probe=lambda argv: {"available": True},
    )

    checks = _checks(result, "linear", "tool")
    assert checks[0]["status"] == "blocked"
    assert "headless" in checks[0]["reason"]
    assert result["ready"] is False
    assert result["qualification"] == "not-assessed"


def test_never_returns_credential_values(tmp_path: Path):
    """Would fail if any readiness field copied a supplied credential value."""
    from ai_dlc.setup.readiness import inspect_readiness

    credential_value = "readiness-credential-value-that-must-not-escape"
    result = inspect_readiness(
        tmp_path,
        _linear_config(),
        environ={"READINESS_TEST_TOKEN": credential_value},
        probe=lambda argv: {"available": True},
    )

    assert result["ready"] is True
    assert credential_value not in repr(result)


@pytest.mark.parametrize("client", ["codex", "claude-code"])
def test_selected_harness_requires_delivered_provider_index(tmp_path, client):
    """Source instructions alone must not satisfy selected harness delivery."""
    from ai_dlc.config import load_project
    from ai_dlc.harness.agents import render_agents
    from ai_dlc.setup.readiness import inspect_readiness

    (tmp_path / "ai-dlc.toml").write_text(
        f'schema=4\n[roles]\nspecs="openspec"\nagent-client=["{client}"]\n'
    )
    config = load_project(tmp_path)

    def inspect():
        return inspect_readiness(tmp_path, config, environ={}, probe=lambda _: {"available": True})

    missing = inspect()
    assert missing["ready"] is False
    assert any(c["dimension"] == "guidance" and c["status"] == "missing" for c in missing["checks"])
    render_agents(tmp_path, apply=True)
    assert inspect()["ready"] is True
    if client == "claude-code":
        (tmp_path / "CLAUDE.md").unlink()
    else:
        (tmp_path / ".ai-dlc/providers/openspec.md").unlink()
    assert inspect()["ready"] is False


def test_unknown_harness_is_explicitly_blocked(tmp_path):
    """An unimplemented harness must not inherit supported-client guidance readiness."""
    from ai_dlc.setup.readiness import inspect_readiness

    result = inspect_readiness(
        tmp_path,
        {"roles": {"specs": "openspec", "agent-client": ["unknown"]}},
        environ={},
        probe=lambda _: {"available": True},
    )
    assert not result["ready"]
    assert any(c["dimension"] == "guidance" and c["status"] == "blocked" for c in result["checks"])


def test_duplicate_managed_sections_cannot_claim_guidance_readiness(tmp_path):
    """A conflicting duplicate index must require repair even if one section is intact."""
    from ai_dlc.config import load_project
    from ai_dlc.harness.agents import render_agents
    from ai_dlc.setup.readiness import inspect_readiness

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nspecs="openspec"\nagent-client=["codex"]\n'
    )
    render_agents(tmp_path, apply=True)
    path = tmp_path / "AGENTS.md"
    path.write_text(path.read_text() * 2)
    result = inspect_readiness(
        tmp_path, load_project(tmp_path), environ={}, probe=lambda _: {"available": True}
    )
    assert not result["ready"]


def test_personal_only_provider_has_actionable_delivery_gap_without_changing_project(tmp_path):
    """Missing personal provider delivery must not prescribe a render that cannot fix it."""
    from ai_dlc.harness.agents import render_agents
    from ai_dlc.setup.readiness import inspect_readiness

    project = tmp_path / "ai-dlc.toml"
    project.write_text('schema=4\n[roles]\nagent-client=["codex"]\n')
    render_agents(tmp_path, apply=True)
    before = project.read_bytes()
    result = inspect_readiness(
        tmp_path,
        {"roles": {"specs": "openspec", "agent-client": ["codex"]}},
        environ={},
        probe=lambda _: {"available": True},
    )
    gap = _checks(result, "codex", "guidance")[0]
    assert gap["status"] == "missing"
    assert "ai-dlc.toml" in gap["next_action"]
    assert project.read_bytes() == before


def test_bundle_guidance_inspection_reports_missing_blocked_stale_and_ready(tmp_path):
    """Would fail if selected unusable guidance could satisfy offline readiness."""
    from ai_dlc.harness.agents import inspect_bundle_guidance, render_agents

    clients = ["codex", "claude-code"]
    config = {"agents": {"bundles": ["review-flow"]}}
    assert inspect_bundle_guidance(tmp_path, config, clients)[0]["status"] == "missing"

    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow", "Version one"))},
    )
    assert inspect_bundle_guidance(tmp_path, config, clients)[0]["status"] == "missing"

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    render_agents(tmp_path, apply=True)
    assert inspect_bundle_guidance(tmp_path, config, clients) == [
        {
            "bundle_id": "review-flow",
            "status": "ready",
            "reason": "bundle guidance is intact and rendered for configured clients",
            "next_action": "No action required.",
        }
    ]

    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow", "Version two"))},
    )
    stale = inspect_bundle_guidance(tmp_path, config, clients)[0]
    assert stale["status"] == "missing"
    assert "full" in stale["next_action"].lower()

    rendered = tmp_path / ".agents/skills/review-flow/SKILL.md"
    rendered.write_text("local edit\n")
    blocked = inspect_bundle_guidance(tmp_path, config, clients)[0]
    assert blocked["status"] == "blocked"
    assert blocked["reason"]
    assert blocked["next_action"]


def test_missing_vendored_payload_is_missing_but_integrity_failure_takes_precedence(tmp_path):
    """Would fail if absent vendored bytes were collapsed into generic invalid content."""
    import json

    from ai_dlc.harness.agents import inspect_bundle_guidance

    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# Note\n")},
    )
    payload = tmp_path / ".ai-dlc/bundles/review-flow/templates/note.md"
    payload.unlink()
    config = {"agents": {"bundles": ["review-flow"]}}

    missing = inspect_bundle_guidance(tmp_path, config, ["codex"])[0]

    assert missing["status"] == "missing"
    assert missing["reason"] == "vendored bundle path is missing: templates/note.md"
    assert missing["next_action"]

    lock_path = tmp_path / ".ai-dlc/bundles/review-flow/bundle.lock.json"
    lock = json.loads(lock_path.read_text())
    lock["schema"] = 2
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")

    blocked = inspect_bundle_guidance(tmp_path, config, ["codex"])[0]

    assert blocked["status"] == "blocked"
    assert "invalid" in blocked["reason"]


@pytest.mark.parametrize(
    ("independent_failure", "expected_reason"),
    [("tampered", "digest mismatch"), ("undeclared", "undeclared")],
)
def test_missing_payload_does_not_hide_independent_bundle_integrity_failure(
    tmp_path, independent_failure, expected_reason
):
    """Would fail if exact-tree absence short-circuited a separately provable blocker."""
    from ai_dlc.harness.agents import inspect_bundle_guidance

    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={
            "missing-note": ("templates/missing.md", "# Missing\n"),
            "present-note": ("templates/present.md", "# Present\n"),
        },
    )
    bundle = tmp_path / ".ai-dlc/bundles/review-flow"
    (bundle / "templates/missing.md").unlink()
    if independent_failure == "tampered":
        (bundle / "templates/present.md").write_text("# Tampered\n")
    else:
        (bundle / "undeclared.md").write_text("# Undeclared\n")

    result = inspect_bundle_guidance(
        tmp_path,
        {"agents": {"bundles": ["review-flow"]}},
        ["codex"],
    )[0]

    assert result["status"] == "blocked"
    assert expected_reason in result["reason"]


def test_missing_manifest_does_not_hide_present_invalid_lock(tmp_path):
    """Would fail if missing metadata short-circuited validation of present metadata."""
    import json

    from ai_dlc.harness.agents import inspect_bundle_guidance

    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# Note\n")},
    )
    bundle = tmp_path / ".ai-dlc/bundles/review-flow"
    (bundle / "bundle.json").unlink()
    lock_path = bundle / "bundle.lock.json"
    lock = json.loads(lock_path.read_text())
    lock["schema"] = 2
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")

    result = inspect_bundle_guidance(
        tmp_path,
        {"agents": {"bundles": ["review-flow"]}},
        ["codex"],
    )[0]

    assert result["status"] == "blocked"
    assert "invalid lock" in result["reason"]


def test_bundle_collision_blocks_every_participating_readiness_result(tmp_path):
    """Would fail if a global export collision were attributed to only one claimant."""
    from ai_dlc.harness.agents import inspect_bundle_guidance

    for bundle_id in ["z-bundle", "a-bundle"]:
        _write_vendored_bundle(
            tmp_path,
            bundle_id,
            templates={"review-note": ("templates/note.md", f"# {bundle_id}\n")},
        )
    results = inspect_bundle_guidance(
        tmp_path,
        {"agents": {"bundles": ["z-bundle", "a-bundle"]}},
        ["codex"],
    )

    assert [result["bundle_id"] for result in results] == ["a-bundle", "z-bundle"]
    assert [result["status"] for result in results] == ["blocked", "blocked"]
    assert all("collision" in result["reason"] for result in results)


def test_bundle_guidance_symlinked_output_is_blocked_even_when_bytes_match(tmp_path):
    """Would fail if readiness followed a substituted owned output outside the project."""
    from ai_dlc.harness.agents import inspect_bundle_guidance, render_agents

    config = {"agents": {"bundles": ["review-flow"]}}
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow"))},
    )
    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["codex"]\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    render_agents(tmp_path, apply=True)
    rendered = tmp_path / ".agents/skills/review-flow/SKILL.md"
    outside = tmp_path / "outside-skill.md"
    outside.write_bytes(rendered.read_bytes())
    rendered.unlink()
    rendered.symlink_to(outside)

    result = inspect_bundle_guidance(tmp_path, config, ["codex"])[0]

    assert result["status"] == "blocked"
    assert "symlink" in result["reason"]


def test_bundle_guidance_list_ownership_document_returns_blocked_result(tmp_path):
    """Would fail if a non-object ownership document escaped structured readiness."""
    from ai_dlc.harness.agents import inspect_bundle_guidance

    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# Note\n")},
    )
    ownership = tmp_path / ".ai-dlc/agent-ownership.json"
    ownership.write_text("[]\n")

    result = inspect_bundle_guidance(
        tmp_path,
        {"agents": {"bundles": ["review-flow"]}},
        ["codex"],
    )

    assert result == [
        {
            "bundle_id": "review-flow",
            "status": "blocked",
            "reason": "bundle ownership is invalid: bundle ownership document must be an object",
            "next_action": (
                "Resolve bundle guidance conflicts or restore exact vendored and owned bytes, "
                "then run a full ai-dlc agents render --apply."
            ),
        }
    ]


def test_bundle_guidance_directory_output_returns_blocked_result(tmp_path):
    """Would fail if a non-file owned destination crashed readiness inspection."""
    from ai_dlc.harness.agents import inspect_bundle_guidance, render_agents

    config = {"agents": {"bundles": ["review-flow"]}}
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow"))},
    )
    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["codex"]\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    render_agents(tmp_path, apply=True)
    rendered = tmp_path / ".agents/skills/review-flow/SKILL.md"
    rendered.unlink()
    rendered.mkdir()

    result = inspect_bundle_guidance(tmp_path, config, ["codex"])[0]

    assert result["status"] == "blocked"
    assert result["reason"] == (
        "owned bundle output is not a regular file: .agents/skills/review-flow/SKILL.md"
    )
    assert result["next_action"]


def test_bundle_cross_owner_collision_blocks_old_and_new_selected_owners(tmp_path):
    """Would fail if readiness omitted the selected prior owner from a destination claim."""
    from ai_dlc.harness.agents import inspect_bundle_guidance, render_agents

    config_path = tmp_path / "ai-dlc.toml"
    config_path.write_text('schema=4\n[agents]\nbundles=["one"]\nskills=[]\n')
    _write_vendored_bundle(
        tmp_path,
        "one",
        templates={"review-note": ("templates/note.md", "# One\n")},
    )
    render_agents(tmp_path, apply=True)
    _write_vendored_bundle(
        tmp_path,
        "one",
        templates={"other-note": ("templates/other.md", "# Other\n")},
    )
    _write_vendored_bundle(
        tmp_path,
        "two",
        templates={"review-note": ("templates/note.md", "# Two\n")},
    )
    config_path.write_text('schema=4\n[agents]\nbundles=["one","two"]\nskills=[]\n')

    results = inspect_bundle_guidance(
        tmp_path,
        {"agents": {"bundles": ["one", "two"]}},
        ["codex"],
    )

    assert [result["status"] for result in results] == ["blocked", "blocked"]
    assert all("collision" in result["reason"] for result in results)


def test_bundle_cross_owner_directory_collision_blocks_both_selected_owners(tmp_path):
    """Would fail if an invalid destination type hid its prior selected owner."""
    from ai_dlc.harness.agents import inspect_bundle_guidance, render_agents

    config_path = tmp_path / "ai-dlc.toml"
    config_path.write_text('schema=4\n[agents]\nbundles=["one"]\nskills=[]\n')
    _write_vendored_bundle(
        tmp_path,
        "one",
        templates={"review-note": ("templates/note.md", "# One\n")},
    )
    render_agents(tmp_path, apply=True)
    _write_vendored_bundle(
        tmp_path,
        "one",
        templates={"other-note": ("templates/other.md", "# Other\n")},
    )
    _write_vendored_bundle(
        tmp_path,
        "two",
        templates={"review-note": ("templates/note.md", "# Two\n")},
    )
    config_path.write_text('schema=4\n[agents]\nbundles=["one","two"]\nskills=[]\n')
    destination = tmp_path / "docs/templates/review-note.md"
    destination.unlink()
    destination.mkdir()

    results = inspect_bundle_guidance(
        tmp_path,
        {"agents": {"bundles": ["one", "two"]}},
        ["codex"],
    )

    assert [result["status"] for result in results] == ["blocked", "blocked"]
    assert all("collision" in result["reason"] for result in results)


def test_project_readiness_maps_bundle_guidance_and_keeps_missing_bundle_blocking(tmp_path):
    """Would fail if bundle inspection did not participate in the guidance gate."""
    from ai_dlc.setup.readiness import inspect_readiness

    config = {
        "roles": {"agent-client": ["codex"]},
        "agents": {"bundles": ["missing-bundle"]},
    }
    result = inspect_readiness(
        tmp_path,
        config,
        environ={},
        probe=lambda argv: {"available": True},
    )

    checks = _checks(result, "bundle:missing-bundle", "guidance")
    assert len(checks) == 1
    assert checks[0]["status"] == "missing"
    assert checks[0]["reason"]
    assert checks[0]["next_action"]
    assert result["ready"] is False


def test_vendored_root_git_is_blocked_bundle_readiness(tmp_path):
    """Undeclared committed Git content must prevent bundle guidance readiness."""
    from ai_dlc.harness.agents import inspect_bundle_guidance

    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# Note\n")},
    )
    metadata = tmp_path / ".ai-dlc/bundles/review-flow/.git"
    metadata.mkdir()
    (metadata / "undeclared.md").write_text("# Undeclared\n")

    result = inspect_bundle_guidance(tmp_path, {"agents": {"bundles": ["review-flow"]}}, ["codex"])[
        0
    ]

    assert result["status"] == "blocked"
    assert "undeclared" in result["reason"]


def test_missing_payload_cannot_hide_canonical_lock_manifest_disagreement(tmp_path):
    """A complete metadata contradiction takes precedence over missing payload bytes."""
    import json

    from ai_dlc.harness.agents import inspect_bundle_guidance

    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# Note\n")},
    )
    bundle = tmp_path / ".ai-dlc/bundles/review-flow"
    (bundle / "templates/note.md").unlink()
    lock_path = bundle / "bundle.lock.json"
    lock = json.loads(lock_path.read_text())
    lock["files"]["templates/note.md"] = "b" * 64
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")

    result = inspect_bundle_guidance(tmp_path, {"agents": {"bundles": ["review-flow"]}}, ["codex"])[
        0
    ]

    assert result["status"] == "blocked"
    assert "lock does not match its manifest" in result["reason"]


def test_duplicate_selected_export_with_missing_payload_blocks_both_bundles(tmp_path):
    """Authenticated export claims remain colliding when one payload disappears."""
    from ai_dlc.harness.agents import inspect_bundle_guidance

    for bundle_id in ["one", "two"]:
        _write_vendored_bundle(
            tmp_path,
            bundle_id,
            templates={"review-note": ("templates/note.md", f"# {bundle_id}\n")},
        )
    (tmp_path / ".ai-dlc/bundles/one/templates/note.md").unlink()

    results = inspect_bundle_guidance(tmp_path, {"agents": {"bundles": ["one", "two"]}}, ["codex"])

    assert [result["status"] for result in results] == ["blocked", "blocked"]
    assert all("collision" in result["reason"] for result in results)


def test_contested_symlink_blocks_both_selected_bundle_owners(tmp_path):
    """A symlink must not hide the prior selected owner of a contested destination."""
    from ai_dlc.harness.agents import inspect_bundle_guidance, render_agents

    (tmp_path / "ai-dlc.toml").write_text('schema=4\n[agents]\nbundles=["one"]\nskills=[]\n')
    _write_vendored_bundle(
        tmp_path, "one", templates={"review-note": ("templates/note.md", "# One\n")}
    )
    render_agents(tmp_path, apply=True)
    _write_vendored_bundle(
        tmp_path, "one", templates={"other-note": ("templates/other.md", "# Other\n")}
    )
    _write_vendored_bundle(
        tmp_path, "two", templates={"review-note": ("templates/note.md", "# Two\n")}
    )
    destination = tmp_path / "docs/templates/review-note.md"
    outside = tmp_path / "outside-note.md"
    destination.rename(outside)
    destination.symlink_to(outside)

    results = inspect_bundle_guidance(tmp_path, {"agents": {"bundles": ["one", "two"]}}, ["codex"])

    assert [result["status"] for result in results] == ["blocked", "blocked"]
    assert all("collision" in result["reason"] for result in results)
    assert outside.read_bytes() == b"# One\n"


@pytest.mark.parametrize("filename", ["AGENTS.md", "CLAUDE.md"])
def test_non_utf8_managed_guidance_returns_blocked_bundle_readiness(tmp_path, filename):
    """Malformed guidance must yield actionable per-bundle results without decode errors."""
    from ai_dlc.harness.agents import inspect_bundle_guidance, render_agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# Note\n")},
    )
    render_agents(tmp_path, apply=True)
    (tmp_path / filename).write_bytes(b"\xff\xfe private invalid bytes\n")
    config = {"agents": {"bundles": ["review-flow"]}}

    results = inspect_bundle_guidance(tmp_path, config, ["codex", "claude-code"])

    assert results[0]["status"] == "blocked"
    assert results[0]["next_action"]
    assert "private" not in results[0]["reason"]
    assert inspect_bundle_guidance(tmp_path, config, ["codex", "claude-code"]) == results
