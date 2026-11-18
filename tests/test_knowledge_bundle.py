"""Merge-time numbering and OKF index generation for knowledge records (KAN-456)."""

import asyncio
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.documentation import knowledge_records as records
from ai_dlc.documentation.knowledge_bundle import index_records, number_records
from ai_dlc.documentation.knowledge_check import check_records
from ai_dlc.documentation.knowledge_notes import split
from ai_dlc.documentation.knowledge_publish import source_sha256

HASH = "sha256:" + "0" * 64
STATUS = {"decision": "accepted", "lesson": "open", "source": "processed", "convention": "active"}
LINK = re.compile(r"\]\(([^)#\s]+)")


def write(folder: Path, name: str, kind: str, rid: str, *, extra: str = "", body: str = ""):
    links = extra or "links: []"
    text = (
        f"---\nid: {rid}\ntype: {kind}\nscope: team\nstatus: {STATUS[kind]}\n"
        f"date: 2026-11-12\nowner: sean\nsources:\n  - {{resource: https://example.invalid/1}}\n"
        f"{links}\n---\n# {rid} title\n{body}"
    )
    if kind == "source":
        text = text.replace(
            "links: []",
            "links: []\nschema_version: 1\nrevision: '1'\nprovider: zoom\ntitle: Call\n"
            "observed_at: 2026-11-10T15:00:00Z",
        )
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def bundle(folder: Path) -> dict[str, records.KnowledgeRecord]:
    found = {}
    for path in sorted(folder.rglob("*.md")):
        if path.name in ("index.md", "log.md"):
            continue
        data, _raw, _body = split(path.read_text())
        assert data is not None
        assert records.errors(data) == [], path
        found[path.relative_to(folder).as_posix()] = records.KnowledgeRecord.model_validate(data)
    return found


def assert_links_resolve(folder: Path) -> None:
    found = bundle(folder)
    names = {name for r in found.values() for name in (r.id, *(r.aliases or []))}
    ids = [r.id for r in found.values()]
    assert len(ids) == len(set(ids))
    for record in found.values():
        for link in record.links:
            assert link.target in names, link
    for path in folder.rglob("*.md"):
        for target in LINK.findall(path.read_text()):
            if "://" not in target:
                assert (path.parent / target).exists(), (path, target)


def snapshot(folder: Path) -> dict[str, str]:
    return {p.relative_to(folder).as_posix(): p.read_text() for p in sorted(folder.rglob("*.md"))}


def git(folder: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=folder,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def merge_step(folder: Path) -> None:
    """What the reusable workflow does after a push to main: number, index, one commit."""
    assert number_records(folder)["status"] in ("numbered", "unchanged")
    assert index_records(folder)["status"] in ("written", "unchanged")
    git(folder, "add", "-A")
    if git(folder, "status", "--porcelain"):
        git(folder, "commit", "-qm", "chore(knowledge): number records")


@pytest.mark.parametrize("order", [("one", "two"), ("two", "one")])
def test_two_branches_merge_in_either_order_with_distinct_numbers(tmp_path, order):
    folder = tmp_path / "kb"
    folder.mkdir()
    git(folder, "init", "-q", "-b", "main")
    (folder / "knowledge.toml").write_text("[format]\nversion = 1\n")
    write(folder, "decisions/DEC-0001.md", "decision", "DEC-0001")
    merge_step(folder)
    for branch, slug in (("one", "pin-harness"), ("two", "release-thursdays")):
        git(folder, "checkout", "-q", "-b", branch, "main")
        write(folder, f"decisions/{slug}.md", "decision", slug)
        write(
            folder,
            f"lessons/{slug}-lesson.md",
            "lesson",
            f"{slug}-lesson",
            extra=f"links:\n  - {{type: implements, target: {slug}}}",
            body=f"See [the decision](../decisions/{slug}.md#context).\n",
        )
        git(folder, "add", "-A")
        git(folder, "commit", "-qm", branch)
        git(folder, "checkout", "-q", "main")
    for branch in order:
        git(folder, "merge", "-q", "--no-ff", "-m", f"merge {branch}", branch)
        merge_step(folder)
    found = bundle(folder)
    decisions = sorted(r.id for r in found.values() if r.type == "decision")
    assert decisions == ["DEC-0001", "DEC-0002", "DEC-0003"]
    first = "pin-harness" if order[0] == "one" else "release-thursdays"
    assert found["decisions/DEC-0002.md"].aliases == [first]
    assert sorted(r.id for r in found.values() if r.type == "lesson") == ["LES-0001", "LES-0002"]
    assert_links_resolve(folder)
    assert check_records(folder)["failures"] == []
    lesson = next(p for p in (folder / "lessons").glob("*.md") if "DEC-0002" in p.read_text())
    assert "../decisions/DEC-0002.md#context" in lesson.read_text()


def test_number_and_index_change_nothing_the_second_time(tmp_path):
    write(tmp_path, "decisions/old.md", "decision", "DEC-0007")
    write(tmp_path, "decisions/new-way.md", "decision", "new-way")
    write(tmp_path, "sources/call.md", "source", "call")
    write(
        tmp_path,
        "lessons/from-call.md",
        "lesson",
        "from-call",
        extra=(
            "links:\n  - {type: derived_from, target: call}\n  - {type: belongs_to, target: KAN-1}"
        ),
    )
    lesson = tmp_path / "lessons/from-call.md"
    lesson.write_text(
        lesson.read_text().replace(
            "  - {resource: https://example.invalid/1}",
            f"  - {{id: call, resource: call, hash: '{HASH}'}}",
        )
    )
    first = number_records(tmp_path)
    assert first["status"] == "numbered"
    assert {item["id"] for item in first["assigned"]} == {"DEC-0008", "SRC-0001", "LES-0001"}
    assert index_records(tmp_path)["status"] == "written"
    after = snapshot(tmp_path)
    assert number_records(tmp_path)["status"] == "unchanged"
    assert index_records(tmp_path)["status"] == "unchanged"
    assert snapshot(tmp_path) == after
    numbered = bundle(tmp_path)["lessons/LES-0001.md"]
    assert numbered.sources[0].id == numbered.sources[0].resource == "SRC-0001"
    assert numbered.links[1].target == "KAN-1"
    text = (tmp_path / "lessons/LES-0001.md").read_text()
    assert "aliases: [from-call]" in text and text.index("id: LES-0001") < text.index("aliases")


def test_check_mode_writes_nothing(tmp_path):
    write(tmp_path, "a-slug.md", "decision", "a-slug")
    before = snapshot(tmp_path)
    result = number_records(tmp_path, write=False)
    assert result["status"] == "pending"
    assert result["assigned"] == [
        {"id": "DEC-0001", "slug": "a-slug", "path": "a-slug.md", "new_path": "DEC-0001.md"}
    ]
    assert index_records(tmp_path, write=False)["status"] == "stale"
    assert snapshot(tmp_path) == before


def test_a_slug_shared_by_two_records_stops_numbering(tmp_path):
    write(tmp_path, "one/same.md", "decision", "same")
    write(tmp_path, "two/same.md", "lesson", "same")
    before = snapshot(tmp_path)
    result = number_records(tmp_path)
    assert result["status"] == "invalid"
    assert "same names 2 records" in result["failures"][0]["message"]
    assert snapshot(tmp_path) == before


def test_invalid_record_stops_both_steps(tmp_path):
    write(tmp_path, "bad.md", "decision", "bad")
    path = tmp_path / "bad.md"
    path.write_text(path.read_text().replace("status: accepted", "status: open"))
    assert number_records(tmp_path)["status"] == "invalid"
    assert index_records(tmp_path)["status"] == "invalid"
    assert not (tmp_path / "index.md").exists()


def test_block_aliases_are_reserialized_and_still_valid(tmp_path):
    write(tmp_path, "x.md", "decision", "x-slug", extra="links: []\naliases:\n  - old-name")
    number_records(tmp_path)
    record = bundle(tmp_path)["x.md"]
    assert record.id == "DEC-0001"
    assert record.aliases == ["old-name", "x-slug"]


def test_index_follows_okf_section_8_and_derives_superseded_by(tmp_path):
    (tmp_path / "knowledge.toml").write_text('[format]\nversion = 1\n[check]\nroots = ["team"]\n')
    (tmp_path / "README.md").write_text("# Not a record\n")
    (tmp_path / "raw").mkdir()
    write(tmp_path, "raw/ignored.md", "decision", "ignored")
    old = write(tmp_path, "team/decisions/DEC-0001.md", "decision", "DEC-0001")
    old.write_text(
        old.read_text()
        .replace("status: accepted", "status: superseded")
        .replace("links: []", "links: []\nvalid_to: 2026-11-12")
    )
    write(
        tmp_path,
        "team/decisions/DEC-0002.md",
        "decision",
        "DEC-0002",
        extra="links:\n  - {type: supersedes, target: DEC-0001}\n"
        "title: Build on every merge\ndescription: CI builds every merge.\ntags: [ci]\n"
        "stale_after: 2027-03-15T00:00:00Z",
    )
    write(tmp_path, "team/lessons/LES-0001.md", "lesson", "LES-0001")
    result = index_records(tmp_path)
    assert result["status"] == "written"
    assert result["indexes"] == [
        "index.md",
        "team/decisions/index.md",
        "team/index.md",
        "team/lessons/index.md",
    ]
    assert result["superseded_by"] == {"DEC-0001": ["DEC-0002"]}
    root = (tmp_path / "index.md").read_text()
    assert root.startswith('---\nokf_version: "0.2"\n---\n# Knowledge records\n')
    assert "* [team/](team/) - 3 records" in root
    team = (tmp_path / "team/index.md").read_text()
    assert not team.startswith("---")
    assert "* [decisions/](decisions/) - 2 records" in team
    decisions = (tmp_path / "team/decisions/index.md").read_text()
    assert (
        "## Decisions\n\n* [Build on every merge](DEC-0002.md) - CI builds every merge. "
        "(DEC-0002; decision; accepted; tags: ci; stale_after: 2027-03-15)"
    ) in decisions
    assert (
        "## Superseded and rejected\n\n* [DEC-0001 title](DEC-0001.md) - "
        "(DEC-0001; decision; superseded; superseded_by: DEC-0002)"
    ) in decisions
    assert "DEC-0001; decision; superseded" not in old.read_text()
    assert not (tmp_path / "raw/index.md").exists()
    assert check_records(tmp_path)["failures"] == []


def test_numbering_an_accepted_decision_passes_check_against_the_base(tmp_path):
    folder = tmp_path / "kb"
    folder.mkdir()
    git(folder, "init", "-q", "-b", "main")
    (folder / "knowledge.toml").write_text("[format]\nversion = 1\n")
    write(folder, "decisions/accepted-one.md", "decision", "accepted-one")
    write(
        folder,
        "lessons/l.md",
        "lesson",
        "l",
        extra="links:\n  - {type: implements, target: accepted-one}",
    )
    git(folder, "add", "-A")
    git(folder, "commit", "-qm", "base")
    merge_step(folder)
    assert check_records(folder, base="HEAD~1")["failures"] == []


def test_generated_indexes_pass_knowledge_check(tmp_path):

    (tmp_path / "knowledge.toml").write_text("[format]\nversion = 1\n")
    write(tmp_path, "decisions/a-slug.md", "decision", "a-slug")
    write(
        tmp_path,
        "lessons/b.md",
        "lesson",
        "b",
        extra="links:\n  - {type: implements, target: a-slug}",
    )
    number_records(tmp_path)
    index_records(tmp_path)
    result = check_records(tmp_path)
    assert result["failures"] == []


def test_five_hundred_records_index_in_under_two_seconds(tmp_path):
    for number in range(1, 501):
        kind = ("decision", "lesson", "convention", "source")[number % 4]
        prefix = records.PREFIXES[kind]
        write(tmp_path, f"{kind}s/{prefix}-{number:04d}.md", kind, f"{prefix}-{number:04d}")
    start = time.perf_counter()
    result = index_records(tmp_path)
    elapsed = time.perf_counter() - start
    assert result["records"] == 500
    assert elapsed < 2, elapsed


def test_cli_and_mcp_entries(tmp_path):
    from ai_dlc.mcp_server import make_server

    write(tmp_path, "a-slug.md", "decision", "a-slug")
    runner = CliRunner()
    checked = runner.invoke(app, ["knowledge", "number", str(tmp_path), "--check"])
    assert checked.exit_code == 1
    assert json.loads(checked.stdout)["status"] == "pending"
    assert runner.invoke(app, ["knowledge", "number", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["knowledge", "index", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["knowledge", "index", str(tmp_path), "--check"]).exit_code == 0

    (tmp_path / "ai-dlc.toml").write_text("schema=4\n")
    server = make_server(tmp_path)
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert {"knowledge_number_plan", "knowledge_index"} <= names


def test_reusable_workflow_serializes_numbering():
    import yaml

    path = Path(__file__).resolve().parents[1] / ".github/workflows/knowledge-merge.yml"
    workflow = yaml.safe_load(path.read_text())
    called = workflow[True]["workflow_call"]
    assert set(called["inputs"]) == {
        "records",
        "branch",
        "numbering-branch",
        "ai-dlc-ref",
        "auto-merge",
    }
    assert called["inputs"]["auto-merge"]["default"] is False
    assert called["secrets"]["token"]["required"] is True
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["number"]
    assert job["concurrency"]["cancel-in-progress"] is False
    script = "\n".join(step.get("run", "") for step in job["steps"])
    assert script.index("knowledge number") < script.index("knowledge index")
    assert "--check" in script
    assert 'push --force origin "HEAD:refs/heads/$NUMBERING"' in script
    gate = script.index('if [ "$AUTO_MERGE" = "true" ]; then')
    assert gate < script.index('gh pr merge "$open" --auto --squash') < script.index("else", gate)
    assert "HEAD:$BRANCH" not in script


def test_numbering_pr_passes_check_for_an_accepted_supersedes_link(tmp_path):
    """Review repro on #260: accepted release-on-merge supersedes weekly-train, both slugs."""
    folder = tmp_path / "kb"
    folder.mkdir()
    git(folder, "init", "-q", "-b", "main")
    (folder / "knowledge.toml").write_text("[format]\nversion = 1\n")
    old = write(folder, "decisions/weekly-train.md", "decision", "weekly-train")
    old.write_text(
        old.read_text()
        .replace("status: accepted", "status: superseded")
        .replace("links: []", "links: []\nvalid_to: 2026-11-12")
    )
    write(
        folder,
        "decisions/release-on-merge.md",
        "decision",
        "release-on-merge",
        extra="links:\n  - {type: supersedes, target: weekly-train}",
    )
    git(folder, "add", "-A")
    git(folder, "commit", "-qm", "base")
    git(folder, "checkout", "-q", "-b", "knowledge-number")
    merge_step(folder)
    numbered = bundle(folder)
    successor = next(r for r in numbered.values() if r.aliases == ["release-on-merge"])
    assert successor.links[0].target in {r.id for r in numbered.values()}
    assert check_records(folder, base="main")["failures"] == []


def test_check_still_refuses_other_link_edits_to_an_accepted_decision(tmp_path):
    folder = tmp_path / "kb"
    folder.mkdir()
    git(folder, "init", "-q", "-b", "main")
    (folder / "knowledge.toml").write_text("[format]\nversion = 1\n")
    write(folder, "decisions/DEC-0001.md", "decision", "DEC-0001")
    write(
        folder, "decisions/DEC-0002.md", "decision", "DEC-0002", extra="links: []\naliases: [two]"
    )
    path = write(folder, "lessons/LES-0001.md", "lesson", "LES-0001")
    git(folder, "add", "-A")
    git(folder, "commit", "-qm", "base")
    accepted = folder / "decisions/DEC-0001.md"
    accepted.write_text(
        accepted.read_text().replace("links: []", "links:\n  - {type: implements, target: two}")
    )
    assert path.exists()
    failures = check_records(folder, base="HEAD")["failures"]
    assert [f["pointer"] for f in failures] == ["/links"]


def test_indexes_list_customer_records_only_inside_their_project(tmp_path):
    boundary = Path(__file__).resolve().parent / "fixtures/boundary"
    shutil.copytree(boundary, tmp_path / "kb")
    result = index_records(tmp_path / "kb")
    assert result["status"] == "written", result
    pages = {path: (tmp_path / "kb" / path).read_text() for path in result["indexes"]}
    customer = {"alpha": ("LES-0001", "SRC-0002"), "beta": ("LES-0002",)}
    for path, text in pages.items():
        inside = next((p for p in customer if path.startswith(f"projects/{p}/")), None)
        for project, ids in customer.items():
            if project == inside:
                continue
            assert f"{project}/" not in text, (path, text)
            assert not any(name in text for name in ids), (path, text)
    assert "LES-0001" in pages["projects/alpha/lessons/index.md"]
    assert "[lessons/](lessons/)" in pages["projects/alpha/index.md"]
    assert "[internal/](internal/) - 1 record" in pages["projects/index.md"]
    assert "[projects/](projects/) - 1 record" in pages["index.md"]


@pytest.mark.parametrize("subfolder", [False, True])
def test_numbering_rewrites_path_resources_to_renamed_files(tmp_path, subfolder):
    folder = tmp_path / "kb"
    folder.mkdir()
    git(folder, "init", "-q", "-b", "main")
    (folder / "knowledge.toml").write_text("[format]\nversion = 1\n")
    source = write(folder, "team/sources/kan-242.md", "source", "kan-242")
    _data, _raw, body = split(source.read_text())
    digest = "sha256:" + source_sha256(body.encode("utf-8"))
    cited = f"  - {{id: kan-242, resource: team/sources/kan-242.md, hash: '{digest}'}}"
    citing = (
        ("team/decisions/accepted-one.md", "decision", "accepted-one"),
        ("team/l.md", "lesson", "a"),
    )
    for name, kind, rid in citing:
        # A body long enough for git to see the numbering rename as a rename.
        path = write(folder, name, kind, rid, body="Decided after a long discussion.\n" * 12)
        text = path.read_text().replace("  - {resource: https://example.invalid/1}", cited)
        path.write_text(text)
    assert check_records(folder)["failures"] == []
    git(folder, "add", "-A")
    git(folder, "commit", "-qm", "base")

    assert number_records(folder / "team" if subfolder else folder)["status"] == "numbered"

    assert not (folder / "team/sources/kan-242.md").exists()
    for path in ("team/decisions/DEC-0001.md", "team/l.md"):
        data, _raw, _body = split((folder / path).read_text())
        assert data is not None
        assert data["sources"][0]["resource"] == "team/sources/SRC-0001.md", path
        assert data["sources"][0]["id"] == "SRC-0001"
    git(folder, "add", "-A")
    git(folder, "commit", "-qm", "number")
    assert check_records(folder, base="HEAD~1")["failures"] == []
