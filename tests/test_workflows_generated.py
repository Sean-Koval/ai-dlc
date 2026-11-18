"""Front-page assets are built on main after merge, so PRs never conflict on them (KAN-535)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
APPLY = "Apply the patch, refusing anything but the rebuilt assets"


def workflow(name):
    return yaml.safe_load((WORKFLOWS / name).read_text())


def triggers(data):
    return data.get("on", data.get(True))  # YAML 1.1 reads a bare `on:` key as True


def step(job, name):
    return next(s for s in job["steps"] if s.get("name") == name)


def test_pull_requests_build_the_assets_but_need_not_commit_them():
    data = workflow("assets.yml")
    on = triggers(data)
    assert "push" not in on, "main is rebuilt by generated.yml, not checked by assets.yml"
    assert {"labeled", "unlabeled", "synchronize"} <= set(on["pull_request"]["types"])
    assert "workflow_dispatch" in on
    guard = data["jobs"]["committed"]
    assert guard["if"] == "github.event_name == 'pull_request'"
    script = step(guard, "Refuse hand-edited recordings and screens")
    assert "generated-files" in script["env"]["LABELED"]
    assert '"$HEAD_REF" = "bot/front-assets"' in script["run"]
    compare = step(data["jobs"]["assets"], "Compare them with the committed ones")["run"]
    assert "::notice" in compare and "exit 1" in compare
    assert "--check" not in step(data["jobs"]["assets"], "Build the assets")["run"]


def test_write_job_runs_no_repository_code():
    jobs = workflow("generated.yml")["jobs"]
    assert jobs["build"]["permissions"] == {"contents": "read"}
    assert workflow("generated.yml")["permissions"] == {}
    publish = jobs["publish"]
    assert publish["needs"] == "build"
    assert publish["permissions"]["contents"] == "write"
    uses = [s["uses"].split("@")[0] for s in publish["steps"] if "uses" in s]
    assert uses == ["actions/checkout", "actions/download-artifact"]
    assert publish["steps"][0]["with"]["persist-credentials"] is False
    scripts = "\n".join(s["run"] for s in publish["steps"] if "run" in s)
    for runner in ("python", "uv ", "ai-dlc ", "sh scripts", "npm ", "pip ", "make "):
        assert runner not in scripts, runner
    assert "bot/front-assets" in scripts
    assert "gh workflow run verify.yml --ref bot/front-assets" in scripts


def test_verify_can_be_started_on_the_bot_branch():
    assert "workflow_dispatch" in triggers(workflow("verify.yml"))


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


@pytest.fixture
def repo(tmp_path):
    if (
        not shutil.which("jq")
        or subprocess.run(
            ["grep", "-P", "x"], input="x", text=True, capture_output=True, check=False
        ).returncode
    ):
        pytest.skip("the publish step runs on ubuntu with jq and GNU grep")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    front = tmp_path / "docs/assets/front"
    front.mkdir(parents=True)
    (front / "work.cast").write_text('{"version": 2}\n[0.1, "o", "one"]\n')
    (front / "build.py").write_text("print('build')\n")
    (tmp_path / "docs/index.md").write_text("# Home\n")
    (tmp_path / "docs/catalog.toml").write_text(
        'schema = 1\n[[documents]]\nid = "home"\npath = "docs/index.md"\nkind = "guide"\n'
        'owner = "maintainers"\nstatus = "active"\n'
    )
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "baseline")
    return tmp_path


def rebuilt_patch(root, *, extra=None, evidence=None):
    """What the build job hands over: the rebuilt asset and its recorded disposition."""
    from ai_dlc.documentation import document_impact

    (root / "docs/assets/front/work.cast").write_text('{"version": 2}\n[0.1, "o", "two"]\n')
    document_impact.record_disposition(
        root,
        base="HEAD",
        decisions=[{"target": "docs/assets/front/work.cast", "outcome": "updated", "reason": "r"}],
        reviewer="generated.yml (front-page build)",
        evidence_id="front-assets",
    )
    path = root / ".ai-dlc/documentation/evidence/front-assets.json"
    if evidence:
        path.write_text(json.dumps(evidence(json.loads(path.read_text()))))
    for relative, text in (extra or {}).items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text)
    git(root, "add", "-A")
    patch = subprocess.check_output(["git", "diff", "--cached", "--binary"], cwd=root)
    git(root, "reset", "-q", "--hard")
    git(root, "clean", "-qfd")
    (root / "runner").mkdir()
    (root / "runner/front-assets.patch").write_bytes(patch)


def apply(root):
    script = step(workflow("generated.yml")["jobs"]["publish"], APPLY)["run"]
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],  # as Actions runs it
        cwd=root,
        env={"PATH": "/usr/bin:/bin", "RUNNER_TEMP": str(root / "runner")},
        capture_output=True,
        text=True,
        check=False,
    )


def test_publish_applies_the_rebuilt_assets_and_their_evidence(repo):
    rebuilt_patch(repo)
    result = apply(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "two" in (repo / "docs/assets/front/work.cast").read_text()
    assert git(repo, "diff", "--cached", "--name-only").splitlines() == [
        ".ai-dlc/documentation/evidence/front-assets.json",
        "docs/assets/front/work.cast",
    ]


@pytest.mark.parametrize(
    "extra",
    [
        {"src/app.py": "print('x')\n"},
        {"docs/assets/front/build.py": "print('changed')\n"},
        {".github/workflows/x.yml": "on: push\n"},
        {"docs/assets/front/nested/x.svg": "<svg/>\n"},
        {".ai-dlc/documentation/evidence/other.json": "{}\n"},
    ],
)
def test_publish_refuses_a_patch_outside_the_rebuilt_assets(repo, extra):
    rebuilt_patch(repo, extra=extra)
    result = apply(repo)
    assert result.returncode == 1
    assert "outside the rebuilt assets" in result.stdout
    assert git(repo, "status", "--porcelain", "--untracked-files=no") == ""


def test_publish_refuses_evidence_that_decides_anything_else(repo):
    def widen(evidence):
        extra = dict(evidence["decisions"][0], target="docs/index.md", bound={"docs/index.md": "x"})
        return dict(evidence, decisions=[*evidence["decisions"], extra])

    rebuilt_patch(repo, evidence=widen)
    result = apply(repo)
    assert result.returncode == 1
    assert "decides more than the rebuilt assets" in result.stdout
