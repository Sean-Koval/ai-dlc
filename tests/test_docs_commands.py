"""The documentation workflow lives under `ai-dlc docs`; the legacy names stay as aliases."""

import json
import subprocess

import pytest
from click import unstyle
from typer.testing import CliRunner

DOCS_COMMANDS = {"check", "review", "gate", "read", "search", "init"}
LEGACY = [
    "docs-init",
    "docs-check",
    "docs-impact",
    "docs-disposition",
    "docs-baseline",
    "docs-style",
    "docs-inventory",
    "docs-search",
    "docs-read",
    "docs-review",
    "docs-review-check",
    "docs-gate",
]


@pytest.fixture
def project(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    (tmp_path / "docs").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "docs/api.md").write_text("# API\n\nVersion one.\n")
    (tmp_path / "src/api.py").write_text("VERSION = 1\n")
    (tmp_path / "docs/catalog.toml").write_text("""schema = 1
[[documents]]
id = "api"
path = "docs/api.md"
kind = "reference"
owner = "maintainers"
status = "active"
code_paths = ["src/*.py"]
""")
    git("add", ".")
    git("commit", "-qm", "baseline")
    (tmp_path / "src/api.py").write_text("VERSION = 2\n")
    return tmp_path


def click_group(name: str):
    import typer.main

    from ai_dlc.cli import app

    root = typer.main.get_command(app)
    return root.get_command(None, name)  # type: ignore[attr-defined]


def visible_commands(group) -> set[str]:
    return {n for n in group.list_commands(None) if not group.get_command(None, n).hidden}


def invoke(*args):
    from ai_dlc.cli import app

    return CliRunner().invoke(app, list(args))


def test_docs_group_lists_exactly_its_six_commands():
    docs = click_group("docs")
    assert visible_commands(docs) == DOCS_COMMANDS
    result = invoke("docs", "--help")
    assert result.exit_code == 0
    for name in DOCS_COMMANDS:
        assert name in unstyle(result.stdout)


def test_no_empty_group_is_registered():
    import typer.main

    from ai_dlc.cli import app

    root = typer.main.get_command(app)
    for name in root.list_commands(None):  # type: ignore[attr-defined]
        command = root.get_command(None, name)  # type: ignore[attr-defined]
        if hasattr(command, "list_commands"):
            assert command.list_commands(None), f"{name} is an empty group"
    assert visible_commands(click_group("design")) == {"capture"}
    assert root.get_command(None, "tracker") is None  # type: ignore[attr-defined]


def test_legacy_names_are_hidden_but_still_named_for_the_installation_probe():
    from ai_dlc.documentation.workspace_diagnostics import REQUIRED_COMMANDS

    project = click_group("project")
    for name in LEGACY:
        assert project.get_command(None, name).hidden, name
    assert not visible_commands(project) & set(LEGACY)
    listing = unstyle(invoke("project", "--help").stdout)
    for name in REQUIRED_COMMANDS:
        assert name in listing


def test_legacy_alias_keeps_stdout_and_exit_status_and_warns_once(project):
    new = invoke("docs", "check", "--root", str(project), "--strict")
    old = invoke("project", "docs-check", "--root", str(project), "--strict")
    assert new.exit_code == old.exit_code == 2
    assert json.loads(new.stdout) == json.loads(old.stdout)
    assert new.stderr == ""
    lines = old.stderr.strip().splitlines()
    assert len(lines) == 1
    assert "ai-dlc project docs-check" in lines[0] and "ai-dlc docs check" in lines[0]


def test_check_modes_are_exclusive_and_style_needs_a_path(project, monkeypatch):
    from ai_dlc.documentation.document_inventory import inventory_documents

    inventory = invoke("docs", "check", "--root", str(project), "--inventory")
    assert inventory.exit_code == 0, inventory.output
    assert json.loads(inventory.stdout) == inventory_documents(project)
    assert json.loads(inventory.stdout) == json.loads(
        invoke("project", "docs-inventory", "--root", str(project)).stdout
    )
    monkeypatch.setenv("PATH", "")
    style = invoke("docs", "check", "--root", str(project), "--style", "--path", "docs/api.md")
    assert style.exit_code == 0, style.output
    assert json.loads(style.stdout)["tool"] == "vale"
    assert invoke("docs", "check", "--root", str(project), "--style", "--strict").exit_code == 2
    both = invoke("docs", "check", "--root", str(project), "--style", "--inventory")
    assert both.exit_code == 2
    assert "--inventory" in unstyle(both.output) and "--style" in unstyle(both.output)


def test_review_default_is_impact_and_disposition_mode_records(project, tmp_path):
    impact = invoke("docs", "review", "--root", str(project), "--base", "HEAD")
    assert impact.exit_code == 0, impact.output
    assert json.loads(impact.stdout)["documents"] == ["docs/api.md"]
    assert json.loads(impact.stdout) == json.loads(
        invoke("project", "docs-impact", "--root", str(project), "--base", "HEAD").stdout
    )
    decisions = project / ".ai-dlc/documentation/decisions.json"
    decisions.parent.mkdir(parents=True)
    decisions.write_text(
        json.dumps([{"target": "docs/api.md", "outcome": "updated", "reason": "Covers two."}])
    )
    recorded = invoke(
        "docs",
        "review",
        "--root",
        str(project),
        "--base",
        "HEAD",
        "--disposition",
        str(decisions),
        "--reviewer",
        "maintainer",
    )
    assert recorded.exit_code == 0, recorded.output
    evidence = json.loads(recorded.stdout)
    assert evidence["reviewer"] == "maintainer"
    baseline = invoke(
        "docs",
        "review",
        "--root",
        str(project),
        "--baseline",
        "--owner",
        "maintainer",
        "--reason",
        "Fixture baseline",
    )
    assert baseline.exit_code == 0, baseline.output
    (project / ".ai-dlc/documentation/baseline.json").write_text(baseline.stdout)
    (project / ".ai-dlc/documentation/current.json").write_text(recorded.stdout)
    assert invoke("docs", "gate", "--root", str(project), "--base", "HEAD").exit_code == 0
    assert invoke("project", "docs-gate", "--root", str(project), "--base", "HEAD").exit_code == 0


def test_review_baseline_report_and_check_modes(project, tmp_path):
    baseline = invoke(
        "docs", "review", "--root", str(project), "--baseline", "--owner", "me", "--reason", "why"
    )
    assert baseline.exit_code == 0, baseline.output
    assert json.loads(baseline.stdout) == json.loads(
        invoke(
            "project", "docs-baseline", "--root", str(project), "--owner", "me", "--reason", "why"
        ).stdout
    )
    report = invoke(
        "docs",
        "review",
        "--root",
        str(project),
        "--base",
        "HEAD",
        "--report",
        "--path",
        "docs/api.md",
    )
    assert report.exit_code == 0, report.output
    packet = json.loads(report.stdout)
    assert [d["path"] for d in packet["documents"]] == ["docs/api.md"]
    packet_file = tmp_path / "packet.json"
    packet_file.write_text(report.stdout)
    review_file = tmp_path / "review.json"
    review_file.write_text("{}")
    checked = invoke(
        "docs",
        "review",
        "--root",
        str(project),
        "--check",
        "--packet",
        str(packet_file),
        "--review",
        str(review_file),
    )
    assert checked.exit_code == 2
    assert json.loads(checked.stdout)["valid"] is False


@pytest.mark.parametrize(
    "args, expected",
    [
        ([], "--base"),
        (["--base", "HEAD", "--source", "inventory"], "--report"),
        (["--base", "HEAD", "--max-bytes", "100"], "--report"),
        (["--base", "HEAD", "--disposition", "x.json"], "--reviewer"),
        (["--base", "HEAD", "--reviewer", "me"], "--disposition"),
        (["--baseline", "--owner", "me"], "--reason"),
        (["--base", "HEAD", "--report"], "--path"),
        (["--check", "--packet", "p.json"], "--review"),
        (["--base", "HEAD", "--report", "--path", "docs/api.md", "--baseline"], "one mode"),
        (["--base", "HEAD", "--packet", "p.json"], "--check"),
    ],
)
def test_review_incomplete_modes_are_usage_errors(project, args, expected):
    result = invoke("docs", "review", "--root", str(project), *args)
    assert result.exit_code == 2, result.output
    assert expected in unstyle(result.output)
    assert result.stdout.strip() == ""


def test_read_search_and_init_match_their_legacy_names(tmp_path):
    read = invoke("docs", "read", "docs/architecture.md", "--root", ".")
    assert read.exit_code == 0, read.output
    assert json.loads(read.stdout) == json.loads(
        invoke("project", "docs-read", "docs/architecture.md", "--root", ".").stdout
    )
    search = invoke("docs", "search", "documentation", "--root", ".", "--limit", "2")
    assert search.exit_code == 0, search.output
    assert json.loads(search.stdout) == json.loads(
        invoke("project", "docs-search", "documentation", "--root", ".", "--limit", "2").stdout
    )
    preview = invoke("docs", "init", "--root", str(tmp_path))
    assert preview.exit_code == 0, preview.output
    assert json.loads(preview.stdout) == json.loads(
        invoke("project", "docs-init", "--root", str(tmp_path)).stdout
    )
    assert not (tmp_path / "docs").exists()
