"""Both arms share one base image: a pinned Python, Git and a checksum-pinned client."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "evaluations/images/claude-code.json"
BUILT = "sha256:" + "b" * 64
CLIENT = b"client-binary"


def image_module():
    from ai_dlc.verification.evaluation import image

    return image


class FakeTools:
    def __init__(self, recipe):
        self.calls, self.dockerfiles, self.recipe = [], [], recipe
        self.layers = {recipe["from"]: ["l1"], BUILT: ["l1", "l2", "l3"]}
        self.arch = "amd64"
        self.client_version = recipe["client"]["version"]

    def __call__(self, args, *, cwd=None, timeout=None):
        del cwd, timeout
        self.calls.append(list(args))
        done = lambda out="", code=0: SimpleNamespace(returncode=code, stdout=out, stderr="boom")
        if args[:2] == ["docker", "version"]:
            return done(self.arch + "\n")
        if args[:2] == ["docker", "build"]:
            context = Path(args[-1])
            assert sorted(p.name for p in context.iterdir()) == ["Dockerfile", "claude"]
            assert (context / "claude").read_bytes() == CLIENT
            assert (context / "claude").stat().st_mode & 0o777 == 0o755
            self.dockerfiles.append((context / "Dockerfile").read_text())
            return done(BUILT + "\n")
        if args[:3] == ["docker", "image", "inspect"]:
            return done(json.dumps(self.layers[args[-1]]))
        if args[:2] == ["docker", "run"]:
            if args[-2:] == ["git", "--version"]:
                return done("git version 2.39.5\n")
            return done(f"{self.client_version} (Claude Code)\n")
        return done()


@pytest.fixture
def shipped():
    return json.loads(RECIPE.read_text())


@pytest.fixture
def recipe(shipped):
    """The shipped recipe with digests of the stand-in client bytes."""
    digest = hashlib.sha256(CLIENT).hexdigest()
    client = dict(shipped["client"], sha256={"linux-x64": digest, "linux-arm64": digest})
    return dict(shipped, client=client)


@pytest.fixture
def tools(monkeypatch, recipe):
    fake = FakeTools(recipe)
    fake.fetched = []
    monkeypatch.setattr(image_module(), "_run", fake)
    monkeypatch.setattr(image_module(), "_fetch", lambda url: fake.fetched.append(url) or CLIENT)
    return fake


def test_the_controller_fetches_the_pinned_client_for_the_daemon_architecture(tools, recipe):
    built = image_module().build_base(recipe)
    dockerfile = tools.dockerfiles[0]
    version = recipe["client"]["version"]
    assert dockerfile.startswith(f"FROM {recipe['from']}\n")
    assert "git" in dockerfile and "COPY claude /usr/local/bin/claude" in dockerfile
    assert "ADD" not in dockerfile and "curl" not in dockerfile  # the build downloads no client
    assert tools.fetched == [f"{image_module().RELEASES}/{version}/linux-x64/claude"]
    assert built == {
        "image": BUILT,
        "from": recipe["from"],
        "client": {"kind": "claude-code", "version": version, "platform": "linux-x64"},
        "git": "git version 2.39.5",
    }
    tools.arch = "arm64"
    image_module().build_base(recipe)
    assert tools.fetched[1].endswith(f"/{version}/linux-arm64/claude")


def test_client_bytes_that_do_not_match_the_recipe_are_refused_before_any_build(tools, shipped):
    with pytest.raises(RuntimeError, match="sha256"):
        image_module().build_base(shipped)  # real digests, stand-in bytes
    assert not [c for c in tools.calls if c[:2] == ["docker", "build"]]


def test_shipped_recipe_is_valid_and_names_both_linux_platforms(shipped):
    from ai_dlc.verification.evaluation.contracts import BaseImage

    declared = BaseImage.model_validate(shipped)
    assert set(declared.client.sha256) == {"linux-x64", "linux-arm64"}
    assert "git" in declared.packages


def test_tools_are_checked_offline_as_the_agent_user(tools, recipe):
    image_module().build_base(recipe)
    checks = [c for c in tools.calls if c[:2] == ["docker", "run"]]
    assert [c[-2:] for c in checks] == [["git", "--version"], ["claude", "--version"]]
    for check in checks:
        assert "--network=none" in check and "--user=1000:1000" in check


def test_wrong_client_version_unknown_architecture_and_unpinned_parent_are_refused(tools, recipe):
    tools.client_version = "9.9.9"
    with pytest.raises(RuntimeError, match="9.9.9"):
        image_module().build_base(recipe)
    tools.arch = "riscv64"
    with pytest.raises(ValueError, match="riscv64"):
        image_module().build_base(recipe)
    tools.calls.clear()
    with pytest.raises(ValueError, match="from"):
        image_module().build_base(dict(recipe, **{"from": "python:3.12-slim"}))
    with pytest.raises(ValueError, match="sha256"):
        image_module().build_base(dict(recipe, client=dict(recipe["client"], sha256={})))
    assert tools.calls == []


real_build = pytest.mark.skipif(
    os.environ.get("AI_DLC_EVAL_BUILD") != "1" or not shutil.which("docker"),
    reason="set AI_DLC_EVAL_BUILD=1 with Docker and network to build the real base image",
)


@real_build
def test_real_base_image_has_git_and_the_pinned_client(recipe):
    built = image_module().build_base(recipe)
    try:
        assert built["client"]["version"] == recipe["client"]["version"]
        assert built["git"].startswith("git version")
    finally:
        subprocess.run(["docker", "rmi", "-f", built["image"]], capture_output=True, check=False)
