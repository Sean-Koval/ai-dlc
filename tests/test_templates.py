import subprocess

import pytest

from ai_dlc.templates import adopt, sync


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def template(tmp_path):
    source = tmp_path / "template"
    source.mkdir()
    (source / "copier.yml").write_text("_subdirectory: project\n")
    project = source / "project"
    project.mkdir()
    (project / "{{ _copier_conf.answers_file }}.jinja").write_text(
        "{{ _copier_answers | to_nice_yaml }}"
    )
    (project / "managed.txt").write_text("first\nsecond\nthird\n")
    git(source, "init")
    git(source, "add", ".")
    git(source, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "v1")
    git(source, "tag", "v1.0.0")
    return source


def release(source, text):
    (source / "project/managed.txt").write_text(text)
    git(source, "add", ".")
    git(source, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "v2")
    git(source, "tag", "v2.0.0")


def test_adopt_preview_and_conflict_preserve(tmp_path, template):
    root = tmp_path / "app"
    root.mkdir()
    (root / "app.py").write_text("user code")
    assert adopt(root, template_source=str(template), vcs_ref="v1.0.0")["status"] == "planned"
    assert not (root / "managed.txt").exists()
    (root / "managed.txt").write_text("mine")
    result = adopt(root, apply=True, template_source=str(template))
    assert result["status"] == "conflict"
    assert (root / "managed.txt").read_text() == "mine"
    assert not (root / ".copier-answers.yml").exists()


def test_real_update_preserves_user_edits(tmp_path, template):
    root = tmp_path / "app"
    adopt(root, apply=True, template_source=str(template), vcs_ref="v1.0.0")
    (root / "app.py").write_text("my application")
    (root / "managed.txt").write_text("first\nsecond\nthird\nlocal addition\n")
    release(template, "upstream\nsecond\nthird\n")
    result = sync(root, apply=True)
    assert result["status"] == "applied"
    assert (root / "managed.txt").read_text() == "upstream\nsecond\nthird\nlocal addition\n"
    assert (root / "app.py").read_text() == "my application"
    assert not (root / ".git").exists()


def test_update_conflict_does_not_touch_destination(tmp_path, template):
    root = tmp_path / "app"
    adopt(root, apply=True, template_source=str(template), vcs_ref="v1.0.0")
    (root / "managed.txt").write_text("local\nsecond\nthird\n")
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    release(template, "upstream\nsecond\nthird\n")
    assert sync(root, apply=True)["status"] == "conflict"
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}


@pytest.mark.parametrize("preset", ["generic", "python", "node", "rust"])
def test_presets(tmp_path, preset):
    import tomllib

    root = tmp_path / preset
    assert adopt(root, preset, apply=True)["status"] == "applied"
    cfg = tomllib.loads((root / "ai-dlc.toml").read_text())
    assert cfg["schema"] == 4
    assert cfg["roles"]["deploy"] == "none"
    assert "repository" not in cfg.get("scm", {})
    assert (root / ".github/workflows/verify.yml").exists()
    assert not list((root / ".ai-dlc/work").glob("*.toml"))


@pytest.mark.parametrize("capabilities", [None, ["specs", "scm"], []])
def test_project_template_includes_workflow_handbook(tmp_path, capabilities):
    root = tmp_path / "project"

    assert adopt(root, apply=True, capabilities=capabilities)["status"] == "applied"

    expected = {
        "docs/development-workflow.md",
        "docs/workflows/brownfield.md",
        "docs/workflows/design-to-implementation.md",
        "docs/workflows/greenfield.md",
        "docs/workflows/tool-map.md",
    }
    generated = {path.relative_to(root).as_posix() for path in root.rglob("*.md")}
    assert expected <= generated
    handbook = (root / "docs/development-workflow.md").read_text()
    assert (
        "[Development workflow](docs/development-workflow.md)" in (root / "AI-DLC.md").read_text()
    )
    selected = (
        {
            "specs",
            "tracker",
            "knowledge",
            "scm",
            "deploy",
            "agent-client",
        }
        if capabilities is None
        else set(capabilities)
    )
    for role in ["specs", "tracker", "knowledge", "scm", "deploy", "agent-client"]:
        state = "configured" if role in selected else "not configured"
        assert f"- `{role}`: {state}" in handbook
    design_headings = {
        line
        for line in (root / "docs/templates/design.md").read_text().splitlines()
        if line.startswith("## ")
    }
    assert {
        "## Identity and links",
        "## Outcome and scope",
        "## User journey and states",
        "## System boundaries and interfaces",
        "## Decisions and rationale",
        "## Behavioral contract",
        "## Verification strategy",
        "## Delivery and recovery",
    } <= design_headings


def test_initialized_python_check_does_not_dirty_repository(tmp_path):
    from ai_dlc.project import check_project, setup_project

    root = tmp_path / "python"
    assert adopt(root, "python", apply=True, initialize=True)["status"] == "applied"
    setup_project(root, state_path=tmp_path / "setup.db", use_mise=False)
    git(root, "init")
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "fixture",
    )

    receipt = check_project(root, use_mise=False)

    assert [item["status"] for item in receipt["outcomes"]] == ["passed", "passed"]
    assert receipt["dirty"] is False
    assert git(root, "status", "--porcelain") == ""


def test_application_symlink_preserved(tmp_path, template):
    root = tmp_path / "app"
    root.mkdir()
    (root / "external").symlink_to(tmp_path / "other")
    assert adopt(root, apply=True, template_source=str(template))["status"] == "applied"
    assert (root / "external").is_symlink()


def test_managed_symlink_is_conflict(tmp_path, template):
    root = tmp_path / "app"
    root.mkdir()
    target = tmp_path / "other"
    target.write_text("outside")
    (root / "managed.txt").symlink_to(target)
    assert adopt(root, apply=True, template_source=str(template))["status"] == "conflict"
    assert target.read_text() == "outside"


def test_runtime_and_ignored_files_are_not_read_or_copied(tmp_path, template, monkeypatch):
    from pathlib import Path

    from ai_dlc import templates

    root = tmp_path / "app"
    adopt(root, apply=True, template_source=str(template), vcs_ref="v1.0.0")
    git(root, "init")
    (root / ".gitignore").write_text("generated-cache/\n")
    excluded = [
        ".venv",
        "node_modules",
        "target",
        ".ai-dlc/local",
        ".pytest_cache",
        "generated-cache",
    ]
    for name in excluded:
        path = root / name / "nested" / "payload.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"cache")
    read = Path.read_bytes

    def guarded_read(path):
        if path.name == "payload.bin":
            pytest.fail("Read excluded runtime file")
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    update = templates.copier.run_update

    def guarded_update(stage, **kwargs):
        for name in excluded:
            assert not (stage / name).exists()
        return update(stage, **kwargs)

    monkeypatch.setattr(templates.copier, "run_update", guarded_update)
    release(template, "upstream\nsecond\nthird\n")
    assert sync(root, apply=True)["status"] == "applied"
    for name in excluded:
        assert (root / name / "nested/payload.bin").exists()


def test_checkout_changed_during_stage_requires_retry(tmp_path, template, monkeypatch):
    from ai_dlc import templates

    root = tmp_path / "app"
    root.mkdir()
    application = root / "app.py"
    application.write_text("before")
    copy = templates.copier.run_copy

    def concurrent_edit(*args, **kwargs):
        result = copy(*args, **kwargs)
        application.write_text("concurrent edit")
        return result

    monkeypatch.setattr(templates.copier, "run_copy", concurrent_edit)
    with pytest.raises(ValueError, match="retry"):
        adopt(root, apply=True, template_source=str(template))
    assert application.read_text() == "concurrent edit"
    assert not (root / "managed.txt").exists()


def test_select_role_capabilities(tmp_path):
    import tomllib

    root = tmp_path / "minimal"
    adopt(root, apply=True, capabilities=["specs", "scm"])
    config = tomllib.loads((root / "ai-dlc.toml").read_text())
    assert config["roles"] == {"specs": "openspec", "scm": "github"}
    assert not config.get("providers", {}).get("linear")


def test_unselected_scm_omits_github_workflow(tmp_path):
    root = tmp_path / "minimal"
    adopt(root, apply=True, capabilities=["specs"])
    assert not (root / ".github").exists()


def test_new_upstream_ignore_rule_does_not_delete_application(tmp_path, template):
    root = tmp_path / "app"
    adopt(root, apply=True, template_source=str(template), vcs_ref="v1.0.0")
    (root / "app.py").write_text("valuable application")
    (template / "project/.gitignore").write_text("app.py\n")
    release(template, "upstream\nsecond\nthird\n")
    assert sync(root, apply=True)["status"] == "applied"
    assert (root / "app.py").read_text() == "valuable application"


@pytest.mark.parametrize(
    "preset,manifest,source",
    [
        ("python", "pyproject.toml", "src/main.py"),
        ("node", "package.json", "src/index.js"),
        ("rust", "Cargo.toml", "src/main.rs"),
    ],
)
def test_initialize_starters_and_adoption_preservation(tmp_path, preset, manifest, source):
    import tomllib

    initialized = tmp_path / ("New " + preset)
    adopt(initialized, preset, apply=True, initialize=True)
    config = tomllib.loads((initialized / "ai-dlc.toml").read_text())
    assert (initialized / manifest).exists()
    assert (initialized / source).exists()
    assert config["checks"]["required"] == ["generated", "language-check"]
    assert config["checks"]["commands"]["generated"] == "ai-dlc agents render --check"
    existing = tmp_path / ("existing-" + preset)
    existing.mkdir()
    (existing / manifest).write_text("user-authored manifest")
    assert adopt(existing, preset, apply=True)["status"] == "applied"
    assert (existing / manifest).read_text() == "user-authored manifest"
    assert not (existing / source).exists()
    assert tomllib.loads((existing / "ai-dlc.toml").read_text())["checks"]["required"] == [
        "generated"
    ]


def test_generic_requires_generated_check(tmp_path):
    import tomllib

    adopt(tmp_path, apply=True, initialize=True)
    config = tomllib.loads((tmp_path / "ai-dlc.toml").read_text())
    assert config["checks"]["required"] == ["generated"]
    assert config["setup"]["steps"] == []


@pytest.mark.parametrize(
    "preset,tool,source,lock",
    [
        ("python", "uv", "src/main.py", "uv.lock"),
        ("node", "npm", "src/index.js", "package-lock.json"),
        ("rust", "cargo", "src/main.rs", "Cargo.lock"),
    ],
)
def test_initialized_setup_and_language_check_offline(tmp_path, preset, tool, source, lock):
    import os
    import shutil
    import sys
    import tomllib
    from pathlib import Path

    from ai_dlc.agents import render_agents

    if not shutil.which(tool):
        pytest.skip(f"{tool} unavailable")
    root = tmp_path / preset
    adopt(root, preset, apply=True, initialize=True)
    render_agents(root, apply=True)
    config = tomllib.loads((root / "ai-dlc.toml").read_text())
    env = {
        **os.environ,
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
        "UV_OFFLINE": "1",
        "UV_PYTHON": sys.executable,
        "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
        "npm_config_offline": "true",
        "npm_config_cache": str(tmp_path / "npm-cache"),
        "CARGO_NET_OFFLINE": "true",
    }

    def run(command):
        return subprocess.run(
            command,
            shell=True,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    command = config["setup"]["steps"][0]["command"]
    result = run(command)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / lock).exists()
    before_lock = (root / lock).read_bytes()
    result = run(command)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / lock).read_bytes() == before_lock
    for check in config["checks"]["required"]:
        result = run(config["checks"]["commands"][check])
        assert result.returncode == 0, result.stdout + result.stderr
    (root / source).write_text("this is deliberately invalid syntax !!!\n")
    assert run(config["checks"]["commands"]["language-check"]).returncode != 0
