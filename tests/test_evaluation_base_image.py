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
MISE = b"mise-binary"
MISE_DECLARATION = {
    "version": "2026.9.1",
    "sha256": {
        "linux-x64": "c98423c8470d6dc416d9f7036d0646d8ef5ae92ad9186907f8fcc84cbe7db4ea",
        "linux-arm64": "0ef0a778eaa8599f3e90a8a0979c9fc3f79922cafb5fa6d39f366d974da33bba",
    },
}


def image_module():
    from ai_dlc.verification.evaluation import image

    return image


class FakeTools:
    def __init__(self, recipe):
        self.calls, self.dockerfiles, self.fetched, self.recipe = [], [], [], recipe
        self.layers = {recipe["from"]: ["l1"], BUILT: ["l1", "l2", "l3"]}
        self.arch = "amd64"
        self.client_version = recipe["client"]["version"]
        self.mise_version = recipe.get("mise", {}).get("version")

    def __call__(self, args, *, cwd=None, timeout=None):
        del cwd, timeout
        self.calls.append(list(args))
        done = lambda out="", code=0: SimpleNamespace(returncode=code, stdout=out, stderr="boom")
        if args[:2] == ["docker", "version"]:
            return done(self.arch + "\n")
        if args[:2] == ["docker", "build"]:
            context = Path(args[-1])
            expected = ["Dockerfile", "claude"] + (["mise"] if "mise" in self.recipe else [])
            assert sorted(p.name for p in context.iterdir()) == sorted(expected)
            assert (context / "claude").read_bytes() == CLIENT
            assert (context / "claude").stat().st_mode & 0o777 == 0o755
            if "mise" in self.recipe:
                assert (context / "mise").read_bytes() == MISE
                assert (context / "mise").stat().st_mode & 0o777 == 0o755
            self.dockerfiles.append((context / "Dockerfile").read_text())
            return done(BUILT + "\n")
        if args[:3] == ["docker", "image", "inspect"]:
            return done(json.dumps(self.layers[args[-1]]))
        if args[:2] == ["docker", "run"]:
            if args[-2:] == ["git", "--version"]:
                return done("git version 2.39.5\n")
            if args[-2:] == ["mise", "--version"]:
                return done(f"{self.mise_version} linux-x64 (fixture)\n")
            return done(f"{self.client_version} (Claude Code)\n")
        return done()


@pytest.fixture
def shipped():
    return json.loads(RECIPE.read_text())


@pytest.fixture
def recipe(shipped):
    """The shipped recipe with digests of the stand-in executable bytes."""
    client_digest = hashlib.sha256(CLIENT).hexdigest()
    mise_digest = hashlib.sha256(MISE).hexdigest()
    client = dict(
        shipped["client"], sha256={"linux-x64": client_digest, "linux-arm64": client_digest}
    )
    mise = dict(MISE_DECLARATION, sha256={"linux-x64": mise_digest, "linux-arm64": mise_digest})
    return dict(shipped, client=client, mise=mise)


@pytest.fixture
def tools(monkeypatch, recipe):
    fake = FakeTools(recipe)
    monkeypatch.setattr(image_module(), "_run", fake)

    def fetch(url):
        fake.fetched.append(url)
        return MISE if "github.com/jdx/mise/" in url else CLIENT

    monkeypatch.setattr(image_module(), "_fetch", fetch)
    return fake


def test_the_controller_fetches_the_pinned_client_for_the_daemon_architecture(tools, recipe):
    built = image_module().build_base(recipe)
    dockerfile = tools.dockerfiles[0]
    version = recipe["client"]["version"]
    assert dockerfile.startswith(f"FROM {recipe['from']}\n")
    assert "git" in dockerfile and "COPY claude /usr/local/bin/claude" in dockerfile
    assert "COPY mise /usr/local/bin/mise" in dockerfile
    assert "ADD" not in dockerfile and "curl" not in dockerfile  # the build downloads no client
    mise_version = recipe["mise"]["version"]
    assert tools.fetched == [
        f"{image_module().RELEASES}/{version}/linux-x64/claude",
        f"{image_module().MISE_RELEASES}/v{mise_version}/mise-v{mise_version}-linux-x64",
    ]
    assert built == {
        "image": BUILT,
        "from": recipe["from"],
        "client": {"kind": "claude-code", "version": version, "platform": "linux-x64"},
        "mise": {"version": mise_version, "platform": "linux-x64"},
        "git": "git version 2.39.5",
    }
    tools.arch = "arm64"
    image_module().build_base(recipe)
    assert tools.fetched[2].endswith(f"/{version}/linux-arm64/claude")
    assert tools.fetched[3].endswith(f"/mise-v{mise_version}-linux-arm64")


def test_downloaded_bytes_that_do_not_match_either_recipe_digest_are_refused_before_build(
    tools, shipped, recipe
):
    with pytest.raises(RuntimeError, match="sha256"):
        image_module().build_base(shipped)  # real digests, stand-in bytes
    mismatched_mise = dict(recipe, mise=dict(recipe["mise"], sha256=shipped["mise"]["sha256"]))
    with pytest.raises(RuntimeError, match="mise.*sha256"):
        image_module().build_base(mismatched_mise)
    assert not [c for c in tools.calls if c[:2] == ["docker", "build"]]


def test_shipped_recipe_is_valid_and_names_both_linux_platforms(shipped):
    from ai_dlc.verification.evaluation.contracts import BaseImage

    declared = BaseImage.model_validate(shipped)
    assert set(declared.client.sha256) == {"linux-x64", "linux-arm64"}
    assert declared.mise is not None
    assert set(declared.mise.sha256) == {"linux-x64", "linux-arm64"}
    assert "git" in declared.packages


def test_schema_one_recipe_without_mise_remains_compatible(tools, recipe):
    legacy = dict(recipe)
    legacy.pop("mise")
    tools.recipe = legacy
    tools.mise_version = None

    from ai_dlc.verification.evaluation.contracts import BaseImage

    assert BaseImage.model_validate(legacy).mise is None
    built = image_module().build_base(legacy)
    assert "mise" not in built
    assert "COPY mise" not in tools.dockerfiles[0]
    assert all("mise" not in url for url in tools.fetched)


def test_mise_contract_is_strict_and_matches_the_bootstrap_linux_pins(shipped):
    from pydantic import ValidationError

    from ai_dlc.verification.evaluation.contracts import BaseImage

    declared = BaseImage.model_validate(dict(shipped, mise=MISE_DECLARATION))
    assert declared.mise is not None
    assert declared.mise.version == "2026.9.1"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        BaseImage.model_validate(
            dict(shipped, mise=dict(MISE_DECLARATION, unexpected="not accepted"))
        )

    pins = (ROOT / "bootstrap/versions.sh").read_text()
    assert f"AI_DLC_MISE_VERSION={MISE_DECLARATION['version']}" in pins
    assert f"AI_DLC_MISE_SHA256={MISE_DECLARATION['sha256']['linux-x64']}" in pins
    assert f"AI_DLC_MISE_SHA256={MISE_DECLARATION['sha256']['linux-arm64']}" in pins


def test_tools_are_checked_offline_as_the_agent_user(tools, recipe):
    image_module().build_base(recipe)
    checks = [c for c in tools.calls if c[:2] == ["docker", "run"]]
    assert [c[-2:] for c in checks] == [
        ["git", "--version"],
        ["claude", "--version"],
        ["mise", "--version"],
    ]
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


def test_missing_mise_architecture_is_refused_before_fetch_or_build(tools, recipe):
    recipe["mise"]["sha256"].pop("linux-x64")

    with pytest.raises(ValueError, match="mise sha256.*amd64"):
        image_module().build_base(recipe)

    assert tools.fetched == []
    assert not [call for call in tools.calls if call[:2] == ["docker", "build"]]


def test_wrong_offline_mise_version_is_refused(tools, recipe):
    tools.mise_version = "2099.1.0"

    with pytest.raises(RuntimeError, match="2099.1.0"):
        image_module().build_base(recipe)

    check = next(call for call in tools.calls if call[-2:] == ["mise", "--version"])
    assert "--network=none" in check and "--user=1000:1000" in check


real_build = pytest.mark.skipif(
    os.environ.get("AI_DLC_EVAL_BUILD") != "1" or not shutil.which("docker"),
    reason="set AI_DLC_EVAL_BUILD=1 with Docker and network to build the real base image",
)


@real_build
def test_real_base_image_has_git_the_pinned_client_and_mise(shipped):
    built = image_module().build_base(shipped)
    try:
        assert built["client"]["version"] == shipped["client"]["version"]
        assert built["mise"]["version"] == shipped["mise"]["version"]
        assert built["git"].startswith("git version")
    finally:
        subprocess.run(["docker", "rmi", "-f", built["image"]], capture_output=True, check=False)
