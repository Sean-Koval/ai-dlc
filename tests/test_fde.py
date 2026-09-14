"""Local FDE documents preserve authored content and enforce explicit stage gates."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app

runner = CliRunner()
STAGES = ["01_discover", "02_frame", "03_design", "04_build", "05_deploy", "06_enable", "07_expand"]


def scaffold(root: Path, *options: str):
    return runner.invoke(
        app,
        [
            "fde",
            "scaffold",
            "sample",
            "--title",
            "Customer delivery",
            "--root",
            str(root),
            *options,
        ],
    )


def engagement(root: Path) -> Path:
    return root / "docs/fde_engagements/sample"


def check(root: Path):
    return runner.invoke(app, ["fde", "check", "sample", "--root", str(root)])


def test_scaffold_creates_charter_seven_stages_and_portable_guidance(tmp_path):
    result = scaffold(tmp_path, "--space", "TEAM", "--parent", "123")
    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["publication"] == "unavailable"
    target = engagement(tmp_path)
    charter = (target / "_index.md").read_text()
    assert "Executive sponsors" in charter and "Business goals" in charter
    assert 'confluence_space_key: "TEAM"' in charter
    assert 'confluence_parent_page_id: "123"' in charter
    for stage, status in zip(STAGES, ["ACTIVE", "GATED", "GATED", *(["PLANNED"] * 4)], strict=True):
        page = (target / stage / "_index.md").read_text()
        assert f"{stage}/_index.md" in charter
        assert f'status: "{status}"' in page
        assert "exit_criteria_met: false" in page
        assert "confluence_parent_page_id" not in page
        assert "confluence_page_id" not in page
    guidance = (target / "AGENTS.md").read_text()
    assert "ai-dlc fde check sample" in guidance
    assert "private" in guidance and "unavailable" in guidance
    assert (target / "CLAUDE.md").read_text() == "@AGENTS.md\n"
    assert check(tmp_path).exit_code == 0


def test_dry_run_exposes_exact_content_without_writing(tmp_path):
    before = list(tmp_path.iterdir())
    result = scaffold(tmp_path, "--dry-run")
    assert result.exit_code == 0, result.output
    preview = json.loads(result.output)
    assert list(tmp_path.iterdir()) == before
    assert preview["applied"] is False
    assert len(preview["files"]) == 10
    applied = scaffold(tmp_path)
    assert applied.exit_code == 0
    for path, content in preview["files"].items():
        assert (tmp_path / path).read_text() == content


def test_existing_engagement_refused_without_touching_authored_files(tmp_path):
    assert scaffold(tmp_path).exit_code == 0
    page = engagement(tmp_path) / "_index.md"
    page.write_text("authored content\n")
    before = {str(p): p.read_bytes() for p in engagement(tmp_path).rglob("*") if p.is_file()}
    result = scaffold(tmp_path)
    assert result.exit_code != 0 and "exists" in result.output
    assert before == {
        str(p): p.read_bytes() for p in engagement(tmp_path).rglob("*") if p.is_file()
    }


@pytest.mark.parametrize(
    "directory", ["../private", "docs/../private", "/tmp/fde", "private", "docs"]
)
def test_unsafe_or_non_dedicated_directory_refused(tmp_path, directory):
    result = scaffold(tmp_path, "--docs-dir", directory)
    assert result.exit_code != 0
    assert not list(tmp_path.iterdir())


def test_symlink_directory_refused_even_inside_repository(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "private").mkdir()
    (tmp_path / "docs/company").symlink_to(tmp_path / "private", target_is_directory=True)
    result = scaffold(tmp_path, "--docs-dir", "docs/company")
    assert result.exit_code != 0 and "symlink" in result.output
    assert not list((tmp_path / "private").iterdir())


def test_configured_company_docs_directory(tmp_path):
    (tmp_path / "ai-dlc.toml").write_text(
        'schema = 4\n[project.fde]\ndocs_dir = "docs/company/engagements"\n'
    )
    result = scaffold(tmp_path)
    assert result.exit_code == 0, result.output
    assert (tmp_path / "docs/company/engagements/sample/_index.md").is_file()
    assert check(tmp_path).exit_code == 0


@pytest.mark.parametrize(
    "options",
    [
        ("--space", "TEAM"),
        ("--parent", "123"),
        ("--space", "TEAM", "--parent", "../bad"),
        ("--space", "bad\nkey", "--parent", "123"),
    ],
)
def test_incomplete_or_unsafe_target_hints_refused(tmp_path, options):
    result = scaffold(tmp_path, *options)
    assert result.exit_code != 0
    assert not list(tmp_path.iterdir())


def test_downstream_activation_requires_all_preceding_exit_evidence(tmp_path):
    assert scaffold(tmp_path).exit_code == 0
    design = engagement(tmp_path) / "03_design/_index.md"
    design.write_text(design.read_text().replace('status: "GATED"', 'status: "ACTIVE"'))
    result = check(tmp_path)
    assert result.exit_code != 0
    assert "01_discover" in result.output and "02_frame" in result.output
    for stage in STAGES[:2]:
        page = engagement(tmp_path) / stage / "_index.md"
        page.write_text(
            page.read_text()
            .replace("exit_criteria_met: false", "exit_criteria_met: true")
            .replace('exit_evidence: ""', 'exit_evidence: "Reviewed requirements, PR 12"')
        )
    result = check(tmp_path)
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    "old,new",
    [
        ('status: "ACTIVE"', 'status: "DONE"'),
        ("exit_criteria_met: false", "exit_criteria_met: true"),
        ("exit_criteria_met: false", 'exit_criteria_met: "true"'),
        ('exit_evidence: ""', "exit_evidence: []"),
    ],
)
def test_invalid_stage_metadata_fails(tmp_path, old, new):
    assert scaffold(tmp_path).exit_code == 0
    page = engagement(tmp_path) / "01_discover/_index.md"
    page.write_text(page.read_text().replace(old, new))
    assert check(tmp_path).exit_code != 0


def test_cannot_bypass_gate_by_marking_downstream_exit_met(tmp_path):
    assert scaffold(tmp_path).exit_code == 0
    page = engagement(tmp_path) / "03_design/_index.md"
    page.write_text(
        page.read_text()
        .replace("exit_criteria_met: false", "exit_criteria_met: true")
        .replace('exit_evidence: ""', 'exit_evidence: "Approved"')
    )
    assert check(tmp_path).exit_code != 0


def test_missing_and_symlinked_stage_pages_fail_without_reading_target(tmp_path):
    assert scaffold(tmp_path).exit_code == 0
    page = engagement(tmp_path) / "01_discover/_index.md"
    page.unlink()
    assert check(tmp_path).exit_code != 0
    private = tmp_path / "private.md"
    private.write_text("sensitive-private-marker")
    page.symlink_to(private)
    result = check(tmp_path)
    assert result.exit_code != 0
    assert "sensitive-private-marker" not in result.output


def test_invalid_slug_cannot_escape(tmp_path):
    result = runner.invoke(
        app, ["fde", "scaffold", "../../private", "--title", "Engagement", "--root", str(tmp_path)]
    )
    assert result.exit_code != 0
    assert not list(tmp_path.iterdir())


def test_generated_command_quotes_shell_metacharacters_and_includes_slug(tmp_path):
    import re
    import subprocess

    directory = "docs/$(touch PWNED)-`touch ALSO_PWNED`"
    result = scaffold(tmp_path, "--docs-dir", directory, "--dry-run")
    assert result.exit_code == 0, result.output
    files = json.loads(result.output)["files"]
    for filename in ("AGENTS.md", "_index.md"):
        page = files[f"{directory}/sample/{filename}"]
        match = re.search(r"(?P<fence>`+)ai-dlc fde check sample.*?(?P=fence)", page)
        assert match, page
        command = match.group().strip("`")
        result = subprocess.run(
            ["sh", "-c", f"set -- {command}; printf '%s\\n' \"$@\""],
            cwd=tmp_path,
            text=True,
            capture_output=True,
            check=True,
        )
        assert result.stdout.splitlines() == [
            "ai-dlc",
            "fde",
            "check",
            "sample",
            "--docs-dir",
            directory,
        ]
        assert not (tmp_path / "PWNED").exists()
        assert not (tmp_path / "ALSO_PWNED").exists()


@pytest.mark.parametrize(
    "contents",
    ["---\ntitle: [unterminated\n---\n", "---\n- not a mapping\n---\n", "no frontmatter"],
)
def test_malformed_yaml_and_missing_charter_fail_cleanly(tmp_path, contents):
    assert scaffold(tmp_path).exit_code == 0
    charter = engagement(tmp_path) / "_index.md"
    charter.write_text(contents)
    result = check(tmp_path)
    assert result.exit_code == 1
    assert "charter" in json.loads(result.output)["findings"][0]
    charter.unlink()
    assert check(tmp_path).exit_code == 1


@pytest.mark.parametrize(
    "field,values",
    [
        ("status", ['"ACTIVE"', '"GATED"']),
        ("exit_criteria_met", ["true", "false"]),
        ("exit_evidence", ['"Reviewed"', '""']),
    ],
)
def test_duplicate_yaml_fields_cannot_override_gate_metadata(tmp_path, field, values):
    assert scaffold(tmp_path).exit_code == 0
    page = engagement(tmp_path) / "03_design/_index.md"
    lines = page.read_text().splitlines()
    lines = [line for line in lines if not line.startswith(field + ":")]
    lines[1:1] = [f"{field}: {value}" for value in values]
    page.write_text("\n".join(lines) + "\n")
    result = check(tmp_path)
    assert result.exit_code == 1, result.output
    assert "03_design: invalid YAML frontmatter" in json.loads(result.output)["findings"]
