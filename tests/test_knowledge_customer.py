"""Customer knowledge repositories, promotion out of them and their leak paths (KAN-475)."""

import shutil
import subprocess
import tomllib
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.documentation.knowledge_check import check_records, repo_boundary
from ai_dlc.documentation.knowledge_customer import (
    customer_files,
    denied,
    init_customer,
    mixed_script,
    promote,
    release_ref,
)
from ai_dlc.documentation.knowledge_render import wiki_target
from ai_dlc.errors import RefusedError

BOUNDARY = Path(__file__).resolve().parent / "fixtures/boundary"
DAY = date(2026, 11, 13)
SUMMARY = (
    "Search clusters behind a bastion often accept traffic only in a maintenance window. "
    "Ask for the window and the port during scoping, before planning any load tests.\n"
)
TITLE = "Ask for maintenance windows before load tests"
EVIDENCE = (
    "The acme search cluster only accepts connections through the jump host on port 8089 "
    "after midnight, says the ops lead."
)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
        },
    ).stdout


def commit_all(root: Path) -> None:
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def lesson(record_id: str, *, project: str = "acme", extra: str = "", body: str = EVIDENCE) -> str:
    return (
        f"---\nid: {record_id}\ntype: lesson\nscope: project\nboundary: customer\n"
        f"project: {project}\nstatus: open\ndate: 2026-11-10\nowner: sean\n"
        "sources:\n  - {resource: KAN-1}\nlinks: []\n"
        f"title: Acme search cluster window\n{extra}---\n{body}\n"
    )


@pytest.fixture
def acme(tmp_path: Path) -> Path:
    repo = tmp_path / "acme-knowledge"
    init_customer(repo, "acme", deny=["Wile E. Coyote", "acme-prod-01"], codeowners=["@org/fde"])
    write(repo, "projects/acme/lessons/LES-0001.md", lesson("LES-0001"))
    commit_all(repo)
    return repo


@pytest.fixture
def team(tmp_path: Path) -> Path:
    repo = tmp_path / "team-knowledge"
    write(repo, "knowledge.toml", '[format]\nversion = 1\n[check]\nroots = ["team"]\n')
    write(
        repo,
        "team/lessons/LES-0001.md",
        "---\nid: LES-0001\ntype: lesson\nscope: team\nstatus: open\ndate: 2026-11-01\n"
        "owner: sean\nsources:\n  - {resource: KAN-2}\nlinks: []\ntitle: Pin the CA\n---\n"
        "Pin the proxy CA bundle before the first install.\n",
    )
    commit_all(repo)
    return repo


# --- init --customer ---------------------------------------------------------------


def test_init_customer_writes_a_repository_that_passes_check_and_renders_nowhere(tmp_path):
    repo = tmp_path / "acme-knowledge"
    planned = init_customer(repo, "acme", dry_run=True)
    assert planned["dry_run"] and not repo.exists()
    assert "knowledge.toml" in planned["files"] and planned["render"] is None

    init_customer(repo, "acme", codeowners=["@org/fde"])
    assert check_records(repo)["status"] == "valid"
    toml = (repo / "knowledge.toml").read_text()
    parsed = tomllib.loads(toml)
    assert "wiki" not in parsed
    assert repo_boundary(parsed) == ("acme", [])
    with pytest.raises(RefusedError, match="no wiki target"):
        wiki_target(repo)
    assert "acme" in (repo / "deny-terms.txt").read_text().splitlines()
    assert (repo / "CODEOWNERS").read_text().endswith("* @org/fde\n")
    readme = (repo / "README.md").read_text()
    assert "company's GitHub" in readme and "customer's own systems" in readme
    assert "knowledge-check.yml" in (repo / ".github/workflows/knowledge.yml").read_text()


def test_init_customer_refuses_a_bad_name_or_a_used_directory(tmp_path):
    with pytest.raises(RefusedError, match="slug"):
        init_customer(tmp_path / "x", "Acme Corp")
    (tmp_path / "used").mkdir()
    (tmp_path / "used" / "f").write_text("x")
    with pytest.raises(RefusedError, match="not empty"):
        init_customer(tmp_path / "used", "acme")
    with pytest.raises(RefusedError, match="codeowner"):
        customer_files("acme", codeowners=["not a handle"])


def test_init_customer_refuses_a_directory_inside_another_repository(team):
    with pytest.raises(RefusedError, match="inside"):
        init_customer(team / "acme-knowledge", "acme")
    assert not (team / "acme-knowledge").exists()


def test_init_customer_makes_its_own_git_repository(tmp_path):
    init_customer(tmp_path / "acme-knowledge", "acme")
    assert (tmp_path / "acme-knowledge" / ".git").is_dir()


def test_init_customer_warns_when_ci_falls_back_to_the_installed_release(tmp_path):
    planned = init_customer(tmp_path / "a", "acme", dry_run=True, codeowners=["@org/fde"])
    assert len(planned["warnings"]) == 1 and release_ref() in planned["warnings"][0]
    assert "--ai-dlc-ref" in planned["warnings"][0]
    pinned = init_customer(
        tmp_path / "b", "acme", dry_run=True, codeowners=["@org/fde"], ai_dlc_ref="v9.9.9"
    )
    assert pinned["warnings"] == []


def test_cli_init_dry_run_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["knowledge", "init", "--customer", "acme", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert f"Warning: CI is pinned to {release_ref()}" in result.stderr
    assert not (tmp_path / "acme-knowledge").exists()


# --- knowledge check in a customer repository ---------------------------------------


def failures(repo: Path) -> list[tuple[str, str, str]]:
    result = check_records(repo)
    return [(f["path"], f["pointer"], f["message"]) for f in result["failures"]]


def test_customer_repository_check_passes_its_own_records(acme):
    assert check_records(acme)["status"] == "valid"


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (lesson("x-team").replace("boundary: customer\nproject: acme\n", ""), "boundary: customer"),
        (lesson("x-beta", project="beta"), "project: acme"),
        (lesson("x-link", extra="links:\n  - {type: implements, target: DEC-0009}\n"), ""),
        (
            lesson("x-url", extra="").replace(
                "links: []", "links:\n  - {type: implements, target: 'https://example.com/x'}"
            ),
            "outside this customer repository",
        ),
        (
            lesson("x-src").replace("{resource: KAN-1}", "{resource: ../team-knowledge/a.md}"),
            "outside this customer repository",
        ),
        (lesson("x-body", body="See [it](../../../../team/lessons/a.md)."), "outside"),
        (lesson("x-file", body="See [it](file:///etc/hosts)."), "outside"),
        (lesson("x-drive", body="See [it](C:\\Data\\notes.md)."), "outside"),
        (lesson("x-drive2", body="See [it](C:/Data/notes.md)."), "outside"),
        (lesson("x-unc", body="See [it](//server/share/notes.md)."), "outside"),
        (lesson("x-auto", body="See <file:///etc/hosts>."), "outside"),
        (lesson("x-href", body='See <a href="../../../../x.md">it</a>.'), "outside"),
        (
            lesson("x-team-id").replace("{resource: KAN-1}", "{id: LES-0099, resource: KAN-1}"),
            "outside",
        ),
        (
            lesson("x-team-link", extra="").replace(
                "links: []", "links:\n  - {type: belongs_to, target: LES-0099}"
            ),
            "outside",
        ),
    ],
)
def test_customer_repository_check_fails_anything_that_leaves_it(acme, record, message):
    write(acme, "projects/acme/lessons/bad.md", record.replace("links: []\nlinks:", "links:"))
    found = [f for f in failures(acme) if f[0].endswith("bad.md")]
    assert found, failures(acme)
    assert any(message in f[2] for f in found), found


def test_customer_repository_allows_a_work_item_and_web_links_in_the_body(acme):
    write(
        acme,
        "projects/acme/lessons/ok.md",
        lesson("ok", body="Public docs: [vendor](https://docs.example.com/x).").replace(
            "links: []",
            "links:\n  - {type: belongs_to, target: ENG-12}\n  - {type: belongs_to, target: acme}",
        ),
    )
    assert check_records(acme)["status"] == "valid", failures(acme)


def test_customer_repository_link_through_a_symlink_that_leaves_it_fails(acme, tmp_path):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "notes.md").write_text("private\n")
    (acme / "projects/acme/shared").symlink_to(outside, target_is_directory=True)
    write(
        acme, "projects/acme/lessons/bad.md", lesson("x-link", body="See [n](../shared/notes.md).")
    )
    assert any(p.endswith("bad.md") and "outside" in m for p, _q, m in failures(acme))


def test_a_repo_table_without_a_valid_declaration_fails_closed(acme):
    toml = acme / "knowledge.toml"
    toml.write_text(
        toml.read_text().replace(
            'boundary = "customer"\nproject = "acme"\n', 'boundry = "customer"\n'
        )
    )
    write(
        acme, "projects/acme/lessons/bad.md", lesson("x-esc", body="[x](../../../../../etc/passwd)")
    )
    found = failures(acme)
    assert any(p == "/repo/boundary" for _path, p, _m in found), found
    assert any(path.endswith("bad.md") for path, _p, _m in found)


def test_customer_repository_record_outside_its_project_folder_fails(acme):
    write(acme, "projects/acme/lessons/../../../stray/x.md", lesson("x-stray"))
    shutil.move(acme / "stray", acme / "projects" / "acme" / "stray")  # inside roots
    write(acme, "projects/beta/lessons/y.md", lesson("y-beta"))
    toml = acme / "knowledge.toml"
    toml.write_text(toml.read_text().replace('roots = ["projects/acme"]', 'roots = ["projects"]'))
    found = failures(acme)
    assert any(path.endswith("y.md") for path, _p, _m in found), found


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ('[wiki]\nsite = "x.atlassian.net"\nsource = "https://g/"\n', "renders only to a wiki"),
        ('[wiki]\nsite = "x.atlassian.net"\nproject = "beta"\n', "renders only to a wiki"),
    ],
)
def test_customer_repository_wiki_must_name_its_project(acme, table, message):
    toml = acme / "knowledge.toml"
    toml.write_text(toml.read_text() + table)
    assert any(message in m for _p, _q, m in failures(acme))
    with pytest.raises(RefusedError):
        wiki_target(acme)


def test_customer_repository_wiki_for_its_own_project_is_allowed(acme):
    toml = acme / "knowledge.toml"
    toml.write_text(
        toml.read_text()
        + '[wiki]\nsite = "acme.atlassian.net"\nsource = "https://g/"\nproject = "acme"\n'
    )
    assert check_records(acme)["status"] == "valid"
    assert wiki_target(acme)["project"] == "acme"


def test_a_malformed_repo_declaration_denies_every_record(acme):
    toml = acme / "knowledge.toml"
    toml.write_text(toml.read_text().replace('boundary = "customer"', 'boundary = "open"'))
    found = failures(acme)
    assert any(p == "/repo/boundary" for _path, p, _m in found)
    assert any(path.endswith("LES-0001.md") for path, _p, _m in found)


# --- promote ------------------------------------------------------------------------


def run_promote(acme: Path, team: Path, **changes):
    arguments = {
        "summary": SUMMARY,
        "title": TITLE,
        "owner": "sean",
        "to": team,
        "today": DAY,
        **changes,
    }
    return promote(acme, "LES-0001", **arguments)


def branches(repo: Path) -> list[str]:
    return git(repo, "branch", "--format=%(refname:short)").split()


def test_promote_writes_a_sanitised_team_record_on_a_branch(acme, team):
    result = run_promote(acme, team)
    assert result["branch"] == "promote/ask-for-maintenance-windows-before-load-tests"
    assert result["branch"] in branches(team)
    # The working tree and current branch are untouched.
    assert git(team, "status", "--porcelain") == ""
    assert git(team, "rev-parse", "--abbrev-ref", "HEAD").strip() == "main"
    tree = team.parent / "checked"
    git(team, "worktree", "add", "-q", str(tree), result["branch"])
    assert check_records(tree)["status"] == "valid", check_records(tree)["failures"]
    source = (tree / result["paths"][0]).read_text()
    record = (tree / result["paths"][1]).read_text()
    assert "customer-record:LES-0001" in source
    for text in (source, record):
        assert "boundary" not in text and "project:" not in text
        assert not denied(text.replace("customer-record", ""), ["acme", "Wile E. Coyote"])
        assert "scope: team" in text
    assert "derived_from" in record


def test_promote_with_a_deny_list_term_exits_non_zero_and_writes_nothing(acme, team):
    before = git(team, "rev-parse", "HEAD"), branches(team)
    for change in (
        {"summary": SUMMARY + "Seen at ACME.\n"},
        {"summary": SUMMARY + "Host acme_prod_01 was down.\n"},
        {"title": "Wile E Coyote's window"},
        {"slug": "acme-window"},
        {"summary": SUMMARY + "Seen at \uff21\uff23\uff2d\uff25.\n"},  # full width
        {"summary": SUMMARY + "Seen at Ac\u200bme.\n"},  # zero-width space
        {"summary": SUMMARY + "Both ACMEs agreed.\n"},
        {"summary": SUMMARY + "Seen at \u0410\u0421\u041c\u0415.\n"},  # Cyrillic look-alikes
        {"summary": SUMMARY + "Seen at A.C.M.E. last week.\n"},
        {"summary": SUMMARY + "Ask WileECoyote first.\n"},
        {"summary": SUMMARY + "Ask wile-e-coyote first.\n"},
    ):
        with pytest.raises(RefusedError, match="deny-list"):
            run_promote(acme, team, **change)
    assert (git(team, "rev-parse", "HEAD"), branches(team)) == before
    assert git(team, "status", "--porcelain") == ""

    (acme.parent / "summary.md").write_text(SUMMARY + "Acme said so.\n")
    result = CliRunner().invoke(
        app,
        [
            "knowledge",
            "promote",
            "LES-0001",
            "--root",
            str(acme),
            "--to",
            str(team),
            "--summary",
            str(acme.parent / "summary.md"),
            "--title",
            TITLE,
            "--owner",
            "sean",
        ],
    )
    assert result.exit_code != 0 and "deny-list" in result.output
    assert branches(team) == before[1]


def test_promote_refuses_a_word_that_mixes_alphabets(acme, team):
    # A Greek omicron inside a Latin word: no deny term, but it hides a spelling.
    with pytest.raises(RefusedError, match="alphabet"):
        run_promote(acme, team, summary=SUMMARY + "Ask the Ini\u03bftech team.\n")
    assert not mixed_script("Ask the \u0391\u03b8\u03ae\u03bd\u03b1 office and the Initech team.")


def test_customer_workflow_is_pinned_and_read_only(tmp_path):
    files = customer_files("acme")
    workflow = files[".github/workflows/knowledge.yml"]
    assert f"@{release_ref()}" in workflow and "@main" not in workflow
    assert workflow.count("contents: read") == 3 and ": write" not in workflow
    assert release_ref() in files["README.md"]
    sha = "0123456789abcdef0123456789abcdef01234567"
    assert (
        f"knowledge-check.yml@{sha}"
        in customer_files("acme", ai_dlc_ref=sha)[".github/workflows/knowledge.yml"]
    )
    for ref in ("main", "x y", "$(id)"):
        with pytest.raises(RefusedError, match="ai-dlc-ref"):
            customer_files("acme", ai_dlc_ref=ref)


def test_promote_refuses_quotes_addresses_and_customer_paths(acme, team):
    quote = "connections through the jump host on port 8089 after midnight"
    with pytest.raises(RefusedError, match="quotes"):
        run_promote(acme, team, summary=SUMMARY + f"Only {quote}.\n")
    with pytest.raises(RefusedError, match="web address"):
        run_promote(acme, team, summary=SUMMARY + "See https://wiki.internal/x.\n")
    with pytest.raises(RefusedError, match="customer path"):
        run_promote(acme, team, summary=SUMMARY + "See projects/zeta/lessons.\n")
    assert branches(team) == ["main"]


def test_promote_refuses_a_payload_quote(acme, team):
    write(
        acme,
        "inbox/transcripts/call.txt",
        "[00:01:00] Ops: " + "rotate the bastion keys every single friday night at nine" + "\n",
    )
    record = acme / "projects/acme/lessons/LES-0001.md"
    record.write_text(
        record.read_text().replace("{resource: KAN-1}", "{resource: inbox/transcripts/call.txt}")
    )
    with pytest.raises(RefusedError, match="quotes"):
        run_promote(
            acme,
            team,
            summary=SUMMARY + "Rotate the bastion keys every single Friday night at nine.\n",
        )


def test_promote_refuses_a_quote_from_any_customer_file(acme, team):
    # A Source cited only through sources[].id, and a file that is not a valid record,
    # are still customer words (fail closed).
    words = "the replica lag alarm fires whenever the nightly export job overlaps backups"
    write(
        acme,
        "projects/acme/sources/SRC-0001.md",
        lesson("SRC-0001", body=words).replace("type: lesson", "type: source"),
    )
    record = acme / "projects/acme/lessons/LES-0001.md"
    record.write_text(
        record.read_text().replace("{resource: KAN-1}", "{id: SRC-0001, resource: KAN-1}")
    )
    with pytest.raises(RefusedError, match="quotes"):
        run_promote(acme, team, summary=SUMMARY + words.capitalize() + ".\n")
    other = "our staging cluster rotates its certificates every ninety days without warning"
    write(acme, "projects/acme/notes/scratch.md", "not a record at all\n" + other + "\n")
    with pytest.raises(RefusedError, match="quotes"):
        run_promote(acme, team, summary=SUMMARY + other.capitalize() + ".\n")
    assert branches(team) == ["main"]


def test_promote_only_from_a_numbered_customer_record_into_a_team_repository(acme, team, tmp_path):
    write(acme, "projects/acme/lessons/draft.md", lesson("acme-draft-lesson"))
    with pytest.raises(RefusedError, match="draft slug"):
        promote(acme, "acme-draft-lesson", summary=SUMMARY, title=TITLE, owner="sean", to=team)
    with pytest.raises(RefusedError, match="--to"):
        promote(acme, "LES-0001", summary=SUMMARY, title=TITLE, owner="sean")
    other = tmp_path / "beta-knowledge"
    init_customer(other, "beta")
    with pytest.raises(RefusedError, match="team repository"):
        run_promote(acme, other)
    with pytest.raises(RefusedError, match="not a customer repository"):
        promote(team, "LES-0001", summary=SUMMARY, title=TITLE, owner="sean", to=team)


def test_promote_refuses_a_taken_slug_or_branch(acme, team):
    first = run_promote(acme, team)
    with pytest.raises(RefusedError, match="already exists"):
        run_promote(acme, team)
    git(team, "merge", "-q", first["branch"])
    with pytest.raises(RefusedError, match="already a record id"):
        run_promote(acme, team, branch="promote/again")
    assert "promote/again" not in branches(team)


def test_promote_dry_run_plans_and_writes_nothing(acme, team):
    result = run_promote(acme, team, dry_run=True)
    assert set(result["planned"]) == set(result["paths"])
    assert branches(team) == ["main"]


def test_promote_is_refused_in_a_team_repository(tmp_path, team):
    """The team-repository promote path is gone (KAN-503): no customer records there."""
    repo = tmp_path / "kb"
    shutil.copytree(BOUNDARY, repo)
    commit_all(repo)
    before = git(repo, "rev-parse", "HEAD"), branches(repo)
    for to in (None, team):
        with pytest.raises(RefusedError, match="not a customer repository"):
            promote(repo, "LES-0001", summary=SUMMARY, title=TITLE, owner="sean", to=to)
    assert (git(repo, "rev-parse", "HEAD"), branches(repo)) == before
    assert branches(team) == ["main"]

    (tmp_path / "summary.md").write_text(SUMMARY)
    result = CliRunner().invoke(
        app,
        [
            "knowledge",
            "promote",
            "LES-0001",
            "--root",
            str(repo),
            "--summary",
            str(tmp_path / "summary.md"),
            "--title",
            TITLE,
            "--owner",
            "sean",
        ],
    )
    assert result.exit_code != 0
    assert "not a customer repository" in result.output
    assert (git(repo, "rev-parse", "HEAD"), branches(repo)) == before


def test_promote_into_a_team_repository_inside_a_larger_checkout(acme, team, tmp_path):
    mono = tmp_path / "mono"
    write(mono, "README.md", "monorepo\n")
    shutil.copytree(team, mono / "kb", ignore=shutil.ignore_patterns(".git"))
    commit_all(mono)
    result = promote(
        acme, "LES-0001", summary=SUMMARY, title=TITLE, owner="sean", to=mono / "kb", today=DAY
    )
    files = git(mono, "show", "--name-only", "--format=", result["branch"]).split()
    assert files and all(name.startswith("kb/") for name in files)
    assert git(mono, "status", "--porcelain") == ""
