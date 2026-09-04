import os
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path


class OpenSpecProvider:
    def __init__(self, root, *, environ: Mapping[str, str] | None = None):
        self.root = Path(root).resolve()
        self.environ = os.environ if environ is None else environ

    def current(self, work, revision=None):
        if revision is not None:
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
                env=self.environ,
            )
            if not revision or head.returncode or head.stdout.strip() != revision:
                raise ValueError("OpenSpec checkout revision must equal the merged revision")
            status = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=all", "--", "openspec"],
                cwd=self.root,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
                env=self.environ,
            )
            if status.returncode or status.stdout.strip():
                raise ValueError("OpenSpec files are dirty or untracked at the merged revision")
        if revision is not None and (
            (self.root / "openspec").is_symlink()
            or any(p.is_symlink() for p in (self.root / "openspec").rglob("*"))
        ):
            raise ValueError("OpenSpec merged evidence cannot contain unverified symlinks")
        reference = work.get("artifacts", {}).get("spec", "")
        archive = (self.root / "openspec/changes/archive").resolve()
        path = (self.root / reference).resolve()
        if (
            not reference
            or not archive.is_relative_to(self.root)
            or not path.is_relative_to(archive)
            or not path.is_dir()
            or not path.name.endswith("-" + work["id"])
        ):
            raise ValueError(
                "Required specification must reference the archived change for this work"
            )
        if not (path / "proposal.md").is_file() or not (path / "tasks.md").is_file():
            raise ValueError("OpenSpec archive is missing proposal or tasks")
        if revision is not None:
            tracked = subprocess.run(
                [
                    "git",
                    "ls-files",
                    "--error-unmatch",
                    "--",
                    str((path / "proposal.md").relative_to(self.root)),
                    str((path / "tasks.md").relative_to(self.root)),
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
                env=self.environ,
            )
            if tracked.returncode:
                raise ValueError("OpenSpec archive must be tracked at the merged revision")
        if re.search(r"^\s*[-*]\s+\[ \]", (path / "tasks.md").read_text(), re.MULTILINE):
            raise ValueError("OpenSpec archive has unfinished tasks")
        help_result = subprocess.run(
            ["openspec", "validate", "--help"],
            cwd=self.root,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
            env=self.environ,
        )
        if help_result.returncode:
            raise ValueError("Cannot discover installed OpenSpec capabilities")
        commands = [["validate", "--all", "--strict", "--no-interactive"]]
        if "--archived" in help_result.stdout:
            commands.append(["validate", "--archived"])
        for args in commands:
            result = subprocess.run(
                ["openspec", *args],
                cwd=self.root,
                text=True,
                capture_output=True,
                timeout=60,
                check=False,
                env=self.environ,
            )
            if result.returncode:
                raise ValueError("OpenSpec validation failed: " + result.stderr + result.stdout)
        return {"current": True, "archive": reference, "revision": revision}
