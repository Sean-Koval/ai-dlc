"""Real scaffold and offline capability boundaries; no live service qualification."""

import shutil
import subprocess
import tomllib

import pytest
import yaml
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.files import assets
from ai_dlc.templates import adopt, sync


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_declared_toolset_plan_is_pure_and_extensible(monkeypatch):
    from ai_dlc import provider_definitions as definitions
    from ai_dlc.templates import plan_toolset

    monkeypatch.setitem(
        definitions.DEFINITIONS,
        "example-tracker",
        definitions.ProviderDefinition("example-tracker", ("tracker",)),
    )
    inputs = {"tracker": "example-tracker", "knowledge": "obsidian"}
    plan = plan_toolset(
        providers=inputs, agent_clients=["claude-code", "antigravity", "claude-code"]
    )
    assert plan["roles"]["tracker"] == "example-tracker"
    assert plan["roles"]["knowledge"] == "obsidian"
    assert plan["roles"]["agent-client"] == ["claude-code", "antigravity"]
    assert plan["providers"]["example-tracker"] == {"kind": "example-tracker"}
    assert inputs == {"tracker": "example-tracker", "knowledge": "obsidian"}


@pytest.mark.parametrize("preset", ["generic", "python", "node", "rust"])
def test_selected_toolset_preview_and_real_adoption(tmp_path, preset):
    root = tmp_path / preset
    options = {
        "preset": preset,
        "providers": {"tracker": "plane", "knowledge": "obsidian"},
        "agent_clients": ["claude-code", "antigravity"],
    }
    preview = adopt(root, **options)
    assert preview["status"] == "planned"
    assert not root.exists()
    assert preview["toolset"]["roles"]["tracker"] == "plane"
    assert any("lifecycle" in gap for gap in preview["toolset"]["limitations"])
    assert adopt(root, apply=True, **options)["status"] == "applied"
    config = tomllib.loads((root / "ai-dlc.toml").read_text())
    assert config["roles"]["tracker"] == "plane"
    assert config["roles"]["knowledge"] == "obsidian"
    assert config["roles"]["agent-client"] == ["claude-code", "antigravity"]
    assert config["providers"]["plane"] == {"kind": "plane"}
    assert "linear" not in config["providers"]
    answers = yaml.safe_load((root / ".copier-answers.yml").read_text())
    assert answers["tracker"] == "plane"
    assert answers["agent_clients"] == ["claude-code", "antigravity"]
    assert answers["knowledge"] == "obsidian"


@pytest.mark.parametrize(
    "options",
    [
        {"providers": {"tracker": "unknown"}},
        {"providers": {"tracker": "obsidian"}},
        {"providers": {"knowledge": "github-issues"}},
        {"agent_clients": ["unknown"]},
        {"capabilities": [], "agent_clients": ["claude-code"]},
        {"capabilities": [], "providers": {"knowledge": "obsidian"}},
    ],
)
def test_invalid_selections_refuse_before_destination_changes(tmp_path, options):
    before = snapshot(tmp_path)
    with pytest.raises(ValueError):
        adopt(tmp_path, apply=True, **options)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("command", ["init", "adopt"])
def test_project_cli_accepts_repeated_native_clients(tmp_path, command):
    root = tmp_path / command
    args = ["project", command]
    args += [str(root)] if command == "init" else ["--root", str(root), "--apply"]
    result = CliRunner().invoke(
        app,
        args
        + [
            "--tracker",
            "github-issues",
            "--knowledge",
            "obsidian",
            "--agent-client",
            "claude-code",
            "--agent-client",
            "antigravity",
            "--agent-client",
            "claude-code",
        ],
    )
    assert result.exit_code == 0, result.output
    assert tomllib.loads((root / "ai-dlc.toml").read_text())["roles"]["agent-client"] == [
        "claude-code",
        "antigravity",
    ]


def test_selected_native_render_uses_existing_owned_adapter(tmp_path):
    from ai_dlc.agents import render_agents

    adopt(
        tmp_path,
        apply=True,
        capabilities=["agent-client"],
        agent_clients=["claude-code", "antigravity"],
    )
    render_agents(tmp_path, apply=True)
    assert (tmp_path / ".agents/rules/ai-dlc.md").is_file()
    assert (tmp_path / ".claude/skills/discovery/SKILL.md").is_file()
    assert (tmp_path / ".agents/skills/discovery/SKILL.md").is_file()
    assert render_agents(tmp_path)["clean"]


def version_template(root, version):
    for args in [
        ("add", "."),
        ("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", version),
        ("tag", version),
    ]:
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.mark.parametrize("legacy", [False, True])
def test_real_copier_sync_preserves_selections_and_authored_content(tmp_path, legacy):
    template = tmp_path / "template"
    shutil.copytree(assets("project-templates"), template)
    subprocess.run(["git", "init", str(template)], check=True, capture_output=True)
    version_template(template, "v1.0.0")
    root = tmp_path / "project"
    options = (
        {} if legacy else {"providers": {"tracker": "plane"}, "agent_clients": ["antigravity"]}
    )
    adopt(root, apply=True, template_source=str(template), vcs_ref="v1.0.0", **options)
    if legacy:
        answers_path = root / ".copier-answers.yml"
        answers = yaml.safe_load(answers_path.read_text())
        for field in ("agent_clients", "knowledge", "tracker_settings"):
            answers.pop(field, None)
        answers_path.write_text(yaml.safe_dump(answers))
    config_path = root / "ai-dlc.toml"
    config_path.write_text(config_path.read_text() + "\n# authored project context\n")
    (template / "project/docs/architecture.md").write_text("# Improved architecture guidance\n")
    version_template(template, "v2.0.0")
    before = snapshot(root)
    assert sync(root)["status"] == "planned"
    assert snapshot(root) == before
    assert sync(root, apply=True)["status"] == "applied"
    assert "# authored project context" in config_path.read_text()
    config = tomllib.loads(config_path.read_text())
    assert config["roles"]["tracker"] == ("linear" if legacy else "plane")
    assert config["roles"]["agent-client"] == (
        ["claude-code", "codex"] if legacy else ["antigravity"]
    )
    assert config["gates"]["finish"] == ["specification-current", "pr-merged", "ci-green"]


def test_selected_adoption_preserves_authored_conflict(tmp_path):
    (tmp_path / "ai-dlc.toml").write_text("# mine\n")
    before = snapshot(tmp_path)
    result = adopt(
        tmp_path, apply=True, providers={"tracker": "plane"}, agent_clients=["antigravity"]
    )
    assert result["status"] == "conflict"
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("vault_state", ["missing", "absent", "file", "alias-only", "directory"])
def test_obsidian_runtime_vault_readiness_is_independent_of_optional_gui(tmp_path, vault_state):
    from ai_dlc.readiness import inspect_readiness

    vault = tmp_path / "vault"
    config = {
        "roles": {"knowledge": "private-notes"},
        "providers": {"private-notes": {"kind": "obsidian"}},
        "preferences": {"headless": True},
    }
    if vault_state in {"directory", "alias-only"}:
        vault.mkdir()
        (vault / "note.md").write_text("Private note; readiness must not read this.")
    elif vault_state == "file":
        vault.write_text("not a directory")
    if vault_state == "alias-only":
        config["providers"]["private-notes"]["vault_path"] = str(vault)
    elif vault_state != "missing":
        config["paths"] = {"vault": str(vault)}
    before = snapshot(tmp_path)
    result = inspect_readiness(
        tmp_path,
        config,
        environ={},
        probe=lambda _: pytest.fail("No executable or service probe needed"),
    )
    assert result["ready"] is (vault_state == "directory")
    rows = [c for c in result["checks"] if c["component"] == "obsidian"]
    assert any(
        c["dimension"] == "configuration"
        and c["status"] == ("ready" if vault_state == "directory" else "missing")
        for c in rows
    )
    assert any(c["dimension"] == "optional-viewer" and "headless" in c["reason"] for c in rows)
    assert result["qualification"] == "not-assessed"
    assert snapshot(tmp_path) == before
    assert "Private note" not in str(result)


def test_plane_guidance_cannot_mask_absent_lifecycle_adapter(tmp_path):
    from ai_dlc.agents import render_agents
    from ai_dlc.config import load_project
    from ai_dlc.readiness import inspect_readiness

    adopt(
        tmp_path,
        apply=True,
        capabilities=["tracker", "agent-client"],
        providers={"tracker": "plane"},
        agent_clients=["claude-code"],
    )
    render_agents(tmp_path, apply=True)
    result = inspect_readiness(
        tmp_path,
        load_project(tmp_path),
        environ={},
        probe=lambda _: pytest.fail("Plane has no required installed executable"),
    )
    assert not result["ready"]
    assert any(
        c["dimension"] == "lifecycle-adapter" and c["status"] == "blocked" for c in result["checks"]
    )
    assert any(
        c["component"] == "claude-code" and c["dimension"] == "guidance" and c["status"] == "ready"
        for c in result["checks"]
    )
    assert (tmp_path / ".ai-dlc/providers/plane.md").is_file()


def test_omitted_selection_preserves_legacy_provider_defaults(tmp_path):
    adopt(tmp_path, apply=True)
    config = tomllib.loads((tmp_path / "ai-dlc.toml").read_text())
    assert config["providers"] == {"linear": {"token_env": "LINEAR_API_KEY"}}


@pytest.mark.parametrize(
    "tamper",
    [
        {"tracker": "unregistered-tracker"},
        {"knowledge": "unregistered-knowledge"},
        {"agent_clients": ["unregistered-client"]},
        {"tracker_settings": {"kind": "unregistered-tracker"}},
    ],
)
def test_real_copier_update_refuses_tampered_selections_without_destination_writes(
    tmp_path, tamper
):
    template = tmp_path / "template"
    shutil.copytree(assets("project-templates"), template)
    subprocess.run(["git", "init", str(template)], check=True, capture_output=True)
    version_template(template, "v1.0.0")
    root = tmp_path / "project"
    adopt(
        root,
        apply=True,
        template_source=str(template),
        vcs_ref="v1.0.0",
        providers={"tracker": "github-issues"},
        agent_clients=["claude-code"],
    )
    answers_path = root / ".copier-answers.yml"
    answers = yaml.safe_load(answers_path.read_text())
    answers.update(tamper)
    answers_path.write_text(yaml.safe_dump(answers))
    (root / "authored.txt").write_text("Preserve user content")
    (template / "project/docs/architecture.md").write_text("# New revision\n")
    version_template(template, "v2.0.0")
    before = snapshot(root)
    with pytest.raises(ValueError):
        sync(root, apply=True)
    assert snapshot(root) == before


def test_real_copier_update_validates_new_defaults_before_applying(tmp_path):
    template = tmp_path / "template"
    shutil.copytree(assets("project-templates"), template)
    subprocess.run(["git", "init", str(template)], check=True, capture_output=True)
    version_template(template, "v1.0.0")
    root = tmp_path / "project"
    adopt(root, apply=True, template_source=str(template), vcs_ref="v1.0.0")
    answers_path = root / ".copier-answers.yml"
    answers = yaml.safe_load(answers_path.read_text())
    answers.pop("agent_clients")
    answers_path.write_text(yaml.safe_dump(answers))
    copier = template / "copier.yml"
    copier.write_text(
        copier.read_text().replace(
            "default: [claude-code, codex]", "default: [unregistered-client]"
        )
    )
    version_template(template, "v2.0.0")
    before = snapshot(root)
    with pytest.raises(ValueError):
        sync(root, apply=True)
    assert snapshot(root) == before
