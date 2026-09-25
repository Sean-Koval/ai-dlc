"""Git workflow assertions use only controller observations of the collected repository."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

import pytest


def git(repository: Path, *args: str, check: bool = True) -> str:
    environment = {
        **os.environ,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    done = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=check,
        capture_output=True,
        text=True,
        env=environment,
    )
    return done.stdout.strip()


def commit(repository: Path, subject: str, *paths: str) -> str:
    git(repository, "add", "--", *paths)
    git(
        repository,
        "-c",
        "user.name=Evaluation User",
        "-c",
        "user.email=evaluation@example.invalid",
        "commit",
        "-qm",
        subject,
    )
    return git(repository, "rev-parse", "HEAD")


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    project = tmp_path / "tree/project"
    project.mkdir(parents=True)
    git(project, "init", "-q", "-b", "main")
    (project / "README.md").write_text("fixture\n")
    anchor = commit(project, "chore: stage evaluation fixture", "README.md")
    git(project, "update-ref", "refs/ai-dlc/evaluation-anchor", anchor)
    (project.parents[1] / "expected-anchor").write_text(anchor + "\n")
    return project


def assertion(kind: str, *, id: str | None = None, **fields: str) -> dict:
    return {
        "id": id or kind,
        "dimension": "workflow",
        "kind": kind,
        **fields,
    }


def grade(run_dir: Path, assertions: list[dict]) -> dict:
    from ai_dlc.verification.evaluation.evaluate import evaluate

    return evaluate(
        {
            "scenario": "git-workflow",
            "arm": "treatment",
            "attempt": 1,
            "outcome": "completed",
        },
        assertions=assertions,
        planned=[item["id"] for item in assertions],
        run_dir=run_dir,
        grade=lambda _: {"exit_code": 0, "stdout": "", "stderr": "OK"},
    )


def retain(project: Path) -> dict:
    from ai_dlc.verification.evaluation.git_observer import retain_git_observation

    expected = (project.parents[1] / "expected-anchor").read_text().strip()
    return retain_git_observation(project.parents[1], expected_anchor=expected)


def by_id(report: dict) -> dict[str, dict]:
    return {item["id"]: item for item in report["assertions"]}


def test_controller_records_anchor_commits_paths_and_passes_git_assertions(repository: Path):
    work = repository / ".ai-dlc/work/item.toml"
    work.parent.mkdir(parents=True)
    work.write_text("id = 'item'\n")
    work_commit = commit(repository, "docs: start work record", ".ai-dlc/work/item.toml")
    implementation = repository / "src/app.py"
    implementation.parent.mkdir()
    implementation.write_text("print('implemented')\n")
    implementation_commit = commit(repository, "feat: implement behavior", "src/app.py")

    observation = retain(repository)

    assert observation["status"] == "available", observation
    assert observation["anchor_commit"] == observation["commits"][0]["hash"]
    assert [(item["order"], item["anchor"], item["paths"]) for item in observation["commits"]] == [
        (0, True, ["README.md"]),
        (1, False, [".ai-dlc/work/item.toml"]),
        (2, False, ["src/app.py"]),
    ]
    assert observation["commits"][1]["hash"] == work_commit
    assert observation["commits"][2]["parents"] == [work_commit]
    assert observation["head_commit"] == implementation_commit
    assert observation["dirty_paths"] == []

    report = grade(
        repository.parents[1],
        [
            assertion("commit-present", id="commit-any"),
            assertion("commit-present", id="commit-code", path="src/*.py"),
            assertion("path-committed", path=".ai-dlc/work/*.toml"),
            assertion("ordering", before=".ai-dlc/work/*.toml", after="src/*.py"),
        ],
    )
    assert {key: value["result"] for key, value in by_id(report).items()} == {
        "commit-any": "pass",
        "commit-code": "pass",
        "path-committed": "pass",
        "ordering": "pass",
    }
    assert all(item["evidence"] == ["grading/git.json"] for item in report["assertions"])


def test_implementation_committed_before_work_record_fails_ordering(repository: Path):
    implementation = repository / "src/app.py"
    implementation.parent.mkdir()
    implementation.write_text("print('too soon')\n")
    commit(repository, "feat: implement first", "src/app.py")
    work = repository / ".ai-dlc/work/item.toml"
    work.parent.mkdir(parents=True)
    work.write_text("id = 'late'\n")
    commit(repository, "docs: add late work record", ".ai-dlc/work/item.toml")
    retain(repository)

    result = by_id(
        grade(
            repository.parents[1],
            [assertion("ordering", before=".ai-dlc/work/*.toml", after="src/*.py")],
        )
    )["ordering"]
    assert result["result"] == "fail"
    assert "before implementation" in result["observed"]


def test_anchor_is_not_mistaken_for_an_agent_commit(repository: Path):
    retain(repository)
    report = grade(
        repository.parents[1],
        [assertion("commit-present"), assertion("commit-present", path="README.md")],
    )
    assert [item["result"] for item in report["assertions"]] == ["fail", "fail"]


def test_uncommitted_matching_path_cannot_pass_path_committed(repository: Path):
    work = repository / ".ai-dlc/work/item.toml"
    work.parent.mkdir(parents=True)
    work.write_text("id = 'item'\n")
    commit(repository, "docs: record work", ".ai-dlc/work/item.toml")
    work.write_text("id = 'changed-but-not-committed'\n")
    retain(repository)

    result = by_id(
        grade(repository.parents[1], [assertion("path-committed", path=".ai-dlc/work/*.toml")])
    )["path-committed"]
    assert result["result"] == "fail"
    assert "uncommitted" in result["observed"]


@pytest.mark.parametrize("damage", ["absent", "corrupt-head", "missing-anchor", "anchor-not-root"])
def test_absent_or_corrupt_repository_makes_git_assertions_unavailable(
    repository: Path, damage: str
):
    work = repository / ".ai-dlc/work/item.toml"
    work.parent.mkdir(parents=True)
    work.write_text("id = 'item'\n")
    latest = commit(repository, "docs: record work", ".ai-dlc/work/item.toml")
    if damage == "absent":
        os.rename(repository / ".git", repository / ".git-absent")
    elif damage == "corrupt-head":
        (repository / ".git/HEAD").write_text("ref: refs/heads/missing\n")
    elif damage == "missing-anchor":
        git(repository, "update-ref", "-d", "refs/ai-dlc/evaluation-anchor")
    else:
        git(repository, "update-ref", "refs/ai-dlc/evaluation-anchor", latest)

    observation = retain(repository)
    result = by_id(grade(repository.parents[1], [assertion("commit-present")]))["commit-present"]
    assert observation["status"] == "unavailable"
    assert result["result"] == "unavailable"
    assert result["evidence"] == ["grading/git.json"]


def test_repository_config_and_hooks_are_ignored(repository: Path, tmp_path: Path):
    marker = tmp_path / "external-side-effect"
    malicious = tmp_path / "malicious.config"
    malicious.write_text(f"[core]\n\tfsmonitor = {tmp_path / 'probe'}\n")
    probe = tmp_path / "probe"
    probe.write_text(f"#!/bin/sh\ntouch {marker}\n")
    probe.chmod(0o755)
    hooks = repository / ".git/hostile-hooks"
    hooks.mkdir()
    (hooks / "post-checkout").write_text(f"#!/bin/sh\ntouch {marker}\n")
    (hooks / "post-checkout").chmod(0o755)
    with (repository / ".git/config").open("a") as config:
        config.write(f"\n[include]\n\tpath = {malicious}\n[core]\n\thooksPath = {hooks}\n")
    (repository / "agent.txt").write_text("agent\n")
    commit(repository, "feat: agent commit", "agent.txt")
    marker.unlink(missing_ok=True)  # the setup Git command may honor the hostile fixture config

    assert retain(repository)["status"] == "available"
    assert not marker.exists()


@pytest.mark.parametrize("filter_kind", ["clean", "process"])
def test_collected_attributes_and_named_filters_never_execute_on_the_controller(
    repository: Path, tmp_path: Path, filter_kind: str
):
    work = repository / ".ai-dlc/work/item.toml"
    work.parent.mkdir(parents=True)
    work.write_text("safe\n")
    commit(repository, "docs: record work", ".ai-dlc/work/item.toml")
    (repository / ".gitattributes").write_text(".ai-dlc/work/item.toml filter=probe\n")
    commit(repository, "test: configure attributes", ".gitattributes")
    marker = tmp_path / f"{filter_kind}-executed"
    if filter_kind == "clean":
        command = f"touch {shlex.quote(str(marker))}; cat"
    else:
        probe = tmp_path / "filter-process"
        probe.write_text(f"#!/bin/sh\ntouch {shlex.quote(str(marker))}\nexit 1\n")
        probe.chmod(0o755)
        command = str(probe)
    git(repository, "config", f"filter.probe.{filter_kind}", command)
    git(repository, "config", "filter.probe.required", "true")
    work.write_text("evil\n")  # same size as the committed bytes

    observation = retain(repository)

    assert not marker.exists()
    assert observation["status"] == "available", observation
    assert ".ai-dlc/work/item.toml" in observation["dirty_paths"]


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_collected_index_flags_cannot_hide_worktree_changes(repository: Path, flag: str):
    work = repository / ".ai-dlc/work/item.toml"
    work.parent.mkdir(parents=True)
    work.write_text("safe\n")
    commit(repository, "docs: record work", ".ai-dlc/work/item.toml")
    git(repository, "update-index", flag, ".ai-dlc/work/item.toml")
    work.write_text("evil\n")  # same size as the committed bytes

    observation = retain(repository)
    result = by_id(
        grade(repository.parents[1], [assertion("path-committed", path=".ai-dlc/work/*.toml")])
    )["path-committed"]

    assert ".ai-dlc/work/item.toml" in observation["dirty_paths"]
    assert result["result"] == "fail"


@pytest.mark.parametrize("damage", ["gitfile", "alternates", "replace-ref", "symlink"])
def test_external_or_replaced_object_paths_are_refused(
    repository: Path, tmp_path: Path, damage: str
):
    (repository / "agent.txt").write_text("agent\n")
    head = commit(repository, "feat: agent commit", "agent.txt")
    if damage == "gitfile":
        external = tmp_path / "external.git"
        os.rename(repository / ".git", external)
        (repository / ".git").write_text(f"gitdir: {external}\n")
    elif damage == "alternates":
        alternate = tmp_path / "alternate-objects"
        alternate.mkdir()
        path = repository / ".git/objects/info/alternates"
        path.parent.mkdir(exist_ok=True)
        path.write_text(str(alternate) + "\n")
    elif damage == "replace-ref":
        anchor = git(repository, "rev-parse", "refs/ai-dlc/evaluation-anchor")
        replacement = repository / f".git/refs/replace/{head}"
        replacement.parent.mkdir(parents=True)
        replacement.write_text(anchor + "\n")
    else:
        source = repository / ".git/HEAD"
        target = tmp_path / "external-head"
        source.replace(target)
        source.symlink_to(target)

    observation = retain(repository)
    assert observation["status"] == "unavailable"


def test_git_assertion_contract_requires_kind_specific_selectors():
    from pydantic import ValidationError

    from ai_dlc.verification.evaluation.contracts import Assertion

    assert Assertion.model_validate(assertion("commit-present", path="src/*.py")).path == "src/*.py"
    assert (
        Assertion.model_validate(
            assertion("ordering", before=".ai-dlc/work/*.toml", after="src/*.py")
        ).after
        == "src/*.py"
    )
    for declaration in [
        assertion("path-committed"),
        assertion("ordering", before=".ai-dlc/work/*.toml"),
        assertion("commit-present", before="one", after="two"),
    ]:
        with pytest.raises(ValidationError):
            Assertion.model_validate(declaration)


def test_malformed_retained_observation_never_passes(repository: Path):
    grading = repository.parents[1] / "grading"
    grading.mkdir()
    (grading / "git.json").write_text('{"status":"available","commits":"forged"}\n')
    report = grade(repository.parents[1], [assertion("commit-present")])
    assert report["assertions"][0]["result"] == "unavailable"
