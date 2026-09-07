import hashlib
import json
import shutil
from pathlib import Path

import pytest


def _write_vendored_bundle(
    root: Path,
    bundle_id: str,
    *,
    skills: dict[str, tuple[str, str]] | None = None,
    templates: dict[str, tuple[str, str]] | None = None,
) -> None:
    skills = skills or {}
    templates = templates or {}
    destination = root / ".ai-dlc/bundles" / bundle_id
    files = {
        path: hashlib.sha256(body.encode()).hexdigest()
        for path, body in [*skills.values(), *templates.values()]
    }
    manifest = {
        "schema": 1,
        "id": bundle_id,
        "skills": {name: path for name, (path, _) in skills.items()},
        "templates": {name: path for name, (path, _) in templates.items()},
        "files": files,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    lock = {
        "schema": 1,
        "id": bundle_id,
        "source": f"https://example.test/{bundle_id}.git",
        "ref": "v1",
        "resolved_commit": "a" * 40,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "files": files,
    }
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "bundle.json").write_bytes(manifest_bytes)
    (destination / "bundle.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    for path, body in [*skills.values(), *templates.values()]:
        output = destination / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(body)


def _skill(name: str, body: str = "Use the reviewed workflow.") -> str:
    return f"---\nname: {name}\ndescription: Portable reviewed workflow\n---\n{body}\n"


@pytest.mark.parametrize("apply", [False, True])
@pytest.mark.parametrize(
    "guidance",
    [
        ".ai-dlc/providers/openspec.md",
        ".agents/skills/day-start/SKILL.md",
        ".claude/skills/day-start/SKILL.md",
    ],
)
def test_provider_switch_refuses_to_delete_still_referenced_owned_guidance(
    tmp_path, apply, guidance
):
    """A custom provider must not gain a link whose formerly owned target gets deleted."""
    import hashlib
    import json

    from ai_dlc.agents import render_agents

    project = tmp_path / "ai-dlc.toml"
    project.write_text('schema=4\n[roles]\nspecs="openspec"\n')
    render_agents(tmp_path, apply=True)
    manifest = tmp_path / "component.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "components": [
                    {
                        "id": "custom-specs",
                        "roles": ["specs"],
                        "modules": [],
                        "guidance": [guidance],
                        "required_config": [],
                    }
                ],
            }
        )
    )
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    project.write_text(
        'schema=4\n[roles]\nspecs="custom-specs"\n[providers.custom-specs]\n'
        'component_manifest="component.json"\n'
        f'component_manifest_sha256="{digest}"\n'
        "[agents]\nskills=[]\n"
    )
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="still referenced"):
        render_agents(tmp_path, apply=apply)
    assert before == {
        p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }


def test_provider_index_delivers_real_owned_instructions_and_removes_stale_copies(tmp_path):
    """Provider selection changes must update links and owned instructions together."""
    import json

    from ai_dlc.agents import render_agents
    from ai_dlc.files import assets

    config = tmp_path / "ai-dlc.toml"
    config.write_text('schema=4\n[roles]\nspecs="openspec"\ntracker="linear"\n')
    render_agents(tmp_path, apply=True)
    guide = (tmp_path / "AGENTS.md").read_text()
    assert ".ai-dlc/providers/openspec.md" in guide
    assert ".ai-dlc/providers/linear.md" in guide
    assert "@AGENTS.md" in (tmp_path / "CLAUDE.md").read_text()
    copy = tmp_path / ".ai-dlc/providers/openspec.md"
    assert copy.read_bytes() == (assets("agents") / "providers/openspec.md").read_bytes()
    ownership = json.loads((tmp_path / ".ai-dlc/agent-ownership.json").read_text())
    assert ".ai-dlc/providers/openspec.md" in ownership["files"]
    config.write_text('schema=4\n[roles]\ntracker="linear"\n')
    render_agents(tmp_path, apply=True)
    assert not copy.exists()
    assert ".ai-dlc/providers/openspec.md" not in (tmp_path / "AGENTS.md").read_text()


@pytest.mark.parametrize("owned", [False, True])
def test_provider_copy_conflicts_preserve_authored_files_without_partial_writes(tmp_path, owned):
    """Authored and edited owned provider instructions must never be overwritten."""
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text('schema=4\n[roles]\nspecs="openspec"\n')
    if owned:
        render_agents(tmp_path, apply=True)
    copy = tmp_path / ".ai-dlc/providers/openspec.md"
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_text("authored instructions")
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    assert before == {
        p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }


def test_render_preserves_authored_text_and_detects_stale_generated_section(tmp_path):
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[checks]\nrequired=["test"]\n[checks.commands]\ntest="pytest"\n[roles]\ntracker="linear"\n'
    )
    (tmp_path / "AGENTS.md").write_text("# My instructions\nKeep this.\n")
    render_agents(tmp_path, apply=True)
    first = (tmp_path / "AGENTS.md").read_bytes()
    render_agents(tmp_path, apply=True)
    assert (tmp_path / "AGENTS.md").read_bytes() == first
    assert first.startswith(b"# My instructions\nKeep this.\n")
    assert render_agents(tmp_path)["clean"] is True
    config = tmp_path / "ai-dlc.toml"
    config.write_text(config.read_text().replace("pytest", "pytest -q"))
    assert render_agents(tmp_path)["clean"] is False


def test_edits_inside_managed_section_are_not_overwritten(tmp_path):
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    render_agents(tmp_path, apply=True)
    agents = tmp_path / "AGENTS.md"
    agents.write_text(agents.read_text().replace("Shared project guidance", "User changed title"))
    before = agents.read_bytes()
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    assert agents.read_bytes() == before


def test_mcp_conflicting_server_preserved(tmp_path):
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[[agents.servers]]\nid="docs"\ncommand="server"\nargs=["run"]\n'
    )
    (tmp_path / ".mcp.json").write_text('{"mcpServers":{"docs":{"command":"mine"}}}')
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    assert "mine" in (tmp_path / ".mcp.json").read_text()


def test_unsupported_required_hook_fails_readiness():
    from ai_dlc.agents import hook_readiness

    result = hook_readiness("codex", "0.151.0", "local", ["request-approval"])
    assert result["ready"] is False
    assert "request-approval" in result["unavailable"]


def test_skills_selection_partial_ownership_and_removal(tmp_path):
    import json

    from ai_dlc.agents import render_agents
    from ai_dlc.files import assets

    config = tmp_path / "ai-dlc.toml"
    config.write_text('schema=4\n[agents]\nskills=["day-start"]\n')
    render_agents(tmp_path, apply=True)
    for directory in [".agents", ".claude"]:
        assert (tmp_path / directory / "skills/day-start/SKILL.md").read_bytes() == (
            assets("agents") / "skills/day-start/SKILL.md"
        ).read_bytes()
    config.write_text("schema=4\n[agents]\nskills=[]\n")
    render_agents(tmp_path, apply=True, client="codex")
    assert not (tmp_path / ".agents/skills/day-start/SKILL.md").exists()
    assert (tmp_path / ".claude/skills/day-start/SKILL.md").exists()
    manifest = json.loads((tmp_path / ".ai-dlc/agent-ownership.json").read_text())
    assert ".claude/skills/day-start/SKILL.md" in manifest["files"]
    render_agents(tmp_path, apply=True, client="claude-code")
    assert not (tmp_path / ".claude/skills/day-start/SKILL.md").exists()


def test_skill_conflict_has_no_partial_writes(tmp_path):
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    skill = tmp_path / ".agents/skills/day-start/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("authored")
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    assert not (tmp_path / "AGENTS.md").exists()
    assert skill.read_text() == "authored"


def test_required_hooks_preserve_unmanaged_and_target_independent(tmp_path):
    import json

    from ai_dlc.agents import render_agents, target_hooks
    from ai_dlc.config import load_project

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents.clients.codex]\nversion="0.151.0"\nrequired_hooks=["bound-push","session-context","stop-reminder"]\n'
    )
    path = tmp_path / ".codex/hooks.json"
    path.parent.mkdir()
    path.write_text(
        '{"custom":true,"hooks":{"Stop":[{"hooks":[{"type":"command","command":"user-hook"}]}]}}'
    )
    render_agents(tmp_path, apply=True)
    content = path.read_text()
    assert "git rev-parse --show-toplevel" in content
    assert "user-hook" in content and json.loads(content)["custom"]
    assert render_agents(tmp_path, target="ci")["clean"]
    assert not target_hooks(load_project(tmp_path), "ci")["ready"]


def test_unsupported_required_hooks_fail_before_writes(tmp_path):
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents.clients.codex]\nversion="0.151.0"\nrequired_hooks=["request-approval"]\n'
    )
    with pytest.raises(ValueError, match="hook"):
        render_agents(tmp_path, apply=True)
    assert not (tmp_path / "AGENTS.md").exists()


def test_digest_mismatch_prevents_all_writes(tmp_path, monkeypatch):
    import shutil

    from ai_dlc import agents
    from ai_dlc.files import assets

    package = tmp_path / "package"
    shutil.copytree(assets("agents"), package)
    (package / "skills/day-start/SKILL.md").write_text("tampered")
    monkeypatch.setattr(
        agents, "assets", lambda name: package if name == "agents" else assets(name)
    )
    project = tmp_path / "project"
    project.mkdir()
    (project / "ai-dlc.toml").write_text("schema=4\n")
    with pytest.raises(ValueError, match="digest"):
        agents.render_agents(project, apply=True)
    assert not (project / "AGENTS.md").exists()


def test_unchanged_owned_skill_updates_and_edited_removal_conflicts(tmp_path, monkeypatch):
    import hashlib
    import json
    import shutil

    from ai_dlc import agents
    from ai_dlc.files import assets

    package = tmp_path / "package"
    shutil.copytree(assets("agents"), package)
    monkeypatch.setattr(
        agents, "assets", lambda name: package if name == "agents" else assets(name)
    )
    project = tmp_path / "project"
    project.mkdir()
    config = project / "ai-dlc.toml"
    config.write_text('schema=4\n[agents]\nskills=["day-start"]\n')
    agents.render_agents(project, apply=True)
    source = package / "skills/day-start/SKILL.md"
    source.write_text(source.read_text() + "\nNew package guidance\n")
    lock_path = package / "skills.lock.json"
    lock = json.loads(lock_path.read_text())
    lock["skills"]["day-start"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    lock_path.write_text(json.dumps(lock))
    agents.render_agents(project, apply=True)
    destination = project / ".agents/skills/day-start/SKILL.md"
    assert destination.read_bytes() == source.read_bytes()
    destination.write_text("user edit")
    config.write_text("schema=4\n[agents]\nskills=[]\n")
    with pytest.raises(ValueError, match="conflict"):
        agents.render_agents(project, apply=True)
    assert destination.read_text() == "user edit"
    assert (project / ".claude/skills/day-start/SKILL.md").exists()


def test_codex_partial_keeps_claude_mcp_ownership_for_later_removal(tmp_path):
    import json

    from ai_dlc.agents import render_agents

    config = tmp_path / "ai-dlc.toml"
    config.write_text('schema=4\n[[agents.servers]]\nid="docs"\ncommand="server"\n')
    render_agents(tmp_path, apply=True)
    config.write_text("schema=4\n")
    render_agents(tmp_path, apply=True, client="codex")
    assert "docs" in json.loads((tmp_path / ".ai-dlc/agent-ownership.json").read_text())["mcp"]
    render_agents(tmp_path, apply=True, client="claude-code")
    assert not json.loads((tmp_path / ".mcp.json").read_text())["mcpServers"]


def test_hook_edit_conflict_and_removal_preserve_user_hook(tmp_path):
    import json

    from ai_dlc.agents import render_agents

    config = tmp_path / "ai-dlc.toml"
    config.write_text(
        'schema=4\n[agents.clients.claude-code]\nversion="2.1.0"\nrequired_hooks=["stop-reminder"]\n'
    )
    render_agents(tmp_path, apply=True)
    path = tmp_path / ".claude/settings.json"
    original = path.read_text()
    path.write_text(original.replace("ai-dlc hook stop", "edited hook"))
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    document = json.loads(original)
    user_hook = {"hooks": [{"type": "command", "command": "user-hook"}]}
    document["hooks"]["Stop"].append(user_hook)
    path.write_text(json.dumps(document))
    config.write_text("schema=4\n")
    render_agents(tmp_path, apply=True)
    assert json.loads(path.read_text())["hooks"]["Stop"] == [user_hook]


def test_unknown_client_version_has_no_claimed_hook_support():
    from ai_dlc.agents import hook_readiness

    result = hook_readiness("codex", "999.0.0", "local", ["bound-push"])
    assert not result["ready"]
    assert result["supported"] == []
    assert "fixture" in result["coverage"]


def test_custom_provider_index_links_to_project_instructions_without_copying_or_replacing_them(
    tmp_path,
):
    """Custom instructions must remain project-owned even if their path matches a packaged file."""
    import hashlib
    import json

    from ai_dlc.agents import render_agents
    from ai_dlc.config import load_project
    from ai_dlc.readiness import inspect_readiness

    guidance = tmp_path / "providers/openspec.md"
    guidance.parent.mkdir()
    guidance.write_text("# Custom specification provider instructions\n")
    manifest = tmp_path / "component.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "components": [
                    {
                        "id": "custom-specs",
                        "roles": ["specs"],
                        "modules": [],
                        "guidance": ["providers/openspec.md"],
                        "required_config": [],
                    }
                ],
            }
        )
    )
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nspecs="custom-specs"\nagent-client=["codex"]\n'
        '[providers.custom-specs]\ncomponent_manifest="component.json"\n'
        f'component_manifest_sha256="{digest}"\n'
    )
    render_agents(tmp_path, apply=True)
    assert (
        "[providers/openspec.md](<providers/openspec.md>)" in (tmp_path / "AGENTS.md").read_text()
    )
    assert not (tmp_path / ".ai-dlc/providers/openspec.md").exists()
    assert guidance.read_text() == "# Custom specification provider instructions\n"
    config = load_project(tmp_path)
    assert inspect_readiness(tmp_path, config, environ={}, probe=lambda _: {"available": True})[
        "ready"
    ]
    guidance.write_text("# Reviewed new custom instructions\n")
    assert render_agents(tmp_path)["clean"]


@pytest.mark.parametrize("client,directory", [("codex", ".agents"), ("claude-code", ".claude")])
@pytest.mark.parametrize("tracker", ["linear", "github-issues"])
def test_product_shaping_guidance_is_available_to_selected_harness(
    tmp_path, client, directory, tracker
):
    from ai_dlc.agents import render_agents
    from ai_dlc.files import assets
    from ai_dlc.templates import adopt

    adopt(tmp_path, apply=True, providers={"tracker": tracker})
    render_agents(tmp_path, apply=True, client=client)
    for name in ["discovery", "prd-draft", "review-inbox"]:
        body = (tmp_path / directory / "skills" / name / "SKILL.md").read_text()
        assert body == (assets("agents") / "skills" / name / "SKILL.md").read_text()
    discovery = (tmp_path / directory / "skills/discovery/SKILL.md").read_text()
    for reference in [
        "docs/templates/product-brief.md",
        "docs/examples/product-shaping/greenfield.md",
        "docs/examples/product-shaping/brownfield.md",
    ]:
        assert reference in discovery
        assert (tmp_path / reference).is_file()
    assert f".ai-dlc/providers/{tracker}.md" in (tmp_path / "AGENTS.md").read_text()
    assert render_agents(tmp_path, client=client)["clean"]


def test_selected_bundle_renders_offline_to_clients_template_and_index(tmp_path, monkeypatch):
    """Would fail if rendering fetched a source or omitted a required discovery destination."""
    import socket
    import subprocess
    import urllib.request

    from ai_dlc import workflow_bundles
    from ai_dlc.agents import render_agents

    fresh_checkout = tmp_path / "fresh-checkout"
    fresh_checkout.mkdir()
    _write_vendored_bundle(
        fresh_checkout,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow"))},
        templates={"review-note": ("templates/review-note.md", "# Review note\n")},
    )
    (fresh_checkout / "ai-dlc.toml").write_text(
        'schema=4\n[roles]\nagent-client=["codex","claude-code"]\n'
        '[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )

    def source_access_forbidden(*args, **kwargs):
        pytest.fail("fresh-checkout render attempted Git or network source access")

    monkeypatch.setattr(workflow_bundles, "resolve_git_source", source_access_forbidden)
    monkeypatch.setattr(subprocess, "run", source_access_forbidden)
    monkeypatch.setattr(socket, "create_connection", source_access_forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", source_access_forbidden)

    result = render_agents(fresh_checkout, apply=True)

    assert result["applied"] is True
    skill = _skill("review-flow")
    assert (fresh_checkout / ".agents/skills/review-flow/SKILL.md").read_text() == skill
    assert (fresh_checkout / ".claude/skills/review-flow/SKILL.md").read_text() == skill
    assert (fresh_checkout / "docs/templates/review-note.md").read_text() == "# Review note\n"
    index = (fresh_checkout / "AGENTS.md").read_text()
    assert "[review-flow](<.ai-dlc/bundles/review-flow/skills/review/SKILL.md>)" in index
    assert "[review-note](<docs/templates/review-note.md>)" in index
    assert "@AGENTS.md\n" in (fresh_checkout / "CLAUDE.md").read_text()
    ownership = json.loads((fresh_checkout / ".ai-dlc/agent-ownership.json").read_text())
    expected_paths = {
        ".agents/skills/review-flow/SKILL.md",
        ".claude/skills/review-flow/SKILL.md",
        "docs/templates/review-note.md",
    }
    assert ownership["schema"] == 3
    assert set(ownership["bundle_files"]) == expected_paths
    assert all(isinstance(digest, str) for digest in ownership["files"].values())
    assert all(
        entry["owner"] == "review-flow" and entry["sha256"] == ownership["files"][path]
        for path, entry in ownership["bundle_files"].items()
    )
    assert render_agents(fresh_checkout)["clean"] is True


def test_bundle_crlf_template_is_clean_after_apply(tmp_path):
    """Would fail if render checks normalized valid bundle payload newlines."""
    from ai_dlc.agents import render_agents

    body = "# Review note\r\n\r\nPreserve these bytes.\r\n"
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={"review-note": ("templates/review-note.md", body)},
    )
    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )

    render_agents(tmp_path, apply=True)
    checked = render_agents(tmp_path)

    assert (tmp_path / "docs/templates/review-note.md").read_bytes() == body.encode()
    assert checked == {"clean": True, "changed": [], "applied": False}


@pytest.mark.parametrize("collision", ["authored", "shipped", "duplicate"])
def test_bundle_collisions_block_the_whole_render_without_writes(tmp_path, collision):
    """Would fail if authored, shipped, or cross-bundle claims were overwritten."""
    from ai_dlc.agents import render_agents

    if collision == "authored":
        _write_vendored_bundle(
            tmp_path,
            "one",
            templates={"review-note": ("templates/note.md", "# Review note\n")},
        )
        authored = tmp_path / "docs/templates/review-note.md"
        authored.parent.mkdir(parents=True)
        authored.write_text("# Review note\n")
        bundles = ["one"]
    elif collision == "shipped":
        _write_vendored_bundle(
            tmp_path,
            "one",
            skills={"day-start": ("skills/day/SKILL.md", _skill("day-start"))},
        )
        authored = None
        bundles = ["one"]
    else:
        for bundle_id in ["one", "two"]:
            _write_vendored_bundle(
                tmp_path,
                bundle_id,
                templates={"review-note": ("templates/note.md", f"# {bundle_id}\n")},
            )
        authored = None
        bundles = ["two", "one"]
    (tmp_path / "ai-dlc.toml").write_text(
        "schema=4\n[agents]\nbundles=" + json.dumps(bundles) + "\nskills=[]\n"
    )
    before = authored.read_bytes() if authored else None

    with pytest.raises(ValueError, match="collision"):
        render_agents(tmp_path, apply=True)

    assert not (tmp_path / "AGENTS.md").exists()
    if authored:
        assert authored.read_bytes() == before


def test_bundle_render_rejects_a_symlinked_vendored_parent_without_writes(tmp_path):
    """Would fail if rendering followed a substituted parent outside the project."""
    from ai_dlc.agents import render_agents

    outside = tmp_path / "outside"
    outside.mkdir()
    _write_vendored_bundle(
        outside,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow"))},
    )
    (tmp_path / ".ai-dlc").mkdir()
    (tmp_path / ".ai-dlc/bundles").symlink_to(outside / ".ai-dlc/bundles")
    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )

    with pytest.raises(ValueError, match="symlink"):
        render_agents(tmp_path, apply=True)

    assert not (tmp_path / "AGENTS.md").exists()


def test_bundle_same_owner_update_partial_client_and_edited_removal(tmp_path):
    """Would fail if partial renders lost ownership or edited obsolete outputs were deleted."""
    from ai_dlc.agents import render_agents

    config = tmp_path / "ai-dlc.toml"
    config.write_text('schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n')
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow", "Version one"))},
    )
    render_agents(tmp_path, apply=True)
    claude = tmp_path / ".claude/skills/review-flow/SKILL.md"
    claude_before = claude.read_bytes()
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow", "Version two"))},
    )

    render_agents(tmp_path, apply=True, client="codex")

    assert "Version two" in (tmp_path / ".agents/skills/review-flow/SKILL.md").read_text()
    assert claude.read_bytes() == claude_before
    ownership = json.loads((tmp_path / ".ai-dlc/agent-ownership.json").read_text())
    assert ownership["bundle_files"][".claude/skills/review-flow/SKILL.md"]["sha256"] == (
        hashlib.sha256(claude_before).hexdigest()
    )
    edited = tmp_path / ".agents/skills/review-flow/SKILL.md"
    edited.write_text("local edit\n")
    config.write_text("schema=4\n[agents]\nbundles=[]\nskills=[]\n")
    before = {path: path.read_bytes() for path in [edited, claude, tmp_path / "AGENTS.md"]}
    with pytest.raises(ValueError, match="conflict"):
        render_agents(tmp_path, apply=True)
    assert {path: path.read_bytes() for path in before} == before

    edited.write_text(_skill("review-flow", "Version two"))
    render_agents(tmp_path, apply=True)
    ownership = json.loads((tmp_path / ".ai-dlc/agent-ownership.json").read_text())
    assert ownership["schema"] == 3
    assert ownership["bundle_files"] == {}
    assert not edited.exists()
    assert not claude.exists()


def test_bundle_render_operational_failure_restores_every_affected_byte(tmp_path, monkeypatch):
    """Would fail if a multi-file bundle publication could leave a partial render."""
    from ai_dlc import agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow", "Version one"))},
        templates={"review-note": ("templates/review-note.md", "# One\n")},
    )
    agents.render_agents(tmp_path, apply=True)
    affected = [
        tmp_path / ".agents/skills/review-flow/SKILL.md",
        tmp_path / ".claude/skills/review-flow/SKILL.md",
        tmp_path / "docs/templates/review-note.md",
        tmp_path / ".ai-dlc/agent-ownership.json",
    ]
    read_only = affected[0]
    read_only.chmod(0o444)
    before = {path: (path.read_bytes(), path.stat().st_mode & 0o777) for path in affected}
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow", "Version two"))},
        templates={"review-note": ("templates/review-note.md", "# Two\n")},
    )
    original = agents._publish_render_change
    calls = 0

    def fail_second_write(state, change, content):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("publication failed")
        return original(state, change, content)

    monkeypatch.setattr(agents, "_publish_render_change", fail_second_write)
    with pytest.raises(OSError, match="publication failed"):
        agents.render_agents(tmp_path, apply=True)

    assert {path: (path.read_bytes(), path.stat().st_mode & 0o777) for path in affected} == before


def test_bundle_render_invalid_template_ancestor_preserves_obsolete_outputs(tmp_path):
    """A late invalid ancestor must not strand earlier removed owned files."""
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow"))},
    )
    render_agents(tmp_path, apply=True)
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# Note\n")},
    )
    (tmp_path / "docs").write_bytes(b"authored docs file\r\n")
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    with pytest.raises((ValueError, OSError)):
        render_agents(tmp_path, apply=True)

    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


@pytest.mark.parametrize("existing", [False, True])
def test_bundle_render_preserves_late_edit_after_planning(tmp_path, monkeypatch, existing):
    """Publication must refuse changed bytes and newly authored destinations."""
    from ai_dlc import agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# One\n")},
    )
    if existing:
        agents.render_agents(tmp_path, apply=True)
        _write_vendored_bundle(
            tmp_path,
            "review-flow",
            templates={"review-note": ("templates/note.md", "# Two\n")},
        )
    destination = tmp_path / "docs/templates/review-note.md"
    original = agents._apply_render_transaction

    def edit_then_apply(*args, **kwargs):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"late authored edit\r\n")
        return original(*args, **kwargs)

    monkeypatch.setattr(agents, "_apply_render_transaction", edit_then_apply)
    with pytest.raises((ValueError, OSError)):
        agents.render_agents(tmp_path, apply=True)

    assert destination.read_bytes() == b"late authored edit\r\n"


def test_bundle_render_parent_swap_cannot_modify_external_file(tmp_path, monkeypatch):
    """Publication must remain bound to validated project directories through replacement."""
    from ai_dlc import agents

    project = tmp_path / "project"
    project.mkdir()
    (project / "ai-dlc.toml").write_text('schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n')
    _write_vendored_bundle(
        project,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# One\n")},
    )
    agents.render_agents(project, apply=True)
    _write_vendored_bundle(
        project,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# Two\n")},
    )
    original = agents.bundle_fs._rename_directory_noreplace
    outside = tmp_path / "outside-docs"
    swapped = False

    def swap_then_write(parent, source, destination):
        nonlocal swapped
        if destination == "review-note.md" and not swapped:
            swapped = True
            (project / "docs").rename(outside)
            (project / "docs").symlink_to(outside, target_is_directory=True)
        return original(parent, source, destination)

    monkeypatch.setattr(agents.bundle_fs, "_rename_directory_noreplace", swap_then_write)
    with pytest.raises((ValueError, OSError)):
        agents.render_agents(project, apply=True)

    assert (outside / "templates/review-note.md").read_bytes() == b"# One\n"


def test_bundle_render_rejects_undeclared_vendored_root_git(tmp_path):
    """Only source checkouts may exempt root Git metadata from exact-tree validation."""
    from ai_dlc.agents import render_agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# Note\n")},
    )
    metadata = tmp_path / ".ai-dlc/bundles/review-flow/.git"
    metadata.mkdir()
    (metadata / "undeclared.md").write_text("# Undeclared\n")
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    with pytest.raises(ValueError, match="undeclared"):
        render_agents(tmp_path, apply=True)

    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


def test_bundle_render_rollback_continues_after_one_restore_failure(tmp_path, monkeypatch):
    """Recovery must restore every path and preserve the publication error after cleanup fails."""
    from ai_dlc import agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow"))},
    )
    agents.render_agents(tmp_path, apply=True)
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        templates={"review-note": ("templates/note.md", "# Note\n")},
    )
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    original_write = agents._publish_render_change
    original_restore = agents._restore_render_change
    publishing_failed = False
    restore_failed = False

    def fail_template_write(state, change, content):
        nonlocal publishing_failed
        if change.path == "docs/templates/review-note.md":
            publishing_failed = True
            raise OSError("original publication failure")
        return original_write(state, change, content)

    def fail_first_restore(*args, **kwargs):
        nonlocal restore_failed
        if publishing_failed and not restore_failed:
            restore_failed = True
            raise OSError("secondary recovery failure")
        return original_restore(*args, **kwargs)

    monkeypatch.setattr(agents, "_publish_render_change", fail_template_write)
    monkeypatch.setattr(agents, "_restore_render_change", fail_first_restore)
    with pytest.raises(OSError, match="original publication failure") as failure:
        agents.render_agents(tmp_path, apply=True)

    after = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert {path: content for path, content in after.items() if path in before} == before
    notes = "\n".join(failure.value.__notes__)
    assert all(path.name.startswith(".ai-dlc-") for path in after.keys() - before.keys())
    assert all(
        path.relative_to(tmp_path).as_posix() in notes for path in after.keys() - before.keys()
    )


def test_bundle_render_staging_collision_preserves_authored_file(tmp_path, monkeypatch):
    """Failed exclusive staging must never clean up a file it did not create."""
    from ai_dlc import agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# One\n")}
    )
    agents.render_agents(tmp_path, apply=True)
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# Two\n")}
    )
    authored = tmp_path / "docs/templates/.ai-dlc-collision"
    authored.write_bytes(b"authored temporary-name file\r\n")
    monkeypatch.setattr(agents.secrets, "token_hex", lambda _: "collision")

    with pytest.raises(FileExistsError):
        agents.render_agents(tmp_path, apply=True)

    assert authored.read_bytes() == b"authored temporary-name file\r\n"
    assert (tmp_path / "docs/templates/review-note.md").read_bytes() == b"# One\n"


def test_bundle_render_recovery_preserves_late_deletion_of_untouched_file(tmp_path, monkeypatch):
    """Rollback must only restore files that this transaction actually mutated."""
    from ai_dlc import agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# One\n")}
    )
    agents.render_agents(tmp_path, apply=True)
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# Two\n")}
    )
    ownership = tmp_path / ".ai-dlc/agent-ownership.json"

    def remove_then_fail(*args):
        ownership.unlink()
        raise OSError("original publication failure")

    monkeypatch.setattr(agents, "_publish_render_change", remove_then_fail)

    with pytest.raises(OSError, match="original publication failure"):
        agents.render_agents(tmp_path, apply=True)

    assert not ownership.exists()
    assert (tmp_path / "docs/templates/review-note.md").read_bytes() == b"# One\n"


def test_bundle_render_rejects_changed_completed_stage_bytes(tmp_path, monkeypatch):
    """A completed stage must stay authenticated to the content planned for ownership."""
    import os

    from ai_dlc import agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# One\n")}
    )
    agents.render_agents(tmp_path, apply=True)
    ownership = tmp_path / ".ai-dlc/agent-ownership.json"
    ownership_before = ownership.read_bytes()
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# Two\n")}
    )
    original_stage = agents._stage_render_file

    def change_completed_stage(parent, content, mode):
        before = set(os.listdir(parent))
        staged = original_stage(parent, content, mode)
        if content == b"# Two\n":
            (name,) = set(os.listdir(parent)) - before
            descriptor = os.open(name, os.O_WRONLY | os.O_TRUNC, dir_fd=parent)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(b"unexpected completed stage bytes\r\n")
        return staged

    monkeypatch.setattr(agents, "_stage_render_file", change_completed_stage)

    with pytest.raises((ValueError, OSError), match="staging file changed"):
        agents.render_agents(tmp_path, apply=True)

    assert (tmp_path / "docs/templates/review-note.md").read_bytes() == b"# One\n"
    assert ownership.read_bytes() == ownership_before


@pytest.mark.parametrize("during_creation", [False, True])
def test_render_stage_cleanup_preserves_replacement_at_delete_boundary(
    tmp_path, monkeypatch, during_creation
):
    """A pathname reused just before deletion must retain the authored inode."""
    import os

    from ai_dlc import agents

    parent = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    original_unlink = os.unlink
    authored = b"authored replacement at cleanup boundary\r\n"
    replacements = []

    def replace_before_unlink(name, *, dir_fd=None):
        if not replacements:
            candidates = list(tmp_path.glob(".ai-dlc-*"))
            stage_path = next(path for path in candidates if path.is_file())
            stage_path.rename(tmp_path / "displaced-stage")
            stage_path.write_bytes(authored)
            replacements.append((stage_path, stage_path.stat().st_ino))
        return original_unlink(name, dir_fd=dir_fd)

    def fail_write(*args):
        original_write(args[0], b"partial stage")
        raise OSError("stage write failed")

    original_write = os.write
    try:
        if during_creation:
            monkeypatch.setattr(os, "write", fail_write)
            monkeypatch.setattr(os, "unlink", replace_before_unlink)
            with pytest.raises(OSError, match="stage write failed") as failure:
                agents._stage_render_file(parent, b"planned bytes", 0o644)
        else:
            stage = agents._stage_render_file(parent, b"planned bytes", 0o644)
            change = agents._RenderChange("target.md", parent, None, stage=stage)
            monkeypatch.setattr(os, "unlink", replace_before_unlink)
            agents._restore_render_change(change)
        if replacements:
            path, inode = replacements[0]
            assert path.read_bytes() == authored
            assert path.stat().st_ino == inode
        else:
            (path,) = tmp_path.glob(".ai-dlc-*")
            assert path.read_bytes() == (b"partial stage" if during_creation else b"planned bytes")
        if during_creation:
            assert any(path.name in note for note in failure.value.__notes__)
    finally:
        os.close(parent)


def test_bundle_render_failure_restores_outputs_and_reports_retained_stages(tmp_path, monkeypatch):
    """Safe residue must be discoverable without changing the original render failure."""
    from ai_dlc import agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# One\n")}
    )
    agents.render_agents(tmp_path, apply=True)
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# Two\n")}
    )
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    original_publish = agents._publish_render_change
    original_error = OSError("original publication failure")

    def publish_then_fail(state, change, content):
        original_publish(state, change, content)
        if change.path == "docs/templates/review-note.md":
            raise original_error

    monkeypatch.setattr(agents, "_publish_render_change", publish_then_fail)
    with pytest.raises(OSError, match="original publication failure") as failure:
        agents.render_agents(tmp_path, apply=True)

    assert failure.value is original_error
    assert all(path.read_bytes() == content for path, content in before.items())
    retained = [path for path in tmp_path.rglob(".ai-dlc-*") if path.is_file()]
    assert retained
    notes = "\n".join(failure.value.__notes__)
    assert all(path.relative_to(tmp_path).as_posix() in notes for path in retained)


@pytest.mark.parametrize("failed_attempts", [1, 2])
def test_bundle_render_recovery_retry_reports_partial_recovery_stage(
    tmp_path, monkeypatch, failed_attempts
):
    """A failed recovery stage remains reported after a later retry restores the output."""
    import os

    from ai_dlc import agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# One\n")}
    )
    agents.render_agents(tmp_path, apply=True)
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# Two\n")}
    )
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    original_publish, original_write = agents._publish_render_change, os.write
    original_error = OSError("original publication failure")
    recovering = False
    recovery_failures = 0

    def publish_then_require_snapshot_recovery(state, change, content):
        nonlocal recovering
        original_publish(state, change, content)
        if change.path == "docs/templates/review-note.md":
            # Exercise the snapshot-recovery state directly. Successful renders
            # no longer delete backups, so the old cleanup-failure trigger no
            # longer reaches it. Keep the accepted retry/note-forwarding contract.
            (tmp_path / "docs/templates" / change.backup).rename(tmp_path / "saved-backup.md")
            change.backup = None
            recovering = True
            raise original_error

    def fail_first_recovery_write(descriptor, content):
        nonlocal recovery_failures
        if recovering and recovery_failures < failed_attempts:
            recovery_failures += 1
            original_write(descriptor, b"partial recovery bytes")
            raise OSError("secondary recovery write failure")
        return original_write(descriptor, content)

    monkeypatch.setattr(agents, "_publish_render_change", publish_then_require_snapshot_recovery)
    monkeypatch.setattr(os, "write", fail_first_recovery_write)
    with pytest.raises(OSError, match="original publication failure") as failure:
        agents.render_agents(tmp_path, apply=True)

    assert failure.value is original_error
    if failed_attempts == 1:
        assert all(path.read_bytes() == content for path, content in before.items())
    partials = [
        path
        for path in tmp_path.rglob(".ai-dlc-*")
        if path.is_file() and path.read_bytes() == b"partial recovery bytes"
    ]
    assert len(partials) == failed_attempts
    assert all(partial.name in "\n".join(failure.value.__notes__) for partial in partials)


@pytest.mark.parametrize("mutation", ["replace", "edit", "symlink"])
def test_successful_bundle_render_preserves_backup_mutated_after_validation(
    tmp_path, monkeypatch, mutation
):
    """A final backup check must not authorize deletion of a later pathname occupant."""
    from ai_dlc import agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# One\n")}
    )
    agents.render_agents(tmp_path, apply=True)
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# Two\n")}
    )
    original_publish, original_read = agents._publish_render_change, agents._read_render_file
    backup = None
    authored = b"authored backup content\r\n"
    authored_inode = None
    outside = tmp_path / "authored.md"
    outside.write_bytes(authored)

    def remember_backup(state, change, content):
        nonlocal backup
        original_publish(state, change, content)
        if change.path == "docs/templates/review-note.md":
            backup = tmp_path / "docs/templates" / change.backup

    def mutate_after_read(parent, name):
        nonlocal authored_inode
        snapshot = original_read(parent, name)
        if backup is not None and name == backup.name and authored_inode is None:
            if mutation != "edit":
                backup.rename(tmp_path / "displaced-backup.md")
            if mutation == "symlink":
                backup.symlink_to(outside)
            else:
                backup.write_bytes(authored)
            authored_inode = backup.lstat().st_ino
        return snapshot

    monkeypatch.setattr(agents, "_publish_render_change", remember_backup)
    monkeypatch.setattr(agents, "_read_render_file", mutate_after_read)
    result = agents.render_agents(tmp_path, apply=True)

    assert backup is not None and authored_inode is not None
    assert backup.exists(), "successful render deleted authored backup content"
    assert backup.lstat().st_ino == authored_inode
    assert backup.read_bytes() == authored
    assert outside.read_bytes() == authored
    assert (tmp_path / "docs/templates/review-note.md").read_bytes() == b"# Two\n"
    assert backup.relative_to(tmp_path).as_posix() in result["retained_backups"]


@pytest.mark.parametrize("remove_export", [False, True])
def test_successful_bundle_render_reports_backups_without_adopting_them(tmp_path, remove_export):
    """Retained old output bytes must be discoverable and stay outside managed ownership."""
    from ai_dlc.agents import render_agents

    config = tmp_path / "ai-dlc.toml"
    config.write_text('schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n')
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# One\n")}
    )
    render_agents(tmp_path, apply=True)
    if remove_export:
        config.write_text("schema=4\n[agents]\nbundles=[]\nskills=[]\n")
    else:
        _write_vendored_bundle(
            tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# Two\n")}
        )
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    render_agents(tmp_path)
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before

    result = render_agents(tmp_path, apply=True)
    retained = result.get("retained_backups", [])
    assert retained, "successful render must report retained backups"
    assert retained == sorted(retained)
    assert {tmp_path / name for name in retained} == {
        path for path in tmp_path.rglob(".ai-dlc-*") if path.is_file()
    }
    template_backup = next(name for name in retained if name.startswith("docs/templates/"))
    assert (tmp_path / template_backup).read_bytes() == b"# One\n"
    if remove_export:
        assert not (tmp_path / "docs/templates/review-note.md").exists()
    else:
        assert (tmp_path / "docs/templates/review-note.md").read_bytes() == b"# Two\n"
    ownership = json.loads((tmp_path / ".ai-dlc/agent-ownership.json").read_text())
    assert set(retained).isdisjoint(ownership["files"])
    (tmp_path / template_backup).write_bytes(b"authored retained backup\r\n")
    residue = {name: (tmp_path / name).read_bytes() for name in retained}
    assert render_agents(tmp_path, apply=True) == {"clean": True, "changed": [], "applied": True}
    assert {name: (tmp_path / name).read_bytes() for name in retained} == residue


def test_bundle_render_recovery_preserves_authored_completed_stage_replacement(
    tmp_path, monkeypatch
):
    """Target conflict recovery must not unlink a replacement of the completed stage."""
    import os

    from ai_dlc import agents

    (tmp_path / "ai-dlc.toml").write_text(
        'schema=4\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# One\n")}
    )
    agents.render_agents(tmp_path, apply=True)
    destination = tmp_path / "docs/templates/review-note.md"
    ownership = tmp_path / ".ai-dlc/agent-ownership.json"
    ownership_before = ownership.read_bytes()
    _write_vendored_bundle(
        tmp_path, "review-flow", templates={"review-note": ("templates/note.md", "# Two\n")}
    )
    original_stage = agents._stage_render_file
    replacements = []

    def replace_completed_stage_then_edit_target(parent, content, mode):
        before = set(os.listdir(parent))
        staged = original_stage(parent, content, mode)
        if content == b"# Two\n":
            (name,) = set(os.listdir(parent)) - before
            authored = destination.parent / name
            authored.rename(tmp_path / "displaced-stage.md")
            authored.write_bytes(b"authored replacement of completed stage\r\n")
            replacements.append(authored)
            destination.write_bytes(b"late authored target edit\r\n")
        return staged

    monkeypatch.setattr(agents, "_stage_render_file", replace_completed_stage_then_edit_target)

    with pytest.raises((ValueError, OSError)):
        agents.render_agents(tmp_path, apply=True)

    assert replacements[0].read_bytes() == b"authored replacement of completed stage\r\n"
    assert destination.read_bytes() == b"late authored target edit\r\n"
    assert ownership.read_bytes() == ownership_before


@pytest.mark.parametrize("clients", [["antigravity"], ["codex", "antigravity"]])
def test_bundle_guidance_uses_native_shared_skill_directory(tmp_path, clients):
    from ai_dlc.agents import inspect_bundle_guidance, render_agents
    from ai_dlc.config import load_project

    manifest = tmp_path / "ai-dlc.toml"
    manifest.write_text(
        "schema=4\n[roles]\nagent-client="
        + json.dumps(clients)
        + '\n[agents]\nbundles=["review-flow"]\nskills=[]\n'
    )
    _write_vendored_bundle(
        tmp_path,
        "review-flow",
        skills={"review-flow": ("skills/review/SKILL.md", _skill("review-flow"))},
    )
    render_agents(tmp_path, apply=True)
    skill = tmp_path / ".agents/skills/review-flow/SKILL.md"
    assert skill.read_text() == _skill("review-flow")
    assert not (tmp_path / ".claude/skills/review-flow/SKILL.md").exists()
    assert render_agents(tmp_path)["clean"]
    assert (
        inspect_bundle_guidance(tmp_path, load_project(tmp_path), clients)[0]["status"] == "ready"
    )
    manifest.write_text(
        'schema=4\n[roles]\nagent-client=["antigravity"]\n[agents]\nbundles=[]\nskills=[]\n'
    )
    result = render_agents(tmp_path, apply=True, client="antigravity")
    assert not skill.exists()
    assert result["retained_backups"]
