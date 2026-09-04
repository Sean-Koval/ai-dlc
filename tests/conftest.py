import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))


@dataclass(frozen=True)
class LocalGitProfile:
    repository: Path
    source: str
    profile_file: str
    commit: str
    environment: dict[str, str]

    def advance(self, manifest: str, *, message: str = "advance profile") -> str:
        path = self.repository / self.profile_file
        path.write_text(manifest)
        _git(self.repository, self.environment, "add", "--", self.profile_file)
        _git(self.repository, self.environment, "commit", "-m", message)
        return _git(self.repository, self.environment, "rev-parse", "HEAD")


def _git(repository: Path, environment: dict[str, str], *arguments: str) -> str:
    git = shutil.which("git", path=environment["PATH"])
    assert git is not None
    result = subprocess.run(
        [git, "-C", str(repository), *arguments],
        capture_output=True,
        check=True,
        env=environment,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


@pytest.fixture
def local_git_profile(tmp_path: Path) -> Callable[..., LocalGitProfile]:
    """Create isolated local Git profile sources with explicit paths and commits."""
    counter = 0

    def create(manifest: str, *, profile_file: str = "ai-dlc-profile.toml") -> LocalGitProfile:
        nonlocal counter
        counter += 1
        root = tmp_path / f"local-git-profile-{counter}"
        repository = root / "repository"
        git_home = root / "git-home"
        git_config = root / "gitconfig"
        repository.mkdir(parents=True)
        git_home.mkdir()
        real_git = shutil.which("git")
        assert real_git is not None
        environment = {
            "PATH": str(Path(real_git).parent),
            "HOME": str(git_home),
            "XDG_CONFIG_HOME": str(root / "xdg-config"),
            "XDG_CACHE_HOME": str(root / "xdg-cache"),
            "XDG_STATE_HOME": str(root / "xdg-state"),
            "GIT_CONFIG_GLOBAL": str(git_config),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/usr/bin/false",
            "SSH_ASKPASS": "/usr/bin/false",
            "LC_ALL": "C",
        }
        _git(repository, environment, "init", "-b", "main")
        _git(repository, environment, "config", "user.name", "AI-DLC Test")
        _git(repository, environment, "config", "user.email", "ai-dlc@example.test")
        source = f"ssh://git@example.test/portable-profile-{counter}.git"
        _git(
            repository,
            environment,
            "config",
            "--global",
            f"url.{repository.as_uri()}.insteadOf",
            source,
        )
        path = repository / profile_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(manifest)
        _git(repository, environment, "add", "--", profile_file)
        _git(repository, environment, "commit", "-m", "add profile")
        return LocalGitProfile(
            repository=repository,
            source=source,
            profile_file=profile_file,
            commit=_git(repository, environment, "rev-parse", "HEAD"),
            environment=environment,
        )

    return create
