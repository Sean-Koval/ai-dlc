"""The front page (README and docs home) and the docs-site link rewriter."""

from __future__ import annotations

import re
import runpy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LINKS = runpy.run_path(str(ROOT / "scripts/docs_site_links.py"))
FRONT = ROOT / "docs/assets/front"


def test_readme_follows_the_front_page_structure():
    readme = (ROOT / "README.md").read_text()
    assert len(readme.splitlines()) <= 150
    headings = re.findall(r"^## (.+)$", readme, re.MULTILINE)
    assert headings == [
        "See it work",
        "What it looks like",
        "Where it sits",
        "Use cases",
        "Get started",
        "Features",
        "Go deeper",
    ]
    use_cases = readme.split("## Use cases", 1)[1].split("## ", 1)[0]
    assert len(re.findall(r"^- \*\*", use_cases, re.MULTILINE)) == 3
    quickstart = readme.split("## Get started", 1)[1].split("```sh\n", 1)[1].split("```", 1)[0]
    assert len(quickstart.strip().splitlines()) == 5


def test_front_page_assets_exist_and_both_pages_use_them():
    readme = (ROOT / "README.md").read_text()
    home = (ROOT / "docs/index.md").read_text()
    for name in ["enroll.svg", "work.svg", "plugin-skills.svg", "project-check.svg"]:
        assert (FRONT / name).is_file()
        assert f"docs/assets/front/{name}" in readme
        assert f"assets/front/{name}" in home
    for name in ["suite-dark.svg", "suite-light.svg", "suite.svg", "enroll.cast", "work.cast"]:
        assert (FRONT / name).is_file()
    assert '--8<-- "docs/assets/front/suite.svg"' in home
    assert (FRONT / "build.py").is_file() and (FRONT / "demo_provider.py").is_file()


def test_recordings_play_once_within_twenty_seconds_and_free_of_machine_paths():
    import json

    for name in ["enroll.cast", "work.cast"]:
        events = [json.loads(line) for line in (FRONT / name).read_text().splitlines()]
        assert 5 <= events[-1][0] <= 20, (name, events[-1][0])
        svg = (FRONT / name.replace(".cast", ".svg")).read_text()
        assert "infinite" not in svg and " forwards" in svg
        assert "work finish" not in svg or "&quot;status&quot;: &quot;blocked&quot;" in svg
    for path in FRONT.glob("*"):
        if path.suffix in {".svg", ".cast"}:
            text = path.read_text()
            assert "/tmp/ai-dlc-front-demo" not in text and "/home/" not in text


def test_link_rewriter_excludes_what_the_site_excludes():
    config = yaml.load((ROOT / "mkdocs.yml").read_text(), Loader=yaml.BaseLoader)
    patterns = {
        line.strip().rstrip("/") for line in config["exclude_docs"].splitlines() if line.strip()
    }
    assert patterns == {"archive", "verification", "reviews", "catalog.toml"}
    assert LINKS["excluded"]("archive/plan.md")
    assert LINKS["excluded"]("verification/run-1/receipt.json")
    assert LINKS["excluded"]("verification/record.md")
    assert LINKS["excluded"]("reviews/2026-09-03-review.md")
    assert LINKS["excluded"]("catalog.toml")
    assert not LINKS["excluded"]("runbooks/record.md")


def test_repository_docs_have_no_link_leaving_the_site():
    assert LINKS["run"](ROOT, False) == {}


def test_link_rewriter_rewrites_only_links_that_leave_the_site(tmp_path):
    docs = tmp_path / "docs"
    (docs / "design").mkdir(parents=True)
    (docs / "archive").mkdir()
    (docs / "archive/old.md").write_text("old\n")
    (docs / "notes").mkdir()
    (docs / "index.md").write_text("home\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/tool.py").write_text("x = 1\n")
    page = docs / "design/page.md"
    page.write_text(
        "[home](../index.md) [code](../../src/tool.py#L1) [old](../archive/old.md)\n"
        "[dir](../notes/) [web](https://example.com) [anchor](#here) ![img](../../src/tool.py)\n"
        "`[inline](../../src/tool.py)`\n"
        "```md\n[fenced](../../src/tool.py)\n```\n"
    )
    found = LINKS["run"](tmp_path, True)
    text = page.read_text()
    base = "https://github.com/Sean-Koval/ai-dlc"
    assert f"[code]({base}/blob/main/src/tool.py#L1)" in text
    assert f"[old]({base}/blob/main/docs/archive/old.md)" in text
    assert f"[dir]({base}/tree/main/docs/notes)" in text
    assert "[home](../index.md)" in text and "[web](https://example.com)" in text
    assert "`[inline](../../src/tool.py)`" in text and "[fenced](../../src/tool.py)" in text
    assert "![img](../../src/tool.py)" in text
    assert len(found["docs/design/page.md"]) == 3
    assert LINKS["main"](["--check", "--root", str(tmp_path)]) == 0


def test_site_styles_are_airframe_tokens_only():
    """Airframe (Sean-Koval/agent-factory) is vendored unmodified; our own CSS uses its tokens, never a color."""
    styles = ROOT / "docs/stylesheets"
    assert re.search(r"Airframe theme-v\d+ tokens", (styles / "airframe.css").read_text()[:300])
    for css in sorted(styles.glob("*.css")):
        if not css.name.startswith("airframe"):
            text = re.sub(r"/\*.*?\*/", "", css.read_text(), flags=re.DOTALL)
            assert not re.search(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\(", text), css.name
