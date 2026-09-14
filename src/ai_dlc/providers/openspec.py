import json
import os
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path

from ai_dlc.errors import RefusedError, UncertainError
from ai_dlc.files import inside, run_git


class OpenSpecProvider:
    def __init__(self, root, *, environ: Mapping[str, str] | None = None):
        self.root = Path(root).resolve()
        self.environ = os.environ if environ is None else environ

    def archive(self, name):
        """Archive one active change and normalize the CLI's JSON result."""
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}", name):
            raise RefusedError("Unsafe OpenSpec change name")
        source = inside(self.root, f"openspec/changes/{name}")
        if not source.is_dir():
            raise RefusedError("Expected an active OpenSpec change directory")
        for entry in source.rglob("*"):
            inside(self.root, str(entry.relative_to(self.root)))
        promoted = [
            f"openspec/specs/{p.parent.name}/spec.md"
            for p in sorted(source.glob("specs/*/spec.md"))
        ]
        for relative in promoted:
            inside(self.root, relative)
            if run_git(
                self.root, "status", "--porcelain", "--", relative, environ=self.environ
            ).stdout.strip():
                raise RefusedError(
                    f"Promoted specification is dirty: {relative}; commit or preserve it before archiving"
                )
        try:
            result = subprocess.run(
                ["openspec", "archive", name, "--yes", "--json"],
                cwd=self.root,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
                env=self.environ,
            )
            if result.returncode:
                raise ValueError(result.stderr.strip() or result.stdout.strip())
            archive = json.loads(result.stdout)["archive"]
            if archive.get("change") != name or not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}-" + re.escape(name), archive.get("archivedAs", "")
            ):
                raise ValueError("Archive result does not identify the selected change")
            relative = f"openspec/changes/archive/{archive['archivedAs']}"
            target = inside(self.root, relative)
            reported = Path(archive["path"])
            if not reported.is_absolute():
                reported = self.root / reported
            if reported.resolve() != target.resolve() or source.exists():
                raise ValueError("Archive result path does not match the moved change")
            if not all((target / filename).is_file() for filename in ("proposal.md", "tasks.md")):
                raise ValueError("Archive is missing proposal or tasks")
            for entry in target.rglob("*"):
                inside(self.root, str(entry.relative_to(self.root)))
            if type(archive.get("specsUpdated")) is not bool:
                raise ValueError("Archive did not report specification promotion")
            promoted = promoted if archive["specsUpdated"] else []
            if not all(inside(self.root, path).is_file() for path in promoted):
                raise ValueError("Promoted specification is absent")
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            raise UncertainError(
                "OpenSpec archive failed or returned unverifiable output; inspect the active change, archive and promoted specifications before retrying: "
                + str(exc)
            ) from exc
        return {"archive": relative, "promoted_specs": promoted}

    def current(self, work, revision=None):
        if revision is not None:
            current = run_git(
                self.root,
                "rev-parse",
                "HEAD",
                environ=self.environ,
                context="OpenSpec checkout revision is unavailable",
            ).stdout.strip()
            if not revision:
                raise ValueError(
                    "OpenSpec merged revision is unknown; authenticate the merged pull request "
                    "before requiring current specification evidence"
                )
            if current != revision:
                raise ValueError(
                    f"OpenSpec checkout revision must equal the merged revision {revision}, but "
                    f"this checkout holds {current}. Prepare a temporary detached checkout at the "
                    "merged revision, run finish from it, then remove it: "
                    f"git worktree add --detach <path> {revision}"
                )
            status = run_git(
                self.root,
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                "openspec",
                environ=self.environ,
                check=False,
            )
            if status.returncode:
                raise ValueError(
                    "OpenSpec tree status is unavailable: "
                    + (status.stderr.strip() or "git status failed")
                )
            if status.stdout.strip():
                raise ValueError(
                    "OpenSpec files are dirty or untracked at the merged revision "
                    f"{revision}; finish from a clean checkout of that revision"
                )
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
                "Required specification must reference the archived change for this work. "
                f"Run `ai-dlc work archive {work['id']}` on the delivery branch and merge again, "
                "or archive in a follow-up pull request and link it with "
                f"`work link {work['id']} pr <url>`."
            )
        if not (path / "proposal.md").is_file() or not (path / "tasks.md").is_file():
            raise ValueError("OpenSpec archive is missing proposal or tasks")
        if revision is not None:
            tracked = run_git(
                self.root,
                "ls-files",
                "--error-unmatch",
                "--",
                str((path / "proposal.md").relative_to(self.root)),
                str((path / "tasks.md").relative_to(self.root)),
                environ=self.environ,
                check=False,
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
