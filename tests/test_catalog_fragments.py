"""A new page brings its own catalog fragment and nav entry, so parallel PRs don't conflict (KAN-486)."""

from __future__ import annotations

import json
import runpy
import subprocess
from pathlib import Path

import pytest
import yaml

from ai_dlc.documentation.catalog import catalog_files, load_catalog
from ai_dlc.documentation.documents import check_documents

ROOT = Path(__file__).resolve().parents[1]
SITE = runpy.run_path(str(ROOT / "scripts/site_config.py"))

MKDOCS = """site_name: example
exclude_docs: |
  verification/
  catalog.toml
  catalog.d/

nav:
  - Home: index.md
  - Decisions:
      - "ADR 0001: First": decisions/0001.md
  - Reference:
      - Terms: terms.md
"""
CATALOG = """schema = 1

[[documents]]
id = "home"
path = "docs/index.md"
kind = "navigation"
owner = "maintainers"
status = "active"
"""


def _fragment(identity: str, page: str, nav: str | None = "Decisions", title: str | None = None):
    lines = ["schema = 1", "", "[[documents]]", f'id = "{identity}"', f'path = "docs/{page}"']
    lines += ['kind = "decision"', 'owner = "maintainers"', 'status = "active"']
    if nav is not None:
        lines.append(f'nav = "{nav}"')
    if title is not None:
        lines.append(f"title = {json.dumps(title)}")
    return "\n".join(lines) + "\n"


@pytest.fixture
def site(tmp_path):
    for page in ("index.md", "terms.md", "decisions/0001.md"):
        (tmp_path / "docs" / page).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "docs" / page).write_text("# Page\n", encoding="utf-8")
    (tmp_path / "mkdocs.yml").write_text(MKDOCS, encoding="utf-8")
    (tmp_path / "docs/catalog.toml").write_text(CATALOG, encoding="utf-8")
    return tmp_path


def _add(root: Path, identity: str, page: str, **fields) -> None:
    (root / "docs" / page).parent.mkdir(parents=True, exist_ok=True)
    (root / "docs" / page).write_text(f"# {identity}\n", encoding="utf-8")
    (root / "docs/catalog.d").mkdir(exist_ok=True)
    (root / f"docs/catalog.d/{identity}.toml").write_text(
        _fragment(identity, page, **fields), encoding="utf-8"
    )


def _nav(text: str) -> list:
    return yaml.load(text, Loader=yaml.BaseLoader)["nav"]


def test_the_catalog_reads_its_fragments_after_catalog_toml(site):
    _add(site, "decision-0003", "decisions/0003.md")
    _add(site, "decision-0002", "decisions/0002.md")
    assert catalog_files(site) == [
        "docs/catalog.toml",
        "docs/catalog.d/decision-0002.toml",
        "docs/catalog.d/decision-0003.toml",
    ]
    assert [e["id"] for e in load_catalog(site)] == ["home", "decision-0002", "decision-0003"]


def test_a_malformed_fragment_is_named(site):
    (site / "docs/catalog.d").mkdir()
    (site / "docs/catalog.d/bad.toml").write_text("schema = 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="docs/catalog.d/bad.toml"):
        load_catalog(site)
    report = check_documents(site)
    assert any(f["code"] == "invalid-catalog" for f in report["findings"])


def test_a_fragment_cannot_repeat_an_id_or_path_of_the_catalog(site):
    _add(site, "home", "decisions/0002.md")
    codes = {f["code"] for f in check_documents(site)["findings"]}
    assert "duplicate-id" in codes


def test_a_fragment_page_joins_its_nav_section(site):
    _add(site, "decision-0002", "decisions/0002.md", title="ADR 0002: Second")
    _add(site, "terms-extra", "extra.md", nav="Reference")
    text, problems = SITE["compose"](site)
    assert problems == []
    nav = _nav(text)
    assert nav[1]["Decisions"] == [
        {"ADR 0001: First": "decisions/0001.md"},
        {"ADR 0002: Second": "decisions/0002.md"},
    ]
    assert nav[2]["Reference"] == [{"Terms": "terms.md"}, "extra.md"]
    assert text.startswith("# Generated") and "site_name: example" in text


def test_a_page_the_nav_already_lists_is_not_added_twice(site):
    (site / "docs/catalog.d").mkdir()
    (site / "docs/catalog.d/first.toml").write_text(
        _fragment("first", "decisions/0001.md"), encoding="utf-8"
    )
    text, problems = SITE["compose"](site)
    assert problems == [] and _nav(text)[1]["Decisions"] == [
        {"ADR 0001: First": "decisions/0001.md"}
    ]


@pytest.mark.parametrize(
    ("fields", "page", "message"),
    [
        ({"nav": "Nowhere"}, "decisions/0002.md", "section of mkdocs.yml"),
        ({"title": " "}, "decisions/0002.md", "title"),
        ({}, "decisions/0002.txt", "Markdown page"),
    ],
)
def test_a_bad_nav_entry_is_reported_and_nothing_is_written(site, fields, page, message):
    _add(site, "decision-0002", page, **fields)
    _text, problems = SITE["compose"](site)
    assert len(problems) == 1 and message in problems[0]
    assert SITE["main"](["--root", str(site)]) == 1
    assert not (site / "site.yml").exists()


def test_a_page_excluded_from_the_site_cannot_join_the_nav(site):
    _add(site, "check", "verification/check.md", nav="Reference")
    assert "excluded from the site" in SITE["compose"](site)[1][0]


def test_a_path_that_leaves_docs_cannot_join_the_nav(site):
    _add(site, "terms-up", "decisions/../terms.md", nav="Reference")
    assert "docs/ Markdown page" in SITE["compose"](site)[1][0]


def test_a_page_in_a_nested_excluded_directory_cannot_join_the_nav(site):
    """exclude_docs is gitignore-style: ``catalog.d/`` leaves out design/catalog.d/x.md too."""
    _add(site, "nested", "design/catalog.d/x.md", nav="Reference")
    assert "excluded from the site" in SITE["compose"](site)[1][0]


def test_hidden_editor_files_in_catalog_d_are_ignored(site):
    _add(site, "decision-0002", "decisions/0002.md")
    (site / "docs/catalog.d/.#decision-0002.toml").write_text("not toml", encoding="utf-8")
    assert catalog_files(site)[1:] == ["docs/catalog.d/decision-0002.toml"]
    assert SITE["compose"](site)[1] == []


def test_a_symlinked_fragment_or_directory_is_refused(site, tmp_path_factory):
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    (elsewhere / "x.toml").write_text(_fragment("x", "decisions/0001.md"), encoding="utf-8")
    (site / "docs/catalog.d").mkdir()
    (site / "docs/catalog.d/x.toml").symlink_to(elsewhere / "x.toml")
    with pytest.raises(ValueError):
        load_catalog(site)
    with pytest.raises(ValueError):
        SITE["catalog_entries"](site)
    (site / "docs/catalog.d/x.toml").unlink()
    (site / "docs/catalog.d").rmdir()
    (site / "docs/catalog.d").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(ValueError):
        load_catalog(site)
    with pytest.raises(ValueError):
        SITE["catalog_entries"](site)


def test_a_broken_fragment_is_reported_at_its_own_path(site):
    (site / "docs/catalog.d").mkdir()
    (site / "docs/catalog.d/bad.toml").write_text("schema = 2\n", encoding="utf-8")
    finding = next(f for f in check_documents(site)["findings"] if f["code"] == "invalid-catalog")
    assert finding["path"] == "docs/catalog.d/bad.toml"


def test_a_missing_page_is_reported(site):
    (site / "docs/catalog.d").mkdir()
    (site / "docs/catalog.d/ghost.toml").write_text(
        _fragment("ghost", "decisions/0009.md"), encoding="utf-8"
    )
    assert "does not exist" in SITE["compose"](site)[1][0]


def test_nav_must_stay_the_last_key(site):
    (site / "mkdocs.yml").write_text(MKDOCS + "extra_css:\n  - a.css\n", encoding="utf-8")
    assert "last top-level key" in SITE["compose"](site)[1][0]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_two_branches_that_each_add_a_page_merge_without_conflict(site):
    assert _git(site, "init", "-q", "-b", "main").returncode == 0
    _git(site, "add", "-A")
    _git(site, "commit", "-qm", "base")
    for branch, page in (("a", "decisions/0002.md"), ("b", "decisions/0003.md")):
        _git(site, "checkout", "-q", "-b", branch, "main")
        _add(site, f"decision-{branch}", page)
        _git(site, "add", "-A")
        _git(site, "commit", "-qm", branch)
    _git(site, "checkout", "-q", "main")
    assert _git(site, "merge", "-q", "--no-edit", "a").returncode == 0
    merged = _git(site, "merge", "-q", "--no-edit", "b")
    assert merged.returncode == 0, merged.stdout + merged.stderr
    text, problems = SITE["compose"](site)
    assert problems == []
    assert [
        next(iter(i.values())) if isinstance(i, dict) else i for i in _nav(text)[1]["Decisions"]
    ] == [
        "decisions/0001.md",
        "decisions/0002.md",
        "decisions/0003.md",
    ]


def test_this_repository_composes_a_site_config():
    assert SITE["main"](["--root", str(ROOT), "--check"]) == 0


def test_build_contracts_writes_every_generated_contract():
    built = runpy.run_path(str(ROOT / "scripts/build_contracts.py"))["generated"]()
    on_disk = {p.name for p in (ROOT / "contracts").glob("*.json")}
    assert set(built) == on_disk
    for name, content in built.items():
        assert json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8")) == content


def test_the_old_way_of_editing_the_nav_by_hand_conflicts(site):
    """The control for the test above: two hand edits at a section's end collide."""
    _git(site, "init", "-q", "-b", "main")
    _git(site, "add", "-A")
    _git(site, "commit", "-qm", "base")
    anchor = '      - "ADR 0001: First": decisions/0001.md\n'
    for branch in ("a", "b"):
        _git(site, "checkout", "-q", "-b", branch, "main")
        text = (site / "mkdocs.yml").read_text(encoding="utf-8")
        line = f"      - ADR {branch}: decisions/{branch}.md\n"
        (site / "mkdocs.yml").write_text(text.replace(anchor, anchor + line), encoding="utf-8")
        _git(site, "commit", "-qam", branch)
    _git(site, "checkout", "-q", "main")
    assert _git(site, "merge", "-q", "--no-edit", "a").returncode == 0
    assert _git(site, "merge", "-q", "--no-edit", "b").returncode != 0
