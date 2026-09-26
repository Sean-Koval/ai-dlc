"""Team source acceptance uses only disposable local Git repositories."""

import json
import os
import subprocess

import pytest
import tomli_w

from ai_dlc.config import resolve_layers
from ai_dlc.environment.enrollment import EnrollmentPaths, read_lock
from ai_dlc.environment.machine import MachineManager
from ai_dlc.harness.agents import managed_section, read_managed_section, render_agents
from ai_dlc.harness.hooks import handle_hook

SKILL = (
    "---\nname: team-review\ndescription: Review team code\n---\nUse the team review checklist.\n"
)


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
    ).stdout.strip()


def write(root, path, body):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body)
    return target


def commit(root):
    git(root, "add", ".")
    git(root, "commit", "-m", "fixture")
    return git(root, "rev-parse", "HEAD")


def native_files():
    return {
        "skills/team-review/SKILL.md": SKILL,
        "rules/review.md": "Team review rule.\n",
        "manifest.toml": tomli_w.dumps(
            {
                "schema": 1,
                "items": [
                    {
                        "kind": "skill",
                        "name": "team-review",
                        "path": "skills/team-review/SKILL.md",
                        "roles": ["developer"],
                        "tags": ["review"],
                    },
                    {"kind": "rule", "name": "review", "path": "rules/review.md"},
                ],
            }
        ),
    }


@pytest.fixture
def source_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")

    def setup(files=None, layout="ai-dlc", roles=None, tags=None):
        repository = tmp_path / "team"
        repository.mkdir()
        git(repository, "init", "-b", "main")
        git(repository, "config", "user.name", "Test")
        git(repository, "config", "user.email", "test@example.test")
        for path, body in (native_files() if files is None else files).items():
            write(repository, path, body)
        revision = commit(repository)
        bare = tmp_path / "team.git"
        git(tmp_path, "clone", "--bare", str(repository), str(bare))
        profile = tmp_path / "profile"
        profile.mkdir()
        git(profile, "init", "-b", "main")
        git(profile, "config", "user.name", "Test")
        git(profile, "config", "user.email", "test@example.test")
        definition = {
            "id": "team",
            "git": str(bare),
            "ref": "main",
            "layout": layout,
            "roles": roles or [],
            "tags": tags or [],
        }
        write(
            profile,
            "ai-dlc-profile.toml",
            tomli_w.dumps(
                {
                    "schema": 4,
                    "profile_id": "test",
                    "sources": [definition],
                    "modules": {"include": []},
                }
            ),
        )
        commit(profile)
        home = tmp_path / "home"
        for name in ["CONFIG", "CACHE", "STATE"]:
            monkeypatch.setenv(f"XDG_{name}_HOME", str(home / name.lower()))
        paths = EnrollmentPaths.from_environment(home=home)
        service = MachineManager(home=home, paths=paths)
        project = tmp_path / "project"
        project.mkdir()
        git(project, "init", "-b", "main")
        write(
            project,
            "ai-dlc.toml",
            'schema=4\n[roles]\nagent-client=["codex", "claude-code"]\n[agents]\nskills=[]\n',
        )
        return repository, bare, profile, revision, paths, service, project

    return setup


def enroll(setup):
    _, _, profile, _, _, service, _ = setup
    return service.enroll(str(profile), "test", "laptop", apply=True)


def test_enroll_locks_source_and_preview_is_not_active(source_setup):
    setup = source_setup()
    _, _, profile, revision, paths, service, _ = setup
    result = service.enroll(str(profile), "test", "laptop")
    assert result["lock"]["sources"][0]["resolved_commit"] == revision
    assert not paths.lock_file.exists()
    enroll(setup)
    assert read_lock(paths).sources[0].resolved_commit == revision


@pytest.mark.parametrize(
    "roles,tags,present",
    [
        ([], [], False),
        (["developer"], [], True),
        ([], ["review"], True),
        (["other"], ["other"], False),
    ],
)
def test_selected_source_skills_and_rules_render(source_setup, roles, tags, present):
    setup = source_setup(roles=roles, tags=tags)
    enroll(setup)
    root = setup[-1]
    render_agents(root, apply=True)
    text = (root / "AGENTS.md").read_text()
    assert ("team-review" in text) is present
    assert "Team review rule." in text
    assert (root / ".agents/skills/team-review/SKILL.md").exists() is present
    if present:
        assert "Use the team review checklist." not in text
        assert "Review team code" in text
        assert "[antigravity, codex]" not in text
        assert "[codex](<.agents/skills/team-review/SKILL.md>)" in text
        assert "[claude-code](<.claude/skills/team-review/SKILL.md>)" in text
        for directory in (".agents", ".claude"):
            assert (root / directory / "skills/team-review/SKILL.md").read_text() == SKILL
    assert render_agents(root)["clean"]


@pytest.mark.parametrize(
    "body,expected",
    [
        ("No frontmatter.\n", "Read the linked skill for its instructions."),
        (
            "---\nname: team-review\ndescription: [malformed\n---\nBody.\n",
            "Read the linked skill for its instructions.",
        ),
        (
            "---\nname: team-review\ndescription: [not, a, string]\n---\nBody.\n",
            "Read the linked skill for its instructions.",
        ),
        (
            "---\nname: team-review\ndescription: '  '\n---\nBody.\n",
            "Read the linked skill for its instructions.",
        ),
        (
            (
                "---\nname: team-review\ndescription: >-\n"
                "  First *bold* line\n"
                "  [link](target) <tag>\u200b\n"
                "---\nBody.\n"
            ),
            r"First \*bold\* line \[link\]\(target\) &lt;tag&gt;",
        ),
        (
            "---\nname: team-review\ndescription: " + "a" * 250 + "\n---\nBody.\n",
            "a" * 239 + "…",
        ),
    ],
)
def test_skill_discovery_description_is_safe_bounded_or_falls_back(source_setup, body, expected):
    files = native_files()
    files["skills/team-review/SKILL.md"] = body
    setup = source_setup(files, roles=["developer"])
    enroll(setup)
    root = setup[-1]

    render_agents(root, apply=True)

    agents = (root / "AGENTS.md").read_text()
    entry = next(line for line in agents.splitlines() if line.startswith("- `team-review`"))
    assert expected in entry
    assert len(entry.split(": ", 1)[1].split(" — ", 1)[0]) <= 240
    assert (root / ".agents/skills/team-review/SKILL.md").read_text() == body


@pytest.mark.parametrize(
    "clients,render_client,expected_links,missing_links",
    [
        (["claude-code"], None, [".claude"], [".agents"]),
        (["codex"], None, [".agents"], [".claude"]),
        (["antigravity"], None, [".agents"], [".claude"]),
        (
            ["claude-code", "codex", "antigravity"],
            None,
            [".agents", ".claude"],
            [],
        ),
        (["claude-code", "codex"], "claude-code", [".claude"], [".agents"]),
    ],
)
def test_skill_discovery_lists_each_effective_destination_once(
    source_setup, clients, render_client, expected_links, missing_links
):
    setup = source_setup(roles=["developer"])
    enroll(setup)
    root = setup[-1]
    write(
        root,
        "ai-dlc.toml",
        "schema=4\n[roles]\nagent-client=" + json.dumps(clients) + "\n[agents]\nskills=[]\n",
    )
    retained = None
    if render_client:
        render_agents(root, apply=True)
        retained = (root / ".agents/skills/team-review/SKILL.md").read_bytes()

    render_agents(root, apply=True, client=render_client)

    agents = (root / "AGENTS.md").read_text()
    entry = next(line for line in agents.splitlines() if line.startswith("- `team-review`"))
    for directory in expected_links:
        path = f"{directory}/skills/team-review/SKILL.md"
        assert entry.count(f"](<{path}>)") == 1
        assert (root / path).read_text() == SKILL
    for directory in missing_links:
        assert f"{directory}/skills/team-review/SKILL.md" not in entry
    if retained is not None:
        assert (root / ".agents/skills/team-review/SKILL.md").read_bytes() == retained
    if clients == ["claude-code", "codex", "antigravity"]:
        assert "[antigravity, codex](<.agents/skills/team-review/SKILL.md>)" in entry


def test_no_client_render_keeps_complete_selected_skills_inline(source_setup):
    setup = source_setup(roles=["developer"])
    enroll(setup)
    root = setup[-1]
    write(root, "ai-dlc.toml", "schema=4\n[roles]\nagent-client=[]\n[agents]\nskills=[]\n")

    render_agents(root, apply=True)

    agents = (root / "AGENTS.md").read_text()
    assert "### Team skill: team-review (team)" in agents
    assert SKILL in agents
    assert not (root / ".agents").exists()
    assert not (root / ".claude").exists()


def test_intact_inline_guidance_migrates_without_touching_authored_text(source_setup):
    setup = source_setup(roles=["developer"])
    enroll(setup)
    root = setup[-1]
    render_agents(root, apply=True)
    agents = root / "AGENTS.md"
    current = agents.read_text()
    managed = read_managed_section(current)
    shared = managed["body"].split("\n## Team sources", 1)[0]
    legacy_body = (
        shared
        + "\n## Team sources\n\n"
        + "### Team skill: team-review (team)\n\n"
        + SKILL
        + "\n### Team rule: review (team)\n\nTeam review rule.\n"
    )
    agents.write_text("Authored preface.\n\n" + managed_section("", legacy_body))
    ownership_path = root / ".ai-dlc/agent-ownership.json"
    ownership = json.loads(ownership_path.read_text())
    before = {
        "agents": agents.read_bytes(),
        "ownership": ownership_path.read_bytes(),
        "skill": (root / ".agents/skills/team-review/SKILL.md").read_bytes(),
    }

    preview = render_agents(root)
    assert not preview["clean"]
    assert agents.read_bytes() == before["agents"]
    assert ownership_path.read_bytes() == before["ownership"]
    assert (root / ".agents/skills/team-review/SKILL.md").read_bytes() == before["skill"]
    render_agents(root, apply=True)

    migrated = agents.read_text()
    assert migrated.startswith("Authored preface.\n\n")
    assert "Use the team review checklist." not in migrated
    assert (root / ".agents/skills/team-review/SKILL.md").read_text() == SKILL
    current_ownership = json.loads(ownership_path.read_text())
    assert current_ownership["source_skills"] == ownership["source_skills"]
    assert current_ownership["source_directories"] == ownership["source_directories"]
    assert render_agents(root)["clean"]


def test_long_skill_body_does_not_increase_managed_guidance_bytes(monkeypatch, tmp_path):
    from ai_dlc.environment.source_content import SourceItem
    from ai_dlc.environment.team_sources import SelectedSources

    description = "Stable deterministic description"
    short = f"---\nname: team-review\ndescription: {description}\n---\nShort body.\n"
    long = f"---\nname: team-review\ndescription: {description}\n---\n" + "Long body.\n" * 600
    current = {"body": short}
    monkeypatch.setattr(
        "ai_dlc.harness.agents.enrolled_sources",
        lambda: SelectedSources(
            [("team", SourceItem("skill", "team-review", "skill.md", body=current["body"]))],
            enrolled=True,
        ),
    )

    counts = {}
    for label, body in [("short", short), ("long", long)]:
        current["body"] = body
        root = tmp_path / label
        root.mkdir()
        write(root, "ai-dlc.toml", 'schema=4\n[roles]\nagent-client=["codex"]\n[agents]\n')
        render_agents(root, apply=True)
        managed = read_managed_section((root / "AGENTS.md").read_text())["body"].encode()
        exported = (root / ".agents/skills/team-review/SKILL.md").read_bytes()
        assert exported == body.encode()
        counts[label] = (len(managed), len(exported), managed)

    assert counts["short"][0] == counts["long"][0]
    assert counts["short"][2] == counts["long"][2]
    long_prefix = counts["long"][2].split(b"\n## Team sources", 1)[0]
    legacy = (
        long_prefix
        + b"\n## Team sources\n\n### Team skill: team-review (team)\n\n"
        + long.encode().rstrip()
        + b"\n"
    )
    assert counts["long"][0] < len(legacy)


def test_machine_roles_are_additive_and_can_deselect(source_setup):
    setup = source_setup()
    enroll(setup)
    paths, root = setup[4], setup[-1]
    paths.machine_file("laptop").write_text('schema=4\nroles=["developer"]\n')
    resolved = resolve_layers(
        [
            ("personal", {"schema": 4, "roles": {"scm": "github"}}),
            ("machine", {"schema": 4, "roles": ["developer"]}),
        ]
    )
    assert resolved.values["roles"]["scm"] == "github"
    render_agents(root, apply=True)
    assert "team-review" in (root / "AGENTS.md").read_text()
    paths.machine_file("laptop").write_text("schema=4\nroles=[]\n")
    render_agents(root, apply=True)
    assert not (root / ".agents/skills/team-review/SKILL.md").exists()
    paths.machine_file("laptop").write_text('schema=4\nroles=["developer"]\n')
    render_agents(root, apply=True)
    for directory in (".agents", ".claude"):
        assert (root / directory / "skills/team-review/SKILL.md").read_text() == SKILL


@pytest.mark.parametrize("layer", ["machine", "project"])
def test_sources_cannot_be_set_outside_personal(layer):
    with pytest.raises(ValueError, match="cannot set sources"):
        resolve_layers([(layer, {"schema": 4, "sources": []})])


@pytest.mark.parametrize("kind", ["symlink", "executable", "env", "oversized", "undeclared"])
def test_unsafe_source_refused_before_enrollment(source_setup, kind):
    setup = source_setup()
    repository, bare, profile, _, paths, service, _ = setup
    if kind == "symlink":
        (repository / "rules/escape.md").symlink_to("/etc/passwd")
        path = "rules/escape.md"
    elif kind == "executable":
        path = "rules/review.md"
        (repository / path).chmod(0o755)
    elif kind == "env":
        path = "env/settings.toml"
        write(repository, path, 'MODE="development"\n')
    elif kind == "oversized":
        path = "rules/review.md"
        write(repository, path, "a" * (2 * 1024 * 1024 + 1))
    else:
        path = "extra.txt"
        write(repository, path, "undeclared")
    commit(repository)
    git(repository, "push", str(bare), "main")
    with pytest.raises(ValueError, match=path):
        service.enroll(str(profile), "test", "laptop", apply=True)
    assert not paths.lock_file.exists()


def test_ref_move_requires_explicit_sync_and_notice_is_read_only(source_setup, monkeypatch):
    from ai_dlc.setup import provision

    # Package reconciliation is independently covered; keep this Git acceptance offline.
    monkeypatch.setattr(provision, "machine_apply", lambda *args, **kwargs: {"ready": True})
    setup = source_setup(roles=["developer"])
    repository, bare, _, _, paths, service, root = setup
    enroll(setup)
    render_agents(root, apply=True)
    before = (root / "AGENTS.md").read_bytes()
    before_skill = (root / ".agents/skills/team-review/SKILL.md").read_bytes()
    old_lock = paths.lock_file.read_bytes()
    write(repository, "rules/review.md", "Updated team review rule.\n")
    updated_skill = (
        "---\nname: team-review\ndescription: Updated team review\n---\n"
        "Use the updated team review checklist.\n"
    )
    write(repository, "skills/team-review/SKILL.md", updated_skill)
    revision = commit(repository)
    git(repository, "push", str(bare), "main")
    notice = handle_hook(root, "session-start", {})["context"]
    assert "team source team has a newer revision; run `ai-dlc machine sync`" in notice
    assert paths.lock_file.read_bytes() == old_lock
    assert render_agents(root)["clean"]
    preview = service.sync()
    assert preview["lock"]["sources"][0]["resolved_commit"] == revision
    assert paths.lock_file.read_bytes() == old_lock
    render_agents(root, apply=True)
    assert (root / "AGENTS.md").read_bytes() == before
    assert (root / ".agents/skills/team-review/SKILL.md").read_bytes() == before_skill
    assert service.sync(apply=True)["applied"]
    render_agents(root, apply=True)
    agents = (root / "AGENTS.md").read_text()
    assert "Updated team review rule." in agents
    assert "Updated team review" in agents
    assert "Use the updated team review checklist." not in agents
    assert (root / ".agents/skills/team-review/SKILL.md").read_text() == updated_skill


@pytest.mark.parametrize("same_bytes", [False, True])
def test_local_skill_collision_does_not_write(source_setup, same_bytes):
    setup = source_setup(roles=["developer"])
    enroll(setup)
    root = setup[-1]
    write(root, ".agents/skills/team-review/SKILL.md", SKILL if same_bytes else "Local skill")
    with pytest.raises(ValueError, match="skill.*conflict|collision"):
        render_agents(root, apply=True)
    assert not (root / "AGENTS.md").exists()


def test_corrupt_cached_source_refused_offline(source_setup):
    setup = source_setup(roles=["developer"])
    enroll(setup)
    paths, root = setup[4], setup[-1]
    cache_file = next(paths.cache_root.rglob("rules/review.md"))
    cache_file.write_text("tampered")
    with pytest.raises((ValueError, RuntimeError), match="digest|corrupt"):
        render_agents(root, apply=True)
    assert not (root / "AGENTS.md").exists()


def teamai_files():
    return {
        "skills/team-review/SKILL.md": SKILL,
        "rules/review.md": "Teamai review rule.\n",
        "culture.md": "Our team culture.\n",
        "mcp/mcp.yaml": "servers:\n  - name: team-tools\n    transport: stdio\n    command: team-mcp\n    args: [serve]\n",
        "hooks/hooks.yaml": "hooks: []\n",
        "agents/reviewer.yaml": "name: reviewer\n",
        "docs/readme.md": "Ignored documentation\n",
        "teamai.yaml": "tags:\n  skills:\n    team-review: [review]\n",
    }


def test_teamai_layout_selection_mcp_and_ignored_notes(source_setup):
    setup = source_setup(teamai_files(), layout="teamai", tags=["review"])
    result = enroll(setup)
    assert any("hooks/hooks.yaml" in note for note in result["source_notes"])
    root = setup[-1]
    rendered = render_agents(root, apply=True)
    assert rendered["source_notes"]
    text = (root / "AGENTS.md").read_text()
    assert "team-review" in text and "Teamai review rule." in text and "Our team culture." in text
    assert "Use the team review checklist." not in text
    assert (root / ".agents/skills/team-review/SKILL.md").read_text() == SKILL
    assert (
        json.loads((root / ".mcp.json").read_text())["mcpServers"]["team-tools"]["command"]
        == "team-mcp"
    )
    assert "Ignored documentation" not in text


@pytest.mark.parametrize(
    "path,body",
    [
        ("env/env.yaml", "MODE: dev\n"),
        (
            "mcp/mcp.yaml",
            "servers:\n  - name: team-tools\n    command: tool\n    token: fixture-secret-do-not-echo\n",
        ),
        (
            "mcp/mcp.yaml",
            'servers:\n  - name: team-tools\n    command: tool\n    args: ["--token=fixture-secret-do-not-echo"]\n',
        ),
    ],
)
def test_teamai_unsafe_values_name_path_without_leaking(source_setup, path, body):
    files = teamai_files()
    files[path] = body
    setup = source_setup(files, layout="teamai")
    with pytest.raises(ValueError, match=path) as raised:
        enroll(setup)
    assert "fixture-secret-do-not-echo" not in str(raised.value)
    assert not setup[4].lock_file.exists()


def test_native_mcp_and_named_hooks_render(source_setup):
    files = native_files()
    files["mcp/servers.toml"] = '[[servers]]\nid="team-tools"\ncommand="team-mcp"\nargs=["serve"]\n'
    files["hooks/hooks.toml"] = 'features=["session-context"]\n'
    files["manifest.toml"] += (
        '\n[[items]]\nkind="mcp"\nname="team-tools"\npath="mcp/servers.toml"\n\n[[items]]\nkind="hook"\nname="session-context"\npath="hooks/hooks.toml"\n'
    )
    setup = source_setup(files)
    enroll(setup)
    root = setup[-1]
    write(
        root,
        "ai-dlc.toml",
        'schema=4\n[roles]\nagent-client=["claude-code"]\n[agents]\nskills=[]\n[agents.clients.claude-code]\nversion="2.1.0"\n',
    )
    render_agents(root, apply=True)
    assert "SessionStart" in json.loads((root / ".claude/settings.json").read_text())["hooks"]
    assert "team-tools" in json.loads((root / ".mcp.json").read_text())["mcpServers"]


@pytest.mark.parametrize(
    "body",
    [
        "servers: []\nservers: []\n",
        "servers: &servers []\nother: *servers\n",
        "servers:\n  - name: team-tools\n    command: tool\n    env: {MODE: dev}\n",
    ],
)
def test_teamai_yaml_is_fail_closed(source_setup, body):
    files = teamai_files()
    files["mcp/mcp.yaml"] = body
    setup = source_setup(files, layout="teamai")
    with pytest.raises(ValueError, match="mcp/mcp.yaml"):
        enroll(setup)


def test_ignored_teamai_yaml_cannot_hide_environment_values(source_setup):
    files = teamai_files()
    files["agents/reviewer.yaml"] = "name: reviewer\nenv: {MODE: dev}\n"
    setup = source_setup(files, layout="teamai")
    with pytest.raises(ValueError, match="agents/reviewer.yaml"):
        enroll(setup)


def test_owned_markers_are_not_accepted_in_source_markdown(source_setup):
    files = native_files()
    files["rules/review.md"] = "Example <!-- ai-dlc:end -->\n"
    setup = source_setup(files)
    with pytest.raises(ValueError, match="rules/review.md"):
        enroll(setup)


def test_corrupt_team_cache_marks_machine_not_ready(source_setup):
    setup = source_setup()
    enroll(setup)
    paths, service = setup[4:6]
    next(paths.cache_root.rglob("rules/review.md")).write_text("tampered")
    status = service.status()
    assert not status["ready"]
    assert "team source cache is corrupt" in status["drift"]


def test_sync_invalid_source_keeps_old_revision(source_setup):
    setup = source_setup()
    repository, bare, _, _, paths, service, root = setup
    enroll(setup)
    prior = paths.lock_file.read_bytes()
    write(repository, "env/bad.toml", 'MODE="dev"')
    commit(repository)
    git(repository, "push", str(bare), "main")
    with pytest.raises(RuntimeError, match="active lock preserved"):
        service.sync(apply=True)
    assert paths.lock_file.read_bytes() == prior
    render_agents(root, apply=True)
    assert "Team review rule." in (root / "AGENTS.md").read_text()


def test_source_rejects_empty_local_skill_directory(source_setup):
    setup = source_setup(roles=["developer"])
    enroll(setup)
    root = setup[-1]
    (root / ".agents/skills/team-review").mkdir(parents=True)
    with pytest.raises(ValueError, match="skill.*conflict|collision"):
        render_agents(root, apply=True)
    assert not (root / "AGENTS.md").exists()


def test_actual_teamai_role_and_tag_files_select_namespaced_skill(source_setup):
    files = teamai_files()
    files["skills/backend/team-review/SKILL.md"] = files.pop("skills/team-review/SKILL.md")
    files["teamai.yaml"] = "name: Team\n"
    files["manifest/roles.yaml"] = (
        "version: 1\nroles:\n  - id: developer\n    resources:\n      skills: [backend]\n      knowledge: []\n"
    )
    files["tags.yaml"] = "skills:\n  team-review: [review]\n"
    setup = source_setup(files, layout="teamai", roles=["developer"])
    enroll(setup)
    render_agents(setup[-1], apply=True)
    assert "team-review" in (setup[-1] / "AGENTS.md").read_text()


def test_disabled_shipped_skill_names_remain_reserved(source_setup):
    files = native_files()
    files["skills/day-start/SKILL.md"] = files.pop("skills/team-review/SKILL.md").replace(
        "team-review", "day-start"
    )
    files["manifest.toml"] = files["manifest.toml"].replace("team-review", "day-start")
    setup = source_setup(files, roles=["developer"])
    enroll(setup)
    with pytest.raises(ValueError, match="skill collision: day-start"):
        render_agents(setup[-1], apply=True)
    assert not (setup[-1] / "AGENTS.md").exists()


@pytest.mark.parametrize("layout", ["ai-dlc", "teamai"])
@pytest.mark.parametrize("flag", ["--token", "--api-key", "--client-secret"])
def test_mcp_separate_secret_arguments_are_refused(source_setup, layout, flag):
    files = teamai_files() if layout == "teamai" else native_files()
    if layout == "teamai":
        path = "mcp/mcp.yaml"
        files[path] = (
            f'servers:\n  - name: team-tools\n    command: tool\n    args: ["{flag}", "SENTINEL123"]\n'
        )
    else:
        path = "mcp/servers.toml"
        files[path] = tomli_w.dumps(
            {"servers": [{"id": "team-tools", "command": "tool", "args": [flag, "SENTINEL123"]}]}
        )
        files["manifest.toml"] += (
            '\n[[items]]\nkind="mcp"\nname="team-tools"\npath="mcp/servers.toml"\n'
        )
    setup = source_setup(files, layout=layout)
    with pytest.raises(ValueError, match=path) as raised:
        enroll(setup)
    assert "SENTINEL123" not in str(raised.value)
    assert not setup[4].lock_file.exists()


@pytest.mark.parametrize("layout", ["ai-dlc", "teamai"])
@pytest.mark.parametrize(
    "assignment",
    [
        '{"token": "SENTINEL123"}',
        '"password": "SENTINEL123"',
        "'api_key' : 'SENTINEL123'",
        '"secret" = "SENTINEL123"',
    ],
)
def test_source_markdown_quoted_credentials_are_refused(source_setup, layout, assignment):
    files = teamai_files() if layout == "teamai" else native_files()
    files["rules/review.md"] = f"# Security\n\n```text\n{assignment}\n```\n"
    setup = source_setup(files, layout=layout)
    with pytest.raises(ValueError, match="rules/review.md") as raised:
        enroll(setup)
    assert "SENTINEL123" not in str(raised.value)
    assert not setup[4].lock_file.exists()


@pytest.mark.parametrize("layout", ["ai-dlc", "teamai"])
def test_source_rules_can_discuss_secret_hygiene(source_setup, layout):
    files = teamai_files() if layout == "teamai" else native_files()
    files["rules/review.md"] = (
        "Never commit a token to Git. Keep password values in your keychain.\n"
        'Never commit a "token" to Git.\n'
    )
    setup = source_setup(files, layout=layout)
    enroll(setup)
    render_agents(setup[-1], apply=True)
    assert files["rules/review.md"] in (setup[-1] / "AGENTS.md").read_text()


def test_teamai_underscore_roles_and_namespaces(source_setup):
    files = teamai_files()
    files["skills/hai_core/team-review/SKILL.md"] = files.pop("skills/team-review/SKILL.md")
    files["teamai.yaml"] = "name: Team\n"
    files["manifest/roles.yaml"] = (
        "version: 1\nroles:\n  - id: hai_dev\n    resources:\n      skills: [hai_core]\n      knowledge: []\n"
    )
    setup = source_setup(files, layout="teamai", roles=["hai_dev"])
    enroll(setup)
    setup[4].machine_file("laptop").write_text('schema=4\nroles=["hai_dev"]\n')
    render_agents(setup[-1], apply=True)
    assert "team-review" in (setup[-1] / "AGENTS.md").read_text()
