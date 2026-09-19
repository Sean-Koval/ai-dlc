"""The candidate image is the baseline image plus a hash-verified engine, never the checkout."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = "python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de"
BUILT = "sha256:" + "e" * 64


def image_module():
    from ai_dlc.verification.evaluation import image

    return image


class FakeTools:
    """Replaces only the uv and docker process boundary."""

    def __init__(self):
        self.calls = []
        self.contexts = []
        self.layers = {BASE: ["l1", "l2"], BUILT: ["l1", "l2", "l3"]}
        self.version_exit = 0

    def __call__(self, args, *, cwd=None, timeout=None):
        del timeout
        self.calls.append(list(args))
        done = lambda out="", code=0: SimpleNamespace(returncode=code, stdout=out, stderr="boom")
        if args[:2] == ["uv", "build"]:
            out = Path(args[args.index("--out-dir") + 1])
            (out / "ai_dlc-9.9.9-py3-none-any.whl").write_bytes(b"wheel-bytes")
        elif args[:2] == ["uv", "export"]:
            Path(args[args.index("--output-file") + 1]).write_text("typer==1.0 --hash=sha256:abc\n")
        elif args[:2] == ["docker", "build"]:
            context = Path(args[-1])
            self.contexts.append(
                {p.name: p.read_text(errors="replace") for p in context.iterdir() if p.is_file()}
            )
            return done(BUILT + "\n")
        elif args[:3] == ["docker", "image", "inspect"]:
            return done(json.dumps(self.layers[args[-1]]))
        elif args[:2] == ["docker", "run"]:
            return done("ai-dlc 9.9.9\n", self.version_exit)
        return done()


@pytest.fixture
def tools(monkeypatch):
    fake = FakeTools()
    monkeypatch.setattr(image_module(), "_run", fake)
    return fake


def test_recipe_installs_hash_pinned_dependencies_then_the_wheel_without_the_checkout(tools):
    result = image_module().build_candidate(ROOT, BASE)
    verbs = [" ".join(call[:2]) for call in tools.calls]
    assert verbs == [
        "uv build",
        "uv export",
        "docker build",
        "docker image",
        "docker image",
        "docker run",
    ]
    context = tools.contexts[0]
    assert set(context) == {"Dockerfile", "requirements.txt", "ai_dlc-9.9.9-py3-none-any.whl"}
    dockerfile = context["Dockerfile"]
    assert dockerfile.startswith(f"FROM {BASE}\n")
    assert "--require-hashes" in dockerfile and "--no-deps" in dockerfile
    assert "COPY . " not in dockerfile and str(ROOT) not in dockerfile
    export = next(call for call in tools.calls if call[:2] == ["uv", "export"])
    assert {"--locked", "--no-dev", "--no-emit-project"} <= set(export)
    assert result == {
        "base": BASE,
        "image": BUILT,
        "engine": {
            "artifact": "ai_dlc-9.9.9-py3-none-any.whl",
            "sha256": hashlib.sha256(b"wheel-bytes").hexdigest(),
            "image": BUILT,
        },
        "version": "ai-dlc 9.9.9",
    }


def test_smoke_check_runs_without_network_and_a_broken_engine_is_refused(tools):
    image_module().build_candidate(ROOT, BASE)
    smoke = next(call for call in tools.calls if call[:2] == ["docker", "run"])
    assert "--network=none" in smoke and smoke[-2:] == ["ai-dlc", "--version"]
    tools.version_exit = 1
    with pytest.raises(RuntimeError, match="does not run"):
        image_module().build_candidate(ROOT, BASE)


def test_unpinned_base_and_underived_result_are_refused(tools):
    with pytest.raises(ValueError, match="digest"):
        image_module().build_candidate(ROOT, "python:3.12-slim")
    assert tools.calls == []
    tools.layers[BUILT] = ["other"]
    with pytest.raises(RuntimeError, match="derived"):
        image_module().build_candidate(ROOT, BASE)


def test_resolved_profile_plans(tools, tmp_path):
    from ai_dlc.verification.evaluation.planning import plan

    built = image_module().build_candidate(ROOT, BASE)
    profile = json.loads((ROOT / "evaluations/profiles/local-deterministic.json").read_text())
    resolved = image_module().resolve_profile(profile, built)
    assert resolved["image"] == BASE and resolved["engine"] == built["engine"]
    suite = json.loads((ROOT / "evaluations/suites/smoke.json").read_text())
    assert plan(suite, resolved)["attempts"][0]["image"] == BUILT


# --- Real build. Needs Docker, the pinned image, uv and a package index; opt in. ---

real = pytest.mark.skipif(
    os.environ.get("AI_DLC_EVAL_BUILD") != "1"
    or not shutil.which("docker")
    or not shutil.which("uv"),
    reason="set AI_DLC_EVAL_BUILD=1 with Docker, uv and network to build a real candidate image",
)


@real
def test_real_candidate_image_contains_the_engine_and_the_baseline_does_not():
    built = image_module().build_candidate(ROOT, BASE)
    try:
        assert built["version"].startswith("ai-dlc")
        absent = subprocess.run(
            ["docker", "run", "--rm", "--network=none", BASE, "sh", "-c", "command -v ai-dlc"],
            capture_output=True, check=False, timeout=120,
        )  # fmt: skip
        assert absent.returncode != 0
    finally:
        subprocess.run(["docker", "rmi", "-f", built["image"]], capture_output=True, check=False)
