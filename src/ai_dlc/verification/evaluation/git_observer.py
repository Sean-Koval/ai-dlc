"""Read-only Git observation of an untrusted, already-collected project tree."""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import stat
import subprocess
import threading
from pathlib import Path

ANCHOR_REF = "refs/ai-dlc/evaluation-anchor"
MAX_COMMITS = 512
MAX_GIT_ENTRIES = 100_000
MAX_OUTPUT_BYTES = 1_048_576
GIT_TIMEOUT_SECONDS = 10
OBJECT_ID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
EVIDENCE = "grading/git.json"


class GitUnavailable(Exception):
    """The collected repository cannot provide a bounded, trustworthy observation."""


def _git(project: Path, *arguments: str) -> bytes:
    executable = shutil.which("git")
    if not executable:
        raise GitUnavailable("controller Git is unavailable")
    environment = {
        "PATH": os.defpath,
        "LC_ALL": "C",
        # GIT_CONFIG replaces the repository config too. The other settings make
        # the boundary explicit across Git versions.
        "GIT_CONFIG": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_PROTOCOL_FROM_USER": "0",
    }
    command = [
        executable,
        "--no-pager",
        "--no-optional-locks",
        "--no-replace-objects",
        f"--git-dir={project / '.git'}",
        f"--work-tree={project}",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        "-c",
        "submodule.recurse=false",
        *arguments,
    ]
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=environment,
        )
    except OSError as exc:
        raise GitUnavailable("controller Git could not inspect the repository") from exc
    output = bytearray()
    overflow = threading.Event()

    def read_output() -> None:
        assert process.stdout is not None
        while chunk := process.stdout.read(65_536):
            if len(output) + len(chunk) > MAX_OUTPUT_BYTES:
                overflow.set()
                try:
                    process.kill()
                except OSError:
                    pass
                return
            output.extend(chunk)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        process.wait(timeout=GIT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        reader.join(2)
        raise GitUnavailable("controller Git exceeded its time limit") from exc
    reader.join(2)
    if reader.is_alive():
        process.kill()
        reader.join(2)
        raise GitUnavailable("controller Git output could not be collected")
    if process.returncode != 0 or overflow.is_set():
        raise GitUnavailable("collected Git history is unavailable or exceeds its limits")
    return bytes(output)


def _preflight(project: Path) -> Path:
    if not project.is_dir() or project.is_symlink():
        raise GitUnavailable("collected project is missing or unsafe")
    git_dir = project / ".git"
    if not git_dir.is_dir() or git_dir.is_symlink():
        raise GitUnavailable("collected project has no internal Git directory")
    forbidden = [
        git_dir / "commondir",
        git_dir / "shallow",
        git_dir / "objects/info/alternates",
        git_dir / "objects/info/http-alternates",
    ]
    if any(path.exists() or path.is_symlink() for path in forbidden):
        raise GitUnavailable("collected Git directory references incomplete or external history")
    replacement_refs = git_dir / "refs/replace"
    if replacement_refs.exists() or replacement_refs.is_symlink():
        raise GitUnavailable("collected Git directory contains replacement history")
    packed_refs = git_dir / "packed-refs"
    if packed_refs.exists():
        if packed_refs.is_symlink() or not packed_refs.is_file():
            raise GitUnavailable("collected Git directory contains an unsafe reference path")
        if packed_refs.stat().st_size > MAX_OUTPUT_BYTES:
            raise GitUnavailable("collected Git references exceed their size limit")
        if "refs/replace/" in packed_refs.read_text(errors="replace"):
            raise GitUnavailable("collected Git directory contains replacement history")

    entries = 0
    for root, directories, files in os.walk(git_dir, followlinks=False):
        for name in [*directories, *files]:
            entries += 1
            if entries > MAX_GIT_ENTRIES:
                raise GitUnavailable("collected Git directory exceeds its entry limit")
            path = Path(root) / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise GitUnavailable("collected Git directory contains an unsafe path")
    return git_dir


def _decode_path(value: bytes) -> str:
    return value.decode("utf-8", errors="backslashreplace")


def _paths(project: Path, commit: str) -> list[str]:
    raw = _git(
        project,
        "diff-tree",
        "--root",
        "-m",
        "--no-commit-id",
        "--name-only",
        "--no-renames",
        "--no-ext-diff",
        "-r",
        "-z",
        commit,
    )
    return sorted({_decode_path(path) for path in raw.split(b"\0") if path})


def _dirty_paths(project: Path) -> list[str]:
    raw = _git(
        project,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=all",
    )
    records = raw.split(b"\0")
    dirty: set[str] = set()
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2:3] != b" ":
            raise GitUnavailable("collected Git status is malformed")
        dirty.add(_decode_path(record[3:]))
        if record[:1] in (b"R", b"C") or record[1:2] in (b"R", b"C"):
            if index >= len(records) or not records[index]:
                raise GitUnavailable("collected Git status is malformed")
            dirty.add(_decode_path(records[index]))
            index += 1
    return sorted(dirty)


def _observe(project: Path, expected_anchor: str | None) -> dict:
    _preflight(project)
    if expected_anchor is None or not OBJECT_ID.fullmatch(expected_anchor):
        raise GitUnavailable("controller staging anchor is missing or malformed")
    anchor = _git(project, "rev-parse", "--verify", f"{ANCHOR_REF}^{{commit}}").decode().strip()
    if anchor != expected_anchor:
        raise GitUnavailable("collected staging anchor differs from the controller record")
    history = _git(
        project,
        "rev-list",
        "--parents",
        "--topo-order",
        "--reverse",
        f"--max-count={MAX_COMMITS + 1}",
        "HEAD",
    ).decode()
    lines = [line.split() for line in history.splitlines() if line]
    if not lines or len(lines) > MAX_COMMITS:
        raise GitUnavailable("collected Git history is empty or exceeds its commit limit")
    if any(not parts or any(not OBJECT_ID.fullmatch(value) for value in parts) for parts in lines):
        raise GitUnavailable("collected Git history contains malformed object identifiers")
    hashes = {parts[0] for parts in lines}
    roots = [parts[0] for parts in lines if len(parts) == 1]
    if roots != [anchor] or any(parent not in hashes for parts in lines for parent in parts[1:]):
        raise GitUnavailable("controller staging anchor is not the sole complete history root")

    commits = [
        {
            "hash": parts[0],
            "parents": parts[1:],
            "order": order,
            "anchor": parts[0] == anchor,
            "paths": _paths(project, parts[0]),
        }
        for order, parts in enumerate(lines)
    ]
    head = _git(project, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    head_paths = sorted(
        _decode_path(path)
        for path in _git(project, "ls-tree", "-r", "-z", "--name-only", head).split(b"\0")
        if path
    )
    return {
        "schema": 1,
        "status": "available",
        "detail": None,
        "anchor_commit": anchor,
        "head_commit": head,
        "commits": commits,
        "head_paths": head_paths,
        "dirty_paths": _dirty_paths(project),
    }


def retain_git_observation(run_dir: Path, *, expected_anchor: str | None) -> dict:
    """Retain a bounded observation; repository failures become evidence, never exceptions."""
    try:
        observation = _observe(run_dir / "tree/project", expected_anchor)
    except (GitUnavailable, OSError, UnicodeError, ValueError) as exc:
        observation = {
            "schema": 1,
            "status": "unavailable",
            "detail": str(exc) or "collected Git history is unavailable",
            "anchor_commit": expected_anchor
            if expected_anchor and OBJECT_ID.fullmatch(expected_anchor)
            else None,
            "head_commit": None,
            "commits": [],
            "head_paths": [],
            "dirty_paths": [],
        }
    grading = run_dir / "grading"
    grading.mkdir(exist_ok=True)
    (grading / "git.json").write_text(json.dumps(observation, indent=2, sort_keys=True) + "\n")
    return observation


def _validated_observation(run_dir: Path) -> dict:
    try:
        observation = json.loads((run_dir / EVIDENCE).read_text())
        if not isinstance(observation, dict) or observation.get("schema") != 1:
            raise ValueError
        if observation.get("status") == "unavailable":
            detail = observation.get("detail")
            if not isinstance(detail, str) or not detail:
                raise ValueError
            return observation
        commits = observation.get("commits")
        if observation.get("status") != "available" or not isinstance(commits, list) or not commits:
            raise ValueError
        if not all(
            isinstance(item, dict)
            and OBJECT_ID.fullmatch(str(item.get("hash", "")))
            and isinstance(item.get("parents"), list)
            and all(OBJECT_ID.fullmatch(str(parent)) for parent in item["parents"])
            and item.get("order") == index
            and isinstance(item.get("anchor"), bool)
            and isinstance(item.get("paths"), list)
            and all(isinstance(path, str) for path in item["paths"])
            for index, item in enumerate(commits)
        ):
            raise ValueError
        anchor = observation.get("anchor_commit")
        if [item["hash"] for item in commits if item["anchor"]] != [anchor]:
            raise ValueError
        seen: set[str] = set()
        for item in commits:
            if (item["hash"] == anchor) != (not item["parents"]):
                raise ValueError
            if any(parent not in seen for parent in item["parents"]):
                raise ValueError
            seen.add(item["hash"])
        if observation.get("head_commit") != commits[-1]["hash"]:
            raise ValueError
        for key in ("head_paths", "dirty_paths"):
            if not isinstance(observation.get(key), list) or not all(
                isinstance(path, str) for path in observation[key]
            ):
                raise ValueError
        return observation
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {"status": "unavailable", "detail": "Git observation missing or malformed"}


def _matching_commits(observation: dict, pattern: str | None) -> list[dict]:
    commits = [item for item in observation["commits"] if not item["anchor"]]
    if pattern is None:
        return commits
    return [
        item
        for item in commits
        if any(fnmatch.fnmatchcase(path, pattern) for path in item["paths"])
    ]


def _ancestors(commits: list[dict], commit: str) -> set[str]:
    parents = {item["hash"]: set(item["parents"]) for item in commits}
    found: set[str] = set()
    pending = list(parents.get(commit, set()))
    while pending:
        parent = pending.pop()
        if parent not in found:
            found.add(parent)
            pending.extend(parents.get(parent, set()))
    return found


def evaluate_git_assertion(
    run_dir: Path, kind: str, *, path: str | None, before: str | None, after: str | None
) -> tuple[str, str, list[str]]:
    observation = _validated_observation(run_dir)
    if observation["status"] != "available":
        return "unavailable", observation["detail"], [EVIDENCE]
    if kind == "commit-present":
        matches = _matching_commits(observation, path)
        target = f" changing {path}" if path else ""
        return (
            ("pass", f"{len(matches)} post-anchor commit(s){target}", [EVIDENCE])
            if matches
            else ("fail", f"no post-anchor commit{target}", [EVIDENCE])
        )
    if kind == "path-committed" and path:
        matches = _matching_commits(observation, path)
        head = [item for item in observation["head_paths"] if fnmatch.fnmatchcase(item, path)]
        dirty = [item for item in observation["dirty_paths"] if fnmatch.fnmatchcase(item, path)]
        if dirty:
            return "fail", f"matching path has uncommitted changes: {', '.join(dirty)}", [EVIDENCE]
        if not matches or not head:
            return "fail", f"no committed path at HEAD matches {path}", [EVIDENCE]
        return "pass", f"{len(head)} committed path(s) at HEAD match {path}", [EVIDENCE]
    if kind == "ordering" and before and after:
        before_commits = _matching_commits(observation, before)
        after_commits = _matching_commits(observation, after)
        before_hashes = {item["hash"] for item in before_commits}
        ordered = bool(before_commits and after_commits) and all(
            bool(before_hashes & _ancestors(observation["commits"], item["hash"]))
            for item in after_commits
        )
        if ordered:
            return "pass", f"{before} was committed before {after}", [EVIDENCE]
        return (
            "fail",
            f"collected history does not commit {before} before implementation matching {after}",
            [EVIDENCE],
        )
    return "unavailable", f"invalid selectors for {kind}", [EVIDENCE]
