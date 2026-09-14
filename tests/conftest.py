import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
import tomli_w
from fixtures.git import git
from fixtures.tracker import Tickets

from ai_dlc.providers import Registry


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
        git(self.repository, "add", "--", self.profile_file, environment=self.environment)
        git(self.repository, "commit", "-m", message, environment=self.environment)
        return git(self.repository, "rev-parse", "HEAD", environment=self.environment)


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
        git(repository, "init", "-b", "main", environment=environment)
        git(repository, "config", "user.name", "AI-DLC Test", environment=environment)
        git(repository, "config", "user.email", "ai-dlc@example.test", environment=environment)
        source = f"ssh://git@example.test/portable-profile-{counter}.git"
        git(
            repository,
            "config",
            "--global",
            f"url.{repository.as_uri()}.insteadOf",
            source,
            environment=environment,
        )
        path = repository / profile_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(manifest)
        git(repository, "add", "--", profile_file, environment=environment)
        git(repository, "commit", "-m", "add profile", environment=environment)
        return LocalGitProfile(
            repository=repository,
            source=source,
            profile_file=profile_file,
            commit=git(repository, "rev-parse", "HEAD", environment=environment),
            environment=environment,
        )

    return create


@pytest.fixture
def checkout(tmp_path):
    """Authored project with three work records and a registered destination tracker."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "ai-dlc.toml").write_text(
        '# authored project\nschema = 4\n[roles]\ntracker = "old" # retain alias\n'
        'specs = "openspec"\nscm = "github"\n[providers.old]\nkind = "linear"\n'
        'team_id = "old-team"\n[providers.destination]\nkind = "fixture-plane"\n'
        '[scm]\nrepository = "org/repo"\n[gates]\nfinish = ["pr-merged", "ci-green"]\n'
    )
    directory = root / ".ai-dlc/work"
    directory.mkdir(parents=True)
    for work_id, providers in [
        ("one", {}),
        ("two", {"tracker": "old"}),
        ("spec", {"specs": "openspec"}),
    ]:
        work = {
            "schema": 1,
            "id": work_id,
            "title": work_id,
            "scope": "scope",
            "requires_spec": False,
            "spec_reason": "fixture",
            "acceptance": ["verified"],
            "reviewed": True,
            "providers": providers,
            "artifacts": {"tracker": f"OLD-{work_id}", "pr": "pull/7", "spec": "change"},
        }
        (directory / f"{work_id}.toml").write_text("# work comment\n" + tomli_w.dumps(work))
    env = {
        key: str(tmp_path / key) for key in ["XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"]
    }
    registry = Registry()
    adapter = Tickets()
    registry.register("destination", adapter)
    return root, env, registry, adapter


@dataclass(frozen=True)
class BuiltDistributions:
    wheel: Path
    source_distribution: Path


@pytest.fixture(scope="session")
def built_distributions(tmp_path_factory) -> BuiltDistributions:
    """Build the wheel and sdist once per session for every packaging assertion."""
    out = tmp_path_factory.mktemp("dist")
    subprocess.run(
        ["uv", "build", "--out-dir", str(out)],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "UV_OFFLINE": "1"},
    )
    return BuiltDistributions(
        wheel=next(out.glob("ai_dlc-*.whl")),
        source_distribution=next(out.glob("ai_dlc-*.tar.gz")),
    )
